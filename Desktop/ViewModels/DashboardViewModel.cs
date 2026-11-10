using System;
using System.Collections.ObjectModel;
using System.Linq;
using CommunityToolkit.Mvvm.ComponentModel;
using AFMI_Gestion_projet.Data;
using AFMI_Gestion_projet.Models;
using AFMI_Gestion_projet.Services;

namespace AFMI_Gestion_projet.ViewModels
{
    public partial class DashboardViewModel : ObservableObject
    {
        private readonly MainViewModel _mainVM;
        private readonly EvmService _evmService;

        [ObservableProperty]
        private int _totalProjectsCount;

        [ObservableProperty]
        private int _activeProjectsCount;

        [ObservableProperty]
        private double _totalPortfolioBudget;

        [ObservableProperty]
        private double _averagePortfolioProgress;

        public ObservableCollection<ProjectTask> AssignedLateTasks { get; } = new();
        public ObservableCollection<string> BudgetAlerts { get; } = new();
        public ObservableCollection<Project> ProjectsSummary { get; } = new();

        public DashboardViewModel(MainViewModel mainVM)
        {
            _mainVM = mainVM;
            _evmService = new EvmService();
            RefreshData();
        }

        public void RefreshData()
        {
            try
            {
                using (var db = new AppDbContext())
                {
                    var projects = db.Projects.ToList();
                    TotalProjectsCount = projects.Count;
                    ActiveProjectsCount = projects.Count(p => p.Status != "Clôture" && p.Status != "Archivé");
                    TotalPortfolioBudget = projects.Sum(p => p.BudgetGlobal);

                    // Load tasks for progress and alert checking
                    AssignedLateTasks.Clear();
                    BudgetAlerts.Clear();
                    ProjectsSummary.Clear();

                    double totalProgressSum = 0;
                    int projectWithTasksCount = 0;
                    var today = DateTime.Today;

                    foreach (var p in projects)
                    {
                        // Explicitly load tasks and costs for EVM calculation
                        db.Entry(p).Collection(proj => proj.Tasks).Load();
                        db.Entry(p).Collection(proj => proj.CostEntries).Load();

                        ProjectsSummary.Add(p);

                        // Calculate average progress
                        if (p.Tasks.Any())
                        {
                            var leafTasks = p.Tasks.Where(t => t.ParentTaskId == null).ToList();
                            double projProgress = leafTasks.Sum(t => t.ProgressPercentage) / Math.Max(1, leafTasks.Count);
                            totalProgressSum += projProgress;
                            projectWithTasksCount++;
                        }

                        // Check budget alert (using EVM CPI)
                        var metrics = _evmService.CalculateMetrics(p);
                        if (metrics.CPI < 0.95 && metrics.AC > 0)
                        {
                            BudgetAlerts.Add($"Projet \"{p.Name}\" : CPI de {metrics.CPI:F2} (dépassement estimé à terminaison de {Math.Abs(metrics.VAC):C0})");
                        }

                        // Collect late tasks (incomplete past target end date)
                        var late = p.Tasks.Where(t => t.Status != "Terminé" && t.TargetEndDate < today).ToList();
                        foreach (var t in late)
                        {
                            t.Project = p; // Ensure parent project context is available for UI binding
                            AssignedLateTasks.Add(t);
                        }
                    }

                    AveragePortfolioProgress = projectWithTasksCount > 0 ? totalProgressSum / projectWithTasksCount : 0;
                }

                _mainVM.UpdateGlobalNotifications();
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Error loading dashboard data: {ex.Message}");
            }
        }
    }
}
