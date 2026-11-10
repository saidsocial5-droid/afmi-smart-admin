using System;

namespace AFMI_Gestion_projet.Models
{
    public class SmtpSettings
    {
        public int Id { get; set; }
        public string Server { get; set; } = string.Empty;
        public int Port { get; set; } = 587;
        public string Username { get; set; } = string.Empty;
        public string Password { get; set; } = string.Empty;
        public string RecipientEmail { get; set; } = string.Empty;
        
        public string ScheduleType { get; set; } = "Aucun"; // Aucun, Hebdomadaire, Mensuel
        public DateTime? LastSentDate { get; set; }
        public bool LastSentSuccess { get; set; }
    }
}
