using System.Configuration;
using System.Data;
using System.Windows;

namespace AFMI_Gestion_projet
{
    public partial class App : Application
    {
        protected override void OnStartup(StartupEventArgs e)
        {
            base.OnStartup(e);

            AppDomain.CurrentDomain.UnhandledException += (s, args) =>
            {
                ShowExceptionDialog(args.ExceptionObject as Exception, "AppDomain Unhandled Exception");
            };

            DispatcherUnhandledException += (s, args) =>
            {
                ShowExceptionDialog(args.Exception, "Dispatcher Unhandled Exception");
                args.Handled = true; // Keep app alive
            };
        }

        protected override void OnExit(ExitEventArgs e)
        {
            // Arrête le backend Python Smart Office lancé par l'application.
            Services.SmartOfficeHostService.Instance.Stop();
            base.OnExit(e);
        }

        private static void ShowExceptionDialog(Exception? ex, string title)
        {
            if (ex == null) return;
            System.Diagnostics.Debug.WriteLine($"[FATAL ERROR] {title}: {ex}");
            string detail = ex.InnerException != null ? $"{ex.Message}\n\n[Détails] : {ex.InnerException.Message}" : ex.Message;
            MessageBox.Show($"Une erreur est survenue lors de cette action :\n\n{detail}\n\nL'application va poursuivre son fonctionnement.", title, MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }
}


