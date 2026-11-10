using System;
using System.Collections.ObjectModel;
using System.Linq;
using System.Text.Json;
using System.Windows.Input;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using AFMI_Gestion_projet.Data;
using AFMI_Gestion_projet.Models;

namespace AFMI_Gestion_projet.ViewModels
{
    public partial class TemplateViewModel : ObservableObject
    {
        private readonly MainViewModel _mainVM;

        [ObservableProperty]
        private ProjectTemplate? _selectedTemplate;

        [ObservableProperty]
        private string _newProjectName = string.Empty;

        [ObservableProperty]
        private string _newProjectCode = string.Empty;

        [ObservableProperty]
        private bool _isCreateFromTemplateVisible = false;

        public ObservableCollection<ProjectTemplate> Templates { get; } = new();

        public ICommand OpenCreateDialogCommand { get; }
        public ICommand CreateProjectFromTemplateCommand { get; }

        public TemplateViewModel(MainViewModel mainVM)
        {
            _mainVM = mainVM;

            OpenCreateDialogCommand = new RelayCommand<ProjectTemplate>(OpenCreateDialog);
            CreateProjectFromTemplateCommand = new RelayCommand(CreateProjectFromTemplate);

            RefreshData();
        }

        public void RefreshData()
        {
            try
            {
                using (var db = new AppDbContext())
                {
                    Templates.Clear();
                    foreach (var t in db.Templates.ToList())
                    {
                        Templates.Add(t);
                    }
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Error loading templates: {ex.Message}");
            }
        }

        private void OpenCreateDialog(ProjectTemplate? template)
        {
            if (template == null) return;
            SelectedTemplate = template;
            NewProjectName = $"Mon Projet {template.Name.Replace("Méthodologie ", "").Replace("Développement ", "")}";
            NewProjectCode = $"PRJ-{new Random().Next(1000, 9999)}";
            IsCreateFromTemplateVisible = true;
        }

        private void CreateProjectFromTemplate()
        {
            if (SelectedTemplate == null || string.IsNullOrWhiteSpace(NewProjectName) || string.IsNullOrWhiteSpace(NewProjectCode))
            {
                System.Windows.MessageBox.Show("Veuillez remplir le nom et le code du projet.", "Champs manquants", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Warning);
                return;
            }

            try
            {
                using (var db = new AppDbContext())
                {
                    // Create Project
                    var newProj = new Project
                    {
                        Name = NewProjectName,
                        Code = NewProjectCode,
                        Description = $"Projet créé à partir du modèle : {SelectedTemplate.Name}",
                        TargetStartDate = DateTime.Today,
                        TargetEndDate = DateTime.Today.AddMonths(3),
                        Status = "Initiation",
                        Priority = "Moyenne",
                        Manager = "Chef de projet",
                        Client = "Client interne"
                    };

                    db.Projects.Add(newProj);
                    db.SaveChanges(); // Saves to get database ID

                    // Deserialize template data
                    var templateData = JsonSerializer.Deserialize<TemplateDataStructure>(SelectedTemplate.ProjectDataJson);
                    if (templateData != null)
                    {
                        // Add steps
                        int order = 1;
                        foreach (var stepName in templateData.Steps)
                        {
                            db.WorkflowSteps.Add(new WorkflowStep
                            {
                                ProjectId = newProj.Id,
                                StepName = stepName,
                                Order = order++,
                                IsCompleted = false
                            });
                        }

                        // Add tasks
                        foreach (var tTask in templateData.Tasks)
                        {
                            db.Tasks.Add(new ProjectTask
                            {
                                ProjectId = newProj.Id,
                                Name = tTask.Name,
                                Description = tTask.Description,
                                Budget = tTask.Budget,
                                Cost = 0,
                                ProgressPercentage = 0,
                                Status = "À faire",
                                TargetStartDate = DateTime.Today,
                                TargetEndDate = DateTime.Today.AddDays(15)
                            });
                        }
                    }

                    // Audit Log
                    db.AuditLogs.Add(new AuditLog
                    {
                        ProjectId = newProj.Id,
                        EntityType = "Projet",
                        EntityId = newProj.Id,
                        ChangeType = "Création",
                        FieldName = "Modèle",
                        NewValue = SelectedTemplate.Name,
                        Timestamp = DateTime.Now
                    });

                    db.SaveChanges();
                    IsCreateFromTemplateVisible = false;

                    // Navigate to newly created project
                    _mainVM.NavigateToProjectDetail(newProj.Id);
                }
            }
            catch (Exception ex)
            {
                System.Windows.MessageBox.Show($"Erreur lors de la création du projet : {ex.Message}", "Erreur", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Error);
            }
        }

        private class TemplateDataStructure
        {
            public System.Collections.Generic.List<string> Steps { get; set; } = new();
            public System.Collections.Generic.List<TemplateTaskItem> Tasks { get; set; } = new();
        }

        private class TemplateTaskItem
        {
            public string Name { get; set; } = string.Empty;
            public string Description { get; set; } = string.Empty;
            public double Budget { get; set; }
        }
    }
}
