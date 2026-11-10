using System;

namespace AFMI_Gestion_projet.Models
{
    public class AuditLog
    {
        public int Id { get; set; }
        public int ProjectId { get; set; }
        public Project Project { get; set; } = null!;
        
        public string EntityType { get; set; } = string.Empty; // Project, Task, CostEntry
        public int EntityId { get; set; }
        public string ChangeType { get; set; } = string.Empty; // Création, Modification, Suppression
        public string FieldName { get; set; } = string.Empty;
        public string OldValue { get; set; } = string.Empty;
        public string NewValue { get; set; } = string.Empty;
        
        public DateTime Timestamp { get; set; } = DateTime.Now;
        public string User { get; set; } = "Utilisateur local";
    }
}
