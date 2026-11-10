using System.Collections.Generic;

namespace AFMI_Gestion_projet.Models
{
    public class Funder
    {
        public int Id { get; set; }
        public string Name { get; set; } = string.Empty;
        public string PrimaryColor { get; set; } = "#000000";
        public string LogoPath { get; set; } = string.Empty;
        public string LegalMentions { get; set; } = string.Empty;
        public string HeaderText { get; set; } = string.Empty;
        public string FooterText { get; set; } = string.Empty;
        
        public ICollection<Project> Projects { get; set; } = new List<Project>();
    }
}
