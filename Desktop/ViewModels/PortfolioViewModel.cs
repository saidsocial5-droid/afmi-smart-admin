using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.IO;
using System.Linq;
using System.Windows.Input;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using AFMI_Gestion_projet.Data;
using AFMI_Gestion_projet.Models;
using AFMI_Gestion_projet.Services;

namespace AFMI_Gestion_projet.ViewModels
{
    public class ProjectComparisonData
    {
        public Project Project { get; set; } = null!;
        public double AverageProgress { get; set; }
        public EvmMetrics Metrics { get; set; } = null!;
    }

    public partial class PortfolioViewModel : ObservableObject
    {
        private readonly MainViewModel _mainVM;
        private readonly ExportService _exportService;
        private readonly EvmService _evmService;

        [ObservableProperty]
        private string _searchText = string.Empty;

        [ObservableProperty]
        private string _selectedStatusFilter = "Tous";

        [ObservableProperty]
        private string _selectedPriorityFilter = "Tous";

        [ObservableProperty]
        private bool _isEditDialogVisible = false;

        [ObservableProperty]
        private Project _editingProject = new();

        [ObservableProperty]
        private bool _isCompareVisible = false;

        public ObservableCollection<Project> Projects { get; } = new();
        
        // Projects checked/selected by user in the grid for comparison
        public ObservableCollection<Project> SelectedProjectsForAction { get; } = new();

        public ObservableCollection<ProjectComparisonData> ComparedProjects { get; } = new();
        public ObservableCollection<Funder> AvailableFunders { get; } = new();

        public List<string> Statuses { get; } = new() { "Tous", "Initiation", "Planification", "Exécution", "Clôture", "Archivé" };
        public List<string> Priorities { get; } = new() { "Tous", "Basse", "Moyenne", "Haute", "Critique" };

        public ICommand RefreshCommand { get; }
        public ICommand SearchCommand { get; }
        public ICommand ClearFiltersCommand { get; }
        public ICommand OpenAddDialogCommand { get; }
        public ICommand OpenEditDialogCommand { get; }
        public ICommand SaveProjectCommand { get; }
        public ICommand ArchiveProjectCommand { get; }
        public ICommand DeleteProjectCommand { get; }
        public ICommand ViewProjectDetailCommand { get; }
        public ICommand ExportCsvCommand { get; }
        public ICommand CompareSelectedCommand { get; }
        public ICommand CloseCompareCommand { get; }
        public ICommand ExportViewCommand { get; }
        public ICommand ImportViewCommand { get; }

        private readonly Services.InternalAiAgentService _aiService;
        public ICommand ImproveDescriptionCommand { get; }

        public PortfolioViewModel(MainViewModel mainVM)
        {
            _mainVM = mainVM;
            _exportService = new ExportService();
            _evmService = new EvmService();

            RefreshCommand = new RelayCommand(RefreshData);
            SearchCommand = new RelayCommand(ApplyFilters);
            ClearFiltersCommand = new RelayCommand(ClearFilters);
            OpenAddDialogCommand = new RelayCommand(OpenAddDialog);
            OpenEditDialogCommand = new RelayCommand<Project>(OpenEditDialog);
            SaveProjectCommand = new RelayCommand(SaveProject);
            ArchiveProjectCommand = new RelayCommand<Project>(ArchiveProject);
            DeleteProjectCommand = new RelayCommand<Project>(DeleteProject);
            _aiService = new Services.InternalAiAgentService();
            ImproveDescriptionCommand = new AsyncRelayCommand(ImproveDescriptionAsync);
            ViewProjectDetailCommand = new RelayCommand<Project>(ViewProjectDetail);
            ExportCsvCommand = new RelayCommand(ExportCsv);
            CompareSelectedCommand = new RelayCommand(CompareSelectedProjects);
            CloseCompareCommand = new RelayCommand(() => IsCompareVisible = false);
            ExportViewCommand = new RelayCommand(ExportViewSettings);
            ImportViewCommand = new RelayCommand(ImportViewSettings);

            RefreshData();
        }

        partial void OnSelectedStatusFilterChanged(string value) => ApplyFilters();
        partial void OnSelectedPriorityFilterChanged(string value) => ApplyFilters();

        public void RefreshData()
        {
            LoadFunders();
            ApplyFilters();
        }

        private void LoadFunders()
        {
            try
            {
                using var db = new AppDbContext();
                AvailableFunders.Clear();
                foreach (var f in db.Funders.ToList())
                {
                    AvailableFunders.Add(f);
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Error loading funders: {ex.Message}");
            }
        }

        private void ApplyFilters()
        {
            try
            {
                using (var db = new AppDbContext())
                {
                    IQueryable<Project> query = db.Projects;

                    // Apply Search Text
                    if (!string.IsNullOrWhiteSpace(SearchText))
                    {
                        string lowerSearch = SearchText.ToLower();
                        query = query.Where(p => p.Name.ToLower().Contains(lowerSearch) || 
                                                 p.Code.ToLower().Contains(lowerSearch) ||
                                                 p.Manager.ToLower().Contains(lowerSearch) ||
                                                 p.Client.ToLower().Contains(lowerSearch) ||
                                                 p.Department.ToLower().Contains(lowerSearch));
                    }

                    // Apply Status Filter
                    if (SelectedStatusFilter != "Tous")
                    {
                        query = query.Where(p => p.Status == SelectedStatusFilter);
                    }

                    // Apply Priority Filter
                    if (SelectedPriorityFilter != "Tous")
                    {
                        query = query.Where(p => p.Priority == SelectedPriorityFilter);
                    }

                    var list = query.OrderBy(p => p.TargetEndDate).ToList();

                    // Load tasks for each project to calculate average progress in memory
                    foreach (var p in list)
                    {
                        db.Entry(p).Collection(proj => proj.Tasks).Load();
                    }

                    Projects.Clear();
                    foreach (var p in list)
                    {
                        Projects.Add(p);
                    }
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Error applying filters: {ex.Message}");
            }
        }

        private void ClearFilters()
        {
            SearchText = string.Empty;
            SelectedStatusFilter = "Tous";
            SelectedPriorityFilter = "Tous";
            ApplyFilters();
        }

        private void OpenAddDialog()
        {
            EditingProject = new Project
            {
                TargetStartDate = DateTime.Today,
                TargetEndDate = DateTime.Today.AddMonths(3),
                Status = "Initiation",
                Priority = "Moyenne"
            };
            IsEditDialogVisible = true;
        }

        private void OpenEditDialog(Project? project)
        {
            if (project == null) return;
            
            // Clone project data to allow cancel
            EditingProject = new Project
            {
                Id = project.Id,
                Code = project.Code,
                Name = project.Name,
                Description = project.Description,
                Manager = project.Manager,
                Owner = project.Owner,
                Client = project.Client,
                Department = project.Department,
                TargetStartDate = project.TargetStartDate,
                TargetEndDate = project.TargetEndDate,
                ActualStartDate = project.ActualStartDate,
                ActualEndDate = project.ActualEndDate,
                Status = project.Status,
                Priority = project.Priority,
                BudgetGlobal = project.BudgetGlobal,
                LessonsLearned = project.LessonsLearned,
                ParentProjectId = project.ParentProjectId,
                FunderId = project.FunderId
            };
            IsEditDialogVisible = true;
        }

        private void SaveProject()
        {
            if (string.IsNullOrWhiteSpace(EditingProject.Name) || string.IsNullOrWhiteSpace(EditingProject.Code))
            {
                // Simple validation failure
                return;
            }

            try
            {
                using (var db = new AppDbContext())
                {
                    if (EditingProject.Id == 0)
                    {
                        // Add Project
                        db.Projects.Add(EditingProject);
                        db.SaveChanges();

                        // Log Creation Audit Trail
                        var audit = new AuditLog
                        {
                            ProjectId = EditingProject.Id,
                            EntityType = "Projet",
                            EntityId = EditingProject.Id,
                            ChangeType = "Création",
                            FieldName = "Projet",
                            NewValue = EditingProject.Name,
                            Timestamp = DateTime.Now
                        };
                        db.AuditLogs.Add(audit);
                        
                        // Seed default workflow steps
                        var defaultSteps = new List<WorkflowStep>
                        {
                            new WorkflowStep { ProjectId = EditingProject.Id, StepName = "Initiation", Order = 1, IsCompleted = false },
                            new WorkflowStep { ProjectId = EditingProject.Id, StepName = "Planification", Order = 2, IsCompleted = false },
                            new WorkflowStep { ProjectId = EditingProject.Id, StepName = "Exécution", Order = 3, IsCompleted = false },
                            new WorkflowStep { ProjectId = EditingProject.Id, StepName = "Clôture", Order = 4, IsCompleted = false }
                        };
                        db.WorkflowSteps.AddRange(defaultSteps);
                        db.SaveChanges();
                    }
                    else
                    {
                        // Update Project
                        var existing = db.Projects.Find(EditingProject.Id);
                        if (existing != null)
                        {
                            // Track changes for Audit Log
                            var changes = new List<AuditLog>();
                            void CheckField(string field, string? oldV, string? newV)
                            {
                                if (oldV != newV)
                                {
                                    changes.Add(new AuditLog
                                    {
                                        ProjectId = existing.Id,
                                        EntityType = "Projet",
                                        EntityId = existing.Id,
                                        ChangeType = "Modification",
                                        FieldName = field,
                                        OldValue = oldV ?? string.Empty,
                                        NewValue = newV ?? string.Empty,
                                        Timestamp = DateTime.Now
                                    });
                                }
                            }

                            CheckField("Nom", existing.Name, EditingProject.Name);
                            CheckField("Code", existing.Code, EditingProject.Code);
                            CheckField("Manager", existing.Manager, EditingProject.Manager);
                            CheckField("Client", existing.Client, EditingProject.Client);
                            CheckField("Statut", existing.Status, EditingProject.Status);
                            CheckField("Budget", existing.BudgetGlobal.ToString(), EditingProject.BudgetGlobal.ToString());

                            existing.Name = EditingProject.Name;
                            existing.Code = EditingProject.Code;
                            existing.Description = EditingProject.Description;
                            existing.Manager = EditingProject.Manager;
                            existing.Owner = EditingProject.Owner;
                            existing.Client = EditingProject.Client;
                            existing.Department = EditingProject.Department;
                            existing.TargetStartDate = EditingProject.TargetStartDate;
                            existing.TargetEndDate = EditingProject.TargetEndDate;
                            existing.ActualStartDate = EditingProject.ActualStartDate;
                            existing.ActualEndDate = EditingProject.ActualEndDate;
                            existing.Status = EditingProject.Status;
                            existing.Priority = EditingProject.Priority;
                            existing.BudgetGlobal = EditingProject.BudgetGlobal;
                            existing.LessonsLearned = EditingProject.LessonsLearned;
                            existing.ParentProjectId = EditingProject.ParentProjectId;

                            db.AuditLogs.AddRange(changes);
                            db.SaveChanges();
                        }
                    }
                }

                IsEditDialogVisible = false;
                RefreshData();
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Error saving project: {ex.Message}");
            }
        }

        private void ArchiveProject(Project? project)
        {
            if (project == null) return;
            try
            {
                using (var db = new AppDbContext())
                {
                    var existing = db.Projects.Find(project.Id);
                    if (existing != null)
                    {
                        existing.Status = "Archivé";
                        
                        db.AuditLogs.Add(new AuditLog
                        {
                            ProjectId = project.Id,
                            EntityType = "Projet",
                            EntityId = project.Id,
                            ChangeType = "Modification",
                            FieldName = "Statut",
                            OldValue = project.Status,
                            NewValue = "Archivé",
                            Timestamp = DateTime.Now
                        });
                        db.SaveChanges();
                    }
                }
                RefreshData();
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Error archiving project: {ex.Message}");
            }
        }

        private void DeleteProject(Project? project)
        {
            if (project == null) return;
            try
            {
                using (var db = new AppDbContext())
                {
                    var existing = db.Projects.Find(project.Id);
                    if (existing != null)
                    {
                        db.Projects.Remove(existing);
                        db.SaveChanges();
                    }
                }
                RefreshData();
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Error deleting project: {ex.Message}");
            }
        }

        private void ViewProjectDetail(Project? project)
        {
            if (project == null) return;
            _mainVM.NavigateToProjectDetail(project.Id);
        }

        private void ExportCsv()
        {
            try
            {
                string downloadsPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Downloads");
                if (!Directory.Exists(downloadsPath))
                {
                    downloadsPath = Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments);
                }
                string filePath = Path.Combine(downloadsPath, $"Portfolio_Projets_{DateTime.Now:yyyyMMdd_HHmmss}.csv");

                _exportService.ExportProjectsToCsv(Projects, filePath);
                
                // Show message or alert in a commercial app, here we write to debug
                System.Diagnostics.Debug.WriteLine($"Portfolio exported to: {filePath}");
                System.Windows.MessageBox.Show($"Le portefeuille a été exporté avec succès dans :\n{filePath}", "Export Réussi", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Information);
            }
            catch (Exception ex)
            {
                System.Windows.MessageBox.Show($"Erreur lors de l'export : {ex.Message}", "Erreur", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Error);
            }
        }

        private void CompareSelectedProjects()
        {
            if (SelectedProjectsForAction.Count < 2)
            {
                System.Windows.MessageBox.Show("Veuillez sélectionner au moins 2 projets (en cochant les cases) pour pouvoir les comparer.", "Sélection insuffisante", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Warning);
                return;
            }

            try
            {
                ComparedProjects.Clear();
                using (var db = new AppDbContext())
                {
                    foreach (var sp in SelectedProjectsForAction)
                    {
                        var p = db.Projects.Find(sp.Id);
                        if (p != null)
                        {
                            db.Entry(p).Collection(proj => proj.Tasks).Load();
                            db.Entry(p).Collection(proj => proj.CostEntries).Load();

                            double progress = 0;
                            if (p.Tasks.Any())
                            {
                                var leafTasks = p.Tasks.Where(t => t.ParentTaskId == null).ToList();
                                progress = leafTasks.Sum(t => t.ProgressPercentage) / Math.Max(1, leafTasks.Count);
                            }

                            ComparedProjects.Add(new ProjectComparisonData
                            {
                                Project = p,
                                AverageProgress = progress,
                                Metrics = _evmService.CalculateMetrics(p)
                            });
                        }
                    }
                }
                IsCompareVisible = true;
            }
            catch (Exception ex)
            {
                System.Windows.MessageBox.Show($"Erreur lors de la comparaison : {ex.Message}", "Erreur", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Error);
            }
        }

        private void ExportViewSettings()
        {
            var sfd = new Microsoft.Win32.SaveFileDialog
            {
                Filter = "Fichiers JSON (*.json)|*.json",
                FileName = "VuePersonnalisee.json",
                Title = "Exporter la vue personnalisée"
            };

            if (sfd.ShowDialog() == true)
            {
                try
                {
                    var settings = new ViewSettings
                    {
                        SearchText = SearchText,
                        SelectedStatusFilter = SelectedStatusFilter,
                        SelectedPriorityFilter = SelectedPriorityFilter
                    };

                    string json = System.Text.Json.JsonSerializer.Serialize(settings, new System.Text.Json.JsonSerializerOptions { WriteIndented = true });
                    File.WriteAllText(sfd.FileName, json);
                }
                catch (Exception ex)
                {
                    System.Windows.MessageBox.Show($"Erreur lors de l'export de la vue: {ex.Message}", "Erreur", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Error);
                }
            }
        }

        private void ImportViewSettings()
        {
            var ofd = new Microsoft.Win32.OpenFileDialog
            {
                Filter = "Fichiers JSON (*.json)|*.json",
                Title = "Importer une vue personnalisée"
            };

            if (ofd.ShowDialog() == true)
            {
                try
                {
                    string json = File.ReadAllText(ofd.FileName);
                    var settings = System.Text.Json.JsonSerializer.Deserialize<ViewSettings>(json);

                    if (settings != null)
                    {
                        SearchText = settings.SearchText ?? string.Empty;
                        SelectedStatusFilter = settings.SelectedStatusFilter ?? "Tous";
                        SelectedPriorityFilter = settings.SelectedPriorityFilter ?? "Tous";
                        ApplyFilters();
                    }
                }
                catch (Exception ex)
                {
                    System.Windows.MessageBox.Show($"Erreur lors de l'import de la vue: {ex.Message}", "Erreur", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Error);
                }
            }
        }

        private async Task ImproveDescriptionAsync()
        {
            if (EditingProject == null || string.IsNullOrWhiteSpace(EditingProject.Description))
            {
                System.Windows.MessageBox.Show("La description est vide.", "Information", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Information);
                return;
            }

            try
            {
                using var db = new AppDbContext();
                var settings = db.AiSettings.FirstOrDefault();
                if (settings != null)
                {
                    _aiService.UseLocalOllamaIfAvailable = settings.UseOllama;
                    _aiService.OllamaEndpoint = settings.OllamaEndpoint;
                    _aiService.OllamaModel = settings.OllamaModel;
                    _aiService.UseCloudApi = settings.UseCloudApi;
                    _aiService.CloudProvider = settings.CloudProvider ?? "OpenAI";
                    _aiService.CloudApiKey = settings.CloudApiKey ?? string.Empty;
                }

                var analysis = await _aiService.ReformulateTextAsync(
                    EditingProject.Description,
                    Services.ReformulationGoal.AmeliorerStyle,
                    Services.ReformulationTone.ProfessionnelFormel,
                    EditingProject
                );

                if (!string.IsNullOrWhiteSpace(analysis.ProcessedText))
                {
                    EditingProject.Description = analysis.ProcessedText;
                }
            }
            catch (Exception ex)
            {
                System.Windows.MessageBox.Show($"Erreur lors de l'appel à l'Agent IA : {ex.Message}", "Erreur IA", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Error);
            }
        }
    }

    public class ViewSettings
    {
        public string SearchText { get; set; } = string.Empty;
        public string SelectedStatusFilter { get; set; } = "Tous";
        public string SelectedPriorityFilter { get; set; } = "Tous";
    }
}
