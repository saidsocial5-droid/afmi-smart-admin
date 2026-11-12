using System.ComponentModel.DataAnnotations;
using AFMI_Gestion_projet.Models.Finance;

namespace AFMI_Gestion_projet.Models
{
    // Lot 10 — dossier de projet : cadre logique, risques, règles du bailleur, cofinancement, imports de documents.
    // Vocabulaire aligné sur l'OCDE-CAD (gestion axée sur les résultats) et la norme IATI (budget, résultats, participants).

    /// <summary>Élément du cadre logique : objectif global, objectif spécifique, résultat (effet) ou produit (extrant).</summary>
    public class LogframeNode : ISoftDeletable
    {
        public int Id { get; set; }
        public int ProjectId { get; set; }
        public Project? Project { get; set; }
        public int? ParentId { get; set; }
        public LogframeNode? Parent { get; set; }
        /// <summary>Objectif global, Objectif spécifique, Résultat, Produit.</summary>
        [MaxLength(30)] public string Level { get; set; } = "Résultat";
        /// <summary>Code du document du bailleur (OG, OS1, R1, 1.2…).</summary>
        [MaxLength(30)] public string Code { get; set; } = string.Empty;
        public string Statement { get; set; } = string.Empty;
        public int SortOrder { get; set; }
        public bool IsDeleted { get; set; }
        public DateTime? DeletedAtUtc { get; set; }
    }

    public class ProjectRisk : ISoftDeletable
    {
        public int Id { get; set; }
        public int ProjectId { get; set; }
        public Project? Project { get; set; }
        public string Description { get; set; } = string.Empty;
        /// <summary>Faible, Moyen, Élevé (vide si le document ne le précise pas).</summary>
        [MaxLength(20)] public string Probability { get; set; } = string.Empty;
        [MaxLength(20)] public string Impact { get; set; } = string.Empty;
        public string Mitigation { get; set; } = string.Empty;
        [MaxLength(150)] public string Owner { get; set; } = string.Empty;
        [MaxLength(20)] public string Status { get; set; } = "Ouvert";
        public bool IsDeleted { get; set; }
        public DateTime? DeletedAtUtc { get; set; }
    }

    /// <summary>Règle fixée par le bailleur et lue dans ses documents (jamais inventée) : contrôlée par l'application.</summary>
    public class DonorRule : ISoftDeletable
    {
        public int Id { get; set; }
        public int FundingAgreementId { get; set; }
        public FundingAgreement? FundingAgreement { get; set; }
        /// <summary>IndirectCostsMaxPercent, CofinancingMinPercent, GrantMaxShareOfIncomePercent, GrantMaxAmount, Other.</summary>
        [MaxLength(40)] public string Kind { get; set; } = "Other";
        public decimal? Value { get; set; }
        public string Text { get; set; } = string.Empty;
        public string SourceExcerpt { get; set; } = string.Empty;
        public bool IsDeleted { get; set; }
        public DateTime? DeletedAtUtc { get; set; }
    }

    /// <summary>Contribution prévue d'un cofinanceur (communauté, association, autre bailleur), en espèces ou en nature.</summary>
    public class CofinancingContribution : ISoftDeletable
    {
        public int Id { get; set; }
        public int ProjectId { get; set; }
        public Project? Project { get; set; }
        public int? FundingAgreementId { get; set; }
        public FundingAgreement? FundingAgreement { get; set; }
        public int? BudgetLineId { get; set; }
        public BudgetLine? BudgetLine { get; set; }
        /// <summary>Communauté, Association, Autre bailleur, Partenaire.</summary>
        [MaxLength(30)] public string SourceType { get; set; } = "Association";
        [MaxLength(150)] public string SourceName { get; set; } = string.Empty;
        /// <summary>Espèces ou Nature.</summary>
        [MaxLength(10)] public string Nature { get; set; } = "Nature";
        public string Description { get; set; } = string.Empty;
        public long PlannedMinor { get; set; }
        [MaxLength(3)] public string Currency { get; set; } = "MAD";
        /// <summary>Engagé (disponible) ou Prévu (projeté).</summary>
        [MaxLength(10)] public string Commitment { get; set; } = "Prévu";
        public bool IsDeleted { get; set; }
        public DateTime? DeletedAtUtc { get; set; }
        public ICollection<CofinancingEntry> Entries { get; set; } = new List<CofinancingEntry>();
    }

    /// <summary>
    /// Réalisation d'une contribution (heures de main-d'œuvre valorisées, local mis à disposition…).
    /// Selon le bailleur (Funder.InKindTreatment) elle est seulement suivie, ou aussi portée en comptabilité
    /// par une écriture de valorisation équilibrée (emploi = ressource), sans effet sur le résultat ni sur la trésorerie.
    /// </summary>
    public class CofinancingEntry : ISoftDeletable
    {
        public int Id { get; set; }
        public int ContributionId { get; set; }
        public CofinancingContribution? Contribution { get; set; }
        public DateOnly Date { get; set; }
        public long AmountMinor { get; set; }
        public string Description { get; set; } = string.Empty;
        /// <summary>Justificatif : feuille de présence, attestation, convention de mise à disposition…</summary>
        public string Evidence { get; set; } = string.Empty;
        [MaxLength(150)] public string CreatedBy { get; set; } = string.Empty;
        public DateTime CreatedAtUtc { get; set; } = DateTime.UtcNow;
        public bool IsDeleted { get; set; }
        public DateTime? DeletedAtUtc { get; set; }
    }

    /// <summary>Import intelligent d'un dossier de projet : fichiers lus, proposition extraite, corrections et application.</summary>
    public class ProjectImport
    {
        public int Id { get; set; }
        public int? ProjectId { get; set; }
        public Project? Project { get; set; }
        public DateTime CreatedAtUtc { get; set; } = DateTime.UtcNow;
        [MaxLength(150)] public string CreatedBy { get; set; } = string.Empty;
        /// <summary>Fichiers analysés (nom, empreinte, pages, document GED).</summary>
        public string FilesJson { get; set; } = "[]";
        /// <summary>Proposition (valeurs, sources, alertes), modifiée par l'utilisateur pendant la revue.</summary>
        public string ResultJson { get; set; } = "{}";
        [MaxLength(80)] public string Engine { get; set; } = string.Empty;
        /// <summary>Brouillon, Appliqué, Abandonné.</summary>
        [MaxLength(20)] public string Status { get; set; } = "Brouillon";
        public DateTime? AppliedAtUtc { get; set; }
        public string AppliedSummary { get; set; } = string.Empty;
    }
}
