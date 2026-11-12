using System.ComponentModel.DataAnnotations;

namespace AFMI_Gestion_projet.Models
{
    /// <summary>Paramètre clé/valeur (JSON). Un paramètre secret est chiffré par DPAPI et jamais journalisé.</summary>
    public class AppSetting
    {
        [Key, MaxLength(150)] public string Key { get; set; } = string.Empty;
        public string ValueJson { get; set; } = "null";
        public bool IsSecret { get; set; }
        public DateTime UpdatedAtUtc { get; set; } = DateTime.UtcNow;
    }

    /// <summary>Entrée du journal d'audit : ajout seul, chaînée par empreinte (toute altération est détectable).</summary>
    public class AuditEntry
    {
        public long Id { get; set; }
        public DateTime TimestampUtc { get; set; }
        [MaxLength(100)] public string User { get; set; } = string.Empty;
        [MaxLength(100)] public string Machine { get; set; } = string.Empty;
        [MaxLength(100)] public string EntityType { get; set; } = string.Empty;
        [MaxLength(100)] public string EntityId { get; set; } = string.Empty;
        /// <summary>Création, Modification, Suppression (logique) ou Suppression définitive.</summary>
        [MaxLength(30)] public string Action { get; set; } = string.Empty;
        /// <summary>{"Champ": {"old": …, "new": …}}</summary>
        public string ChangesJson { get; set; } = "{}";
        [MaxLength(64)] public string PreviousHash { get; set; } = string.Empty;
        [MaxLength(64)] public string Hash { get; set; } = string.Empty;
    }
}
