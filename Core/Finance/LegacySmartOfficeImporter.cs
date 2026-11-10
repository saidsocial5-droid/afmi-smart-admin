using System.Globalization;
using AFMI_Gestion_projet.Data;
using AFMI_Gestion_projet.Models;
using AFMI_Gestion_projet.Models.Finance;
using Microsoft.Data.Sqlite;

namespace AFMI_Gestion_projet.Finance
{
    public sealed record LegacyImportResult(int ProjectsCreated, int OperationsCreated, int Skipped, IReadOnlyList<string> Messages);

    /// <summary>
    /// Reprise des données de la base Smart Office 1.x (afmi_smartoffice.db) dans la base unique :
    /// - projets absents (même code) recréés ;
    /// - transactions reprises en **brouillons** sur le compte choisi par l'utilisateur, à ventiler puis valider.
    /// Une transaction déjà reprise (référence « SO-&lt;id&gt; ») n'est jamais dupliquée. La base source n'est pas modifiée.
    /// </summary>
    public sealed class LegacySmartOfficeImporter(AppDbContext db)
    {
        private static readonly string[] DateFormats = { "yyyy-MM-dd", "dd/MM/yyyy", "dd-MM-yyyy", "dd/MM/yy", "yyyy/MM/dd", "dd.MM.yyyy" };

        public LegacyImportResult Import(string smartOfficeDbPath, int targetAccountId)
        {
            if (!File.Exists(smartOfficeDbPath)) throw new FileNotFoundException("Base Smart Office introuvable.", smartOfficeDbPath);
            var account = db.BankAccounts.Single(a => a.Id == targetAccountId);
            var messages = new List<string>();
            int projects = 0, operations = 0, skipped = 0;

            using var source = new SqliteConnection(new SqliteConnectionStringBuilder
            {
                DataSource = smartOfficeDbPath, Mode = SqliteOpenMode.ReadOnly, Pooling = false,
            }.ToString());
            source.Open();

            var existingCodes = db.Projects.Select(p => p.Code).ToHashSet(StringComparer.OrdinalIgnoreCase);
            using (var cmd = source.CreateCommand())
            {
                cmd.CommandText = "SELECT code, title, total_budget, currency, start_date, end_date, status FROM projects";
                try
                {
                    using var r = cmd.ExecuteReader();
                    while (r.Read())
                    {
                        string code = r.GetString(0);
                        if (existingCodes.Contains(code)) continue;
                        db.Projects.Add(new Project
                        {
                            Code = code, Name = r.GetString(1), BudgetGlobal = r.IsDBNull(2) ? 0 : r.GetDouble(2),
                            Currency = r.IsDBNull(3) ? "MAD" : Money.NormalizeCurrency(r.GetString(3)),
                            TargetStartDate = ParseDate(r.IsDBNull(4) ? null : r.GetString(4))?.ToDateTime(TimeOnly.MinValue),
                            TargetEndDate = ParseDate(r.IsDBNull(5) ? null : r.GetString(5))?.ToDateTime(TimeOnly.MinValue),
                            Description = "Repris de Smart Office 1.x",
                        });
                        existingCodes.Add(code);
                        projects++;
                    }
                }
                catch (SqliteException) { messages.Add("Table « projects » absente : aucun projet repris."); }
            }
            db.SaveChanges();

            var imported = db.Operations.Where(o => o.Reference.StartsWith("SO-")).Select(o => o.Reference).ToHashSet();
            var finance = new FinanceService(db);
            using (var cmd = source.CreateCommand())
            {
                cmd.CommandText = "SELECT id, tx_date, label, reference, debit, credit, beneficiary_or_emitter FROM financial_transactions ORDER BY id";
                try
                {
                    using var r = cmd.ExecuteReader();
                    while (r.Read())
                    {
                        string key = $"SO-{r.GetInt64(0)}";
                        if (imported.Contains(key)) { skipped++; continue; }
                        var date = ParseDate(r.IsDBNull(1) ? null : r.GetString(1));
                        decimal debit = r.IsDBNull(4) ? 0 : (decimal)r.GetDouble(4), credit = r.IsDBNull(5) ? 0 : (decimal)r.GetDouble(5);
                        if (date == null || (debit == 0) == (credit == 0))
                        {
                            messages.Add($"Transaction {key} ignorée : date ou montant inexploitable.");
                            skipped++;
                            continue;
                        }
                        bool isCredit = credit > 0;
                        try
                        {
                            finance.AddDraft(new Operation
                            {
                                BankAccountId = account.Id, OperationDate = date.Value, Label = r.IsDBNull(2) ? "" : Truncate(r.GetString(2), 500),
                                Reference = key, ThirdParty = r.IsDBNull(6) ? "" : Truncate(r.GetString(6), 200),
                                Notes = r.IsDBNull(3) ? "Repris de Smart Office 1.x" : $"Repris de Smart Office 1.x (réf. {r.GetString(3)})",
                                Direction = isCredit ? OperationDirection.Credit : OperationDirection.Debit,
                                Nature = isCredit ? OperationNature.Income : OperationNature.Expense,
                                AmountMinor = Money.ToMinor(isCredit ? credit : debit), Currency = account.Currency,
                            });
                            operations++;
                        }
                        catch (OperationValidationException ex)
                        {
                            messages.Add($"Transaction {key} ignorée : {ex.Message}");
                            skipped++;
                        }
                    }
                }
                catch (SqliteException) { messages.Add("Table « financial_transactions » absente : aucune transaction reprise."); }
            }
            return new LegacyImportResult(projects, operations, skipped, messages);
        }

        private static DateOnly? ParseDate(string? text) =>
            !string.IsNullOrWhiteSpace(text) && DateOnly.TryParseExact(text.Trim()[..Math.Min(10, text.Trim().Length)], DateFormats,
                CultureInfo.InvariantCulture, DateTimeStyles.None, out var d) ? d : null;

        private static string Truncate(string s, int max) => s.Length <= max ? s : s[..max];
    }
}
