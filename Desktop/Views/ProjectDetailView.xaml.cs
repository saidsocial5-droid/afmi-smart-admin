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

        private bool _meetingsLoaded;

        /// <summary>Onglet « Comptes rendus & PV » : chargé à la première ouverture (démarre Smart Office si besoin).</summary>
        private async void OnProjectTabChanged(object sender, SelectionChangedEventArgs e)
        {
            if (e.OriginalSource != sender || _meetingsLoaded || !ReferenceEquals(((TabControl)sender).SelectedItem, MeetingsTab) || _vm == null) return;
            _meetingsLoaded = true;
            try
            {
                await MeetingsBrowser.EnsureCoreWebView2Async(await Services.WebViewEnvironment.GetAsync());
                string url = await Services.SmartOfficeHostService.Instance.EnsureStartedAsync();
                MeetingsBrowser.Source = new System.Uri($"{url}/?afmi_token={Services.SmartOfficeHostService.Instance.SessionToken}#meetings-embed/{_vm.Project.Id}");
                MeetingsStatus.Visibility = Visibility.Collapsed;
            }
            catch (System.Exception ex)
            {
                _meetingsLoaded = false;
                MeetingsStatus.Text = "Comptes rendus indisponibles : " + ex.Message;
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


