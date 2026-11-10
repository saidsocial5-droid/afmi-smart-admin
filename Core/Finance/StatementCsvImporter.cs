using System.Globalization;
using System.Text;
using AFMI_Gestion_projet.Data;
using AFMI_Gestion_projet.Models.Finance;

namespace AFMI_Gestion_projet.Finance
{
    public sealed record ParsedStatementLine(DateOnly OperationDate, DateOnly? ValueDate, string Label, string Reference, long DebitMinor, long CreditMinor);

    public sealed record ParsedStatement(IReadOnlyList<ParsedStatementLine> Lines, IReadOnlyList<string> Errors)
    {
        public long NetMovementMinor => Lines.Sum(l => l.CreditMinor - l.DebitMinor);
    }

    /// <summary>
    /// Import d'un relevé exporté par la banque en CSV (séparateur ; , ou tabulation, détecté).
    /// Colonnes reconnues par leur en-tête : date (opération), date de valeur, libellé, référence,
    /// débit et crédit, ou un montant unique signé. Formats de date et de nombre français ou ISO.
    /// </summary>
    public static class StatementCsvImporter
    {
        private static readonly string[] DateFormats = { "dd/MM/yyyy", "d/M/yyyy", "dd-MM-yyyy", "dd.MM.yyyy", "yyyy-MM-dd", "dd/MM/yy" };

        public static ParsedStatement Parse(string content)
        {
            var errors = new List<string>();
            var lines = new List<ParsedStatementLine>();
            var rows = content.Replace("\r\n", "\n").Split('\n').Where(r => r.Trim().Length > 0).ToList();
            if (rows.Count < 2) return new ParsedStatement(lines, new[] { "Fichier vide ou sans ligne de données." });

            char sep = new[] { ';', '\t', ',' }.OrderByDescending(c => rows[0].Count(ch => ch == c)).First();
            var header = SplitRow(rows[0], sep).Select(Normalize).ToList();
            int Col(params string[] names) => header.FindIndex(h => names.Any(n => h == n || h.StartsWith(n + " ")));
            int date = Col("date operation", "date op", "date"), valueDate = Col("date valeur", "date de valeur", "valeur");
            if (valueDate == date) valueDate = header.FindIndex(h => h.Contains("valeur"));
            int label = Col("libelle", "libelle operation", "description", "designation", "operation");
            int reference = Col("reference", "ref", "n piece", "numero");
            int debit = Col("debit", "debit mad"), credit = Col("credit", "credit mad"), amount = Col("montant", "amount");
            if (date < 0 || label < 0 || (amount < 0 && (debit < 0 || credit < 0)))
                return new ParsedStatement(lines, new[] { "En-têtes non reconnus : il faut au moins Date, Libellé et Débit/Crédit (ou Montant)." });

            for (int i = 1; i < rows.Count; i++)
            {
                var cells = SplitRow(rows[i], sep);
                string Cell(int idx) => idx >= 0 && idx < cells.Count ? cells[idx].Trim() : string.Empty;
                if (!TryDate(Cell(date), out var opDate)) { errors.Add($"Ligne {i + 1} : date illisible « {Cell(date)} »."); continue; }
                DateOnly? vDate = TryDate(Cell(valueDate), out var v) ? v : null;
                long debitMinor, creditMinor;
                if (amount >= 0 && (debit < 0 || credit < 0))
                {
                    if (!TryAmount(Cell(amount), out long signed)) { errors.Add($"Ligne {i + 1} : montant illisible."); continue; }
                    (debitMinor, creditMinor) = signed < 0 ? (-signed, 0L) : (0L, signed);
                }
                else
                {
                    bool okD = TryAmount(Cell(debit), out debitMinor, allowEmpty: true);
                    bool okC = TryAmount(Cell(credit), out creditMinor, allowEmpty: true);
                    if (!okD || !okC) { errors.Add($"Ligne {i + 1} : montant illisible."); continue; }
                    debitMinor = Math.Abs(debitMinor);
                    creditMinor = Math.Abs(creditMinor);
                }
                if (debitMinor == 0 && creditMinor == 0) continue; // ligne de solde ou de report
                if (debitMinor > 0 && creditMinor > 0) { errors.Add($"Ligne {i + 1} : débit et crédit renseignés."); continue; }
                lines.Add(new ParsedStatementLine(opDate, vDate, Cell(label), Cell(reference), debitMinor, creditMinor));
            }
            return new ParsedStatement(lines, errors);
        }

        /// <summary>Crée le relevé (brouillon) et ses lignes. Les soldes viennent du relevé papier ou PDF de la banque.</summary>
        public static BankStatement Import(AppDbContext db, int accountId, ParsedStatement parsed, long openingMinor, long closingMinor,
            DateOnly? periodStart = null, DateOnly? periodEnd = null)
        {
            if (parsed.Lines.Count == 0) throw new FinanceRuleException("Aucune ligne à importer.");
            var statement = new BankStatement
            {
                BankAccountId = accountId,
                PeriodStart = periodStart ?? parsed.Lines.Min(l => l.OperationDate),
                PeriodEnd = periodEnd ?? parsed.Lines.Max(l => l.OperationDate),
                OpeningBalanceMinor = openingMinor,
                ClosingBalanceMinor = closingMinor,
                Source = StatementSource.Csv,
            };
            foreach (var l in parsed.Lines)
            {
                statement.Lines.Add(new StatementLine
                {
                    OperationDate = l.OperationDate, ValueDate = l.ValueDate, Label = l.Label, Reference = l.Reference,
                    DebitMinor = l.DebitMinor, CreditMinor = l.CreditMinor,
                });
            }
            db.BankStatements.Add(statement);
            db.SaveChanges();
            return statement;
        }

        internal static bool TryAmount(string text, out long minor, bool allowEmpty = false)
        {
            minor = 0;
            string s = text.Replace(" ", "").Replace(" ", "").Replace(" ", "").Replace("MAD", "", StringComparison.OrdinalIgnoreCase)
                .Replace("DH", "", StringComparison.OrdinalIgnoreCase).Trim();
            if (s.Length == 0) return allowEmpty;
            bool negative = s.StartsWith('-') || (s.StartsWith('(') && s.EndsWith(')'));
            s = s.Trim('-', '(', ')', '+');
            int lastComma = s.LastIndexOf(','), lastDot = s.LastIndexOf('.');
            if (lastComma >= 0 && lastDot >= 0)
                s = lastComma > lastDot ? s.Replace(".", "").Replace(',', '.') : s.Replace(",", "");
            else if (lastComma >= 0)
                s = s.Length - lastComma - 1 == 3 && s.Count(c => c == ',') > 1 ? s.Replace(",", "") : s.Replace(',', '.');
            if (!decimal.TryParse(s, NumberStyles.AllowDecimalPoint, CultureInfo.InvariantCulture, out var value)) return false;
            minor = Money.ToMinor(negative ? -value : value);
            return true;
        }

        internal static bool TryDate(string text, out DateOnly date) =>
            DateOnly.TryParseExact(text.Trim(), DateFormats, CultureInfo.InvariantCulture, DateTimeStyles.None, out date);

        private static string Normalize(string header)
        {
            var sb = new StringBuilder();
            foreach (char c in header.Trim().ToLowerInvariant().Normalize(NormalizationForm.FormD))
            {
                if (CharUnicodeInfo.GetUnicodeCategory(c) == UnicodeCategory.NonSpacingMark) continue;
                sb.Append(char.IsLetterOrDigit(c) ? c : ' ');
            }
            return string.Join(' ', sb.ToString().Split(' ', StringSplitOptions.RemoveEmptyEntries));
        }

        private static List<string> SplitRow(string row, char sep)
        {
            var cells = new List<string>();
            var sb = new StringBuilder();
            bool quoted = false;
            for (int i = 0; i < row.Length; i++)
            {
                char c = row[i];
                if (c == '"')
                {
                    if (quoted && i + 1 < row.Length && row[i + 1] == '"') { sb.Append('"'); i++; }
                    else quoted = !quoted;
                }
                else if (c == sep && !quoted) { cells.Add(sb.ToString()); sb.Clear(); }
                else sb.Append(c);
            }
            cells.Add(sb.ToString());
            return cells;
        }
    }
}
