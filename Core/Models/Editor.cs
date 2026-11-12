using System.ComponentModel.DataAnnotations;
using AFMI_Gestion_projet.Models.Finance;

namespace AFMI_Gestion_projet.Models.Editor
{
    // Lot 4 : éditeur de documents, chartes graphiques, modèles et photos. Le contenu est manipulé par le module
    // Smart Office (React + backend Python) ; le schéma reste géré ici, par les migrations EF Core.

    public enum ChartScope { Association, Funder, Project }

    /// <summary>
    /// Charte graphique : couleurs, polices, logos et positions, marges, en-têtes et pieds de page, mentions
    /// obligatoires, style des tableaux. Héritage : charte de l'association ← charte du bailleur ← charte du projet.
    /// </summary>
    public class GraphicChart : ISoftDeletable
    {
        public int Id { get; set; }
        [MaxLength(150)] public string Name { get; set; } = string.Empty;
        public ChartScope Scope { get; set; }
        public int? FunderId { get; set; }
        public Funder? Funder { get; set; }
        public int? ProjectId { get; set; }
        public Project? Project { get; set; }
        /// <summary>Réglages (JSON) ; seules les valeurs renseignées surchargent la charte parente.</summary>
        public string StyleJson { get; set; } = "{}";
        public DateTime UpdatedAtUtc { get; set; } = DateTime.UtcNow;
        public bool IsDeleted { get; set; }
        public DateTime? DeletedAtUtc { get; set; }
    }

    /// <summary>Modèle de document réutilisable (contenu de l'éditeur + mise en page), partageable.</summary>
    public class DocumentTemplate : ISoftDeletable
    {
        public int Id { get; set; }
        [MaxLength(200)] public string Name { get; set; } = string.Empty;
        public string Description { get; set; } = string.Empty;
        /// <summary>Rapport d'activité, rapport financier, note, courrier…</summary>
        [MaxLength(50)] public string Kind { get; set; } = string.Empty;
        public string ContentJson { get; set; } = "{}";
        public string LayoutJson { get; set; } = "{}";
        public bool IsShared { get; set; } = true;
        [MaxLength(100)] public string CreatedBy { get; set; } = string.Empty;
        public DateTime UpdatedAtUtc { get; set; } = DateTime.UtcNow;
        public bool IsDeleted { get; set; }
        public DateTime? DeletedAtUtc { get; set; }
    }

    public class EditorDocument : ISoftDeletable
    {
        public int Id { get; set; }
        [MaxLength(250)] public string Title { get; set; } = string.Empty;
        public int? ProjectId { get; set; }
        public Project? Project { get; set; }
        public int? FunderId { get; set; }
        public Funder? Funder { get; set; }
        public int? TemplateId { get; set; }
        public DocumentTemplate? Template { get; set; }
        [MaxLength(5)] public string Language { get; set; } = "fr";
        /// <summary>Contenu de l'éditeur (JSON ProseMirror/TipTap).</summary>
        public string ContentJson { get; set; } = "{}";
        /// <summary>Surcharges de mise en page propres au document (marges, en-têtes…), par-dessus la charte.</summary>
        public string LayoutJson { get; set; } = "{}";
        public int CurrentVersion { get; set; }
        [MaxLength(30)] public string Status { get; set; } = "Brouillon";
        [MaxLength(100)] public string CreatedBy { get; set; } = string.Empty;
        public DateTime CreatedAtUtc { get; set; } = DateTime.UtcNow;
        public DateTime UpdatedAtUtc { get; set; } = DateTime.UtcNow;
        public bool IsDeleted { get; set; }
        public DateTime? DeletedAtUtc { get; set; }

        public ICollection<DocumentVersion> Versions { get; set; } = new List<DocumentVersion>();
        public ICollection<DocumentComment> Comments { get; set; } = new List<DocumentComment>();
    }

    /// <summary>Version enregistrée d'un document (instantané complet, restaurable).</summary>
    public class DocumentVersion
    {
        public int Id { get; set; }
        public int EditorDocumentId { get; set; }
        public EditorDocument? EditorDocument { get; set; }
        public int Number { get; set; }
        public string ContentJson { get; set; } = "{}";
        public string LayoutJson { get; set; } = "{}";
        [MaxLength(300)] public string Note { get; set; } = string.Empty;
        [MaxLength(100)] public string CreatedBy { get; set; } = string.Empty;
        public DateTime CreatedAtUtc { get; set; } = DateTime.UtcNow;
    }

    /// <summary>Commentaire ancré sur un passage (marque « comment » portant <see cref="AnchorId"/> dans le contenu).</summary>
    public class DocumentComment
    {
        public int Id { get; set; }
        public int EditorDocumentId { get; set; }
        public EditorDocument? EditorDocument { get; set; }
        [MaxLength(40)] public string AnchorId { get; set; } = string.Empty;
        public int? ParentId { get; set; }
        public string Text { get; set; } = string.Empty;
        [MaxLength(300)] public string QuotedText { get; set; } = string.Empty;
        [MaxLength(100)] public string Author { get; set; } = string.Empty;
        public DateTime CreatedAtUtc { get; set; } = DateTime.UtcNow;
        public DateTime? ResolvedAtUtc { get; set; }
    }

    /// <summary>Photo d'activité : fichier archivé, métadonnées (EXIF), légende, crédit et consentement au droit à l'image.</summary>
    public class Photo : ISoftDeletable
    {
        public int Id { get; set; }
        public int StoredFileId { get; set; }
        public StoredFile? StoredFile { get; set; }
        public int? ProjectId { get; set; }
        public Project? Project { get; set; }
        public int? ProjectTaskId { get; set; }
        public ProjectTask? ProjectTask { get; set; }
        public int? ActivityReportId { get; set; }
        public ActivityReport? ActivityReport { get; set; }
        public DateTime? TakenAt { get; set; }
        [MaxLength(200)] public string Location { get; set; } = string.Empty;
        public double? Latitude { get; set; }
        public double? Longitude { get; set; }
        [MaxLength(500)] public string Caption { get; set; } = string.Empty;
        /// <summary>Légende proposée par l'IA, à valider (jamais publiée sans validation).</summary>
        [MaxLength(500)] public string SuggestedCaption { get; set; } = string.Empty;
        public bool CaptionValidated { get; set; }
        [MaxLength(150)] public string Credit { get; set; } = string.Empty;
        /// <summary>Consentement au droit à l'image recueilli : sans lui, la photo n'est jamais insérée automatiquement.</summary>
        public bool ConsentGiven { get; set; }
        public int Width { get; set; }
        public int Height { get; set; }
        public DateTime ImportedAtUtc { get; set; } = DateTime.UtcNow;
        public bool IsDeleted { get; set; }
        public DateTime? DeletedAtUtc { get; set; }
    }
}
