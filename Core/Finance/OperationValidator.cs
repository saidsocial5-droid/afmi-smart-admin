using AFMI_Gestion_projet.Models.Finance;

namespace AFMI_Gestion_projet.Finance
{
    public sealed record ValidationIssue(string Code, string Message);

    public sealed class OperationValidationException(IReadOnlyList<ValidationIssue> issues)
        : InvalidOperationException("Opération refusée : " + string.Join(" ; ", issues.Select(i => i.Message)))
    {
        public IReadOnlyList<ValidationIssue> Issues { get; } = issues;
    }

    /// <summary>Règles d'intégrité d'une opération. Un brouillon peut être incomplet ; une opération validée, jamais.</summary>
    public static class OperationValidator
    {
        public static IReadOnlyList<ValidationIssue> Validate(Operation op, BankAccount account,
            IReadOnlyDictionary<int, BudgetLine> budgetLines, bool forValidation)
        {
            var issues = new List<ValidationIssue>();
            void Add(string code, string message) => issues.Add(new ValidationIssue(code, message));

            if (op.AmountMinor <= 0) Add("AMOUNT", "Le montant doit être strictement positif (le sens est donné par Débit/Crédit).");
            if (op.Currency != account.Currency) Add("CURRENCY", $"La devise ({op.Currency}) doit être celle du compte ({account.Currency}).");
            if (op.OperationDate < account.OpeningDate) Add("BEFORE_OPENING", $"Date antérieure à l'ouverture du compte ({account.OpeningDate:dd/MM/yyyy}).");
            if (account.Status == AccountStatus.Closed && account.ClosedDate is { } closed && op.OperationDate > closed)
                Add("ACCOUNT_CLOSED", $"Compte clôturé le {closed:dd/MM/yyyy}.");
            if (account.IsDeleted) Add("ACCOUNT_DELETED", "Compte supprimé.");

            switch (op.Nature)
            {
                case OperationNature.Income when op.Direction != OperationDirection.Credit:
                    Add("NATURE_DIRECTION", "Une recette est un crédit sur le compte.");
                    break;
                case OperationNature.Expense when op.Direction != OperationDirection.Debit:
                    Add("NATURE_DIRECTION", "Une dépense est un débit sur le compte.");
                    break;
            }

            if (op.Nature == OperationNature.InternalTransfer)
            {
                if (op.TransferGroupId is null) Add("TRANSFER_GROUP", "Un virement interne doit être apparié (identifiant de virement manquant).");
                if (op.Allocations.Count > 0) Add("TRANSFER_ALLOCATION", "Un virement interne ne se ventile pas : ce n'est ni une recette ni une dépense.");
                return issues;
            }
            if (op.TransferGroupId is not null) Add("TRANSFER_GROUP", "Seul un virement interne porte un identifiant de virement.");

            long allocated = op.Allocations.Sum(a => a.AmountMinor);
            if (op.Allocations.Any(a => a.AmountMinor <= 0)) Add("ALLOCATION_AMOUNT", "Chaque ventilation doit avoir un montant positif.");

            if (forValidation)
            {
                if (op.Allocations.Count == 0) Add("NOT_ALLOCATED", "Opération non ventilée (projet ou fonctionnement, ligne budgétaire).");
                else if (allocated != op.AmountMinor)
                    Add("ALLOCATION_SUM", $"Ventilations ({Money.Format(allocated, op.Currency)}) ≠ montant ({Money.Format(op.AmountMinor, op.Currency)}).");

                foreach (var a in op.Allocations)
                {
                    if (a.BudgetLineId is not { } lineId) { Add("NO_BUDGET_LINE", "Chaque ventilation doit désigner une ligne budgétaire."); continue; }
                    if (!budgetLines.TryGetValue(lineId, out var line)) { Add("UNKNOWN_BUDGET_LINE", $"Ligne budgétaire {lineId} introuvable."); continue; }
                    if (line.ProjectId != a.ProjectId)
                        Add("BUDGET_LINE_PROJECT", $"La ligne « {line.Code} {line.Label} » n'appartient pas au projet de la ventilation.");
                }
            }
            else if (allocated > op.AmountMinor)
            {
                Add("ALLOCATION_SUM", "Les ventilations dépassent le montant de l'opération.");
            }

            return issues;
        }
    }
}
