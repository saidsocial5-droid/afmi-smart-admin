using System.ComponentModel.DataAnnotations;
using AFMI_Gestion_projet.Models.Finance;

namespace AFMI_Gestion_projet.Models
{
    /// <summary>
    /// Obligation de reporting envers un bailleur (rapport narratif, financier, final…), saisie ou proposée par l'analyse
    /// d'une convention (statut « Proposée » tant que l'utilisateur ne l'a pas confirmée).
    /// </summary>
    public class ReportingObligation : ISoftDeletable
    {
        public int Id { get; set; }
        public int ProjectId { get; set; }
        public Project? Project { get; set; }
        public int? FundingAgreementId { get; set; }
        public FundingAgreement? FundingAgreement { get; set; }
        [MaxLength(250)] public string Title { get; set; } = string.Empty;
        [MaxLength(50)] public string Kind { get; set; } = "Rapport narratif";
        public DateOnly DueDate { get; set; }
        /// <summary>Proposée, À venir, Remise.</summary>
        [MaxLength(20)] public string Status { get; set; } = "À venir";
        public int? DeliveredDocumentId { get; set; }
        public ProjectDocument? DeliveredDocument { get; set; }
        public int? SourceDocumentId { get; set; }
        public ProjectDocument? SourceDocument { get; set; }
        /// <summary>Phrase du document dont l'obligation a été déduite (traçabilité).</summary>
        public string SourceExcerpt { get; set; } = string.Empty;
        public string Notes { get; set; } = string.Empty;
        public bool IsDeleted { get; set; }
        public DateTime? DeletedAtUtc { get; set; }
    }

    /// <summary>Jalon du projet (lancement, atelier, comité de pilotage, clôture…) pour la frise du cycle de vie.</summary>
    public class ProjectMilestone : ISoftDeletable
    {
        public int Id { get; set; }
        public int ProjectId { get; set; }
        public Project? Project { get; set; }
        [MaxLength(250)] public string Title { get; set; } = string.Empty;
        public DateOnly Date { get; set; }
        [MaxLength(30)] public string Phase { get; set; } = string.Empty;
        public bool Done { get; set; }
        public int? SourceDocumentId { get; set; }
        public ProjectDocument? SourceDocument { get; set; }
        public bool IsDeleted { get; set; }
        public DateTime? DeletedAtUtc { get; set; }
    }

    /// <summary>Passage de texte d'un document, indexé en plein texte (FTS5) et, si un modèle est disponible, sémantiquement.</summary>
    public class DocumentChunk
    {
        public int Id { get; set; }
        public int DocumentId { get; set; }
        public ProjectDocument? Document { get; set; }
        public int Ordinal { get; set; }
        public int? Page { get; set; }
        public string Text { get; set; } = string.Empty;
        /// <summary>Vecteur (float32) du modèle d'embeddings, null si aucun modèle n'était disponible.</summary>
        public byte[]? Embedding { get; set; }
        [MaxLength(100)] public string EmbeddingModel { get; set; } = string.Empty;
    }
}
