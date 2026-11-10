namespace AFMI_Gestion_projet.Models.Finance
{
    // Toutes les énumérations sont stockées en texte (lisible par le backend Python et dans les exports).

    public enum AccountKind { Bank, Cash }

    /// <summary>Fonctionnement, dédié à un projet, dépôt (épargne, DAT), autre.</summary>
    public enum AccountPurpose { Operating, Project, Deposit, Other }

    public enum AccountStatus { Active, Closed }

    /// <summary>Clé de répartition d'une liaison compte ↔ projet.</summary>
    public enum AllocationMode { None, Percentage, FixedAmount }

    public enum FiscalYearStatus { Open, Closed }

    public enum LedgerAccountType { Expense, Income, BalanceSheet }

    public enum CategoryKind { Income, Expense }

    /// <summary>Sens du mouvement sur le compte : Debit = sortie, Credit = entrée.</summary>
    public enum OperationDirection { Debit, Credit }

    /// <summary>Un virement interne compte dans les soldes mais jamais dans les recettes ni les dépenses.</summary>
    public enum OperationNature { Income, Expense, InternalTransfer }

    public enum OperationStatus { Draft, Validated }

    public enum RuleMatchType { Contains, Regex }

    public enum RuleSource { Manual, Learned }
}
