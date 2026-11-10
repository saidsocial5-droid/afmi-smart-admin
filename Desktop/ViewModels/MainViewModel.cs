using System;
using System.IO;
using System.Linq;
using System.Windows.Input;
using Microsoft.EntityFrameworkCore;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using AFMI_Gestion_projet.Data;
using AFMI_Gestion_projet.Models;
using AFMI_Gestion_projet.Services;

namespace AFMI_Gestion_projet.ViewModels
{
    public partial class MainViewModel : ObservableObject
    {
        [ObservableProperty]
        private ObservableObject? _currentViewModel;

        [ObservableProperty]
        private string _activeViewName = "Tableau de Bord";

        [ObservableProperty]
        private int _notificationCount = 0;

        [ObservableProperty]
        private bool _isSmtpConfigVisible = false;

        [ObservableProperty]
        private SmtpSettings _smtpConfig = new();

        // ViewModels
        public DashboardViewModel DashboardVM { get; }
        public PortfolioViewModel PortfolioVM { get; }
        public TemplateViewModel TemplateVM { get; }
        public AiAssistantViewModel AiAssistantVM { get; }
        public FundersViewModel FundersVM { get; }
        public SmartOfficeViewModel SmartOfficeVM { get; }

        public ICommand NavigateCommand { get; }
        public ICommand OpenSmtpConfigCommand { get; }
        public ICommand SaveSmtpSettingsCommand { get; }
        public ICommand ExportDbCommand { get; }
        public ICommand ImportDbCommand { get; }

        public MainViewModel()
        {
            // Initialize Database and Seed data
            using (var db = new AppDbContext())
            {
                DatabaseInitializer.Initialize(db);
            }

            // Run rolling database backup
            AutoBackupDatabase();

            // Check and process SMTP email scheduling
            CheckScheduledReports();

            // Instantiate child ViewModels
            DashboardVM = new DashboardViewModel(this);
            PortfolioVM = new PortfolioViewModel(this);
            TemplateVM = new TemplateViewModel(this);
            AiAssistantVM = new AiAssistantViewModel(this);
            FundersVM = new FundersViewModel(this);
            SmartOfficeVM = new SmartOfficeViewModel();

            // Set Initial View
            CurrentViewModel = DashboardVM;
            ActiveViewName = "Tableau de Bord";

            // Wire up navigation command
            NavigateCommand = new RelayCommand<string>(Navigate);
            OpenSmtpConfigCommand = new RelayCommand(OpenSmtpConfig);
            SaveSmtpSettingsCommand = new RelayCommand(SaveSmtpSettings);
            ExportDbCommand = new RelayCommand(ExportDatabase);
            ImportDbCommand = new RelayCommand(ImportDatabase);

            UpdateGlobalNotifications();
        }

        public void Navigate(string? destination)
        {
            if (string.IsNullOrEmpty(destination)) return;

            switch (destination.ToLower())
            {
                case "dashboard":
                    CurrentViewModel = DashboardVM;
                    ActiveViewName = "Tableau de Bord";
                    DashboardVM.RefreshData();
                    break;
                case "portfolio":
                    CurrentViewModel = PortfolioVM;
                    ActiveViewName = "Portefeuille de Projets";
                    PortfolioVM.RefreshData();
                    break;
                case "templates":
                    CurrentViewModel = TemplateVM;
                    ActiveViewName = "Bibliothèque de Modèles";
                    TemplateVM.RefreshData();
                    break;
                case "ai_assistant":
                    CurrentViewModel = AiAssistantVM;
                    ActiveViewName = "Agent IA Interne (Gratuit & Hors-ligne)";
                    AiAssistantVM.RefreshProjects();
                    break;
                case "funders":
                    CurrentViewModel = FundersVM;
                    ActiveViewName = "Bailleurs de Fonds";
                    FundersVM.LoadFunders();
                    break;
                case "smart_office":
                    CurrentViewModel = SmartOfficeVM;
                    ActiveViewName = "Smart Office — Agents IA, OCR & Radar";
                    break;
            }
        }

        public void NavigateToProjectDetail(int projectId)
        {
            var projectDetailVM = new ProjectDetailViewModel(this, projectId);
            CurrentViewModel = projectDetailVM;
            ActiveViewName = $"Projet : {projectDetailVM.Project.Name}";
        }

        public void NavigateToAiAssistantWithProject(int projectId)
        {
            CurrentViewModel = AiAssistantVM;
            ActiveViewName = "Agent IA Interne (Gratuit & Hors-ligne)";
            AiAssistantVM.RefreshProjects(projectId);
        }

        public void UpdateGlobalNotifications()
        {
            try
            {
                using (var db = new AppDbContext())
                {
                    var today = DateTime.Today;
                    // Count incomplete tasks past their target end date
                    int lateTasks = 0;
                    foreach (var p in db.Projects)
                    {
                        lateTasks += db.Tasks.Count(t => t.ProjectId == p.Id && t.Status != "Terminé" && t.TargetEndDate < today);
                    }
                    NotificationCount = lateTasks;
                }
            }
            catch
            {
                NotificationCount = 0;
            }
        }

        private void AutoBackupDatabase()
        {
            try
            {
                string dbPath = DatabasePaths.GetDatabasePath();
                string folder = Path.GetDirectoryName(dbPath)!;
                
                if (File.Exists(dbPath))
                {
                    string backupFolder = Path.Combine(folder, "Backups");
                    if (!Directory.Exists(backupFolder))
                    {
                        Directory.CreateDirectory(backupFolder);
                    }
                    
                    // Maintain last 5 rolling backups
                    string backupPath = Path.Combine(backupFolder, $"database_backup_{DateTime.Now:yyyyMMdd_HHmmss}.db");
                    File.Copy(dbPath, backupPath, true);
                    
                    var files = Directory.GetFiles(backupFolder, "database_backup_*.db")
                                         .OrderBy(f => File.GetCreationTime(f))
                                         .ToList();
                                         
                    while (files.Count > 5)
                    {
                        File.Delete(files[0]);
                        files.RemoveAt(0);
                    }
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Auto backup failed: {ex.Message}");
            }
        }

        private void CheckScheduledReports()
        {
            try
            {
                using (var db = new AppDbContext())
                {
                    // Ensure SMTP settings exist
                    var settings = db.SmtpSettings.FirstOrDefault();
                    if (settings == null)
                    {
                        settings = new SmtpSettings
                        {
                            Server = string.Empty,
                            Port = 587,
                            Username = string.Empty,
                            Password = string.Empty,
                            RecipientEmail = string.Empty,
                            ScheduleType = "Aucun"
                        };
                        db.SmtpSettings.Add(settings);
                        db.SaveChanges();
                    }

                    if (settings.ScheduleType == "Aucun") return;

                    bool sendNeeded = false;
                    var now = DateTime.Now;

                    if (settings.LastSentDate == null)
                    {
                        sendNeeded = true;
                    }
                    else if (settings.ScheduleType == "Hebdomadaire" && (now - settings.LastSentDate.Value).TotalDays >= 7)
                    {
                        sendNeeded = true;
                    }
                    else if (settings.ScheduleType == "Mensuel" && (now - settings.LastSentDate.Value).TotalDays >= 30)
                    {
                        sendNeeded = true;
                    }

                    if (sendNeeded)
                    {
                        // Get the first project to report on
                        var project = db.Projects.FirstOrDefault();
                        if (project != null)
                        {
                            // Load tasks collection
                            db.Entry(project).Collection(p => p.Tasks).Load();

                            string tempPath = Path.Combine(Path.GetTempPath(), $"Rapport_Automatique_{project.Code}_{now:yyyyMMdd}.pdf");
                            
                            var reportGenerator = new ReportGeneratorService();
                            reportGenerator.GenerateProgressReportPdf(project, tempPath);

                            var mailService = new MailService();
                            bool success = mailService.SendReport(settings, tempPath, $"Avancement Automatique ({settings.ScheduleType})");

                            settings.LastSentDate = now;
                            settings.LastSentSuccess = success;
                            db.SaveChanges();

                            // Cleanup temp file
                            if (File.Exists(tempPath))
                            {
                                try { File.Delete(tempPath); } catch { }
                            }
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Scheduled report checker failed: {ex.Message}");
            }
        }

        private void OpenSmtpConfig()
        {
            using (var db = new AppDbContext())
            {
                var settings = db.SmtpSettings.FirstOrDefault();
                if (settings == null)
                {
                    settings = new SmtpSettings { ScheduleType = "Aucun" };
                    db.SmtpSettings.Add(settings);
                    db.SaveChanges();
                }
                SmtpConfig = settings;
            }
            IsSmtpConfigVisible = true;
        }

        private void SaveSmtpSettings()
        {
            try
            {
                using (var db = new AppDbContext())
                {
                    var dbSettings = db.SmtpSettings.FirstOrDefault(s => s.Id == SmtpConfig.Id);
                    if (dbSettings != null)
                    {
                        dbSettings.Server = SmtpConfig.Server;
                        dbSettings.Port = SmtpConfig.Port;
                        dbSettings.Username = SmtpConfig.Username;
                        dbSettings.Password = SmtpConfig.Password;
                        dbSettings.RecipientEmail = SmtpConfig.RecipientEmail;
                        dbSettings.ScheduleType = SmtpConfig.ScheduleType;
                        db.SaveChanges();
                    }
                }
                IsSmtpConfigVisible = false;
                System.Windows.MessageBox.Show("Configuration SMTP enregistrée avec succès !", "Succès", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Information);
            }
            catch (Exception ex)
            {
                System.Windows.MessageBox.Show($"Erreur lors de la sauvegarde SMTP : {ex.Message}", "Erreur", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Error);
            }
        }

        private void ExportDatabase()
        {
            var sfd = new Microsoft.Win32.SaveFileDialog
            {
                Filter = "Base de données SQLite (*.db)|*.db",
                FileName = "database_backup.db",
                Title = "Exporter la base de données"
            };

            if (sfd.ShowDialog() == true)
            {
                try
                {
                    string dbPath = DatabasePaths.GetDatabasePath();
                    string folder = Path.GetDirectoryName(dbPath)!;

                    if (File.Exists(dbPath))
                    {
                        File.Copy(dbPath, sfd.FileName, true);
                        System.Windows.MessageBox.Show("Base de données exportée avec succès !", "Succès", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Information);
                    }
                    else
                    {
                        System.Windows.MessageBox.Show("Fichier de base de données introuvable.", "Erreur", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Warning);
                    }
                }
                catch (Exception ex)
                {
                    System.Windows.MessageBox.Show($"Erreur lors de l'exportation: {ex.Message}", "Erreur", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Error);
                }
            }
        }

        private void ImportDatabase()
        {
            var ofd = new Microsoft.Win32.OpenFileDialog
            {
                Filter = "Base de données SQLite (*.db)|*.db",
                Title = "Importer une base de données"
            };

            if (ofd.ShowDialog() == true)
            {
                var result = System.Windows.MessageBox.Show(
                    "Attention : Importer une base de données va remplacer l'intégralité de vos projets et tâches actuels par ceux du fichier importé. Voulez-vous continuer ?",
                    "Confirmation d'importation",
                    System.Windows.MessageBoxButton.YesNo,
                    System.Windows.MessageBoxImage.Warning
                );

                if (result == System.Windows.MessageBoxResult.Yes)
                {
                    try
                    {
                        string dbPath = DatabasePaths.GetDatabasePath();
                        string folder = Path.GetDirectoryName(dbPath)!;

                        // Perform a safety backup of current db before replacing it
                        if (File.Exists(dbPath))
                        {
                            string safetyBackup = Path.Combine(folder, "database_before_import.db");
                            File.Copy(dbPath, safetyBackup, true);
                        }

                        // Close EF connections by clearing the pool
                        using (var dbContext = new AppDbContext())
                        {
                            dbContext.Database.GetDbConnection().Close();
                        }
                        Microsoft.Data.Sqlite.SqliteConnection.ClearAllPools();

                        // Copy imported database
                        File.Copy(ofd.FileName, dbPath, true);

                        // La base importée peut venir d'une version antérieure : elle sera sauvegardée puis migrée
                        // à la prochaine ouverture (ci-dessous). En cas d'échec, l'ancienne base est restaurée.
                        DatabaseMigrator.ForgetMigrationState();
                        try
                        {
                            using var migrated = new AppDbContext();
                        }
                        catch
                        {
                            Microsoft.Data.Sqlite.SqliteConnection.ClearAllPools();
                            string safetyBackup = Path.Combine(folder, "database_before_import.db");
                            if (File.Exists(safetyBackup)) File.Copy(safetyBackup, dbPath, true);
                            DatabaseMigrator.ForgetMigrationState();
                            throw;
                        }

                        System.Windows.MessageBox.Show(
                            "Base de données importée avec succès ! L'application va recharger les données.",
                            "Succès",
                            System.Windows.MessageBoxButton.OK,
                            System.Windows.MessageBoxImage.Information
                        );

                        // Trigger view reload
                        Navigate(ActiveViewName);
                        UpdateGlobalNotifications();
                    }
                    catch (Exception ex)
                    {
                        System.Windows.MessageBox.Show($"Erreur lors de l'importation: {ex.Message}", "Erreur", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Error);
                    }
                }
            }
        }
    }
}
