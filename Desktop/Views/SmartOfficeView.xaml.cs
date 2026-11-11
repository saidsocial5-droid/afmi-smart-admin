using System;
using System.ComponentModel;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using AFMI_Gestion_projet.ViewModels;
using Microsoft.Web.WebView2.Core;

namespace AFMI_Gestion_projet.Views
{
    public partial class SmartOfficeView : UserControl
    {
        private SmartOfficeViewModel? _viewModel;
        private bool _webViewReady;

        public SmartOfficeView()
        {
            InitializeComponent();
            DataContextChanged += OnDataContextChanged;
            Loaded += OnLoaded;
        }

        private async void OnLoaded(object sender, RoutedEventArgs e)
        {
            if (_webViewReady) return;
            try
            {
                // Profil WebView2 dans LocalAppData : le dossier de l'exécutable peut être en lecture seule.
                string userData = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "AFMIGestionProjet", "WebView2");
                var env = await CoreWebView2Environment.CreateAsync(null, userData);
                await WebView.EnsureCoreWebView2Async(env);
                WebView.CoreWebView2.NewWindowRequested += OnNewWindowRequested;
                _webViewReady = true;
                ApplyState();
            }
            catch (Exception ex)
            {
                if (_viewModel != null)
                {
                    _viewModel.HasError = true;
                    _viewModel.StatusMessage = "Le composant Microsoft Edge WebView2 est indisponible : " + ex.Message;
                }
            }
        }

        private async void OnDataContextChanged(object sender, DependencyPropertyChangedEventArgs e)
        {
            if (_viewModel != null) _viewModel.PropertyChanged -= OnViewModelPropertyChanged;
            _viewModel = e.NewValue as SmartOfficeViewModel;
            if (_viewModel == null) return;

            _viewModel.PropertyChanged += OnViewModelPropertyChanged;
            ApplyState();
            if (_viewModel.PageUri == null) await _viewModel.StartAsync();
        }

        private void OnViewModelPropertyChanged(object? sender, PropertyChangedEventArgs e)
        {
            if (e.PropertyName is nameof(SmartOfficeViewModel.PageUri)
                or nameof(SmartOfficeViewModel.IsLoading)
                or nameof(SmartOfficeViewModel.HasError))
            {
                ApplyState();
            }
        }

        private void ApplyState()
        {
            if (_viewModel == null) return;

            bool showPage = _webViewReady && _viewModel.PageUri != null && !_viewModel.IsLoading && !_viewModel.HasError;
            StatusOverlay.Visibility = showPage ? Visibility.Collapsed : Visibility.Visible;

            // Comparaison sur l'URL complète : Uri.Equals ignore le fragment (#settings), qui sélectionne l'onglet
            if (showPage && WebView.Source?.AbsoluteUri != _viewModel.PageUri!.AbsoluteUri)
            {
                WebView.Source = _viewModel.PageUri;
            }
        }

        private void OnNewWindowRequested(object? sender, CoreWebView2NewWindowRequestedEventArgs e)
        {
            // Liens externes (portails bailleurs, flux RSS) : navigateur par défaut, pas une fenêtre WebView2.
            e.Handled = true;
            if (Uri.TryCreate(e.Uri, UriKind.Absolute, out var uri) && (uri.Scheme == Uri.UriSchemeHttp || uri.Scheme == Uri.UriSchemeHttps))
            {
                System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo { FileName = uri.AbsoluteUri, UseShellExecute = true });
            }
        }
    }
}
