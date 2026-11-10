namespace AFMI_Gestion_projet.Finance
{
    /// <summary>
    /// Répartit un montant selon une clé (pourcentages ou poids) sans perdre de centime :
    /// méthode du plus fort reste, la somme des parts est toujours égale au total.
    /// </summary>
    public static class AllocationSplitter
    {
        public static long[] Split(long totalMinor, IReadOnlyList<decimal> weights)
        {
            if (totalMinor < 0) throw new ArgumentOutOfRangeException(nameof(totalMinor), "Montant négatif.");
            if (weights.Count == 0) throw new ArgumentException("Clé de répartition vide.", nameof(weights));
            if (weights.Any(w => w < 0)) throw new ArgumentException("Poids négatif dans la clé de répartition.", nameof(weights));
            decimal sum = weights.Sum();
            if (sum == 0) throw new ArgumentException("La somme des poids est nulle.", nameof(weights));

            var exact = weights.Select(w => totalMinor * w / sum).ToArray();
            var parts = exact.Select(e => (long)decimal.Floor(e)).ToArray();
            long remainder = totalMinor - parts.Sum();
            foreach (int i in Enumerable.Range(0, parts.Length)
                         .OrderByDescending(i => exact[i] - parts[i]).ThenBy(i => i).Take((int)remainder))
            {
                parts[i]++;
            }
            return parts;
        }
    }
}
