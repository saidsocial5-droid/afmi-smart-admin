using System.Collections.ObjectModel;
using AFMI_Gestion_projet.Data;
using AFMI_Gestion_projet.Finance;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace AFMI_Gestion_projet.ViewModels.Treasury
{
    /// <summary>Prévision de trésorerie 3, 6 ou 12 mois et alertes.</summary>
    public partial class TreasuryViewModel
    {
        public static IReadOnlyList<Option<int>> HorizonOptions { get; } =
            new[] { new Option<int>(3, "3 mois"), new Option<int>(6, "6 mois"), new Option<int>(12, "12 mois") };

        [ObservableProperty] private Option<int> _horizon = HorizonOptions[1];
        public ObservableCollection<ForecastRow> ForecastMonths { get; } = new();
        public ObservableCollection<string> ForecastNotes { get; } = new();
        public ObservableCollection<AlertRow> Alerts { get; } = new();
        [ObservableProperty] private string _forecastSummary = string.Empty;

        partial void OnHorizonChanged(Option<int> value) => RefreshForecast();

        [RelayCommand]
        private void RefreshForecast()
        {
            ForecastMonths.Clear();
            ForecastNotes.Clear();
            Alerts.Clear();
            try
            {
                using var db = new AppDbContext();
                var forecast = new TreasuryForecastService(db).Forecast(Today, Horizon.Value);
                foreach (var m in forecast.Months) ForecastMonths.Add(new ForecastRow(m));
                foreach (var n in forecast.Notes) ForecastNotes.Add(n);
                ForecastSummary = $"Trésorerie consolidée au {Today:dd/MM/yyyy} : {Money.Format(forecast.StartingMadMinor)}   |   " +
                                  $"Point bas sur {Horizon.Label} : {Money.Format(forecast.LowestClosingMadMinor)}";
                foreach (var a in new TreasuryAlertService(db).GetAlerts(Today)) Alerts.Add(new AlertRow(a));
            }
            catch (Exception ex) when (ex is MissingExchangeRateException or InvalidOperationException)
            {
                ForecastSummary = "Prévision indisponible : " + ex.Message;
            }
        }
    }
}
