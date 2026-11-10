using AFMI_Gestion_projet.Models.Finance;

namespace AFMI_Gestion_projet.Finance
{
    public sealed class MissingExchangeRateException(string currency, DateOnly date)
        : InvalidOperationException($"Aucun taux {currency}/MAD connu au {date:dd/MM/yyyy} ou avant. Saisissez le taux : il n'est jamais deviné.")
    {
        public string Currency { get; } = currency;
        public DateOnly Date { get; } = date;
    }

    public static class CurrencyConverter
    {
        /// <summary>Taux à appliquer : le plus récent dont la date est antérieure ou égale à <paramref name="date"/>.</summary>
        public static decimal FindRate(IEnumerable<CurrencyRate> rates, string currency, DateOnly date)
        {
            currency = Money.NormalizeCurrency(currency);
            if (currency == Money.DefaultCurrency) return 1m;
            var rate = rates.Where(r => r.Currency == currency && r.Date <= date).OrderByDescending(r => r.Date).FirstOrDefault();
            return rate?.RateToMad ?? throw new MissingExchangeRateException(currency, date);
        }

        /// <summary>Contre-valeur en MAD, arrondie au centime (arrondi commercial).</summary>
        public static long ToMadMinor(long amountMinor, decimal rateToMad) =>
            (long)decimal.Round(amountMinor * rateToMad, 0, MidpointRounding.AwayFromZero);
    }
}
