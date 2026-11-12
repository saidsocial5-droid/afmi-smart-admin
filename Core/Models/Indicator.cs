using System.Collections.Generic;

namespace AFMI_Gestion_projet.Models
{
    public class Indicator
    {
        public int Id { get; set; }
        public string Name { get; set; } = string.Empty;
        public string Description { get; set; } = string.Empty;
        public double TargetValue { get; set; }
        public double CurrentValue { get; set; }
        public string Unit { get; set; } = string.Empty;

        /// <summary>Niveau dans la chaîne de résultats (GAR) : Impact, Effet, Extrant.</summary>
        public string Level { get; set; } = "Extrant";
        /// <summary>Valeur de référence (situation de départ).</summary>
        public double? BaselineValue { get; set; }
        /// <summary>Comment cumuler les mesures d'une période : Somme (personnes formées…) ou Dernière (taux, surface…).</summary>
        public string Aggregation { get; set; } = "Somme";

        public ICollection<IndicatorMeasurement> Measurements { get; set; } = new List<IndicatorMeasurement>();
        
        public int ProjectId { get; set; }
        public Project? Project { get; set; }
    }
}
