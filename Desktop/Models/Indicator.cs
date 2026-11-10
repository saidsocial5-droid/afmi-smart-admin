using System.Collections.Generic;

namespace AFMI_Gestion_projet.Models
{
    public class Indicator
    {
        public int Id { get; set; }
        public string Name { get; set; } = string.Empty;
        public string Description { get; set; } = string.Empty;
        public double TargetValue { get; set; }
        public double CurrentValue { get; set; }
        public string Unit { get; set; } = string.Empty;
        
        public int ProjectId { get; set; }
        public Project? Project { get; set; }
    }
}
