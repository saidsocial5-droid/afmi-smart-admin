using System;
using System.Threading.Tasks;
using System.Windows.Input;
using AFMI_Gestion_projet.Services;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace AFMI_Gestion_projet.ViewModels
{
    /// <summary>
    /// Module « Smart Office » : agents IA, OCR financier, radar d'appels à projets, mémoire institutionnelle.
    /// L'interface web est servie par le backend Python et affichée dans un WebView2.
    /// </summary>
    public partial class SmartOfficeViewModel : ObservableObject
    {
        [ObservableProperty]
        private bool _isLoading;

        [ObservableProperty]
        private bool _hasError;

        [ObservableProperty]
        private string _statusMessage = string.Empty;

        [ObservableProperty]
        private Uri? _pageUri;

        public ICommand RetryCommand { get; }

        /// <summary>Onglet demandé (ex. « settings ») : transmis à la page par le fragment d'URL.</summary>
        private string? _tab;
        private string? _baseUri;

        public void OpenTab(string? tab)
        {
            _tab = tab;
            if (_baseUri != null) PageUri = BuildUri();
        }

        private Uri BuildUri() => new($"{_baseUri}#{_tab ?? "dashboard"}");

        public SmartOfficeViewModel()
        {
            RetryCommand = new AsyncRelayCommand(StartAsync);
        }

        public async Task StartAsync()
        {
            if (IsLoading) return;

            IsLoading = true;
            HasError = false;
            StatusMessage = "Démarrage du moteur Smart Office (agents IA, OCR, radar)…";
            try
            {
                string url = await SmartOfficeHostService.Instance.EnsureStartedAsync();
                // La page reçoit le jeton une fois ; le backend le remplace par un cookie HttpOnly.
                _baseUri = $"{url}/?afmi_token={SmartOfficeHostService.Instance.SessionToken}";
                PageUri = BuildUri();
                StatusMessage = string.Empty;
            }
            catch (Exception ex)
            {
                HasError = true;
                StatusMessage = ex.Message;
            }
            finally
            {
                IsLoading = false;
            }
        }
    }
}
