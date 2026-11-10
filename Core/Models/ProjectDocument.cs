using System;

namespace AFMI_Gestion_projet.Models
{
    public class ProjectDocument
    {
        public int Id { get; set; }
        public int ProjectId { get; set; }
        public Project Project { get; set; } = null!;

        // Document Metadata
        public string Title { get; set; } = string.Empty;
        
        // Category: Convention Bailleur, Dossier Projet, Budget Initial, Étude de Diagnostic, Cadre Logique, Avenant
        public string Category { get; set; } = "Convention Bailleur"; 

        // Project Phase this document belongs to
        // Values: Diagnostic, Montage, Rédaction, Exécution, Évaluation, Clôture
        public string DocumentPhase { get; set; } = "Montage";

        // Searchable keyword tags (comma-separated)
        public string Tags { get; set; } = string.Empty;

        // Flag: is this a key reference document used in all report generation?
        public bool IsKeyReference { get; set; } = false;

        // Version label (e.g. "Version 1", "Avenant n°2")
        public string DocumentVersion { get; set; } = string.Empty;
        
        // Donor or partner entity
        public string DonorName { get; set; } = string.Empty;
        
        // Official registration code or contract reference
        public string DocumentReference { get; set; } = string.Empty;

        // Key Dates
        public DateTime? SignatureDate { get; set; }
        public DateTime? ContractualEndDate { get; set; } // End of eligibility period
        
        // Financial commitment from donor in this document
        public double ApprovedGrantAmount { get; set; }
        
        // Physical File Details
        public string FilePath { get; set; } = string.Empty;
        public string OriginalFileName { get; set; } = string.Empty;
        public string FileExtension { get; set; } = string.Empty;
        public long FileSize { get; set; }

        // Narrative Summary & Extracted Content
        public string Notes { get; set; } = string.Empty;

        // Short summary (up to 2000 chars) for display in diagnostic panel
        public string ExtractedSummary { get; set; } = string.Empty;

        // Full extracted text — used as knowledge base for report generation
        public string FullExtractedText { get; set; } = string.Empty;

        // AI-style key insights extracted from document text
        // Stored as semicolon-separated insights, e.g. "Objectif: réduction pauvreté;Budget: 500000€"
        public string KeyInsights { get; set; } = string.Empty;

        // When was the deep analysis last run on this document
        public DateTime? AnalyzedDate { get; set; }

        public DateTime UploadedDate { get; set; } = DateTime.Now;

        // UI-only helpers (not persisted)
        [System.ComponentModel.DataAnnotations.Schema.NotMapped]
        public string Description
        {
            get => Notes;
            set => Notes = value;
        }

        /// <summary>Temp path selected by user before the file is copied to storage</summary>
        [System.ComponentModel.DataAnnotations.Schema.NotMapped]
        public string OriginalFilePath { get; set; } = string.Empty;

        /// <summary>UI display: phase + category badge label</summary>
        [System.ComponentModel.DataAnnotations.Schema.NotMapped]
        public string PhaseBadge => string.IsNullOrEmpty(DocumentPhase) ? Category : DocumentPhase;

        /// <summary>UI display: file size in KB</summary>
        [System.ComponentModel.DataAnnotations.Schema.NotMapped]
        public string FileSizeDisplay => FileSize > 0 ? $"{FileSize / 1024:N0} Ko" : "—";

        /// <summary>UI display: formatted list of insights</summary>
        [System.ComponentModel.DataAnnotations.Schema.NotMapped]
        public string[] InsightsList => string.IsNullOrWhiteSpace(KeyInsights)
            ? System.Array.Empty<string>()
            : KeyInsights.Split(';', System.StringSplitOptions.RemoveEmptyEntries);
    }
}

