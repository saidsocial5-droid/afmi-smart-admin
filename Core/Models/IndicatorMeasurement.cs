using System.ComponentModel.DataAnnotations;

namespace AFMI_Gestion_projet.Models
{
    /// <summary>
    /// Mesure d'un indicateur sur une période, éventuellement désagrégée (sexe, tranche d'âge, zone).
    /// Les rapports annuels cumulent les mesures de l'exercice selon <see cref="Indicator.Aggregation"/>.
    /// </summary>
    public class IndicatorMeasurement
    {
        public int Id { get; set; }
        public int IndicatorId { get; set; }
        public Indicator? Indicator { get; set; }
        public DateOnly PeriodEnd { get; set; }
        public double Value { get; set; }
        /// <summary>F, M ou vide (non désagrégé).</summary>
        [MaxLength(1)] public string Sex { get; set; } = string.Empty;
        [MaxLength(30)] public string AgeGroup { get; set; } = string.Empty;
        [MaxLength(100)] public string Zone { get; set; } = string.Empty;
        [MaxLength(200)] public string Source { get; set; } = string.Empty;
        public string Notes { get; set; } = string.Empty;
        public DateTime CreatedAtUtc { get; set; } = DateTime.UtcNow;
    }
}
