using System;
using System.Collections.Generic;

namespace AFMI_Gestion_projet.Models
{
    public class Project : ISoftDeletable
    {
        public int Id { get; set; }
        public string Name { get; set; } = string.Empty;
        public string Code { get; set; } = string.Empty;
        public string Description { get; set; } = string.Empty;
        public string Manager { get; set; } = string.Empty;
        public string Owner { get; set; } = string.Empty;
        public string Client { get; set; } = string.Empty;
        public string Department { get; set; } = string.Empty;
        
        public int? FunderId { get; set; }
        public Funder? Funder { get; set; }
        
        public DateTime? TargetStartDate { get; set; }
        public DateTime? TargetEndDate { get; set; }
        public DateTime? ActualStartDate { get; set; }
        public DateTime? ActualEndDate { get; set; }
        
        public string Status { get; set; } = "Initiation"; // Initiation, Planification, Exécution, Clôture, Archivé
        public string Priority { get; set; } = "Moyenne"; // Basse, Moyenne, Haute, Critique
        public double BudgetGlobal { get; set; }
        /// <summary>Devise de référence du projet (MAD par défaut).</summary>
        public string Currency { get; set; } = "MAD";
        
        public int? ParentProjectId { get; set; }
        public Project? ParentProject { get; set; }
        public ICollection<Project> SubProjects { get; set; } = new List<Project>();
        
        public string LessonsLearned { get; set; } = string.Empty;
        public string LocalFolderPath { get; set; } = string.Empty;
        
        // Relations
        public ICollection<ProjectTask> Tasks { get; set; } = new List<ProjectTask>();
        public ICollection<CostEntry> CostEntries { get; set; } = new List<CostEntry>();
        public ICollection<WorkflowStep> WorkflowSteps { get; set; } = new List<WorkflowStep>();
        public ICollection<AuditLog> AuditLogs { get; set; } = new List<AuditLog>();
        public ICollection<ReportHistory> ReportHistories { get; set; } = new List<ReportHistory>();
        public ICollection<ProjectDocument> Documents { get; set; } = new List<ProjectDocument>();
        public ICollection<Indicator> Indicators { get; set; } = new List<Indicator>();
        public ProjectBaseline? Baseline { get; set; }

        public bool IsDeleted { get; set; }
        public DateTime? DeletedAtUtc { get; set; }
    }
}
