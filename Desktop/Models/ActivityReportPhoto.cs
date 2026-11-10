namespace AFMI_Gestion_projet.Models
{
    public class ActivityReportPhoto
    {
        public int Id { get; set; }
        public string LocalFilePath { get; set; } = string.Empty;
        public string Caption { get; set; } = string.Empty;
        
        public int ActivityReportId { get; set; }
        public ActivityReport? ActivityReport { get; set; }
    }
}
