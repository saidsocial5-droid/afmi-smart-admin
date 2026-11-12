using System.ComponentModel.DataAnnotations;
using AFMI_Gestion_projet.Models.Editor;

namespace AFMI_Gestion_projet.Models
{
    /// <summary>
    /// Compte rendu (Lot 9) : PV de réunion, comité de pilotage, assemblée générale, conseil d'administration, rencontre
    /// avec un partenaire, visite de terrain, ou compte rendu d'activité (atelier, formation, sensibilisation…).
    /// Sans projet : vie associative (gouvernance). Le texte est rédigé dans l'éditeur (EditorDocument) ; décisions et
    /// actions sont structurées pour être suivies (tâches, alertes, réunion suivante, rapport annuel).
    /// </summary>
    public class Meeting : ISoftDeletable
    {
        public int Id { get; set; }
        /// <summary>Réunion, COPIL, AG, CA, Rencontre, Visite, Activité.</summary>
        [MaxLength(30)] public string Kind { get; set; } = "Réunion";
        [MaxLength(250)] public string Title { get; set; } = string.Empty;
        public DateOnly Date { get; set; }
        [MaxLength(10)] public string StartTime { get; set; } = string.Empty;
        [MaxLength(200)] public string Location { get; set; } = string.Empty;
        public int? ProjectId { get; set; }
        public Project? Project { get; set; }
        /// <summary>Activité du projet (pour un compte rendu d'activité : alimente les rapports et les indicateurs).</summary>
        public int? ProjectTaskId { get; set; }
        public ProjectTask? ProjectTask { get; set; }
        public int? ActivityReportId { get; set; }
        public ActivityReport? ActivityReport { get; set; }
        public int? EditorDocumentId { get; set; }
        public EditorDocument? EditorDocument { get; set; }
        /// <summary>Document de la GED (PV signé ou exporté) une fois le compte rendu validé.</summary>
        public int? ArchivedDocumentId { get; set; }
        public ProjectDocument? ArchivedDocument { get; set; }
        [MaxLength(150)] public string Organizer { get; set; } = string.Empty;
        [MaxLength(150)] public string Secretary { get; set; } = string.Empty;
        public string Agenda { get; set; } = string.Empty;
        public string Summary { get; set; } = string.Empty;
        /// <summary>Brouillon, Validé, Diffusé.</summary>
        [MaxLength(20)] public string Status { get; set; } = "Brouillon";
        [MaxLength(100)] public string CreatedBy { get; set; } = string.Empty;
        public DateTime CreatedAtUtc { get; set; }
        public DateTime UpdatedAtUtc { get; set; }
        public ICollection<MeetingParticipant> Participants { get; set; } = new List<MeetingParticipant>();
        public ICollection<MeetingResolution> Decisions { get; set; } = new List<MeetingResolution>();
        public ICollection<MeetingAction> Actions { get; set; } = new List<MeetingAction>();
        public bool IsDeleted { get; set; }
        public DateTime? DeletedAtUtc { get; set; }
    }

    public class MeetingParticipant
    {
        public int Id { get; set; }
        public int MeetingId { get; set; }
        public Meeting? Meeting { get; set; }
        [MaxLength(150)] public string Name { get; set; } = string.Empty;
        [MaxLength(150)] public string Organization { get; set; } = string.Empty;
        [MaxLength(100)] public string Role { get; set; } = string.Empty;
        /// <summary>« », F ou M (désagrégation des bénéficiaires).</summary>
        [MaxLength(1)] public string Sex { get; set; } = string.Empty;
        public bool Present { get; set; } = true;
    }

    public class MeetingResolution
    {
        public int Id { get; set; }
        public int MeetingId { get; set; }
        public Meeting? Meeting { get; set; }
        public int Number { get; set; }
        public string Text { get; set; } = string.Empty;
        [MaxLength(150)] public string Responsible { get; set; } = string.Empty;
    }

    /// <summary>Action décidée en réunion, suivie jusqu'à sa réalisation (tâche du projet, alerte d'échéance).</summary>
    public class MeetingAction
    {
        public int Id { get; set; }
        public int MeetingId { get; set; }
        public Meeting? Meeting { get; set; }
        public string Text { get; set; } = string.Empty;
        [MaxLength(150)] public string Responsible { get; set; } = string.Empty;
        public DateOnly? DueDate { get; set; }
        /// <summary>À faire, En cours, Fait, Abandonné.</summary>
        [MaxLength(20)] public string Status { get; set; } = "À faire";
        public DateOnly? DoneDate { get; set; }
        public int? ProjectTaskId { get; set; }
        public ProjectTask? ProjectTask { get; set; }
    }

    /// <summary>Dossier personnalisé de la GED, sous le classement automatique (année › projet › type).</summary>
    public class DocumentFolder : ISoftDeletable
    {
        public int Id { get; set; }
        public int? ParentId { get; set; }
        public DocumentFolder? Parent { get; set; }
        public int? ProjectId { get; set; }
        public Project? Project { get; set; }
        public int? Year { get; set; }
        [MaxLength(150)] public string Name { get; set; } = string.Empty;
        public bool IsDeleted { get; set; }
        public DateTime? DeletedAtUtc { get; set; }
    }
}
