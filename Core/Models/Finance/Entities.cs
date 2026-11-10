using System.ComponentModel.DataAnnotations;

namespace AFMI_Gestion_projet.Models.Finance
{
    // Montants : entiers en unités mineures (centimes) dans la devise indiquée. Jamais de double pour l'argent.

    public class FiscalYear
    {
        public int Id { get; set; }
        public int Year { get; set; }
        public DateOnly StartDate { get; set; }
        public DateOnly EndDate { get; set; }
        public FiscalYearStatus Status { get; set; } = FiscalYearStatus.Open;
        public DateTime? ClosedAtUtc { get; set; }
    }

    /// <summary>Taux de change daté : 1 unité de <see cref="Currency"/> = <see cref="RateToMad"/> MAD.</summary>
    public class CurrencyRate
    {
        public int Id { get; set; }
        [MaxLength(3)] public string Currency { get; set; } = "EUR";
        public DateOnly Date { get; set; }
        public decimal RateToMad { get; set; }
        [MaxLength(100)] public string Source { get; set; } = string.Empty;
    }

    public class BankAccount : ISoftDeletable
    {
        public int Id { get; set; }
        public AccountKind Kind { get; set; } = AccountKind.Bank;
        public AccountPurpose Purpose { get; set; } = AccountPurpose.Operating;
        [MaxLength(150)] public string BankName { get; set; } = string.Empty;
        [MaxLength(150)] public string Branch { get; set; } = string.Empty;
        [MaxLength(200)] public string Title { get; set; } = string.Empty;
        /// <summary>RIB marocain, 24 chiffres sans espace. Vide pour la caisse.</summary>
        [MaxLength(24)] public string? Rib { get; set; }
        [MaxLength(3)] public string Currency { get; set; } = "MAD";
        public long OpeningBalanceMinor { get; set; }
        public DateOnly OpeningDate { get; set; }
        public AccountStatus Status { get; set; } = AccountStatus.Active;
        public DateOnly? ClosedDate { get; set; }
        /// <summary>Alerte « solde bas » sous ce montant (null = pas d'alerte).</summary>
        public long? LowBalanceThresholdMinor { get; set; }
        public string Notes { get; set; } = string.Empty;
        public bool IsDeleted { get; set; }
        public DateTime? DeletedAtUtc { get; set; }

        public ICollection<AccountProjectLink> ProjectLinks { get; set; } = new List<AccountProjectLink>();
        public ICollection<Operation> Operations { get; set; } = new List<Operation>();
    }

    /// <summary>Un compte finance plusieurs projets et un projet est alimenté par plusieurs comptes, sur une période.</summary>
    public class AccountProjectLink : ISoftDeletable
    {
        public int Id { get; set; }
        public int BankAccountId { get; set; }
        public BankAccount? BankAccount { get; set; }
        public int ProjectId { get; set; }
        public Project? Project { get; set; }
        public DateOnly ValidFrom { get; set; }
        public DateOnly? ValidTo { get; set; }
        public AllocationMode AllocationMode { get; set; } = AllocationMode.None;
        /// <summary>Pourcentage (0–100) si <see cref="AllocationMode.Percentage"/>.</summary>
        public decimal? AllocationPercent { get; set; }
        /// <summary>Montant en unités mineures si <see cref="AllocationMode.FixedAmount"/>.</summary>
        public long? AllocationAmountMinor { get; set; }
        public bool IsDeleted { get; set; }
        public DateTime? DeletedAtUtc { get; set; }
    }

    /// <summary>Plan de comptes paramétrable (aucun plan n'est imposé : à importer depuis celui de l'expert-comptable).</summary>
    public class LedgerAccount
    {
        public int Id { get; set; }
        [MaxLength(20)] public string Code { get; set; } = string.Empty;
        [MaxLength(200)] public string Label { get; set; } = string.Empty;
        public LedgerAccountType Type { get; set; }
        public int? ParentId { get; set; }
        public LedgerAccount? Parent { get; set; }
        public bool IsActive { get; set; } = true;
    }

    public class Category
    {
        public int Id { get; set; }
        public CategoryKind Kind { get; set; }
        [MaxLength(30)] public string Code { get; set; } = string.Empty;
        [MaxLength(200)] public string Label { get; set; } = string.Empty;
        public int? ParentId { get; set; }
        public Category? Parent { get; set; }
        public int? LedgerAccountId { get; set; }
        public LedgerAccount? LedgerAccount { get; set; }
        public bool IsActive { get; set; } = true;
    }

    /// <summary>Convention de financement signée avec un bailleur pour un projet.</summary>
    public class FundingAgreement : ISoftDeletable
    {
        public int Id { get; set; }
        public int FunderId { get; set; }
        public Funder? Funder { get; set; }
        public int ProjectId { get; set; }
        public Project? Project { get; set; }
        [MaxLength(100)] public string Reference { get; set; } = string.Empty;
        [MaxLength(250)] public string Title { get; set; } = string.Empty;
        public long AmountMinor { get; set; }
        [MaxLength(3)] public string Currency { get; set; } = "MAD";
        /// <summary>Taux imposé par la convention (null = taux daté de la table des taux).</summary>
        public decimal? ContractualRateToMad { get; set; }
        public DateOnly? SignatureDate { get; set; }
        public DateOnly? StartDate { get; set; }
        public DateOnly? EndDate { get; set; }
        public string Notes { get; set; } = string.Empty;
        public bool IsDeleted { get; set; }
        public DateTime? DeletedAtUtc { get; set; }

        public ICollection<FundingTranche> Tranches { get; set; } = new List<FundingTranche>();
    }

    /// <summary>Tranche de l'échéancier de versement d'une convention (base de la prévision de trésorerie).</summary>
    public class FundingTranche : ISoftDeletable
    {
        public int Id { get; set; }
        public int FundingAgreementId { get; set; }
        public FundingAgreement? FundingAgreement { get; set; }
        [MaxLength(100)] public string Label { get; set; } = string.Empty;
        public DateOnly ExpectedDate { get; set; }
        public long AmountMinor { get; set; }
        /// <summary>Opération de recette qui a encaissé la tranche.</summary>
        public int? ReceivedOperationId { get; set; }
        public Operation? ReceivedOperation { get; set; }
        public bool IsDeleted { get; set; }
        public DateTime? DeletedAtUtc { get; set; }
    }

    /// <summary>Ligne budgétaire d'un projet (ou du fonctionnement si <see cref="ProjectId"/> est null).</summary>
    public class BudgetLine : ISoftDeletable
    {
        public int Id { get; set; }
        public int? ProjectId { get; set; }
        public Project? Project { get; set; }
        public int? FundingAgreementId { get; set; }
        public FundingAgreement? FundingAgreement { get; set; }
        public int? FiscalYearId { get; set; }
        public FiscalYear? FiscalYear { get; set; }
        /// <summary>Code de la rubrique (nomenclature du bailleur).</summary>
        [MaxLength(30)] public string Code { get; set; } = string.Empty;
        [MaxLength(250)] public string Label { get; set; } = string.Empty;
        public int? CategoryId { get; set; }
        public Category? Category { get; set; }
        public long PlannedMinor { get; set; }
        [MaxLength(3)] public string Currency { get; set; } = "MAD";
        public bool IsDeleted { get; set; }
        public DateTime? DeletedAtUtc { get; set; }
    }

    /// <summary>
    /// Mouvement sur un compte (ou la caisse). Source unique de vérité des recettes et dépenses.
    /// Une opération validée est entièrement ventilée (projet ou fonctionnement, ligne budgétaire, catégorie).
    /// </summary>
    public class Operation : ISoftDeletable
    {
        public int Id { get; set; }
        public int BankAccountId { get; set; }
        public BankAccount? BankAccount { get; set; }
        public DateOnly OperationDate { get; set; }
        public DateOnly? ValueDate { get; set; }
        [MaxLength(500)] public string Label { get; set; } = string.Empty;
        [MaxLength(100)] public string Reference { get; set; } = string.Empty;
        [MaxLength(200)] public string ThirdParty { get; set; } = string.Empty;
        public OperationDirection Direction { get; set; }
        public OperationNature Nature { get; set; }
        /// <summary>Montant positif, dans la devise du compte.</summary>
        public long AmountMinor { get; set; }
        [MaxLength(3)] public string Currency { get; set; } = "MAD";
        /// <summary>Taux appliqué (null en MAD) et contre-valeur en MAD, figés à l'enregistrement.</summary>
        public decimal? RateToMad { get; set; }
        public long AmountMadMinor { get; set; }
        /// <summary>Identifie les deux jambes d'un virement interne.</summary>
        public Guid? TransferGroupId { get; set; }
        public OperationStatus Status { get; set; } = OperationStatus.Draft;
        public DateTime? ValidatedAtUtc { get; set; }
        [MaxLength(100)] public string ValidatedBy { get; set; } = string.Empty;
        public string Notes { get; set; } = string.Empty;
        public bool IsDeleted { get; set; }
        public DateTime? DeletedAtUtc { get; set; }

        public ICollection<OperationAllocation> Allocations { get; set; } = new List<OperationAllocation>();
        public ICollection<OperationAttachment> Attachments { get; set; } = new List<OperationAttachment>();

        public long SignedAmountMinor => Direction == OperationDirection.Credit ? AmountMinor : -AmountMinor;
    }

    /// <summary>Ventilation d'une opération : la somme des ventilations est égale au montant de l'opération.</summary>
    public class OperationAllocation
    {
        public int Id { get; set; }
        public int OperationId { get; set; }
        public Operation? Operation { get; set; }
        /// <summary>null = fonctionnement général de l'association.</summary>
        public int? ProjectId { get; set; }
        public Project? Project { get; set; }
        public int? BudgetLineId { get; set; }
        public BudgetLine? BudgetLine { get; set; }
        public int? CategoryId { get; set; }
        public Category? Category { get; set; }
        public long AmountMinor { get; set; }
    }

    /// <summary>Fichier archivé (relevé, justificatif), identifié par son empreinte SHA-256.</summary>
    public class StoredFile
    {
        public int Id { get; set; }
        [MaxLength(64)] public string Sha256 { get; set; } = string.Empty;
        [MaxLength(500)] public string RelativePath { get; set; } = string.Empty;
        [MaxLength(255)] public string OriginalName { get; set; } = string.Empty;
        [MaxLength(100)] public string MimeType { get; set; } = string.Empty;
        public long SizeBytes { get; set; }
        public DateTime ImportedAtUtc { get; set; } = DateTime.UtcNow;
    }

    /// <summary>Justificatif d'une opération : fichier archivé ou document de la GED du projet.</summary>
    public class OperationAttachment
    {
        public int Id { get; set; }
        public int OperationId { get; set; }
        public Operation? Operation { get; set; }
        public int? StoredFileId { get; set; }
        public StoredFile? StoredFile { get; set; }
        public int? ProjectDocumentId { get; set; }
        public ProjectDocument? ProjectDocument { get; set; }
        [MaxLength(200)] public string Label { get; set; } = string.Empty;
    }

    /// <summary>Règle de catégorisation automatique des opérations (saisie ou apprise des corrections).</summary>
    public class CategorizationRule
    {
        public int Id { get; set; }
        [MaxLength(300)] public string Pattern { get; set; } = string.Empty;
        public RuleMatchType MatchType { get; set; } = RuleMatchType.Contains;
        public OperationDirection? Direction { get; set; }
        public int? CategoryId { get; set; }
        public Category? Category { get; set; }
        public int? ProjectId { get; set; }
        public int? BudgetLineId { get; set; }
        public RuleSource Source { get; set; } = RuleSource.Manual;
        public int Priority { get; set; } = 100;
        public int HitCount { get; set; }
        public bool IsActive { get; set; } = true;
    }

    /// <summary>Relevé de compte (saisi, importé d'un fichier de la banque, ou lu sur un scan au Lot 3).</summary>
    public class BankStatement : ISoftDeletable
    {
        public int Id { get; set; }
        public int BankAccountId { get; set; }
        public BankAccount? BankAccount { get; set; }
        public DateOnly PeriodStart { get; set; }
        public DateOnly PeriodEnd { get; set; }
        public long OpeningBalanceMinor { get; set; }
        public long ClosingBalanceMinor { get; set; }
        public StatementSource Source { get; set; } = StatementSource.Manual;
        public int? SourceFileId { get; set; }
        public StoredFile? SourceFile { get; set; }
        [MaxLength(100)] public string Template { get; set; } = string.Empty;
        public StatementStatus Status { get; set; } = StatementStatus.Draft;
        public DateTime ImportedAtUtc { get; set; } = DateTime.UtcNow;
        public string Notes { get; set; } = string.Empty;
        public bool IsDeleted { get; set; }
        public DateTime? DeletedAtUtc { get; set; }

        public ICollection<StatementLine> Lines { get; set; } = new List<StatementLine>();
    }

    /// <summary>Ligne de relevé, telle que la banque l'a passée.</summary>
    public class StatementLine
    {
        public int Id { get; set; }
        public int BankStatementId { get; set; }
        public BankStatement? BankStatement { get; set; }
        public DateOnly OperationDate { get; set; }
        public DateOnly? ValueDate { get; set; }
        [MaxLength(500)] public string Label { get; set; } = string.Empty;
        [MaxLength(100)] public string Reference { get; set; } = string.Empty;
        public long DebitMinor { get; set; }
        public long CreditMinor { get; set; }
        /// <summary>Confiance de l'extraction par champ (Lot 3), JSON.</summary>
        public string ConfidenceJson { get; set; } = "{}";
        public int? SuggestedCategoryId { get; set; }
        public int? SuggestedProjectId { get; set; }
        public int? SuggestedBudgetLineId { get; set; }

        public ReconciliationMatch? Match { get; set; }

        public long SignedAmountMinor => CreditMinor - DebitMinor;
    }

    /// <summary>Rapprochement d'une ligne de relevé avec une opération (un pour un).</summary>
    public class ReconciliationMatch
    {
        public int Id { get; set; }
        public int StatementLineId { get; set; }
        public StatementLine? StatementLine { get; set; }
        public int OperationId { get; set; }
        public Operation? Operation { get; set; }
        public MatchMode Mode { get; set; }
        public double Score { get; set; }
        public DateTime MatchedAtUtc { get; set; } = DateTime.UtcNow;
        [MaxLength(100)] public string MatchedBy { get; set; } = string.Empty;
    }
}
