using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Input;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Microsoft.Win32;
using AFMI_Gestion_projet.Data;
using AFMI_Gestion_projet.Models;
using AFMI_Gestion_projet.Services;

namespace AFMI_Gestion_projet.ViewModels
{
    public partial class AiAssistantViewModel : ObservableObject
    {
        private readonly MainViewModel _mainVM;
        private readonly InternalAiAgentService _aiService;
        private readonly ExportService _exportService;

        // Onglet actif : 0 = Comptes Rendus, 1 = Rapports, 2 = Correction & Reformulation, 3 = Paramètres
        [ObservableProperty]
        private int _selectedTabIndex = 0;

        [ObservableProperty]
        private bool _isBusy = false;

        [ObservableProperty]
        private string _busyStatus = string.Empty;

        // Projets pour injection de contexte
        public ObservableCollection<Project> AvailableProjects { get; } = new();

        [ObservableProperty]
        private Project? _selectedProject;

        partial void OnSelectedProjectChanged(Project? value)
        {
            if (value != null)
            {
                // Auto-compléter les métadonnées dans les comptes rendus si vides
                if (string.IsNullOrWhiteSpace(MeetingOrganizer) && !string.IsNullOrWhiteSpace(value.Manager))
                {
                    MeetingOrganizer = value.Manager;
                }
                if (string.IsNullOrWhiteSpace(MeetingTitle))
                {
                    MeetingTitle = $"Compte Rendu de Suivi — {value.Name}";
                }
            }
        }

        #region 1. Comptes Rendus (CR)

        public List<string> MeetingTypes { get; } = new()
        {
            "Suivi Périodique (Hebdomadaire / Mensuel)",
            "Comité de Pilotage (COPIL) / Arbitrage",
            "Cadrage & Lancement de Projet (Kick-off)",
            "Visite de Terrain / Inspection de Chantier",
            "Atelier Partenaires & Bailleur de Fonds",
            "Clôture de Projet & Rétrospective"
        };

        [ObservableProperty]
        private string _selectedMeetingType = "Suivi Périodique (Hebdomadaire / Mensuel)";

        [ObservableProperty]
        private string _meetingTitle = "Compte Rendu de Réunion de Suivi";

        [ObservableProperty]
        private DateTime _meetingDate = DateTime.Today;

        [ObservableProperty]
        private string _meetingLocation = "Salle de réunion / Visioconférence Teams";

        [ObservableProperty]
        private string _meetingOrganizer = string.Empty;

        [ObservableProperty]
        private string _meetingSecretary = string.Empty;

        [ObservableProperty]
        private string _meetingAttendees = string.Empty;

        [ObservableProperty]
        private string _meetingExcused = string.Empty;

        [ObservableProperty]
        private string _meetingAgenda = "1. Revue de l'avancement des actions\n2. Examen des jalons et livrables\n3. Analyse des points bloquants et risques\n4. Validation du plan d'actions pour la période suivante";

        [ObservableProperty]
        private string _meetingRawNotes = string.Empty;

        [ObservableProperty]
        private string _meetingQDecisions = string.Empty;

        [ObservableProperty]
        private string _meetingQBlockers = string.Empty;

        [ObservableProperty]
        private string _meetingQNextSteps = string.Empty;

        [ObservableProperty]
        private string _generatedMinutesText = string.Empty;

        [ObservableProperty]
        private MeetingMinutesModel _currentMinutes = new();

        [ObservableProperty]
        private ObservableCollection<string> _importedPhotos = new();

        public ICommand GenerateMinutesCommand { get; }
        public ICommand ExportMinutesWordCommand { get; }
        public ICommand CopyMinutesCommand { get; }
        public ICommand ImportPhotosCommand { get; }
        public ICommand RemovePhotoCommand { get; }

        #endregion

        #region 2. Rapports & Synthèses

        public List<string> ReportTypes { get; } = new()
        {
            "Rapport Narratif d'Avancement Périodique",
            "Rapport d'Analyse des Risques, Délais & Coûts",
            "Note de Cadrage & Alignement Stratégique",
            "Rapport de Conformité & Exigences Bailleur",
            "Bilan Final de Clôture & Capitalisation"
        };

        [ObservableProperty]
        private string _selectedReportType = "Rapport Narratif d'Avancement Périodique";

        [ObservableProperty]
        private string _reportAdditionalNotes = string.Empty;

        [ObservableProperty]
        private string _reportQAchievements = string.Empty;

        [ObservableProperty]
        private string _reportQDifficulties = string.Empty;

        [ObservableProperty]
        private string _reportQNextObjectives = string.Empty;

        [ObservableProperty]
        private string _generatedReportText = string.Empty;

        public ICommand GenerateReportCommand { get; }
        public ICommand ExportReportWordCommand { get; }
        public ICommand CopyReportCommand { get; }

        #endregion

        #region 3. Correction & Reformulation

        public List<string> AvailableTones { get; } = new()
        {
            "Professionnel & Institutionnel (Bailleurs, Ministères)",
            "Exécutif & Synthétique (Direction Générale, Décideurs)",
            "Opérationnel & Technique (Équipe Projet, Ingénieurs, Terrain)",
            "Persuasif & Impactant (Plaidoyers, Demandes de Subventions)"
        };

        [ObservableProperty]
        private string _selectedTone = "Professionnel & Institutionnel (Bailleurs, Ministères)";

        public List<string> AvailableGoals { get; } = new()
        {
            "Améliorer le style et le vocabulaire",
            "Synthétiser sous forme de liste à puces",
            "Développer et argumenter",
            "Transformer en matrice de plan d'actions"
        };

        [ObservableProperty]
        private string _selectedGoal = "Améliorer le style et le vocabulaire";

        [ObservableProperty]
        private string _sourceText = string.Empty;

        [ObservableProperty]
        private string _resultText = string.Empty;

        [ObservableProperty]
        private string _correctionsSummary = string.Empty;

        public ObservableCollection<CorrectionItem> CorrectionsList { get; } = new();

        public ICommand CorrectTextCommand { get; }
        public ICommand ReformulateTextCommand { get; }
        public ICommand CopyResultCommand { get; }
        public ICommand ReplaceSourceWithResultCommand { get; }
        public ICommand ApplyToProjectDescriptionCommand { get; }

        #endregion

        #region 4. Paramètres Moteur IA

        [ObservableProperty]
        private bool _useOllama = false;

        [ObservableProperty]
        private string _ollamaEndpoint = "http://localhost:11434";

        [ObservableProperty]
        private string _ollamaModel = "mistral";

        [ObservableProperty]
        private string _ollamaStatusMessage = "Moteur Interne Local 100% Gratuit & Hors-ligne actif.";

        [ObservableProperty]
        private bool _useCloudApi = false;

        [ObservableProperty]
        private string _cloudProvider = "OpenAI";

        [ObservableProperty]
        private string _cloudApiKey = string.Empty;

        public List<string> CloudProviders { get; } = new() { "OpenAI", "Gemini" };

        partial void OnUseOllamaChanged(bool value) => SaveAiSettings();
        partial void OnOllamaEndpointChanged(string value) => SaveAiSettings();
        partial void OnOllamaModelChanged(string value) => SaveAiSettings();
        partial void OnUseCloudApiChanged(bool value) => SaveAiSettings();
        partial void OnCloudProviderChanged(string value) => SaveAiSettings();
        partial void OnCloudApiKeyChanged(string value) => SaveAiSettings();

        private void SaveAiSettings()
        {
            try
            {
                using var db = new AppDbContext();
                var settings = db.AiSettings.FirstOrDefault();
                if (settings != null)
                {
                    settings.UseOllama = UseOllama;
                    settings.OllamaEndpoint = OllamaEndpoint;
                    settings.OllamaModel = OllamaModel;
                    settings.UseCloudApi = UseCloudApi;
                    settings.CloudProvider = CloudProvider;
                    settings.CloudApiKey = CloudApiKey;
                    db.SaveChanges();
                }
            }
            catch { }
        }

        public ICommand TestOllamaCommand { get; }

        #endregion

        public AiAssistantViewModel(MainViewModel mainVM)
        {
            _mainVM = mainVM;
            _aiService = new InternalAiAgentService();
            _exportService = new ExportService();

            // Initialisation des commandes
            GenerateMinutesCommand = new AsyncRelayCommand(GenerateMeetingMinutesAsync);
            ExportMinutesWordCommand = new RelayCommand(ExportMinutesWord);
            CopyMinutesCommand = new RelayCommand(CopyMinutesToClipboard);
            ImportPhotosCommand = new RelayCommand(ImportPhotos);
            RemovePhotoCommand = new RelayCommand<string>(RemovePhoto);

            GenerateReportCommand = new AsyncRelayCommand(GenerateReportAsync);
            ExportReportWordCommand = new RelayCommand(ExportReportWord);
            CopyReportCommand = new RelayCommand(CopyReportToClipboard);

            CorrectTextCommand = new AsyncRelayCommand(CorrectTextAsync);
            ReformulateTextCommand = new AsyncRelayCommand(ReformulateTextAsync);
            CopyResultCommand = new RelayCommand(CopyResultToClipboard);
            ReplaceSourceWithResultCommand = new RelayCommand(ReplaceSourceWithResult);
            ApplyToProjectDescriptionCommand = new RelayCommand(ApplyToProjectDescription);

            TestOllamaCommand = new AsyncRelayCommand(TestOllamaConnectionAsync);

            LoadAiSettings();
            RefreshProjects();
        }

        private void LoadAiSettings()
        {
            try
            {
                using var db = new AppDbContext();
                var settings = db.AiSettings.FirstOrDefault();
                if (settings != null)
                {
                    UseOllama = settings.UseOllama;
                    OllamaEndpoint = settings.OllamaEndpoint;
                    OllamaModel = settings.OllamaModel;
                    UseCloudApi = settings.UseCloudApi;
                    CloudProvider = settings.CloudProvider ?? "OpenAI";
                    CloudApiKey = settings.CloudApiKey ?? string.Empty;
                }
                else
                {
                    db.AiSettings.Add(new AiSettings { UseOllama = false, OllamaEndpoint = "http://localhost:11434", OllamaModel = "mistral", UseCloudApi = false, CloudProvider = "OpenAI", CloudApiKey = "" });
                    db.SaveChanges();
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Error loading AiSettings: {ex.Message}");
            }
        }

        public void RefreshProjects(int? selectProjectId = null)
        {
            try
            {
                using var db = new AppDbContext();
                AvailableProjects.Clear();
                var list = db.Projects.OrderBy(p => p.Name).ToList();
                
                // Charger les relations utiles pour les projets
                foreach (var p in list)
                {
                    db.Entry(p).Collection(proj => proj.Tasks).Load();
                    db.Entry(p).Reference(proj => proj.Funder).Load();
                    AvailableProjects.Add(p);
                }

                if (selectProjectId.HasValue)
                {
                    SelectedProject = AvailableProjects.FirstOrDefault(p => p.Id == selectProjectId.Value);
                }
                else if (SelectedProject == null && AvailableProjects.Any())
                {
                    SelectedProject = AvailableProjects.FirstOrDefault();
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Error loading projects in AI assistant: {ex.Message}");
            }
        }

        #region Actions Comptes Rendus

        private async Task GenerateMeetingMinutesAsync()
        {
            IsBusy = true;
            BusyStatus = "Génération du compte rendu structuré en cours...";

            try
            {
                var model = new MeetingMinutesModel
                {
                    Title = MeetingTitle,
                    MeetingType = SelectedMeetingType,
                    MeetingDate = MeetingDate,
                    Location = MeetingLocation,
                    Organizer = MeetingOrganizer,
                    Secretary = MeetingSecretary,
                    Attendees = MeetingAttendees,
                    Excused = MeetingExcused,
                    Agenda = MeetingAgenda,
                    RawNotes = MeetingRawNotes,
                    Q_Decisions = MeetingQDecisions,
                    Q_Blockers = MeetingQBlockers,
                    Q_NextSteps = MeetingQNextSteps,
                    Photos = ImportedPhotos.ToList()
                };

                _aiService.UseLocalOllamaIfAvailable = UseOllama;
                _aiService.OllamaEndpoint = OllamaEndpoint;
                _aiService.OllamaModel = OllamaModel;

                var result = await _aiService.GenerateMeetingMinutesAsync(model, SelectedProject);
                CurrentMinutes = result;
                GeneratedMinutesText = result.GeneratedSummary;
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Erreur lors de la génération du compte rendu : {ex.Message}", "Erreur IA", MessageBoxButton.OK, MessageBoxImage.Error);
            }
            finally
            {
                IsBusy = false;
            }
        }

        private void ExportMinutesWord()
        {
            if (string.IsNullOrWhiteSpace(GeneratedMinutesText))
            {
                MessageBox.Show("Veuillez d'abord générer un compte rendu.", "Information", MessageBoxButton.OK, MessageBoxImage.Information);
                return;
            }

            var sfd = new SaveFileDialog
            {
                Title = "Exporter le Compte Rendu en Document Word",
                Filter = "Document Word (*.docx)|*.docx|Tous les fichiers (*.*)|*.*",
                FileName = $"Compte_Rendu_{DateTime.Now:yyyyMMdd_HHmm}.docx"
            };

            if (sfd.ShowDialog() == true)
            {
                try
                {
                    _exportService.ExportMeetingMinutesToWord(CurrentMinutes, sfd.FileName);
                    MessageBox.Show($"Compte rendu exporté avec succès dans :\n{sfd.FileName}", "Export Réussi", MessageBoxButton.OK, MessageBoxImage.Information);
                }
                catch (Exception ex)
                {
                    MessageBox.Show($"Erreur d'export : {ex.Message}", "Erreur", MessageBoxButton.OK, MessageBoxImage.Error);
                }
            }
        }

        private void CopyMinutesToClipboard()
        {
            if (!string.IsNullOrWhiteSpace(GeneratedMinutesText))
            {
                Clipboard.SetText(GeneratedMinutesText);
                MessageBox.Show("Le compte rendu a été copié dans le presse-papiers.", "Copié", MessageBoxButton.OK, MessageBoxImage.Information);
            }
        }

        private void ImportPhotos()
        {
            var ofd = new OpenFileDialog
            {
                Filter = "Images (*.png;*.jpg;*.jpeg)|*.png;*.jpg;*.jpeg",
                Multiselect = true
            };

            if (ofd.ShowDialog() == true)
            {
                foreach (var file in ofd.FileNames)
                {
                    if (!ImportedPhotos.Contains(file))
                    {
                        ImportedPhotos.Add(file);
                    }
                }
            }
        }

        private void RemovePhoto(string? photoPath)
        {
            if (!string.IsNullOrEmpty(photoPath) && ImportedPhotos.Contains(photoPath))
            {
                ImportedPhotos.Remove(photoPath);
            }
        }

        #endregion

        #region Actions Rapports

        private async Task GenerateReportAsync()
        {
            if (SelectedProject == null)
            {
                MessageBox.Show("Veuillez sélectionner un projet pour générer le rapport.", "Sélection requise", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            IsBusy = true;
            BusyStatus = "Rédaction du rapport officiel par l'Agent IA...";

            try
            {
                _aiService.UseLocalOllamaIfAvailable = UseOllama;
                _aiService.OllamaEndpoint = OllamaEndpoint;
                _aiService.OllamaModel = OllamaModel;

                var type = SelectedReportType switch
                {
                    "Rapport d'Analyse des Risques, Délais & Coûts" => InternalAiAgentService.AiReportType.AnalyseRisquesEtCouts,
                    "Note de Cadrage & Alignement Stratégique" => InternalAiAgentService.AiReportType.NoteStrategiqueCadrage,
                    "Rapport de Conformité & Exigences Bailleur" => InternalAiAgentService.AiReportType.ConformiteBailleur,
                    "Bilan Final de Clôture & Capitalisation" => InternalAiAgentService.AiReportType.BilanClotureCapitalisation,
                    _ => InternalAiAgentService.AiReportType.RapportAvancementNarratif
                };

                string fullNotes = ReportAdditionalNotes;
                if (!string.IsNullOrWhiteSpace(ReportQAchievements)) fullNotes += "\\nRéalisations principales : " + ReportQAchievements;
                if (!string.IsNullOrWhiteSpace(ReportQDifficulties)) fullNotes += "\\nDifficultés rencontrées : " + ReportQDifficulties;
                if (!string.IsNullOrWhiteSpace(ReportQNextObjectives)) fullNotes += "\\nObjectifs prochaine période : " + ReportQNextObjectives;
                GeneratedReportText = await _aiService.GenerateAiReportAsync(type, SelectedProject, fullNotes);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Erreur lors de la rédaction du rapport : {ex.Message}", "Erreur IA", MessageBoxButton.OK, MessageBoxImage.Error);
            }
            finally
            {
                IsBusy = false;
            }
        }

        private void ExportReportWord()
        {
            if (string.IsNullOrWhiteSpace(GeneratedReportText))
            {
                MessageBox.Show("Veuillez d'abord générer un rapport.", "Information", MessageBoxButton.OK, MessageBoxImage.Information);
                return;
            }

            var sfd = new SaveFileDialog
            {
                Title = "Exporter le Rapport en Document Word",
                Filter = "Document Word (*.docx)|*.docx|Tous les fichiers (*.*)|*.*",
                FileName = $"Rapport_{SelectedProject?.Code ?? "Projet"}_{DateTime.Now:yyyyMMdd_HHmm}.docx"
            };

            if (sfd.ShowDialog() == true)
            {
                try
                {
                    _exportService.ExportAiReportToWord(SelectedReportType, GeneratedReportText, SelectedProject, sfd.FileName);
                    MessageBox.Show($"Rapport exporté avec succès dans :\n{sfd.FileName}", "Export Réussi", MessageBoxButton.OK, MessageBoxImage.Information);
                }
                catch (Exception ex)
                {
                    MessageBox.Show($"Erreur d'export : {ex.Message}", "Erreur", MessageBoxButton.OK, MessageBoxImage.Error);
                }
            }
        }

        private void CopyReportToClipboard()
        {
            if (!string.IsNullOrWhiteSpace(GeneratedReportText))
            {
                Clipboard.SetText(GeneratedReportText);
                MessageBox.Show("Le rapport a été copié dans le presse-papier !", "Copié", MessageBoxButton.OK, MessageBoxImage.Information);
            }
        }

        #endregion

        #region Actions Correction & Reformulation

        private async Task CorrectTextAsync()
        {
            if (string.IsNullOrWhiteSpace(SourceText)) return;

            IsBusy = true;
            BusyStatus = "Correction orthographique en cours...";

            try
            {
                _aiService.UseLocalOllamaIfAvailable = UseOllama;
                _aiService.OllamaEndpoint = OllamaEndpoint;
                _aiService.OllamaModel = OllamaModel;

                var analysis = await _aiService.CorrectTextAsync(SourceText);
                ResultText = analysis.ProcessedText;

                CorrectionsList.Clear();
                foreach (var c in analysis.Corrections)
                {
                    CorrectionsList.Add(c);
                }

                CorrectionsSummary = $"✅ Analyse terminée : {analysis.CorrectionsCount} point(s) corrigé(s) ou normalisé(s). Moteur : {analysis.ExecutionEngine}";
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Erreur lors de la correction : {ex.Message}", "Erreur IA", MessageBoxButton.OK, MessageBoxImage.Error);
            }
            finally
            {
                IsBusy = false;
            }
        }

        private async Task ReformulateTextAsync()
        {
            if (string.IsNullOrWhiteSpace(SourceText)) return;

            IsBusy = true;
            BusyStatus = "Amélioration et reformulation rédactionnelle...";

            try
            {
                _aiService.UseLocalOllamaIfAvailable = UseOllama;
                _aiService.OllamaEndpoint = OllamaEndpoint;
                _aiService.OllamaModel = OllamaModel;

                var goal = SelectedGoal switch
                {
                    "Synthétiser sous forme de liste à puces" => ReformulationGoal.SynthetiserPuces,
                    "Développer et argumenter" => ReformulationGoal.DevelopperArgumenter,
                    "Transformer en matrice de plan d'actions" => ReformulationGoal.TransformerEnPlanActions,
                    _ => ReformulationGoal.AmeliorerStyle
                };

                var tone = SelectedTone switch
                {
                    "Exécutif & Synthétique (Direction Générale, Décideurs)" => ReformulationTone.ExecutifSynthetique,
                    "Opérationnel & Technique (Équipe Projet, Ingénieurs, Terrain)" => ReformulationTone.OperationnelTechnique,
                    "Persuasif & Impactant (Plaidoyers, Demandes de Subventions)" => ReformulationTone.PersuasifImpact,
                    _ => ReformulationTone.ProfessionnelFormel
                };

                var analysis = await _aiService.ReformulateTextAsync(SourceText, goal, tone, SelectedProject);
                ResultText = analysis.ProcessedText;

                CorrectionsList.Clear();
                foreach (var c in analysis.Corrections)
                {
                    CorrectionsList.Add(c);
                }

                CorrectionsSummary = $"✨ Reformulation accomplie ({analysis.WordCount} mots). Moteur : {analysis.ExecutionEngine}";
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Erreur lors de la reformulation : {ex.Message}", "Erreur IA", MessageBoxButton.OK, MessageBoxImage.Error);
            }
            finally
            {
                IsBusy = false;
            }
        }

        private void CopyResultToClipboard()
        {
            if (!string.IsNullOrWhiteSpace(ResultText))
            {
                Clipboard.SetText(ResultText);
                MessageBox.Show("Le texte amélioré a été copié dans le presse-papier !", "Copié", MessageBoxButton.OK, MessageBoxImage.Information);
            }
        }

        private void ReplaceSourceWithResult()
        {
            if (!string.IsNullOrWhiteSpace(ResultText))
            {
                SourceText = ResultText;
            }
        }

        private void ApplyToProjectDescription()
        {
            if (SelectedProject == null)
            {
                MessageBox.Show("Veuillez sélectionner un projet dans la liste pour lui appliquer cette description.", "Information", MessageBoxButton.OK, MessageBoxImage.Information);
                return;
            }

            if (string.IsNullOrWhiteSpace(ResultText))
            {
                MessageBox.Show("Aucun texte rédigé à appliquer.", "Information", MessageBoxButton.OK, MessageBoxImage.Information);
                return;
            }

            var confirm = MessageBox.Show($"Souhaitez-vous remplacer la description du projet « {SelectedProject.Name} » par le texte rédigé par l'Agent IA ?", "Confirmation", MessageBoxButton.YesNo, MessageBoxImage.Question);
            if (confirm == MessageBoxResult.Yes)
            {
                try
                {
                    using var db = new AppDbContext();
                    var p = db.Projects.Find(SelectedProject.Id);
                    if (p != null)
                    {
                        p.Description = ResultText;
                        db.AuditLogs.Add(new AuditLog
                        {
                            ProjectId = p.Id,
                            EntityType = "Projet",
                            EntityId = p.Id,
                            ChangeType = "Modification IA",
                            FieldName = "Description",
                            NewValue = "Description mise à jour par l'Agent IA",
                            Timestamp = DateTime.Now
                        });
                        db.SaveChanges();
                        SelectedProject.Description = ResultText;
                        MessageBox.Show("Description du projet mise à jour avec succès !", "Mise à jour Réussie", MessageBoxButton.OK, MessageBoxImage.Information);
                    }
                }
                catch (Exception ex)
                {
                    MessageBox.Show($"Erreur lors de la mise à jour : {ex.Message}", "Erreur", MessageBoxButton.OK, MessageBoxImage.Error);
                }
            }
        }

        #endregion

        #region Actions Paramètres

        private async Task TestOllamaConnectionAsync()
        {
            OllamaStatusMessage = "Test de connexion au serveur Ollama en cours...";
            try
            {
                using var client = new System.Net.Http.HttpClient { Timeout = TimeSpan.FromSeconds(3) };
                var res = await client.GetAsync($"{OllamaEndpoint.TrimEnd('/')}/api/tags");
                if (res.IsSuccessStatusCode)
                {
                    OllamaStatusMessage = "✅ Serveur Ollama local détecté et opérationnel ! Les réponses pourront être enrichies par le LLM local.";
                }
                else
                {
                    OllamaStatusMessage = $"⚠️ Serveur Ollama répond avec le code {res.StatusCode}. Le Moteur Interne Autonome reste actif par défaut.";
                }
            }
            catch (Exception ex)
            {
                OllamaStatusMessage = $"ℹ️ Serveur Ollama non joignable ({ex.Message}). Le Moteur Interne Local (100% Gratuit & Hors-ligne) fonctionne de manière autonome.";
            }
        }

        #endregion
    }
}
