using System;
using System.Collections.Generic;

namespace AFMI_Gestion_projet.Models
{
    public class ActivityReport
    {
        public int Id { get; set; }
        public string Title { get; set; } = string.Empty;
        public DateTime ActivityDate { get; set; }
        public string Location { get; set; } = string.Empty;
        public int ParticipantsCount { get; set; }
        
        public string Narrative { get; set; } = string.Empty;
        public string Difficulties { get; set; } = string.Empty;
        public string Recommendations { get; set; } = string.Empty;
        
        public string Status { get; set; } = "Brouillon"; // Brouillon, Validé
        
        public int ProjectTaskId { get; set; }
        public ProjectTask? ProjectTask { get; set; }
        
        public int? IndicatorId { get; set; }
        public Indicator? Indicator { get; set; }
        
        public ICollection<ActivityReportPhoto> Photos { get; set; } = new List<ActivityReportPhoto>();
    }
}
