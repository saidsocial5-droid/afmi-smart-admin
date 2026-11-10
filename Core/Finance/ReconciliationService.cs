using AFMI_Gestion_projet.Data;
using AFMI_Gestion_projet.Models.Finance;
using Microsoft.EntityFrameworkCore;

namespace AFMI_Gestion_projet.Finance
{
    public sealed record StatementCheck(bool BalanceOk, long ComputedClosingMinor, IReadOnlyList<string> Errors, IReadOnlyList<string> Warnings);

    public sealed record ReconciliationReport(
        BankStatement Statement,
        long BankClosingMinor,
        long BookBalanceMinor,
        IReadOnlyList<Operation> UnmatchedOperations,
        IReadOnlyList<StatementLine> UnmatchedLines)
    {
        /// <summary>Solde banque + opérations non encore passées en banque − mouvements bancaires non comptabilisés.</summary>
        public long AdjustedBankMinor => BankClosingMinor + UnmatchedOperations.Sum(o => o.SignedAmountMinor) - UnmatchedLines.Sum(l => l.SignedAmountMinor);

        /// <summary>Écart inexpliqué : 0 quand le rapprochement est complet.</summary>
        public long UnexplainedDifferenceMinor => BookBalanceMinor - AdjustedBankMinor;
    }

    /// <summary>
    /// Relevés et rapprochement bancaire. Une ligne de relevé est rapprochée d'au plus une opération (et inversement).
    /// Automatique : même compte, même montant signé, date à ± N jours ; le libellé départage. Un cas ambigu
    /// (deux candidats aussi probables) n'est jamais rapproché automatiquement.
    /// </summary>
    public sealed class ReconciliationService(AppDbContext db)
    {
        public const int DefaultToleranceDays = 3;

        public StatementCheck Check(int statementId)
        {
            var st = db.BankStatements.Include(s => s.Lines).Single(s => s.Id == statementId);
            var errors = new List<string>();
            var warnings = new List<string>();

            long computed = st.OpeningBalanceMinor + st.Lines.Sum(l => l.SignedAmountMinor);
            bool balanceOk = computed == st.ClosingBalanceMinor;
            if (!balanceOk)
                errors.Add($"Solde initial + mouvements = {Money.Format(computed)} ≠ solde final {Money.Format(st.ClosingBalanceMinor)}.");
            if (st.Lines.Any(l => l.OperationDate < st.PeriodStart || l.OperationDate > st.PeriodEnd))
                warnings.Add("Des lignes sont datées hors de la période du relevé.");

            var others = db.BankStatements.Where(s => s.BankAccountId == st.BankAccountId && s.Id != st.Id).ToList();
            if (others.Any(o => o.PeriodStart == st.PeriodStart && o.PeriodEnd == st.PeriodEnd && o.ClosingBalanceMinor == st.ClosingBalanceMinor))
                errors.Add("Ce relevé semble déjà importé (même période et même solde final).");
            else if (others.Any(o => o.PeriodStart <= st.PeriodEnd && o.PeriodEnd >= st.PeriodStart))
                warnings.Add("La période chevauche celle d'un autre relevé de ce compte.");

            var previous = others.Where(o => o.PeriodEnd < st.PeriodStart).OrderByDescending(o => o.PeriodEnd).FirstOrDefault();
            if (previous != null)
            {
                if (previous.ClosingBalanceMinor != st.OpeningBalanceMinor)
                    errors.Add($"Rupture de continuité : solde final du relevé précédent {Money.Format(previous.ClosingBalanceMinor)} ≠ solde initial {Money.Format(st.OpeningBalanceMinor)}.");
                if (previous.PeriodEnd.AddDays(1) < st.PeriodStart)
                    warnings.Add($"Relevé manquant entre le {previous.PeriodEnd:dd/MM/yyyy} et le {st.PeriodStart:dd/MM/yyyy}.");
            }
            return new StatementCheck(balanceOk, computed, errors, warnings);
        }

        /// <summary>Valide un relevé : ses contrôles bloquants doivent être levés.</summary>
        public void Validate(int statementId)
        {
            var check = Check(statementId);
            if (check.Errors.Count > 0) throw new FinanceRuleException(string.Join(" ", check.Errors));
            db.BankStatements.Single(s => s.Id == statementId).Status = StatementStatus.Validated;
            db.SaveChanges();
        }

        public int AutoMatch(int statementId, string user, int toleranceDays = DefaultToleranceDays)
        {
            var st = db.BankStatements.Single(s => s.Id == statementId);
            var lines = db.StatementLines.Where(l => l.BankStatementId == statementId && l.Match == null).ToList();
            if (lines.Count == 0) return 0;

            var from = lines.Min(l => l.OperationDate).AddDays(-toleranceDays);
            var to = lines.Max(l => l.OperationDate).AddDays(toleranceDays);
            var matchedOps = db.ReconciliationMatches.Select(m => m.OperationId);
            var ops = db.Operations
                .Where(o => o.BankAccountId == st.BankAccountId && o.Status == OperationStatus.Validated
                            && o.OperationDate >= from && o.OperationDate <= to && !matchedOps.Contains(o.Id))
                .ToList();

            var candidates = new List<(StatementLine Line, Operation Op, double Score)>();
            foreach (var line in lines)
            {
                foreach (var op in ops.Where(o => o.SignedAmountMinor == line.SignedAmountMinor))
                {
                    int days = Math.Abs(op.OperationDate.DayNumber - line.OperationDate.DayNumber);
                    if (days > toleranceDays) continue;
                    double dateScore = 1.0 - (double)days / (toleranceDays + 1);
                    double labelScore = LabelSimilarity(line.Label + " " + line.Reference, op.Label + " " + op.Reference + " " + op.ThirdParty);
                    candidates.Add((line, op, Math.Round(0.6 * dateScore + 0.4 * labelScore, 4)));
                }
            }

            int count = 0;
            var usedLines = new HashSet<int>();
            var usedOps = new HashSet<int>();
            foreach (var c in candidates.OrderByDescending(c => c.Score))
            {
                if (usedLines.Contains(c.Line.Id) || usedOps.Contains(c.Op.Id)) continue;
                bool ambiguous = candidates.Any(o => o != c && o.Score == c.Score
                    && ((o.Line.Id == c.Line.Id && !usedOps.Contains(o.Op.Id)) || (o.Op.Id == c.Op.Id && !usedLines.Contains(o.Line.Id))));
                if (ambiguous) continue;
                db.ReconciliationMatches.Add(new ReconciliationMatch
                {
                    StatementLineId = c.Line.Id, OperationId = c.Op.Id, Mode = MatchMode.Auto, Score = c.Score, MatchedBy = user,
                });
                usedLines.Add(c.Line.Id);
                usedOps.Add(c.Op.Id);
                count++;
            }
            db.SaveChanges();
            return count;
        }

        public void Match(int statementLineId, int operationId, string user)
        {
            var line = db.StatementLines.Include(l => l.BankStatement).Single(l => l.Id == statementLineId);
            var op = db.Operations.Single(o => o.Id == operationId);
            if (op.BankAccountId != line.BankStatement!.BankAccountId) throw new FinanceRuleException("L'opération n'est pas sur le compte du relevé.");
            if (op.Status != OperationStatus.Validated) throw new FinanceRuleException("Seule une opération validée peut être rapprochée.");
            if (op.SignedAmountMinor != line.SignedAmountMinor) throw new FinanceRuleException("Les montants diffèrent : corrigez l'opération ou la ligne avant de rapprocher.");
            if (db.ReconciliationMatches.Any(m => m.StatementLineId == statementLineId || m.OperationId == operationId))
                throw new FinanceRuleException("La ligne ou l'opération est déjà rapprochée.");
            db.ReconciliationMatches.Add(new ReconciliationMatch
            {
                StatementLineId = statementLineId, OperationId = operationId, Mode = MatchMode.Manual, Score = 1, MatchedBy = user,
            });
            db.SaveChanges();
        }

        public void Unmatch(int statementLineId)
        {
            var match = db.ReconciliationMatches.SingleOrDefault(m => m.StatementLineId == statementLineId);
            if (match == null) return;
            db.ReconciliationMatches.Remove(match);
            db.SaveChanges();
        }

        /// <summary>État de rapprochement à la date de fin du relevé.</summary>
        public ReconciliationReport GetReport(int statementId)
        {
            var st = db.BankStatements.Include(s => s.BankAccount).Single(s => s.Id == statementId);
            var statements = db.BankStatements.Where(s => s.BankAccountId == st.BankAccountId && s.PeriodEnd <= st.PeriodEnd).ToList();
            var firstStart = statements.Min(s => s.PeriodStart);
            var statementIds = statements.Select(s => s.Id).ToList();

            var unmatchedLines = db.StatementLines
                .Where(l => statementIds.Contains(l.BankStatementId) && l.Match == null)
                .OrderBy(l => l.OperationDate).ToList();
            var matchedOps = db.ReconciliationMatches.Select(m => m.OperationId);
            var unmatchedOps = db.Operations
                .Where(o => o.BankAccountId == st.BankAccountId && o.Status == OperationStatus.Validated
                            && o.OperationDate >= firstStart && o.OperationDate <= st.PeriodEnd && !matchedOps.Contains(o.Id))
                .OrderBy(o => o.OperationDate).ToList();

            long book = new FinanceService(db).GetBalanceMinor(st.BankAccountId, st.PeriodEnd);
            return new ReconciliationReport(st, st.ClosingBalanceMinor, book, unmatchedOps, unmatchedLines);
        }

        /// <summary>Similarité de libellés (mots communs / mots distincts), insensible aux accents et à la casse.</summary>
        public static double LabelSimilarity(string a, string b)
        {
            static HashSet<string> Tokens(string s) => s.Normalize(System.Text.NormalizationForm.FormD)
                .Where(c => System.Globalization.CharUnicodeInfo.GetUnicodeCategory(c) != System.Globalization.UnicodeCategory.NonSpacingMark)
                .Select(char.ToLowerInvariant).Aggregate(new System.Text.StringBuilder(), (sb, c) => sb.Append(char.IsLetterOrDigit(c) ? c : ' '))
                .ToString().Split(' ', StringSplitOptions.RemoveEmptyEntries).Where(t => t.Length > 2).ToHashSet();
            var ta = Tokens(a);
            var tb = Tokens(b);
            if (ta.Count == 0 || tb.Count == 0) return 0;
            return (double)ta.Intersect(tb).Count() / ta.Union(tb).Count();
        }
    }
}
