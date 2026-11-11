using System;
using System.Threading.Tasks;
using System.Windows;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using AFMI_Gestion_projet.Services;

namespace AFMI_Gestion_projet.ViewModels
{
    /// <summary>Mise à jour automatique : bandeau « nouvelle version », téléchargement vérifié, installation silencieuse.</summary>
    public partial class MainViewModel
    {
        private UpdateManifest? _pendingUpdate;

        [ObservableProperty] private bool _isUpdateBannerVisible;
        [ObservableProperty] private string _updateMessage = "";
        [ObservableProperty] private string _updateNotes = "";
        [ObservableProperty, NotifyPropertyChangedFor(nameof(IsUpdateIdle))] private bool _isUpdateBusy;
        public bool IsUpdateIdle => !IsUpdateBusy;
        [ObservableProperty] private double _updateProgress;

        public string InstalledVersionLabel => $"Version {UpdateService.InstalledVersion}";

        /// <summary>Recherche en arrière-plan au démarrage (sauf démonstration ou paramètre désactivé), sans bloquer l'interface.</summary>
        private void StartUpdateCheck()
        {
            if (IsDemoMode || !UpdateService.AutoCheckEnabled()) return;
            _ = Task.Run(async () =>
            {
                await Task.Delay(TimeSpan.FromSeconds(10));
                try
                {
                    var m = await UpdateService.CheckAsync();
                    if (m != null) Application.Current?.Dispatcher.Invoke(() => ShowUpdate(m));
                }
                catch (Exception ex)
                {
                    // Hors ligne ou manifeste refusé : silencieux au démarrage, consigné pour le support
                    System.Diagnostics.Debug.WriteLine($"Mise à jour : {ex.Message}");
                }
            });
        }

        private void ShowUpdate(UpdateManifest m)
        {
            _pendingUpdate = m;
            UpdateMessage = $"Nouvelle version {m.Version} disponible (installée : {UpdateService.InstalledVersion}).";
            UpdateNotes = m.Notes;
            UpdateProgress = 0;
            IsUpdateBannerVisible = true;
        }

        [RelayCommand]
        private async Task CheckUpdatesNow()
        {
            if (IsUpdateBusy) return;
            IsUpdateBusy = true;
            try
            {
                var m = await UpdateService.CheckAsync();
                if (m != null) ShowUpdate(m);
                else MessageBox.Show($"Vous utilisez la dernière version ({UpdateService.InstalledVersion}).", "Mises à jour",
                    MessageBoxButton.OK, MessageBoxImage.Information);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Recherche de mise à jour impossible : {ex.Message}", "Mises à jour", MessageBoxButton.OK, MessageBoxImage.Warning);
            }
            finally { IsUpdateBusy = false; }
        }

        [RelayCommand]
        private void DismissUpdate() => IsUpdateBannerVisible = false;

        [RelayCommand]
        private async Task InstallUpdate()
        {
            if (_pendingUpdate == null || IsUpdateBusy) return;
            var m = _pendingUpdate;
            if (MessageBox.Show($"Installer la version {m.Version} maintenant ?\n\nUne sauvegarde de la base est faite d'abord. " +
                                "L'application se ferme pendant l'installation (une à deux minutes) puis redémarre seule.",
                    "Mise à jour", MessageBoxButton.OKCancel, MessageBoxImage.Question) != MessageBoxResult.OK) return;
            IsUpdateBusy = true;
            try
            {
                UpdateMessage = $"Téléchargement de la version {m.Version}…";
                var progress = new Progress<double>(p => UpdateProgress = p * 100);
                string installer = await UpdateService.DownloadAsync(m, progress);
                UpdateMessage = "Fichier vérifié (signature et empreinte). Sauvegarde de la base et lancement de l'installation…";
                UpdateService.BackupAndLaunch(installer, m);
                Application.Current.Shutdown();
            }
            catch (Exception ex)
            {
                UpdateMessage = $"Mise à jour non installée : {ex.Message}";
                IsUpdateBusy = false;
            }
        }
    }
}
