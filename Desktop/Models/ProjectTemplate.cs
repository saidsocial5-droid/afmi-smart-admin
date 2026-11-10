namespace AFMI_Gestion_projet.Models
{
    public class ProjectTemplate
    {
        public int Id { get; set; }
        public string Name { get; set; } = string.Empty;
        public string Description { get; set; } = string.Empty;
        public string ProjectDataJson { get; set; } = string.Empty; // Holds template details (tasks, steps)
    }
}
