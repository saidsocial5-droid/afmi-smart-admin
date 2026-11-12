using System.Windows;
using System.Windows.Controls;
using AFMI_Gestion_projet.ViewModels;

namespace AFMI_Gestion_projet.Views
{
    public partial class ProjectDetailView : UserControl
    {
        private ProjectDetailViewModel? _vm;
        private bool _editorReady;

        public ProjectDetailView()
        {
            InitializeComponent();
            Loaded += async (_, _) =>
            {
                if (_editorReady) return;
                try
                {
                    await ReportEditor.EnsureCoreWebView2Async(await Services.WebViewEnvironment.GetAsync());
                    _editorReady = true;
                    ApplyEditorUri();
                }
                catch (System.Exception ex)
                {
                    if (_vm != null) _vm.ReportEditorStatus = "Composant WebView2 indisponible : " + ex.Message;
                }
            };
            DataContextChanged += (_, e) =>
            {
                if (_vm != null) _vm.PropertyChanged -= OnVmPropertyChanged;
                _vm = e.NewValue as ProjectDetailViewModel;
                if (_vm != null) _vm.PropertyChanged += OnVmPropertyChanged;
                ApplyEditorUri();
            };
        }

        private void OnVmPropertyChanged(object? sender, System.ComponentModel.PropertyChangedEventArgs e)
        {
            if (e.PropertyName == nameof(ProjectDetailViewModel.ReportEditorUri)) ApplyEditorUri();
        }

        private readonly System.Collections.Generic.HashSet<string> _loadedTabs = new();

        /// <summary>
        /// Onglets Smart Office de la fiche projet (Vue 360°, Comptes rendus & PV, Dossier du bailleur) : chargés à la première ouverture, ce qui
        /// démarre Smart Office si besoin.
        /// </summary>
        private async void OnProjectTabChanged(object sender, SelectionChangedEventArgs e)
        {
            if (e.OriginalSource != sender || _vm == null) return;
            var selected = ((TabControl)sender).SelectedItem;
            var (browser, status, route) = ReferenceEquals(selected, MeetingsTab) ? (MeetingsBrowser, MeetingsStatus, "meetings-embed")
                : ReferenceEquals(selected, OverviewTab) ? (OverviewBrowser, OverviewStatus, "project360-embed")
                : ReferenceEquals(selected, DossierTab) ? (DossierBrowser, DossierStatus, "dossier-embed") : (null, null, "");
            if (browser == null || status == null || !_loadedTabs.Add(route)) return;
            try
            {
                await browser.EnsureCoreWebView2Async(await Services.WebViewEnvironment.GetAsync());
                string url = await Services.SmartOfficeHostService.Instance.EnsureStartedAsync();
                browser.Source = new System.Uri($"{url}/?afmi_token={Services.SmartOfficeHostService.Instance.SessionToken}#{route}/{_vm.Project.Id}");
                status.Visibility = Visibility.Collapsed;
            }
            catch (System.Exception ex)
            {
                _loadedTabs.Remove(route);
                status.Text = "Indisponible : " + ex.Message;
            }
        }

        /// <summary>Le document n'est chargé qu'une fois WebView2 initialisé avec le profil de l'application.</summary>
        private void ApplyEditorUri()
        {
            if (!_editorReady || _vm?.ReportEditorUri is not { } uri) return;
            if (ReportEditor.Source?.AbsoluteUri != uri.AbsoluteUri) ReportEditor.Source = uri;
        }

        private void OnCancelTaskClick(object sender, RoutedEventArgs e)
        {
            if (DataContext is ProjectDetailViewModel vm)
            {
                vm.IsTaskEditVisible = false;
            }
        }

        private void OnCancelCostClick(object sender, RoutedEventArgs e)
        {
            if (DataContext is ProjectDetailViewModel vm)
            {
                vm.IsCostEditVisible = false;
            }
        }

        private void OnCancelStepClick(object sender, RoutedEventArgs e)
        {
            if (DataContext is ProjectDetailViewModel vm)
            {
                vm.IsStepEditVisible = false;
            }
        }

        private void OnCancelDocumentUploadClick(object sender, RoutedEventArgs e)
        {
            if (DataContext is ProjectDetailViewModel vm)
            {
                vm.IsDocumentUploadVisible = false;
            }
        }

        private void OnCancelDocumentPreviewClick(object sender, RoutedEventArgs e)
        {
            if (DataContext is ProjectDetailViewModel vm)
            {
                vm.IsDocumentPreviewVisible = false;
            }
        }

        private void OnCancelWorkProgramClick(object sender, RoutedEventArgs e)
        {
            if (DataContext is ProjectDetailViewModel vm)
            {
                vm.IsWorkProgramModalVisible = false;
            }
        }
    }
}


