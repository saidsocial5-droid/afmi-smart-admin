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
                PageUri = new Uri(url + "/");
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
