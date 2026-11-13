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
    public class GanttTaskItem
    {
        public ProjectTask Task { get; set; } = null!;
        public double X { get; set; }
        public double Y { get; set; }
        public double Width { get; set; }
        public int RowIndex { get; set; }
        public bool IsParent { get; set; }
    }

    public class GanttDependencyItem
    {
        public double X1 { get; set; }
        public double Y1 { get; set; }
        public double X2 { get; set; }
        public double Y2 { get; set; }
    }

    public partial class ProjectDetailViewModel : ObservableObject
    {
        private readonly MainViewModel _mainVM;
        private readonly EvmService _evmService;
        private readonly ReportGeneratorService _reportService;
        private readonly ExportService _exportService;
        private readonly DocumentAnalysisService _documentService;

        public int ProjectId { get; }

        [ObservableProperty]
        private Project _project = new();

        [ObservableProperty]
        private EvmMetrics _metrics = new();

        [ObservableProperty]
        private List<SCurvePoint> _sCurveData = new();

        [ObservableProperty]
        private SynthesisResult _synthesis = new();

        // Foundation Documents & Baseline Models
        [ObservableProperty]
        private ProjectDocument _editingDocument = new();

        [ObservableProperty]
        private bool _isDocumentUploadVisible = false;

        // Document preview panel (view extracted text / insights)
        [ObservableProperty]
        private bool _isDocumentPreviewVisible = false;

        [ObservableProperty]
        private string _previewDocumentTitle = string.Empty;

        [ObservableProperty]
        private string _previewDocumentContent = string.Empty;

        [ObservableProperty]
        private string _previewDocumentInsights = string.Empty;

        // Document filters
        [ObservableProperty]
        private string _selectedCategoryFilter = "Toutes";

        [ObservableProperty]
        private string _selectedPhaseFilter = "Toutes";

        [ObservableProperty]
        private ProjectBaseline _baseline = new();


        [ObservableProperty]
        private BaselineDiagnosticResult _baselineDiagnostic = new();

        // Automatic Work Program & Proposal Generation
        [ObservableProperty]
        private GeneratedWorkProgram _generatedProgram = new();

        [ObservableProperty]
        private bool _isWorkProgramModalVisible = false;


        // Active Editing Models
        [ObservableProperty]
        private ProjectTask _editingTask = new();

        [ObservableProperty]
        private bool _isTaskEditVisible = false;

        [ObservableProperty]
        private CostEntry _editingCost = new();

        [ObservableProperty]
        private bool _isCostEditVisible = false;

        [ObservableProperty]
        private WorkflowStep _editingStep = new();

        [ObservableProperty]
        private bool _isStepEditVisible = false;

        // Custom report settings
        [ObservableProperty]
        private string _reportThemeColor = "#2B579A";

        [ObservableProperty]
        private string _selectedReportType = "Rapport d'Avancement";

        [ObservableProperty]
        private string _selectedExportFormat = "PDF";

        [ObservableProperty]
        private string _previewTitle = string.Empty;

        [ObservableProperty]
        private string _previewContent = string.Empty;

        [ObservableProperty]
        private bool _isPreviewVisible = false;

        // Éditeur de type Word (Smart Office) intégré à l'onglet Rapports : le rapport y devient un document modifiable
        [ObservableProperty]
        [NotifyPropertyChangedFor(nameof(IsReportEditorVisible))]
        private Uri? _reportEditorUri;

        [ObservableProperty]
        private string _reportEditorStatus = string.Empty;

        public bool IsReportEditorVisible => ReportEditorUri != null;

        private static readonly System.Net.Http.HttpClient EditorHttp = new() { Timeout = TimeSpan.FromSeconds(90) };

        public List<string> ReportTypes { get; } = new() 
        { 
            "Rapport d'Avancement", 
            "Rapport Financier", 
            "Bilan Final de Clôture",
            "Rapport de Conformité Bailleur"
        };
        public ObservableCollection<string> AvailableExportFormats { get; } = new() { "PDF", "Word" };

        // Activity Report Wizard (ONG)
        [ObservableProperty]
        private ActivityReportWizardViewModel? _activityReportWizard;

        [ObservableProperty]
        private bool _isActivityReportWizardVisible = false;

        // Filter options
        public List<string> CategoryFilterOptions { get; } = new()
        {
            "Toutes",
            "Convention / Accord de Financement Bailleur",
            "Dossier de Montage & Fiche Projet Initiale",
            "Budget Initial Approuvé",
            "Étude de Faisabilité & Diagnostic",
            "Cadre Logique & Matrice d'Indicateurs",
            "Correspondance & Avenant Contractuel"
        };

        public List<string> PhaseFilterOptions { get; } = new()
        {
            "Toutes", "Diagnostic", "Montage", "Rédaction", "Exécution", "Évaluation", "Clôture"
        };

        // Lists
        public ObservableCollection<ProjectDocument> Documents { get; } = new();
        public ObservableCollection<ProjectDocument> FilteredDocuments { get; } = new();
        public ObservableCollection<Funder> AvailableFunders { get; } = new();

        public List<string> DocumentCategories { get; } = new()
        {
            "Convention / Accord de Financement Bailleur",
            "Dossier de Montage & Fiche Projet Initiale",
            "Budget Initial Approuvé",
            "Étude de Faisabilité & Diagnostic",
            "Cadre Logique & Matrice d'Indicateurs",
            "Correspondance & Avenant Contractuel"
        };

        public List<string> DocumentPhases { get; } = new()
        {
            "Diagnostic", "Montage", "Rédaction", "Exécution", "Évaluation", "Clôture"
        };

        public ObservableCollection<ProjectTask> RootTasks { get; } = new();
        public ObservableCollection<ProjectTask> AllTasksFlat { get; } = new();
        public ObservableCollection<CostEntry> CostEntries { get; } = new();
        public ObservableCollection<WorkflowStep> WorkflowSteps { get; } = new();
        public ObservableCollection<AuditLog> AuditLogs { get; } = new();
        public ObservableCollection<ReportHistory> ReportHistories { get; } = new();
        
        // Gantt chart items
        public ObservableCollection<GanttTaskItem> GanttTasks { get; } = new();
        public ObservableCollection<GanttDependencyItem> GanttDependencies { get; } = new();
        [ObservableProperty]
        private DateTime _ganttMinDate = DateTime.Today;
        [ObservableProperty]
        private DateTime _ganttMaxDate = DateTime.Today.AddMonths(3);

        // Command definitions
        public ICommand SaveTaskCommand { get; }
        public ICommand OpenAddTaskCommand { get; }
        public ICommand OpenEditTaskCommand { get; }
        public ICommand DeleteTaskCommand { get; }
        public ICommand SaveCostCommand { get; }
        public ICommand OpenAddCostCommand { get; }
        public ICommand DeleteCostCommand { get; }
        public ICommand ToggleStepCommand { get; }
        public ICommand SaveStepCommand { get; }
        public ICommand OpenAddStepCommand { get; }
        public ICommand DeleteStepCommand { get; }

        // Foundation Documents & Baseline actions
        public ICommand OpenUploadDocumentCommand { get; }
        public ICommand SaveDocumentCommand { get; }
        public ICommand DeleteDocumentCommand { get; }
        public ICommand OpenDocumentFileCommand { get; }
        public ICommand PreviewDocumentCommand { get; }
        public ICommand RunDeepAnalysisCommand { get; }
        public ICommand SyncWbsFromBaselineCommand { get; }
        public ICommand GeneratePdfDonorComplianceCommand { get; }
        public ICommand BrowseDocumentFileCommand { get; }
        public ICommand BrowseMultipleDocumentsCommand { get; }
        public ICommand ApplyDocumentFilterCommand { get; }
        public ICommand GenerateWorkProgramCommand { get; }
        public ICommand ExportWorkProgramToWordCommand { get; }
        public ICommand ApplyWorkProgramToWbsCommand { get; }
        
        // Report actions
        public ICommand GeneratePdfProgressCommand { get; }
        public ICommand GeneratePdfFinancialCommand { get; }
        public ICommand GeneratePdfCloseoutCommand { get; }
        public ICommand OpenReportCommand { get; }
        public ICommand ShowPreviewCommand { get; }
        public ICommand ExportReportCommand { get; }
        
        // ONG / CR
        public ICommand OpenActivityReportWizardCommand { get; }
        
        // Export budget
        public ICommand ExportBudgetCsvCommand { get; }
        public ICommand GoBackCommand { get; }
        public ICommand OpenAiAssistantForProjectCommand { get; }
        public ICommand ImproveDescriptionCommand { get; }
        public ICommand ImproveTaskDescriptionCommand { get; }
        public ICommand ImproveDocumentDescriptionCommand { get; }
        public ICommand ImproveCostDescriptionCommand { get; }
        public ICommand SaveProjectFunderCommand { get; }
        public ICommand CreateProjectFoldersCommand { get; }
        public ICommand OpenProjectFolderCommand { get; }

        private readonly ProjectFolderService _folderService;
        private readonly InternalAiAgentService _aiService;

        // Computed / aliased properties for bindings
        public ObservableCollection<ProjectDocument> ProjectDocuments => FilteredDocuments;

        public bool HasDiagnostic => !string.IsNullOrEmpty(BaselineDiagnostic?.ExecutiveSummary);
        public bool HasComplianceAlerts => BaselineDiagnostic?.ComplianceAlerts?.Count > 0;
        public bool HasExtractedObjectives => BaselineDiagnostic?.ExtractedObjectives?.Count > 0;
        public bool HasKnowledgeBase => !string.IsNullOrEmpty(BaselineDiagnostic?.KnowledgeBaseSummary);

        // Phase coverage summaries for the UI
        public string DiagnosticPhaseDocs => GetPhaseDocCount("Diagnostic");
        public string MontagePhaseDocs => GetPhaseDocCount("Montage");
        public string RedactionPhaseDocs => GetPhaseDocCount("Rédaction");
        public string ExecutionPhaseDocs => GetPhaseDocCount("Exécution");
        public string EvaluationPhaseDocs => GetPhaseDocCount("Évaluation");
        public string CloturePhaseDocs => GetPhaseDocCount("Clôture");

        private string GetPhaseDocCount(string phase)
        {
            int count = BaselineDiagnostic?.DocumentsPerPhase?.GetValueOrDefault(phase, 0) ?? 0;
            return count > 0 ? $"{count} doc(s)" : "0 — Manquant";
        }

        // Also expose TotalSpent from BaselineDiagnostic which is computed in LoadProjectData
        public ProjectDetailViewModel(MainViewModel mainVM, int projectId)
        {
            _mainVM = mainVM;
            ProjectId = projectId;
            _evmService = new EvmService();
            _reportService = new ReportGeneratorService();
            _exportService = new ExportService();
            _documentService = new DocumentAnalysisService();
            _folderService = new ProjectFolderService();
            _aiService = new InternalAiAgentService();

            CreateProjectFoldersCommand = new RelayCommand(CreateProjectFolders);
            OpenProjectFolderCommand = new RelayCommand(OpenProjectFolder);

            SaveTaskCommand = new RelayCommand(SaveTask);
            OpenAddTaskCommand = new RelayCommand<ProjectTask>(OpenAddTask);
            OpenEditTaskCommand = new RelayCommand<ProjectTask>(OpenEditTask);
            DeleteTaskCommand = new RelayCommand<ProjectTask>(DeleteTask);

            SaveCostCommand = new RelayCommand(SaveCost);
            OpenAddCostCommand = new RelayCommand(OpenAddCost);
            DeleteCostCommand = new RelayCommand<CostEntry>(DeleteCost);

            ToggleStepCommand = new RelayCommand<WorkflowStep>(ToggleStep);
            SaveStepCommand = new RelayCommand(SaveStep);
            OpenAddStepCommand = new RelayCommand(OpenAddStep);
            DeleteStepCommand = new RelayCommand<WorkflowStep>(DeleteStep);

            // Foundation Documents & Baseline commands
            OpenUploadDocumentCommand = new RelayCommand(OpenUploadDocument);
            SaveDocumentCommand = new RelayCommand(SaveDocument);
            DeleteDocumentCommand = new RelayCommand<ProjectDocument>(DeleteDocument);
            OpenDocumentFileCommand = new RelayCommand<ProjectDocument>(OpenDocumentFile);
            PreviewDocumentCommand = new RelayCommand<ProjectDocument>(PreviewDocument);
            RunDeepAnalysisCommand = new RelayCommand(RunDeepAnalysis);
            SyncWbsFromBaselineCommand = new RelayCommand(SyncWbsFromBaseline);
            GeneratePdfDonorComplianceCommand = new RelayCommand(GenerateDonorComplianceReport);
            BrowseDocumentFileCommand = new RelayCommand(BrowseDocumentFile);
            BrowseMultipleDocumentsCommand = new RelayCommand(BrowseMultipleDocuments);
            ApplyDocumentFilterCommand = new RelayCommand(ApplyDocumentFilter);
            GenerateWorkProgramCommand = new RelayCommand(GenerateWorkProgram);
            ExportWorkProgramToWordCommand = new RelayCommand(ExportWorkProgramToWordFile);
            ApplyWorkProgramToWbsCommand = new RelayCommand(ApplyWorkProgramToWbs);


            GeneratePdfProgressCommand = new RelayCommand(GenerateProgressReport);
            GeneratePdfFinancialCommand = new RelayCommand(GenerateFinancialReport);
            GeneratePdfCloseoutCommand = new RelayCommand(GenerateCloseoutReport);
            OpenReportCommand = new RelayCommand<ReportHistory>(OpenReportFile);
            ShowPreviewCommand = new RelayCommand(ShowReportPreview);
            ExportReportCommand = new RelayCommand(ExportReportToFile);
            
            OpenActivityReportWizardCommand = new RelayCommand<ProjectTask>(OpenActivityReportWizard);

            ExportBudgetCsvCommand = new RelayCommand(ExportBudgetCsv);
            GoBackCommand = new RelayCommand(() => _mainVM.Navigate("portfolio"));
            OpenAiAssistantForProjectCommand = new RelayCommand(() => _mainVM.NavigateToAiAssistantWithProject(ProjectId));
            ImproveDescriptionCommand = new AsyncRelayCommand(ImproveDescriptionAsync);
            ImproveTaskDescriptionCommand = new AsyncRelayCommand(ImproveTaskDescriptionAsync);
            ImproveDocumentDescriptionCommand = new AsyncRelayCommand(ImproveDocumentDescriptionAsync);
            ImproveCostDescriptionCommand = new AsyncRelayCommand(ImproveCostDescriptionAsync);
            SaveProjectFunderCommand = new RelayCommand(SaveProjectFunder);

            LoadProjectData();
        }




        private void SaveProjectFunder()
        {
            try
            {
                using var db = new AppDbContext();
                var proj = db.Projects.Find(ProjectId);
                if (proj != null)
                {
                    proj.FunderId = Project.FunderId;
                    db.SaveChanges();
                    System.Windows.MessageBox.Show("Configuration du bailleur enregistrée avec succès. La charte graphique et les en-têtes seront appliqués aux prochains rapports générés pour ce projet.", "Succès", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Information);
                    LoadProjectData();
                }
            }
            catch (Exception ex)
            {
                System.Windows.MessageBox.Show($"Erreur lors de la sauvegarde : {ex.Message}", "Erreur", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Error);
            }
        }

        private void OpenActivityReportWizard(ProjectTask? task)
        {
            if (task == null) return;
            ActivityReportWizard = new ActivityReportWizardViewModel(task.Id, ProjectId)
            {
                OnWizardCompleted = () =>
                {
                    IsActivityReportWizardVisible = false;
                    ActivityReportWizard = null;
                    LoadProjectData();
                },
                OnWizardCancelled = () =>
                {
                    IsActivityReportWizardVisible = false;
                    ActivityReportWizard = null;
                }
            };
            IsActivityReportWizardVisible = true;
        }

        public void LoadProjectData()
        {
            try
            {
                using (var db = new AppDbContext())
                {
                    Project = db.Projects.Find(ProjectId) ?? new Project();
                    if (Project.Id == 0) return;

                    // Load relations
                    db.Entry(Project).Collection(p => p.Tasks).Load();
                    db.Entry(Project).Collection(p => p.CostEntries).Load();
                    db.Entry(Project).Collection(p => p.WorkflowSteps).Load();
                    db.Entry(Project).Collection(p => p.AuditLogs).Load();
                    db.Entry(Project).Collection(p => p.ReportHistories).Load();
                    db.Entry(Project).Collection(p => p.Documents).Load();
                    db.Entry(Project).Reference(p => p.Baseline).Load();
                    db.Entry(Project).Reference(p => p.Funder).Load();

                    AvailableFunders.Clear();
                    foreach (var funder in db.Funders.ToList())
                    {
                        AvailableFunders.Add(funder);
                    }

                    // WBS tree parsing
                    AllTasksFlat.Clear();
                    RootTasks.Clear();
                    var allTasks = Project.Tasks.ToList();
                    
                    foreach (var t in allTasks)
                    {
                        AllTasksFlat.Add(t);
                    }

                    var roots = allTasks.Where(t => t.ParentTaskId == null).OrderBy(t => t.TargetStartDate).ToList();
                    foreach (var r in roots)
                    {
                        LoadTaskSubTree(r, allTasks);
                        RootTasks.Add(r);
                    }

                    // Cost entries
                    CostEntries.Clear();
                    foreach (var c in Project.CostEntries.OrderByDescending(c => c.Date))
                    {
                        CostEntries.Add(c);
                    }

                    // Workflow steps
                    WorkflowSteps.Clear();
                    foreach (var s in Project.WorkflowSteps.OrderBy(s => s.Order))
                    {
                        WorkflowSteps.Add(s);
                    }

                    // Audit Logs
                    AuditLogs.Clear();
                    foreach (var log in Project.AuditLogs.OrderByDescending(l => l.Timestamp))
                    {
                        AuditLogs.Add(log);
                    }

                    // Report histories
                    ReportHistories.Clear();
                    foreach (var r in Project.ReportHistories.OrderByDescending(rh => rh.GeneratedDate))
                    {
                        ReportHistories.Add(r);
                    }

                    // Foundation Documents
                    Documents.Clear();
                    FilteredDocuments.Clear();
                    foreach (var d in Project.Documents.OrderByDescending(doc => doc.UploadedDate))
                    {
                        Documents.Add(d);
                        FilteredDocuments.Add(d);
                    }

                    // Contractual Baseline
                    if (Project.Baseline != null)
                    {
                        Baseline = Project.Baseline;
                    }
                    else
                    {
                        Baseline = new ProjectBaseline { ProjectId = ProjectId };
                    }

                    // Run baseline diagnostic
                    BaselineDiagnostic = _documentService.PerformDeepDiagnostic(Project);

                    // EVM & Synthesis recalculation
                    Metrics = _evmService.CalculateMetrics(Project);
                    SCurveData = _evmService.GetSCurveData(Project, 12);
                    Synthesis = _reportService.GenerateSynthesis(Project);

                    // Gantt coordinate plotting
                    BuildGanttTimeline();
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Error loading project detail data: {ex.Message}");
            }
        }

        private void LoadTaskSubTree(ProjectTask parent, List<ProjectTask> allTasks)
        {
            parent.SubTasks = allTasks.Where(t => t.ParentTaskId == parent.Id).OrderBy(t => t.TargetStartDate).ToList();
            foreach (var child in parent.SubTasks)
            {
                LoadTaskSubTree(child, allTasks);
            }
        }

        #region WBS Task Actions
        private void OpenAddTask(ProjectTask? parentTask)
        {
            EditingTask = new ProjectTask
            {
                ProjectId = ProjectId,
                ParentTaskId = parentTask?.Id,
                TargetStartDate = parentTask?.TargetStartDate ?? Project.TargetStartDate ?? DateTime.Today,
                TargetEndDate = parentTask?.TargetEndDate ?? Project.TargetEndDate ?? DateTime.Today.AddDays(14),
                Status = "À faire"
            };
            IsTaskEditVisible = true;
        }

        private void OpenEditTask(ProjectTask? task)
        {
            if (task == null) return;
            EditingTask = new ProjectTask
            {
                Id = task.Id,
                ProjectId = task.ProjectId,
                ParentTaskId = task.ParentTaskId,
                Name = task.Name,
                Description = task.Description,
                Assignee = task.Assignee,
                TargetStartDate = task.TargetStartDate,
                TargetEndDate = task.TargetEndDate,
                ActualStartDate = task.ActualStartDate,
                ActualEndDate = task.ActualEndDate,
                ProgressPercentage = task.ProgressPercentage,
                Status = task.Status,
                Budget = task.Budget,
                Cost = task.Cost,
                Predecessors = task.Predecessors
            };
            IsTaskEditVisible = true;
        }

        private void SaveTask()
        {
            if (string.IsNullOrWhiteSpace(EditingTask.Name)) return;

            try
            {
                using (var db = new AppDbContext())
                {
                    if (EditingTask.Id == 0)
                    {
                        // Insert Task
                        db.Tasks.Add(EditingTask);
                        db.SaveChanges();

                        db.AuditLogs.Add(new AuditLog
                        {
                            ProjectId = ProjectId,
                            EntityType = "Tâche",
                            EntityId = EditingTask.Id,
                            ChangeType = "Création",
                            FieldName = "Nom",
                            NewValue = EditingTask.Name,
                            Timestamp = DateTime.Now
                        });
                    }
                    else
                    {
                        // Update Task
                        var existing = db.Tasks.Find(EditingTask.Id);
                        if (existing != null)
                        {
                            var audit = new AuditLog
                            {
                                ProjectId = ProjectId,
                                EntityType = "Tâche",
                                EntityId = existing.Id,
                                ChangeType = "Modification",
                                FieldName = "Plusieurs champs",
                                OldValue = $"Progression: {existing.ProgressPercentage}%, Statut: {existing.Status}",
                                NewValue = $"Progression: {EditingTask.ProgressPercentage}%, Statut: {EditingTask.Status}",
                                Timestamp = DateTime.Now
                            };
                            db.AuditLogs.Add(audit);

                            existing.Name = EditingTask.Name;
                            existing.Description = EditingTask.Description;
                            existing.Assignee = EditingTask.Assignee;
                            existing.TargetStartDate = EditingTask.TargetStartDate;
                            existing.TargetEndDate = EditingTask.TargetEndDate;
                            existing.ActualStartDate = EditingTask.ActualStartDate;
                            existing.ActualEndDate = EditingTask.ActualEndDate;
                            existing.ProgressPercentage = EditingTask.ProgressPercentage;
                            existing.Status = EditingTask.Status;
                            existing.Budget = EditingTask.Budget;
                            existing.Cost = EditingTask.Cost;
                            existing.Predecessors = EditingTask.Predecessors;
                        }
                    }

                    db.SaveChanges();

                    // Automatically recalculate task parent summaries bottom-up
                    RecalculateTaskHierarchy(db);
                }

                IsTaskEditVisible = false;
                LoadProjectData();
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Error saving task: {ex.Message}");
            }
        }

        private void DeleteTask(ProjectTask? task)
        {
            if (task == null) return;
            try
            {
                using (var db = new AppDbContext())
                {
                    var existing = db.Tasks.Find(task.Id);
                    if (existing != null)
                    {
                        db.Tasks.Remove(existing);
                        db.SaveChanges();
                        RecalculateTaskHierarchy(db);
                    }
                }
                LoadProjectData();
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Error deleting task: {ex.Message}");
            }
        }

        private void RecalculateTaskHierarchy(AppDbContext db)
        {
            var tasks = db.Tasks.Where(t => t.ProjectId == ProjectId).ToList();
            var roots = tasks.Where(t => t.ParentTaskId == null).ToList();

            foreach (var root in roots)
            {
                RecalculateTaskNode(root, tasks);
            }

            db.SaveChanges();
        }

        private void RecalculateTaskNode(ProjectTask task, List<ProjectTask> allTasks)
        {
            var children = allTasks.Where(c => c.ParentTaskId == task.Id).ToList();
            if (!children.Any()) return; // Leaf

            foreach (var child in children)
            {
                RecalculateTaskNode(child, allTasks);
            }

            task.TargetStartDate = children.Min(c => c.TargetStartDate);
            task.TargetEndDate = children.Max(c => c.TargetEndDate);
            task.ActualStartDate = children.Min(c => c.ActualStartDate);
            task.ActualEndDate = children.All(c => c.Status == "Terminé") ? children.Max(c => c.ActualEndDate) : null;
            
            task.Budget = children.Sum(c => c.Budget);
            task.Cost = children.Sum(c => c.Cost);
            
            double totalBudget = children.Sum(c => c.Budget);
            if (totalBudget > 0)
            {
                task.ProgressPercentage = children.Sum(c => c.ProgressPercentage * c.Budget) / totalBudget;
            }
            else
            {
                task.ProgressPercentage = children.Average(c => c.ProgressPercentage);
            }

            if (children.All(c => c.Status == "Terminé"))
                task.Status = "Terminé";
            else if (children.All(c => c.Status == "À faire"))
                task.Status = "À faire";
            else if (children.Any(c => c.Status == "Bloqué"))
                task.Status = "Bloqué";
            else
                task.Status = "En cours";
        }
        #endregion

        #region Gantt Chart Construction
        private void BuildGanttTimeline()
        {
            GanttTasks.Clear();
            GanttDependencies.Clear();

            var flatTasks = AllTasksFlat.OrderBy(t => t.TargetStartDate).ToList();
            if (!flatTasks.Any()) return;

            // Find min and max dates to set timeline limits
            var minDate = flatTasks.Min(t => t.TargetStartDate) ?? DateTime.Today;
            var maxDate = flatTasks.Max(t => t.TargetEndDate) ?? DateTime.Today.AddMonths(1);
            
            // Give 5 days buffer on each side
            GanttMinDate = minDate.AddDays(-5);
            GanttMaxDate = maxDate.AddDays(5);

            double totalDays = (GanttMaxDate - GanttMinDate).TotalDays;
            if (totalDays <= 0) totalDays = 30;

            double widthFactor = 800.0 / totalDays; // Width of timeline in pixels
            double rowHeight = 35.0;

            var taskRowMapping = new Dictionary<int, int>();
            int rowIndex = 0;

            // Build vertical WBS order list
            var orderedWbs = new List<ProjectTask>();
            foreach (var root in RootTasks)
            {
                FlattenWbs(root, orderedWbs);
            }

            foreach (var t in orderedWbs)
            {
                taskRowMapping[t.Id] = rowIndex;

                var start = t.TargetStartDate ?? GanttMinDate;
                var end = t.TargetEndDate ?? start.AddDays(1);
                
                double x = (start - GanttMinDate).TotalDays * widthFactor;
                double w = (end - start).TotalDays * widthFactor;
                double y = rowIndex * rowHeight + 10;

                GanttTasks.Add(new GanttTaskItem
                {
                    Task = t,
                    X = x,
                    Y = y,
                    Width = Math.Max(10, w),
                    RowIndex = rowIndex,
                    IsParent = t.SubTasks != null && t.SubTasks.Any()
                });

                rowIndex++;
            }

            // Draw dependencies
            foreach (var gt in GanttTasks)
            {
                if (string.IsNullOrEmpty(gt.Task.Predecessors)) continue;
                
                var parts = gt.Task.Predecessors.Split(',');
                foreach (var part in parts)
                {
                    if (int.TryParse(part, out int predId) && taskRowMapping.TryGetValue(predId, out int predRow))
                    {
                        var predGantt = GanttTasks.FirstOrDefault(t => t.Task.Id == predId);
                        if (predGantt != null)
                        {
                            GanttDependencies.Add(new GanttDependencyItem
                            {
                                X1 = predGantt.X + predGantt.Width,
                                Y1 = predRow * rowHeight + 20,
                                X2 = gt.X,
                                Y2 = gt.RowIndex * rowHeight + 20
                            });
                        }
                    }
                }
            }
        }

        private void FlattenWbs(ProjectTask node, List<ProjectTask> list)
        {
            list.Add(node);
            foreach (var child in node.SubTasks)
            {
                FlattenWbs(child, list);
            }
        }
        #endregion

        #region Cost Ledger Actions
        private void OpenAddCost()
        {
            EditingCost = new CostEntry
            {
                ProjectId = ProjectId,
                Date = DateTime.Today,
                Category = "Divers"
            };
            IsCostEditVisible = true;
        }

        private void SaveCost()
        {
            if (EditingCost.ActualCost < 0 && EditingCost.EstimatedCost < 0) return;

            try
            {
                using (var db = new AppDbContext())
                {
                    if (EditingCost.Id == 0)
                    {
                        db.CostEntries.Add(EditingCost);
                        db.SaveChanges();

                        db.AuditLogs.Add(new AuditLog
                        {
                            ProjectId = ProjectId,
                            EntityType = "Finances",
                            EntityId = EditingCost.Id,
                            ChangeType = "Création",
                            FieldName = "Dépense",
                            NewValue = $"{EditingCost.Category} - {EditingCost.ActualCost} {Project.Currency}",
                            Timestamp = DateTime.Now
                        });
                    }
                    db.SaveChanges();
                }

                IsCostEditVisible = false;
                LoadProjectData();
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Error saving cost entry: {ex.Message}");
            }
        }

        private void DeleteCost(CostEntry? cost)
        {
            if (cost == null) return;
            try
            {
                using (var db = new AppDbContext())
                {
                    var existing = db.CostEntries.Find(cost.Id);
                    if (existing != null)
                    {
                        db.CostEntries.Remove(existing);
                        db.SaveChanges();
                    }
                }
                LoadProjectData();
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Error deleting cost entry: {ex.Message}");
            }
        }
        #endregion

        #region Workflow Steps Actions
        private void ToggleStep(WorkflowStep? step)
        {
            if (step == null) return;
            try
            {
                using (var db = new AppDbContext())
                {
                    var existing = db.WorkflowSteps.Find(step.Id);
                    if (existing != null)
                    {
                        existing.IsCompleted = !existing.IsCompleted;
                        existing.CompletedDate = existing.IsCompleted ? DateTime.Now : null;
                        
                        db.AuditLogs.Add(new AuditLog
                        {
                            ProjectId = ProjectId,
                            EntityType = "Workflow",
                            EntityId = step.Id,
                            ChangeType = "Modification",
                            FieldName = step.StepName,
                            NewValue = existing.IsCompleted ? "Complété" : "Inactif",
                            Timestamp = DateTime.Now
                        });
                        db.SaveChanges();
                    }
                }
                LoadProjectData();
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Error toggling workflow step: {ex.Message}");
            }
        }

        private void OpenAddStep()
        {
            EditingStep = new WorkflowStep
            {
                ProjectId = ProjectId,
                Order = WorkflowSteps.Count + 1
            };
            IsStepEditVisible = true;
        }

        private void SaveStep()
        {
            if (string.IsNullOrWhiteSpace(EditingStep.StepName)) return;

            try
            {
                using (var db = new AppDbContext())
                {
                    db.WorkflowSteps.Add(EditingStep);
                    db.SaveChanges();
                }
                IsStepEditVisible = false;
                LoadProjectData();
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Error saving workflow step: {ex.Message}");
            }
        }

        private void DeleteStep(WorkflowStep? step)
        {
            if (step == null) return;
            try
            {
                using (var db = new AppDbContext())
                {
                    var existing = db.WorkflowSteps.Find(step.Id);
                    if (existing != null)
                    {
                        db.WorkflowSteps.Remove(existing);
                        db.SaveChanges();
                    }
                }
                LoadProjectData();
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Error deleting workflow step: {ex.Message}");
            }
        }
        #endregion

        #region PDF Report Generation Actions
        private void GenerateProgressReport()
        {
            GenerateReport("Avancement", _reportService.GenerateProgressReportPdf);
        }

        private void GenerateFinancialReport()
        {
            GenerateReport("Financier", _reportService.GenerateFinancialReportPdf);
        }

        private void GenerateCloseoutReport()
        {
            GenerateReport("Clôture", _reportService.GenerateCloseoutReportPdf);
        }

        private void GenerateReport(string type, Action<Project, string, string> pdfGenerator)
        {
            try
            {
                string docsDir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "AFMIGestionProjet", "Rapports");
                if (!Directory.Exists(docsDir))
                {
                    Directory.CreateDirectory(docsDir);
                }

                string fileName = $"Rapport_{type}_{Project.Code}_{DateTime.Now:yyyyMMdd_HHmmss}.pdf";
                string fullPath = Path.Combine(docsDir, fileName);

                pdfGenerator(Project, fullPath, ReportThemeColor);

                // Add to database history
                using (var db = new AppDbContext())
                {
                    var history = new ReportHistory
                    {
                        ProjectId = ProjectId,
                        ReportType = type,
                        Title = $"Rapport d'{type} - {DateTime.Now:dd/MM/yyyy HH:mm}",
                        GeneratedDate = DateTime.Now,
                        FilePath = fullPath
                    };
                    db.ReportHistories.Add(history);
                    db.SaveChanges();
                }

                LoadProjectData();
                System.Windows.MessageBox.Show($"Le rapport d'{type} a été généré avec succès :\n{fullPath}", "Rapport Généré", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Information);
            }
            catch (Exception ex)
            {
                System.Windows.MessageBox.Show($"Erreur lors de la génération du rapport : {ex.Message}", "Erreur de génération", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Error);
            }
        }

        private void OpenReportFile(ReportHistory? history)
        {
            if (history == null || !File.Exists(history.FilePath))
            {
                System.Windows.MessageBox.Show("Fichier introuvable. Il a peut-être été déplacé ou supprimé.", "Fichier inexistant", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Warning);
                return;
            }

            try
            {
                System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
                {
                    FileName = history.FilePath,
                    UseShellExecute = true // Opens with default PDF reader on Windows
                });
            }
            catch (Exception ex)
            {
                System.Windows.MessageBox.Show($"Impossible d'ouvrir le fichier : {ex.Message}", "Erreur d'ouverture", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Error);
            }
        }
        #endregion

        #region Foundation Documents & Baseline Actions
        private void OpenUploadDocument()
        {
            // Open blank form — user can fill in metadata and browse the file separately
            EditingDocument = new ProjectDocument
            {
                ProjectId = ProjectId,
                Category = "Convention / Accord de Financement Bailleur",
                DocumentPhase = "Montage",
                SignatureDate = DateTime.Today,
                ContractualEndDate = Project.TargetEndDate,
                ApprovedGrantAmount = Project.BudgetGlobal
            };
            IsDocumentUploadVisible = true;
        }

        private void BrowseDocumentFile()
        {
            var ofd = new Microsoft.Win32.OpenFileDialog
            {
                Title = "Sélectionner un document fondateur",
                Filter = "Tous documents supportés (*.pdf;*.docx;*.doc;*.xlsx;*.xls;*.pptx;*.txt)|*.pdf;*.docx;*.doc;*.xlsx;*.xls;*.pptx;*.txt|Fichiers PDF (*.pdf)|*.pdf|Documents Word (*.docx;*.doc)|*.docx;*.doc|Feuilles Excel (*.xlsx;*.xls)|*.xlsx;*.xls|Tous les fichiers (*.*)|*.*"
            };

            if (ofd.ShowDialog() == true)
            {
                var fileInfo = new FileInfo(ofd.FileName);
                EditingDocument.OriginalFilePath = ofd.FileName;
                EditingDocument.OriginalFileName = fileInfo.Name;
                EditingDocument.FileSize = fileInfo.Length;
                EditingDocument.FileExtension = fileInfo.Extension.ToLower();

                // Auto-fill title from filename if still empty
                if (string.IsNullOrWhiteSpace(EditingDocument.Title))
                {
                    EditingDocument.Title = Path.GetFileNameWithoutExtension(ofd.FileName);
                    OnPropertyChanged(nameof(EditingDocument));
                }
            }
        }

        private void BrowseMultipleDocuments()
        {
            var ofd = new Microsoft.Win32.OpenFileDialog
            {
                Title = "Sélectionner plusieurs documents fondateurs",
                Filter = "Tous documents supportés (*.pdf;*.docx;*.doc;*.xlsx;*.xls;*.txt)|*.pdf;*.docx;*.doc;*.xlsx;*.xls;*.txt|Tous les fichiers (*.*)|*.*",
                Multiselect = true
            };

            if (ofd.ShowDialog() != true || ofd.FileNames.Length == 0) return;
            AddDocumentFiles(ofd.FileNames);
        }

        /// <summary>Documents choisis ou glissés-déposés (Lot 11) : stockage, extraction du texte, analyse.</summary>
        public ICommand DropDocumentsCommand => _dropDocumentsCommand ??= new RelayCommand<string[]>(files => { if (files?.Length > 0) AddDocumentFiles(files); });
        private ICommand? _dropDocumentsCommand;

        private void AddDocumentFiles(IEnumerable<string> paths)
        {
            int successCount = 0;
            var errors = new List<string>();

            foreach (var filePath in paths)
            {
                try
                {
                    var fileInfo = new FileInfo(filePath);
                    var doc = new ProjectDocument
                    {
                        ProjectId = ProjectId,
                        Title = Path.GetFileNameWithoutExtension(filePath),
                        OriginalFileName = fileInfo.Name,
                        FileSize = fileInfo.Length,
                        FileExtension = fileInfo.Extension.ToLower(),
                        Category = "Convention / Accord de Financement Bailleur",
                        DocumentPhase = "Montage",
                        UploadedDate = DateTime.Now
                    };

                    // Store and extract
                    var (storedPath, size, ext) = _documentService.StoreDocumentFile(ProjectId, filePath);
                    doc.FilePath = storedPath;
                    doc.FileSize = size;
                    doc.FileExtension = ext;

                    string fullText = _documentService.ExtractTextFromDocument(storedPath);
                    doc.FullExtractedText = fullText.Length > 50000 ? fullText.Substring(0, 50000) : fullText;
                    doc.ExtractedSummary = fullText.Length > 2000 ? fullText.Substring(0, 2000) + "..." : fullText;

                    var insights = _documentService.AnalyzeDocumentInsights(doc);
                    doc.KeyInsights = _documentService.SerializeInsights(insights);
                    doc.AnalyzedDate = DateTime.Now;

                    using (var db = new AppDbContext())
                    {
                        db.Documents.Add(doc);
                        db.SaveChanges();

                        db.AuditLogs.Add(new AuditLog
                        {
                            ProjectId = ProjectId,
                            EntityType = "Document",
                            EntityId = doc.Id,
                            ChangeType = "Import multiple",
                            FieldName = "Document Fondateur",
                            NewValue = doc.Title,
                            Timestamp = DateTime.Now
                        });
                        db.SaveChanges();
                    }
                    successCount++;
                }
                catch (Exception ex)
                {
                    string errorMsg = GetFullExceptionMessage(ex);
                    errors.Add($"{Path.GetFileName(filePath)}: {errorMsg}");
                }
            }


            LoadProjectData();
            RunDeepAnalysis();

            string msg = $"{successCount} document(s) importé(s) avec succès.";
            if (errors.Count > 0)
                msg += $"\n\nErreurs ({errors.Count}) :\n" + string.Join("\n", errors);

            System.Windows.MessageBox.Show(msg, "Import Multiple", System.Windows.MessageBoxButton.OK,
                errors.Count > 0 ? System.Windows.MessageBoxImage.Warning : System.Windows.MessageBoxImage.Information);
        }

        private void ApplyDocumentFilter()
        {
            FilteredDocuments.Clear();
            foreach (var doc in Documents)
            {
                bool matchCat = SelectedCategoryFilter == "Toutes" || doc.Category == SelectedCategoryFilter;
                bool matchPhase = SelectedPhaseFilter == "Toutes" || doc.DocumentPhase == SelectedPhaseFilter;
                if (matchCat && matchPhase)
                    FilteredDocuments.Add(doc);
            }
        }

        private void PreviewDocument(ProjectDocument? doc)
        {
            if (doc == null) return;

            PreviewDocumentTitle = $"📄 {doc.Title}  [{doc.Category}]";

            // Build content: prefer full extracted text, fallback to summary
            string text = !string.IsNullOrEmpty(doc.FullExtractedText)
                ? doc.FullExtractedText
                : (!string.IsNullOrEmpty(doc.ExtractedSummary) ? doc.ExtractedSummary : "(Aucun texte extrait pour ce document)");

            // Cap display to 10000 chars for UI
            PreviewDocumentContent = text.Length > 10000
                ? text.Substring(0, 10000) + $"\n\n[... {text.Length - 10000} caractères supplémentaires non affichés ...]"
                : text;

            // Build insights summary
            var sb = new System.Text.StringBuilder();
            if (doc.InsightsList.Length > 0)
            {
                sb.AppendLine("■ INFORMATIONS CLÉS EXTRAITES :");
                foreach (var insight in doc.InsightsList)
                    sb.AppendLine($"  • {insight.Trim()}");
            }
            else
            {
                sb.AppendLine("(Aucune information clé extraite — lancez 'Analyse Approfondie' pour analyser ce document)");
            }

            if (doc.AnalyzedDate.HasValue)
                sb.AppendLine($"\nDernière analyse : {doc.AnalyzedDate:dd/MM/yyyy HH:mm}");
            if (doc.ApprovedGrantAmount > 0)
                sb.AppendLine($"Montant conventionné : {doc.ApprovedGrantAmount:N0} {Project.Currency}");
            if (!string.IsNullOrEmpty(doc.DonorName))
                sb.AppendLine($"Bailleur : {doc.DonorName}");
            if (!string.IsNullOrEmpty(doc.DocumentReference))
                sb.AppendLine($"Référence : {doc.DocumentReference}");

            PreviewDocumentInsights = sb.ToString();
            IsDocumentPreviewVisible = true;
        }

        private void SaveDocument()
        {
            if (string.IsNullOrWhiteSpace(EditingDocument.Title))
            {
                System.Windows.MessageBox.Show("Veuillez renseigner au minimum le titre du document.", "Champs requis", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Warning);
                return;
            }

            try
            {
                string sourceFilePath = EditingDocument.OriginalFilePath;

                if (!string.IsNullOrWhiteSpace(sourceFilePath) && File.Exists(sourceFilePath))
                {
                    // Store copy of file in isolated project storage
                    var (storedPath, fileSize, ext) = _documentService.StoreDocumentFile(ProjectId, sourceFilePath);
                    EditingDocument.FilePath = storedPath;
                    EditingDocument.FileSize = fileSize;
                    EditingDocument.FileExtension = ext;

                    // Extract full text and generate summary
                    string fullText = _documentService.ExtractTextFromDocument(storedPath);
                    EditingDocument.FullExtractedText = fullText.Length > 50000 ? fullText.Substring(0, 50000) : fullText;
                    EditingDocument.ExtractedSummary = fullText.Length > 2000 ? fullText.Substring(0, 2000) + "..." : fullText;

                    // Perform initial insight analysis
                    var insights = _documentService.AnalyzeDocumentInsights(EditingDocument);
                    EditingDocument.KeyInsights = _documentService.SerializeInsights(insights);
                    EditingDocument.AnalyzedDate = DateTime.Now;
                }
                else if (string.IsNullOrWhiteSpace(EditingDocument.FilePath))
                {
                    // Allow saving metadata-only documents (e.g. paper documents not yet scanned)
                    EditingDocument.FilePath = string.Empty;
                }

                EditingDocument.UploadedDate = DateTime.Now;

                using (var db = new AppDbContext())
                {
                    db.Documents.Add(EditingDocument);
                    
                    db.AuditLogs.Add(new AuditLog
                    {
                        ProjectId = ProjectId,
                        EntityType = "Document",
                        EntityId = EditingDocument.Id,
                        ChangeType = "Création",
                        FieldName = "Document Fondateur",
                        NewValue = $"{EditingDocument.Title} ({EditingDocument.Category}) — Phase : {EditingDocument.DocumentPhase}",
                        Timestamp = DateTime.Now
                    });

                    db.SaveChanges();
                }

                IsDocumentUploadVisible = false;
                LoadProjectData();
                RunDeepAnalysis();

                System.Windows.MessageBox.Show("Document importé et analysé avec succès ! Le texte a été extrait et les informations clés indexées dans la base de référence du projet.", "Succès", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Information);
            }
            catch (Exception ex)
            {
                System.Windows.MessageBox.Show($"Erreur lors de l'enregistrement du document : {ex.Message}", "Erreur", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Error);
            }
        }

        private void DeleteDocument(ProjectDocument? doc)
        {
            if (doc == null) return;
            var result = System.Windows.MessageBox.Show($"Êtes-vous sûr de vouloir supprimer le document '{doc.Title}' ? Cette action supprimera également le fichier local.", "Confirmation", System.Windows.MessageBoxButton.YesNo, System.Windows.MessageBoxImage.Question);
            if (result != System.Windows.MessageBoxResult.Yes) return;

            try
            {
                using (var db = new AppDbContext())
                {
                    var existing = db.Documents.Find(doc.Id);
                    if (existing != null)
                    {
                        db.Documents.Remove(existing);
                        db.SaveChanges();
                    }
                }

                // Remove local file
                if (File.Exists(doc.FilePath))
                {
                    try { File.Delete(doc.FilePath); } catch { }
                }

                LoadProjectData();
                RunDeepAnalysis();
            }
            catch (Exception ex)
            {
                System.Windows.MessageBox.Show($"Erreur lors de la suppression : {ex.Message}", "Erreur", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Error);
            }
        }

        private void OpenDocumentFile(ProjectDocument? doc)
        {
            if (doc == null || !File.Exists(doc.FilePath))
            {
                System.Windows.MessageBox.Show("Fichier introuvable. Il a peut-être été déplacé ou supprimé.", "Fichier inexistant", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Warning);
                return;
            }

            try
            {
                System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
                {
                    FileName = doc.FilePath,
                    UseShellExecute = true
                });
            }
            catch (Exception ex)
            {
                System.Windows.MessageBox.Show($"Impossible d'ouvrir le fichier : {ex.Message}", "Erreur d'ouverture", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Error);
            }
        }

        private void RunDeepAnalysis()
        {
            try
            {
                BaselineDiagnostic = _documentService.PerformDeepDiagnostic(Project);

                // Persist baseline in database
                using (var db = new AppDbContext())
                {
                    var existingBaseline = db.Baselines.FirstOrDefault(b => b.ProjectId == ProjectId);
                    if (existingBaseline == null)
                    {
                        existingBaseline = new ProjectBaseline
                        {
                            ProjectId = ProjectId
                        };
                        db.Baselines.Add(existingBaseline);
                    }

                    var conventionDoc = Project.Documents.FirstOrDefault(d => !string.IsNullOrEmpty(d.DonorName));
                    existingBaseline.DonorName = conventionDoc?.DonorName ?? (string.IsNullOrEmpty(existingBaseline.DonorName) ? "Bailleur de fonds institutionnel" : existingBaseline.DonorName);
                    existingBaseline.ContractualReference = conventionDoc?.DocumentReference ?? existingBaseline.ContractualReference;
                    existingBaseline.TotalGrantCommitted = BaselineDiagnostic.TotalGrantCommitted;
                    existingBaseline.ComplianceScore = BaselineDiagnostic.ComplianceScore;
                    existingBaseline.DiagnosticSummary = BaselineDiagnostic.ExecutiveSummary;
                    existingBaseline.NextReportingDeadline = BaselineDiagnostic.NextReportDueDate;
                    existingBaseline.LastAnalyzedDate = DateTime.Now;

                    db.SaveChanges();
                    Baseline = existingBaseline;
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Error running deep diagnostic: {ex.Message}");
            }
        }

        private void SyncWbsFromBaseline()
        {
            if (Project.Tasks.Any())
            {
                var result = System.Windows.MessageBox.Show("Le projet contient déjà des tâches WBS. Souhaitez-vous tout de même ajouter les livrables contractuels types issus de la convention bailleur ?", "Ajout de tâches contractuelles", System.Windows.MessageBoxButton.YesNo, System.Windows.MessageBoxImage.Question);
                if (result != System.Windows.MessageBoxResult.Yes) return;
            }

            try
            {
                using (var db = new AppDbContext())
                {
                    var deliverables = new List<(string Name, string Desc, double BudgetShare)>
                    {
                        ("Cadrage initial & Signature de la convention", "Validation des clauses contractuelles et plan de travail bailleur", 0.05),
                        ("Exécution des composantes techniques & livrables", "Réalisation des activités conventionnées", 0.65),
                        ("Audit intermédiaire & Rapport de justification bailleur", "Édition du rapport financier et d'avancement pour la tranche suivante", 0.15),
                        ("Clôture contractuelle & Rapport final d'évaluation", "Rapport final, audit externe et apurement des comptes", 0.15)
                    };

                    double totalGrant = BaselineDiagnostic.TotalGrantCommitted > 0 ? BaselineDiagnostic.TotalGrantCommitted : Project.BudgetGlobal;
                    var start = Project.TargetStartDate ?? DateTime.Today;

                    foreach (var del in deliverables)
                    {
                        db.Tasks.Add(new ProjectTask
                        {
                            ProjectId = ProjectId,
                            Name = del.Name,
                            Description = del.Desc,
                            Budget = totalGrant * del.BudgetShare,
                            Cost = 0,
                            ProgressPercentage = 0,
                            Status = "À faire",
                            TargetStartDate = start,
                            TargetEndDate = start.AddMonths(3)
                        });
                        start = start.AddMonths(2);
                    }

                    db.SaveChanges();
                }

                LoadProjectData();
                System.Windows.MessageBox.Show("Les livrables et tâches contractuels ont été synchronisés dans la WBS avec succès !", "Synchronisation réussie", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Information);
            }
            catch (Exception ex)
            {
                System.Windows.MessageBox.Show($"Erreur lors de la synchronisation : {ex.Message}", "Erreur", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Error);
            }
        }

        private void GenerateDonorComplianceReport()
        {
            GenerateReport("Conformité_Bailleur", _reportService.GenerateDonorComplianceReportPdf);
        }

        private void GenerateWorkProgram()
        {
            try
            {
                GeneratedProgram = _documentService.GenerateWorkProgramFromKnowledgeBase(Project);
                IsWorkProgramModalVisible = true;
            }
            catch (Exception ex)
            {
                System.Windows.MessageBox.Show($"Erreur lors de la génération du programme de travail : {ex.Message}", "Erreur", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Error);
            }
        }

        private void ExportWorkProgramToWordFile()
        {
            if (GeneratedProgram == null || string.IsNullOrEmpty(GeneratedProgram.ProjectName))
            {
                GeneratedProgram = _documentService.GenerateWorkProgramFromKnowledgeBase(Project);
            }

            try
            {
                var sfd = new Microsoft.Win32.SaveFileDialog
                {
                    Title = "Exporter le Programme de Travail en Word",
                    FileName = $"Programme_Travail_{Project.Code}_{DateTime.Now:yyyyMMdd_HHmmss}.docx",
                    Filter = "Document Word (*.docx)|*.docx|Document Word 97-2003 (*.doc)|*.doc|Tous les fichiers (*.*)|*.*"
                };

                if (sfd.ShowDialog() == true)
                {
                    _exportService.ExportWorkProgramToWord(GeneratedProgram, sfd.FileName);
                    System.Windows.MessageBox.Show($"Le programme de travail a été exporté avec succès sous Word !\n\nChemin : {sfd.FileName}", "Export Word Réussi", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Information);
                }
            }
            catch (Exception ex)
            {
                System.Windows.MessageBox.Show($"Erreur lors de l'export Word : {ex.Message}", "Erreur", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Error);
            }
        }

        private void ApplyWorkProgramToWbs()
        {
            if (GeneratedProgram == null || !GeneratedProgram.Activities.Any())
            {
                System.Windows.MessageBox.Show("Aucun programme de travail n'est actuellement disponible.", "Information", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Warning);
                return;
            }

            var confirm = System.Windows.MessageBox.Show(
                $"Voulez-vous intégrer automatiquement les {GeneratedProgram.Activities.Count} activités et les {GeneratedProgram.BudgetLedger.Count} postes budgétaires générés dans la WBS et le registre des dépenses du projet ?",
                "Confirmation d'intégration",
                System.Windows.MessageBoxButton.YesNo,
                System.Windows.MessageBoxImage.Question);

            if (confirm != System.Windows.MessageBoxResult.Yes) return;

            try
            {
                using (var db = new AppDbContext())
                {
                    var start = GeneratedProgram.TargetStartDate;

                    foreach (var act in GeneratedProgram.Activities)
                    {
                        db.Tasks.Add(new ProjectTask
                        {
                            ProjectId = ProjectId,
                            Name = act.Name,
                            Description = $"{act.Description} (Livrable : {act.ExpectedDeliverable})",
                            Assignee = act.ResponsibleRole,
                            Budget = act.EstimatedBudget,
                            Cost = 0,
                            ProgressPercentage = 0,
                            Status = "À faire",
                            TargetStartDate = start,
                            TargetEndDate = start.AddDays(act.DurationWeeks * 7)
                        });
                        start = start.AddDays(14);
                    }

                    foreach (var b in GeneratedProgram.BudgetLedger)
                    {
                        db.CostEntries.Add(new CostEntry
                        {
                            ProjectId = ProjectId,
                            Category = b.Category,
                            Description = b.Description,
                            EstimatedCost = b.EstimatedCost,
                            ActualCost = 0,
                            Date = DateTime.Today,
                            ResourceName = b.FundingSource
                        });
                    }

                    db.AuditLogs.Add(new AuditLog
                    {
                        ProjectId = ProjectId,
                        EntityType = "Projet",
                        EntityId = ProjectId,
                        ChangeType = "Tessetage automatique",
                        FieldName = "WBS & Budget",
                        NewValue = $"{GeneratedProgram.Activities.Count} tâches et {GeneratedProgram.BudgetLedger.Count} lignes budgétaires créées",
                        Timestamp = DateTime.Now
                    });

                    db.SaveChanges();
                }

                IsWorkProgramModalVisible = false;
                LoadProjectData();

                System.Windows.MessageBox.Show("Les activités et le budget prévisionnel ont été intégrés avec succès dans la WBS et les dépenses du projet !", "Intégration Réussi", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Information);
            }
            catch (Exception ex)
            {
                System.Windows.MessageBox.Show($"Erreur lors de l'intégration : {ex.Message}", "Erreur", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Error);
            }
        }
        #endregion


        private void ShowReportPreview()
        {
            try
            {
                var metrics = _evmService.CalculateMetrics(Project);

                if (SelectedReportType == "Rapport d'Avancement")
                {
                    AvailableExportFormats.Clear();
                    AvailableExportFormats.Add("PDF");
                    AvailableExportFormats.Add("Word");
                    SelectedExportFormat = "PDF";

                    // Re-trigger text synthesis if not done
                    if (string.IsNullOrEmpty(Synthesis.ExecutiveSummary))
                    {
                        var reportService = new ReportGeneratorService();
                        Synthesis = reportService.GenerateSynthesis(Project);
                    }

                    string wbsInfo = string.Join("\n", Project.Tasks.Where(t => t.ParentTaskId == null).Select(t => $"- {t.Name} : {t.ProgressPercentage}% ({t.Status})"));

                    PreviewTitle = "RAPPORT D'AVANCEMENT - " + Project.Name;
                    PreviewContent =
                        $"RAPPORT D'AVANCEMENT SYNTHÉTIQUE\n" +
                        $"------------------------------------------------\n" +
                        $"Date d'édition : {DateTime.Now:dd/MM/yyyy HH:mm}\n" +
                        $"Chef de Projet : {Project.Manager}\n" +
                        $"Client cible : {Project.Client}\n" +
                        $"Avancement global physique : {Project.Tasks.Where(t => t.ParentTaskId == null).Sum(t => t.ProgressPercentage) / Math.Max(1, Project.Tasks.Count(t => t.ParentTaskId == null)):F1}%\n" +
                        $"Statut général : {Project.Status}\n" +
                        $"Priorité : {Project.Priority}\n\n" +
                        $"=== SYNTHÈSE DE PERFORMANCE ===\n" +
                        $"{Synthesis.ExecutiveSummary}\n\n" +
                        $"=== RISQUES IDENTIFIÉS ===\n" +
                        $"{string.Join("\n", Synthesis.Risks.Select(r => $"• {r}"))}\n\n" +
                        $"=== ACTIONS CONSEILLÉES ===\n" +
                        $"{string.Join("\n", Synthesis.Actions.Select(a => $"• {a}"))}\n\n" +
                        $"=== RÉSEAU DES TÂCHES PRINCIPALES (WBS) ===\n" +
                        $"{wbsInfo}";
                }
                else if (SelectedReportType == "Rapport Financier")
                {
                    AvailableExportFormats.Clear();
                    AvailableExportFormats.Add("PDF");
                    AvailableExportFormats.Add("Excel");
                    SelectedExportFormat = "PDF";

                    string costLines = string.Join("\n", CostEntries.Select(c => $"- {c.Description} ({c.Category}) : Prévu {c.EstimatedCost:N0} {Project.Currency} | Réel {c.ActualCost:N0} {Project.Currency}"));

                    PreviewTitle = "RAPPORT FINANCIER (EVM) - " + Project.Name;
                    PreviewContent =
                        $"ANALYSE DE PERFORMANCE FINANCIÈRE (EARNED VALUE MANAGEMENT)\n" +
                        $"------------------------------------------------\n" +
                        $"Date d'édition : {DateTime.Now:dd/MM/yyyy HH:mm}\n" +
                        $"Budget Total Alloué (BAC) : {metrics.BAC:N0} {Project.Currency}\n" +
                        $"Valeur Planifiée cumulée (PV) : {metrics.PV:N0} {Project.Currency}\n" +
                        $"Valeur Acquise cumulée (EV) : {metrics.EV:N0} {Project.Currency}\n" +
                        $"Coût Réel cumulé (AC) : {metrics.AC:N0} {Project.Currency}\n\n" +
                        $"=== INDICATEURS CLÉS ===\n" +
                        $"- Indice de Performance Coût (CPI) : {metrics.CPI:F2} ({(metrics.CPI >= 1.0 ? "Sous contrôle budgétaire" : "Risque de dépassement financier")})\n" +
                        $"- Indice de Performance Planning (SPI) : {metrics.SPI:F2} ({(metrics.SPI >= 1.0 ? "Dans les délais" : "Glissement de calendrier")})\n" +
                        $"- Écart Budgétaire (CV) : {metrics.CV:N0} {Project.Currency}\n" +
                        $"- Écart de Planning (SV) : {metrics.SV:N0} {Project.Currency}\n\n" +
                        $"=== ESTIMATIONS À TERMINAISON ===\n" +
                        $"- Coût Total Estimé à terme (EAC) : {metrics.EAC:N0} {Project.Currency}\n" +
                        $"- Reste à Dépenser estimé (ETC) : {metrics.ETC:N0} {Project.Currency}\n" +
                        $"- Écart final estimé (VAC) : {metrics.VAC:N0} {Project.Currency}\n\n" +
                        $"=== TRANSPARENCE DU REGISTRE DE COMPTABILITÉ ===\n" +
                        $"{costLines}";
                }
                else if (SelectedReportType == "Bilan Final de Clôture")
                {
                    AvailableExportFormats.Clear();
                    AvailableExportFormats.Add("PDF");
                    AvailableExportFormats.Add("Word");
                    SelectedExportFormat = "PDF";

                    string lessons = string.IsNullOrWhiteSpace(Project.LessonsLearned) ? "Aucun retour d'expérience enregistré pour ce projet." : Project.LessonsLearned;

                    PreviewTitle = "BILAN FINAL DE CLÔTURE - " + Project.Name;
                    PreviewContent =
                        $"RAPPORT DE CLÔTURE ET RETOURS D'EXPÉRIENCE\n" +
                        $"------------------------------------------------\n" +
                        $"Date d'édition : {DateTime.Now:dd/MM/yyyy HH:mm}\n" +
                        $"Chef de Projet : {Project.Manager}\n" +
                        $"Client destinataire : {Project.Client}\n\n" +
                        $"=== BILAN DES OBJECTIFS ET DU BUDGET ===\n" +
                        $"- Budget Initial : {metrics.BAC:N0} {Project.Currency}\n" +
                        $"- Coût Réel Final : {metrics.AC:N0} {Project.Currency}\n" +
                        $"- Écart Final Constaté : {metrics.BAC - metrics.AC:N0} {Project.Currency} ({(metrics.BAC >= metrics.AC ? "Économie réalisée" : "Surcoût final")})\n" +
                        $"- Nombre total de tâches validées : {Project.Tasks.Count(t => t.Status == "Terminé")} / {Project.Tasks.Count}\n\n" +
                        $"=== RETOURS D'EXPÉRIENCE (LESSONS LEARNED) ===\n" +
                        $"{lessons}\n\n" +
                        $"=== PROTOCOLE D'ARCHIVAGE CONSEILLÉ ===\n" +
                        $"1. Procéder au verrouillage définitif et à l'archivage dans la base de données locale.\n" +
                        $"2. Diffuser ce rapport aux commanditaires.\n" +
                        $"3. Archiver les factures réelles enregistrées dans le registre de dépenses.";
                }
                else if (SelectedReportType == "Rapport de Conformité Bailleur")
                {
                    AvailableExportFormats.Clear();
                    AvailableExportFormats.Add("PDF");
                    AvailableExportFormats.Add("Word");
                    SelectedExportFormat = "PDF";

                    var diag = _documentService.PerformDeepDiagnostic(Project);

                    string docList = Project.Documents.Any() 
                        ? string.Join("\n", Project.Documents.Select(d => $"- {d.Title} ({d.Category}) | Réf: {d.DocumentReference} | Subvention: {d.ApprovedGrantAmount:N0} {Project.Currency}")) 
                        : "Aucun document initial ou convention enregistré.";

                    PreviewTitle = "RAPPORT DE CONFORMITÉ & SUIVI DES CONVENTIONS - " + Project.Name;
                    PreviewContent =
                        $"RAPPORT DE CONFORMITÉ CONTRACTUELLE & SUIVI BAILLEURS\n" +
                        $"------------------------------------------------\n" +
                        $"Date d'édition : {DateTime.Now:dd/MM/yyyy HH:mm}\n" +
                        $"Projet : {Project.Name} ({Project.Code})\n" +
                        $"Responsable : {Project.Manager}\n\n" +
                        $"=== SYNTHÈSE DU DIAGNOSTIC CONTRACTUEL ===\n" +
                        $"{diag.ExecutiveSummary}\n\n" +
                        $"=== INDICATEURS DU SOCLE CONVENTIONNÉ ===\n" +
                        $"- Enveloppe Totale Subvention : {diag.TotalGrantCommitted:N0} {Project.Currency}\n" +
                        $"- Dépenses Réelles Justifiées : {diag.GrantConsumedAmount:N0} {Project.Currency}\n" +
                        $"- Reliquat Disponible : {diag.GrantRemainingAmount:N0} {Project.Currency}\n" +
                        $"- Taux de Consommation Financière : {diag.GrantConsumptionRate:F1}%\n" +
                        $"- Score Global de Conformité : {diag.ComplianceScore:F0} / 100\n" +
                        $"- Prochaine Échéance de Rapport Bailleur : {(diag.NextReportDueDate.HasValue ? diag.NextReportDueDate.Value.ToString("dd/MM/yyyy") : "Non définie")}\n\n" +
                        $"=== DOCUMENTS FONDATEURS ENREGISTRÉS ===\n" +
                        $"{docList}\n\n" +
                        $"=== ALERTES & POINTS DE VIGILANCE ===\n" +
                        $"{string.Join("\n", diag.ComplianceAlerts.Select(a => $"• {a}"))}\n\n" +
                        $"=== RECOMMANDATIONS STRATÉGIQUES BAILLEUR ===\n" +
                        $"{string.Join("\n", diag.StrategicRecommendations.Select(r => $"• {r}"))}";
                }

                IsPreviewVisible = true;
                _ = OpenReportInEditorAsync();
            }
            catch (Exception ex)
            {
                System.Windows.MessageBox.Show($"Erreur lors de la génération de l'aperçu: {ex.Message}", "Erreur", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Error);
            }
        }

        /// <summary>
        /// Envoie le rapport à l'éditeur de Smart Office (nouvelle version si le document existe déjà) et l'affiche dans
        /// l'onglet. En cas d'indisponibilité, l'aperçu texte reste affiché avec le motif.
        /// </summary>
        private async System.Threading.Tasks.Task OpenReportInEditorAsync()
        {
            ReportEditorStatus = "Ouverture du rapport dans l'éditeur…";
            try
            {
                string url = await SmartOfficeHostService.Instance.EnsureStartedAsync();
                string token = SmartOfficeHostService.Instance.SessionToken ?? string.Empty;
                string payload = System.Text.Json.JsonSerializer.Serialize(new
                {
                    project_id = Project.Id,
                    report_type = SelectedReportType,
                    title = $"{SelectedReportType} — {Project.Code}",
                    text = PreviewContent,
                });
                using var request = new System.Net.Http.HttpRequestMessage(System.Net.Http.HttpMethod.Post, $"{url}/api/editor/documents/from-report")
                {
                    Content = new System.Net.Http.StringContent(payload, System.Text.Encoding.UTF8, "application/json"),
                };
                request.Headers.Add("X-AFMI-Token", token);
                using var response = await EditorHttp.SendAsync(request);
                string body = await response.Content.ReadAsStringAsync();
                using var json = System.Text.Json.JsonDocument.Parse(body);
                if (!response.IsSuccessStatusCode)
                    throw new InvalidOperationException(json.RootElement.TryGetProperty("detail", out var d) ? d.ToString() : $"erreur {(int)response.StatusCode}");
                int id = json.RootElement.GetProperty("id").GetInt32();
                ReportEditorUri = new Uri($"{url}/?afmi_token={token}#editor-embed/{id}");
                ReportEditorStatus = string.Empty;
            }
            catch (Exception ex)
            {
                ReportEditorUri = null;
                ReportEditorStatus = $"Éditeur indisponible ({ex.Message}) : aperçu texte affiché.";
            }
        }

        private void ExportReportToFile()
        {
            if (string.IsNullOrEmpty(PreviewTitle) || string.IsNullOrEmpty(PreviewContent))
            {
                System.Windows.MessageBox.Show("Veuillez d'abord afficher l'aperçu du rapport.", "Aperçu requis", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Warning);
                return;
            }

            string ext = SelectedExportFormat == "PDF" ? ".pdf" : (SelectedExportFormat == "Word" ? ".doc" : ".xls");
            string filter = SelectedExportFormat == "PDF" ? "Fichier PDF (*.pdf)|*.pdf" : (SelectedExportFormat == "Word" ? "Document Word (*.doc)|*.doc" : "Feuille Excel (*.xls)|*.xls");
            string historyType = SelectedReportType.Replace("Rapport d'", "").Replace("Rapport ", "").Replace("Bilan Final de ", "");

            var sfd = new Microsoft.Win32.SaveFileDialog
            {
                Filter = filter,
                FileName = $"Rapport_{historyType}_{Project.Code}_{DateTime.Now:yyyyMMdd_HHmmss}{ext}",
                Title = $"Exporter le rapport au format {SelectedExportFormat}"
            };

            if (sfd.ShowDialog() == true)
            {
                try
                {
                    if (SelectedExportFormat == "PDF")
                    {
                        if (SelectedReportType == "Rapport d'Avancement")
                            _reportService.GenerateProgressReportPdf(Project, sfd.FileName, ReportThemeColor);
                        else if (SelectedReportType == "Rapport Financier")
                            _reportService.GenerateFinancialReportPdf(Project, sfd.FileName, ReportThemeColor);
                        else if (SelectedReportType == "Bilan Final de Clôture")
                            _reportService.GenerateCloseoutReportPdf(Project, sfd.FileName, ReportThemeColor);
                        else if (SelectedReportType == "Rapport de Conformité Bailleur")
                            _reportService.GenerateDonorComplianceReportPdf(Project, sfd.FileName, ReportThemeColor);
                    }
                    else if (SelectedExportFormat == "Word")
                    {
                        ExportToWordHtml(sfd.FileName, PreviewTitle, PreviewContent);
                    }
                    else if (SelectedExportFormat == "Excel")
                    {
                        ExportToExcelTsv(sfd.FileName);
                    }

                    // Log in history database
                    using (var db = new AppDbContext())
                    {
                        var history = new ReportHistory
                        {
                            ProjectId = ProjectId,
                            ReportType = historyType,
                            Title = $"Rapport d'{historyType} ({SelectedExportFormat}) - {DateTime.Now:dd/MM/yyyy HH:mm}",
                            GeneratedDate = DateTime.Now,
                            FilePath = sfd.FileName
                        };
                        db.ReportHistories.Add(history);
                        db.SaveChanges();
                    }

                    LoadProjectData();
                    System.Windows.MessageBox.Show($"Rapport exporté avec succès dans le fichier final :\n{sfd.FileName}", "Exportation Réussie", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Information);
                }
                catch (Exception ex)
                {
                    System.Windows.MessageBox.Show($"Erreur lors de l'exportation: {ex.Message}", "Erreur d'exportation", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Error);
                }
            }
        }

        public void ExportToWordHtml(string path, string title, string content)
        {
            var html = $@"<html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
<head>
<meta charset='utf-8'/>
<style>
body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 30px; line-height: 1.6; color: #334155; }}
h1 {{ color: #1e3a8a; border-bottom: 2px solid #3b82f6; padding-bottom: 8px; font-size: 24px; }}
h2 {{ color: #0f172a; margin-top: 25px; border-bottom: 1px solid #cbd5e1; padding-bottom: 5px; font-size: 18px; }}
p {{ margin-bottom: 12px; }}
ul {{ margin-left: 20px; margin-bottom: 12px; }}
li {{ margin-bottom: 6px; }}
.header-box {{ background-color: #f8fafc; border: 1px solid #e2e8f0; padding: 15px; border-radius: 6px; margin-bottom: 20px; }}
</style>
</head>
<body>
<h1>{title}</h1>
<div class='header-box'>
<p><b>Date d'édition :</b> {DateTime.Now:dd/MM/yyyy HH:mm}</p>
<p><b>Code Projet :</b> {Project.Code}</p>
<p><b>Manager :</b> {Project.Manager}</p>
</div>
{content.Replace("\n", "<br/>")}
</body>
</html>";
            File.WriteAllText(path, html, System.Text.Encoding.UTF8);
        }

        public void ExportToExcelTsv(string path)
        {
            var metrics = _evmService.CalculateMetrics(Project);
            var sb = new System.Text.StringBuilder();
            sb.Append('\uFEFF'); // UTF-8 BOM
            
            sb.AppendLine("RAPPORT FINANCIER & ANALYSE EVM");
            sb.AppendLine($"Projet\t{Project.Name} ({Project.Code})");
            sb.AppendLine($"Manager\t{Project.Manager}");
            sb.AppendLine($"Client\t{Project.Client}");
            sb.AppendLine($"Date de génération\t{DateTime.Now:dd/MM/yyyy HH:mm}");
            sb.AppendLine();
            
            sb.AppendLine($"INDICATEURS EVM\tVALEUR ({Project.Currency})\tDESCRIPTION");
            sb.AppendLine($"BAC (Budget à terminaison)\t{metrics.BAC}\tBudget global alloué au projet");
            sb.AppendLine($"PV (Valeur planifiée)\t{metrics.PV}\tBudget planifié cumulé à date");
            sb.AppendLine($"EV (Valeur acquise)\t{metrics.EV}\tAvancement physique converti en valeur budgétaire");
            sb.AppendLine($"AC (Coût réel engagé)\t{metrics.AC}\tTotal des coûts réels cumulés à date");
            sb.AppendLine($"CPI (Indice de Performance Coût)\t{metrics.CPI:F2}\tIndice d'efficacité financière (cible >= 1.0)");
            sb.AppendLine($"SPI (Indice de Performance Planning)\t{metrics.SPI:F2}\tIndice de vitesse du planning (cible >= 1.0)");
            sb.AppendLine($"CV (Écart de coût)\t{metrics.CV}\tÉcart budgétaire (positif = sous le budget)");
            sb.AppendLine($"SV (Écart de planning)\t{metrics.SV}\tÉcart calendaire (positif = en avance)");
            sb.AppendLine($"EAC (Coût estimé à terminaison)\t{metrics.EAC:F1}\tEstimation du coût total du projet à terme");
            sb.AppendLine($"ETC (Reste à dépenser)\t{metrics.ETC:F1}\tMontant prévisionnel pour finir le projet");
            sb.AppendLine($"VAC (Écart à la clôture)\t{metrics.VAC:F1}\tÉcart final prévisionnel (positif = économie)");
            sb.AppendLine();
            
            sb.AppendLine("REGISTRE DES DEPENSES COMPTABLES");
            sb.AppendLine($"Date\tCatégorie\tDescription\tFournisseur/Bénéficiaire\tBudget Prévu ({Project.Currency})\tCoût Réel ({Project.Currency})");
            foreach (var c in CostEntries)
            {
                sb.AppendLine($"{c.Date:dd/MM/yyyy}\t{c.Category}\t{c.Description}\t{c.ResourceName}\t{c.EstimatedCost}\t{c.ActualCost}");
            }
            
            File.WriteAllText(path, sb.ToString(), System.Text.Encoding.UTF8);
        }

        private void ExportBudgetCsv()
        {
            try
            {
                string downloadsPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Downloads");
                if (!Directory.Exists(downloadsPath))
                {
                    downloadsPath = Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments);
                }
                string filePath = Path.Combine(downloadsPath, $"Budget_Projet_{Project.Code}_{DateTime.Now:yyyyMMdd_HHmmss}.csv");

                _exportService.ExportProjectBudgetToCsv(Project, CostEntries, filePath);

                System.Windows.MessageBox.Show($"Le budget détaillé du projet a été exporté dans :\n{filePath}", "Export Réussi", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Information);
            }
            catch (Exception ex)
            {
                System.Windows.MessageBox.Show($"Erreur lors de l'export : {ex.Message}", "Erreur", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Error);
            }
        }

        private void CreateProjectFolders()
        {
            var result = _folderService.CreateQuarterlyFolderStructure(Project);
            if (result.Success)
            {
                if (string.IsNullOrEmpty(Project.LocalFolderPath) || Project.LocalFolderPath != result.RootFolderPath)
                {
                    Project.LocalFolderPath = result.RootFolderPath;
                    try
                    {
                        using (var db = new AppDbContext())
                        {
                            var p = db.Projects.Find(Project.Id);
                            if (p != null)
                            {
                                p.LocalFolderPath = result.RootFolderPath;
                                db.SaveChanges();
                            }
                        }
                    }
                    catch (Exception ex)
                    {
                        System.Diagnostics.Debug.WriteLine($"Could not save LocalFolderPath: {ex.Message}");
                    }
                }
                System.Windows.MessageBox.Show(result.Message, "Dossiers Créés", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Information);
            }
            else
            {
                System.Windows.MessageBox.Show(result.Message, "Erreur", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Error);
            }
        }

        private void OpenProjectFolder()
        {
            if (string.IsNullOrEmpty(Project.LocalFolderPath))
            {
                System.Windows.MessageBox.Show("Le dossier du projet n'a pas encore été créé.\nVeuillez cliquer sur 'Créer Dossiers' d'abord.", "Dossier introuvable", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Warning);
                return;
            }

            bool opened = _folderService.OpenFolderInExplorer(Project.LocalFolderPath);
            if (!opened)
            {
                System.Windows.MessageBox.Show($"Impossible d'ouvrir le dossier :\n{Project.LocalFolderPath}", "Erreur", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Error);
            }
        }

        private static string GetFullExceptionMessage(Exception ex)
        {
            var msgs = new List<string>();
            var curr = ex;
            while (curr != null)
            {
                if (!string.IsNullOrWhiteSpace(curr.Message))
                    msgs.Add(curr.Message);
                curr = curr.InnerException;
            }
            return string.Join(" → ", msgs);
        }
                private async Task ImproveTaskDescriptionAsync()
        {
            if (EditingTask == null || string.IsNullOrWhiteSpace(EditingTask.Description)) return;
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
                var analysis = await _aiService.ReformulateTextAsync(EditingTask.Description, ReformulationGoal.AmeliorerStyle, ReformulationTone.ProfessionnelFormel, Project);
                if (!string.IsNullOrWhiteSpace(analysis.ProcessedText)) EditingTask.Description = analysis.ProcessedText;
            }
            catch {}
        }
        private async Task ImproveDocumentDescriptionAsync()
        {
            if (EditingDocument == null || string.IsNullOrWhiteSpace(EditingDocument.Description)) return;
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
                var analysis = await _aiService.ReformulateTextAsync(EditingDocument.Description, ReformulationGoal.AmeliorerStyle, ReformulationTone.ProfessionnelFormel, Project);
                if (!string.IsNullOrWhiteSpace(analysis.ProcessedText)) EditingDocument.Description = analysis.ProcessedText;
            }
            catch {}
        }
        private async Task ImproveCostDescriptionAsync()
        {
            if (EditingCost == null || string.IsNullOrWhiteSpace(EditingCost.Description)) return;
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
                var analysis = await _aiService.ReformulateTextAsync(EditingCost.Description, ReformulationGoal.AmeliorerStyle, ReformulationTone.ProfessionnelFormel, Project);
                if (!string.IsNullOrWhiteSpace(analysis.ProcessedText)) EditingCost.Description = analysis.ProcessedText;
            }
            catch {}
        }

        private async Task ImproveDescriptionAsync()
        {
            if (Project == null || string.IsNullOrWhiteSpace(Project.Description))
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
                    Project.Description,
                    ReformulationGoal.AmeliorerStyle,
                    ReformulationTone.ProfessionnelFormel,
                    Project
                );

                if (!string.IsNullOrWhiteSpace(analysis.ProcessedText))
                {
                    Project.Description = analysis.ProcessedText;
                    System.Windows.MessageBox.Show("La description a été reformulée par l'IA.", "Succès", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Information);
                    using (var ctx = new AppDbContext()) { ctx.Projects.Update(Project); ctx.SaveChanges(); }
                }
            }
            catch (Exception ex)
            {
                System.Windows.MessageBox.Show($"Erreur lors de l'appel à l'Agent IA : {ex.Message}", "Erreur IA", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Error);
            }
            finally
            {
                
            }
        }
    }
}
