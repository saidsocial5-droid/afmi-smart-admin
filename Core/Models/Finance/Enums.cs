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

    /// <summary>
    /// Un virement interne compte dans les soldes mais jamais dans les recettes ni les dépenses.
    /// Une recette au débit (restitution à un bailleur) vient en diminution des recettes ; une dépense au crédit
    /// (avoir, remboursement) en diminution des dépenses.
    /// </summary>
    public enum OperationNature { Income, Expense, InternalTransfer }

    public enum OperationStatus { Draft, Validated }

    public enum RuleMatchType { Contains, Regex }

    public enum RuleSource { Manual, Learned }

    /// <summary>Origine d'un relevé : saisie, fichier CSV/Excel de la banque, ou lecture d'un scan (Lot 3).</summary>
    public enum StatementSource { Manual, Csv, Ocr }

    public enum StatementStatus { Draft, Validated }

    public enum MatchMode { Auto, Manual }
}
