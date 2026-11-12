using System;
using System.Collections.Generic;

namespace AFMI_Gestion_projet.Models
{
    public class ProjectTask
    {
        public int Id { get; set; }
        public int ProjectId { get; set; }
        public Project Project { get; set; } = null!;
        
        public int? ParentTaskId { get; set; }
        public ProjectTask? ParentTask { get; set; }
        public ICollection<ProjectTask> SubTasks { get; set; } = new List<ProjectTask>();
        
        public string Name { get; set; } = string.Empty;
        public string Description { get; set; } = string.Empty;
        public string Assignee { get; set; } = string.Empty;
        /// <summary>Code de l'activité dans le document du bailleur (1.1, A2.3, 1.1.4…).</summary>
        public string Code { get; set; } = string.Empty;
        
        public DateTime? TargetStartDate { get; set; }
        public DateTime? TargetEndDate { get; set; }
        public DateTime? ActualStartDate { get; set; }
        public DateTime? ActualEndDate { get; set; }
        
        public double ProgressPercentage { get; set; } // 0 to 100
        public string Status { get; set; } = "À faire"; // À faire, En cours, Terminé, Bloqué
        
        public double Budget { get; set; } // Budgeted cost of task
        public double Cost { get; set; }   // Actual cost of task
        
        // Comma-separated list of task IDs that must finish before this task starts
        public string Predecessors { get; set; } = string.Empty; 
        
        public ICollection<ActivityReport> ActivityReports { get; set; } = new List<ActivityReport>();
    }
}
