using System;
using System.Collections.ObjectModel;
using System.IO;
using System.Linq;
using System.Windows;
using System.Windows.Input;
using AFMI_Gestion_projet.Data;
using AFMI_Gestion_projet.Models;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Microsoft.EntityFrameworkCore;
using Microsoft.Win32;

namespace AFMI_Gestion_projet.ViewModels
{
    public partial class ActivityReportWizardViewModel : ObservableObject
    {
        private readonly int _taskId;
        private readonly int _projectId;
        public Action? OnWizardCompleted;
        public Action? OnWizardCancelled;

        [ObservableProperty]
        private ActivityReport _report = new();

        [ObservableProperty]
        private int _currentStep = 1;

        [ObservableProperty]
        private ObservableCollection<Indicator> _availableIndicators = new();

        [ObservableProperty]
        private ObservableCollection<ActivityReportPhoto> _photos = new();

        public ICommand NextStepCommand { get; }
        public ICommand PreviousStepCommand { get; }
        public ICommand AddPhotoCommand { get; }
        public ICommand RemovePhotoCommand { get; }
        public ICommand SubmitCommand { get; }
        public ICommand CancelCommand { get; }

        public ActivityReportWizardViewModel(int taskId, int projectId)
        {
            _taskId = taskId;
            _projectId = projectId;

            Report = new ActivityReport 
            { 
                ProjectTaskId = taskId, 
                ActivityDate = DateTime.Today,
                Status = "Brouillon"
            };

            NextStepCommand = new RelayCommand(NextStep, CanGoNext);
            PreviousStepCommand = new RelayCommand(PreviousStep, CanGoPrevious);
            AddPhotoCommand = new RelayCommand(AddPhoto);
            RemovePhotoCommand = new RelayCommand<ActivityReportPhoto>(RemovePhoto);
            SubmitCommand = new RelayCommand(Submit, CanSubmit);
            CancelCommand = new RelayCommand(Cancel);

            LoadData();
        }

        private void LoadData()
        {
            using var db = new AppDbContext();
            var indicators = db.Indicators.Where(i => i.ProjectId == _projectId).ToList();
            AvailableIndicators = new ObservableCollection<Indicator>(indicators);
        }

        private bool CanGoNext() => CurrentStep < 3;
        private void NextStep() 
        { 
            if (CurrentStep < 3) 
            {
                CurrentStep++; 
                NotifyCommands();
            }
        }

        private bool CanGoPrevious() => CurrentStep > 1;
        private void PreviousStep() 
        { 
            if (CurrentStep > 1) 
            {
                CurrentStep--; 
                NotifyCommands();
            }
        }

        private void NotifyCommands()
        {
            ((RelayCommand)NextStepCommand).NotifyCanExecuteChanged();
            ((RelayCommand)PreviousStepCommand).NotifyCanExecuteChanged();
            ((RelayCommand)SubmitCommand).NotifyCanExecuteChanged();
        }

        private void AddPhoto()
        {
            var ofd = new OpenFileDialog
            {
                Filter = "Images (*.png;*.jpg;*.jpeg)|*.png;*.jpg;*.jpeg",
                Multiselect = true
            };

            if (ofd.ShowDialog() == true)
            {
                // Copie dans un dossier local (AppData) pour ne pas dépendre du fichier d'origine
                string appDataFolder = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "AFMIGestionProjet", "Photos");
                Directory.CreateDirectory(appDataFolder);

                foreach (var file in ofd.FileNames)
                {
                    string newFileName = $"{Guid.NewGuid()}{Path.GetExtension(file)}";
                    string destPath = Path.Combine(appDataFolder, newFileName);
                    File.Copy(file, destPath);

                    Photos.Add(new ActivityReportPhoto 
                    { 
                        LocalFilePath = destPath, 
                        Caption = "Nouvelle photo..." 
                    });
                }
            }
        }

        private void RemovePhoto(ActivityReportPhoto? photo)
        {
            if (photo != null)
            {
                Photos.Remove(photo);
            }
        }

        private bool CanSubmit() => CurrentStep == 3 && !string.IsNullOrWhiteSpace(Report.Title);

        private void Submit()
        {
            try
            {
                using var db = new AppDbContext();
                
                // Mettre à jour la valeur de l'indicateur si sélectionné
                if (Report.IndicatorId.HasValue)
                {
                    var indicator = db.Indicators.Find(Report.IndicatorId.Value);
                    if (indicator != null)
                    {
                        // Incrémente ou remplace selon la logique métier, on incrémente ici par défaut avec le nombre de participants ou une valeur fixe.
                        // Pour faire simple, on pourrait rajouter une propriété "Valeur Apportée" dans le rapport.
                        indicator.CurrentValue += Report.ParticipantsCount; 
                        db.Indicators.Update(indicator);
                    }
                }

                Report.Status = "Validé";
                db.ActivityReports.Add(Report);
                db.SaveChanges(); // Récupère le Report.Id
                
                // Sauvegarder les photos liées
                foreach (var photo in Photos)
                {
                    photo.ActivityReportId = Report.Id;
                    db.ActivityReportPhotos.Add(photo);
                }
                db.SaveChanges();

                MessageBox.Show("Compte rendu enregistré avec succès.", "Succès", MessageBoxButton.OK, MessageBoxImage.Information);
                OnWizardCompleted?.Invoke();
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Erreur lors de la sauvegarde : {ex.Message}", "Erreur", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void Cancel()
        {
            OnWizardCancelled?.Invoke();
        }
    }
}
