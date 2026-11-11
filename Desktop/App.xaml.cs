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

            // Restauration demandée depuis Paramètres › Sauvegardes : appliquée avant toute ouverture de la base,
            // après une sauvegarde de sécurité de la base courante.
            try
            {
                string db = Data.DatabasePaths.GetDatabasePath();
                string? restored = Services.BackupService.ApplyPendingRestore(db, Services.BackupService.FolderFromDatabase(db));
                if (restored != null)
                    MessageBox.Show($"La sauvegarde {System.IO.Path.GetFileName(restored)} a été restaurée.\nLa base précédente a été conservée (motif « avant_restauration »).",
                        "AFMI Smart Admin — restauration", MessageBoxButton.OK, MessageBoxImage.Information);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Restauration annulée : {ex.Message}\nLa base actuelle est inchangée.", "AFMI Smart Admin — restauration",
                    MessageBoxButton.OK, MessageBoxImage.Warning);
            }

            // Mise à jour du schéma avant toute fenêtre : sauvegarde automatique puis migrations EF Core.
            // En cas d'échec, la transaction est annulée et l'application s'arrête au lieu de travailler sur une base incohérente.
            try
            {
                using var db = new Data.AppDbContext();
            }
            catch (Exception ex)
            {
                string dbPath = Data.DatabasePaths.GetDatabasePath();
                MessageBox.Show(
                    "La mise à jour de la base de données a échoué. Aucune donnée n'a été modifiée.\n\n" +
                    $"Détail : {ex.GetBaseException().Message}\n\n" +
                    $"Base : {dbPath}\nSauvegardes : {Data.DatabasePaths.GetBackupDirectory(dbPath)}",
                    "AFMI Smart Admin — mise à jour impossible", MessageBoxButton.OK, MessageBoxImage.Error);
                Shutdown(1);
            }
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


