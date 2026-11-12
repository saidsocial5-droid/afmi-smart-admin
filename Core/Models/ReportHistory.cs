using System;

namespace AFMI_Gestion_projet.Models
{
    public class ReportHistory
    {
        public int Id { get; set; }
        public int ProjectId { get; set; }
        public Project Project { get; set; } = null!;
        
        public string ReportType { get; set; } = string.Empty; // Avancement, Financier, Clôture
        public string Title { get; set; } = string.Empty;
        public DateTime GeneratedDate { get; set; } = DateTime.Now;
        public string FilePath { get; set; } = string.Empty;
        public string ContentJson { get; set; } = string.Empty; // Metadata of the report
    }
}
