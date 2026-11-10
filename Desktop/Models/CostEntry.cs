using System;

namespace AFMI_Gestion_projet.Models
{
    public class CostEntry
    {
        public int Id { get; set; }
        public int ProjectId { get; set; }
        public Project Project { get; set; } = null!;
        
        public string Category { get; set; } = "Divers"; // Ressources, Matériel, Prestataires, Divers
        public string ResourceName { get; set; } = string.Empty;
        public string Supplier { get; set; } = string.Empty;
        public string Description { get; set; } = string.Empty;
        
        public double EstimatedCost { get; set; }
        public double ActualCost { get; set; }
        public DateTime Date { get; set; } = DateTime.Now;
    }
}
