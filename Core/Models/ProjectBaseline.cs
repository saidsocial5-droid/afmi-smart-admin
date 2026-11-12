using System;

namespace AFMI_Gestion_projet.Models
{
    public class ProjectBaseline
    {
        public int Id { get; set; }
        public int ProjectId { get; set; }
        public Project Project { get; set; } = null!;

        // Contractual Reference
        public string DonorName { get; set; } = string.Empty;
        public string ContractualReference { get; set; } = string.Empty;

        // Financial Commitments
        public double TotalGrantCommitted { get; set; }
        public double CoFinancingShare { get; set; }

        // Contractual Timelines & Reporting
        public DateTime? EligibilityDeadline { get; set; }
        public DateTime? NextReportingDeadline { get; set; }
        public string ReportingFrequency { get; set; } = "Semestriel"; // Trimestriel, Semestriel, Annuel

        // Key Deliverables and Compliance Rules from initial dossier
        public string ContractualDeliverables { get; set; } = string.Empty;
        public string EligibilityRulesNotes { get; set; } = string.Empty;

        // Deep Analysis Outputs
        public double ComplianceScore { get; set; } = 100; // 0 to 100
        public string DiagnosticSummary { get; set; } = string.Empty;
        public DateTime LastAnalyzedDate { get; set; } = DateTime.Now;
    }
}
