using System;
using System.Collections.Generic;

namespace AFMI_Gestion_projet.Models
{
    public class MeetingActionItem
    {
        public string Action { get; set; } = string.Empty;
        public string Responsible { get; set; } = string.Empty;
        public DateTime? DueDate { get; set; }
        public string Priority { get; set; } = "Moyenne"; // Haute, Moyenne, Basse
        public string Status { get; set; } = "À faire"; // À faire, En cours, Terminé
    }

    public class MeetingDecision
    {
        public string Reference { get; set; } = string.Empty;
        public string Decision { get; set; } = string.Empty;
        public string Impact { get; set; } = string.Empty;
        public string Responsible { get; set; } = string.Empty;
    }

    public class MeetingMinutesModel
    {
        public string Title { get; set; } = "Compte Rendu de Réunion";
        public string MeetingType { get; set; } = "Suivi de Projet"; // Cadrage, COPIL, Suivi, Chantier/Terrain, Clôture
        public DateTime MeetingDate { get; set; } = DateTime.Today;
        public string Location { get; set; } = "Salle de réunion / Visioconférence";
        public string Organizer { get; set; } = string.Empty;
        public string Secretary { get; set; } = string.Empty;
        public string Attendees { get; set; } = string.Empty;
        public string Excused { get; set; } = string.Empty;
        public string Agenda { get; set; } = string.Empty;
        public string RawNotes { get; set; } = string.Empty;
        public string GeneratedSummary { get; set; } = string.Empty;

        public string Q_Decisions { get; set; } = string.Empty;
        public string Q_Blockers { get; set; } = string.Empty;
        public string Q_NextSteps { get; set; } = string.Empty;
        
        // Associated Project details
        public int? ProjectId { get; set; }
        public string ProjectName { get; set; } = string.Empty;
        public string ProjectCode { get; set; } = string.Empty;
        public string ProjectManager { get; set; } = string.Empty;
        public string ClientOrDonor { get; set; } = string.Empty;
        
        public string FunderName { get; set; } = string.Empty;
        public string FunderPrimaryColor { get; set; } = "#1E293B"; // Default color used in Word
        public string FunderLogoPath { get; set; } = string.Empty;
        public string FunderHeaderText { get; set; } = string.Empty;
        public string FunderFooterText { get; set; } = string.Empty;

        public List<MeetingDecision> Decisions { get; set; } = new();
        public List<MeetingActionItem> ActionItems { get; set; } = new();
        
        public List<string> Photos { get; set; } = new();

        public string NextMeetingDate { get; set; } = string.Empty;
        public string NextMeetingAgenda { get; set; } = string.Empty;
    }
}
