using System.Globalization;

namespace AFMI_Gestion_projet.Finance
{
    /// <summary>Montants en unités mineures (centimes). Toutes les devises gérées ont 2 décimales.</summary>
    public static class Money
    {
        public const string DefaultCurrency = "MAD";
        private static readonly CultureInfo French = CultureInfo.GetCultureInfo("fr-FR");

        public static long ToMinor(decimal amount) => (long)decimal.Round(amount * 100m, 0, MidpointRounding.AwayFromZero);

        public static decimal FromMinor(long minor) => minor / 100m;

        public static string Format(long minor, string currency = DefaultCurrency) =>
            FromMinor(minor).ToString("N2", French) + " " + currency;

        public static string NormalizeCurrency(string? code)
        {
            string c = (code ?? string.Empty).Trim().ToUpperInvariant();
            if (c is "DH" or "DHS") c = "MAD";
            if (c.Length != 3 || !c.All(char.IsAsciiLetterUpper))
                throw new ArgumentException($"Code devise ISO 4217 attendu (MAD, EUR, USD…) : « {code} ».", nameof(code));
            return c;
        }
    }
}
