using System;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using AFMI_Gestion_projet.Data;
using AFMI_Gestion_projet.Models;
using AFMI_Gestion_projet.Services;
using AFMI_Gestion_projet.ViewModels;
using Xunit;

namespace AFMI_Gestion_projet.Tests
{
    public class AiAgentTests
    {
        [Fact]
        public void TestTextCorrectionAndTypography()
        {
            var service = new InternalAiAgentService();
            string raw = "il y a des tache a faire et des activite pour la reunion: le projet est en retard?";
            
            var result = service.CorrectText(raw);

            Assert.NotNull(result);
            Assert.True(result.CorrectionsCount > 0);
            // Vérifier la présence d'accents corrigés et de la ponctuation typographique
            Assert.Contains("tâches", result.ProcessedText);
            Assert.Contains("activités", result.ProcessedText);
            Assert.Contains("réunion", result.ProcessedText);
            Assert.Contains(" ?", result.ProcessedText); // Espace insécable avant ?
            Assert.Contains(" :", result.ProcessedText); // Espace insécable avant :
        }

        [Fact]
        public async Task TestReformulationAndToneAdjustment()
        {
            var service = new InternalAiAgentService();
            string input = "on doit faire la synthese des activites et voir le budget car on est en retard.";

            // 1. Amélioration de style
            var resStyle = await service.ReformulateTextAsync(input, ReformulationGoal.AmeliorerStyle, ReformulationTone.ProfessionnelFormel);
            Assert.NotNull(resStyle);
            Assert.False(string.IsNullOrWhiteSpace(resStyle.ProcessedText));

            // 2. Synthèse en liste à puces
            var resPuces = await service.ReformulateTextAsync(input, ReformulationGoal.SynthetiserPuces, ReformulationTone.ExecutifSynthetique);
            Assert.Contains("•", resPuces.ProcessedText);

            // 3. Transformation en matrice de plan d'actions
            var resPlan = await service.ReformulateTextAsync(input, ReformulationGoal.TransformerEnPlanActions, ReformulationTone.OperationnelTechnique);
            Assert.Contains("| ACT-", resPlan.ProcessedText);
        }

        [Fact]
        public async Task TestGenerateMeetingMinutesWithProjectContext()
        {
            var service = new InternalAiAgentService();
            var project = new Project
            {
                Code = "PRJ-TEST",
                Name = "Projet Reforestation",
                Manager = "Karim Idrissi",
                Client = "Bailleur Vert",
                BudgetGlobal = 75000,
                Status = "Exécution"
            };

            var minutes = new MeetingMinutesModel
            {
                Title = "Comité de Pilotage Trimestriel",
                MeetingType = "Comité de Pilotage (COPIL)",
                MeetingDate = DateTime.Today,
                Organizer = "Karim Idrissi",
                Attendees = "Karim Idrissi, Fatima Zahra, Représentant Bailleur",
                Agenda = "Revue des jalons\nValidation des dépenses\nPlan de formation",
                RawNotes = "Validation des études de sol.\nAccord pour engager la phase 2.\nPoint d'attention sur les délais de livraison des plants."
            };

            var generated = await service.GenerateMeetingMinutesAsync(minutes, project);

            Assert.NotNull(generated);
            Assert.False(string.IsNullOrWhiteSpace(generated.GeneratedSummary));
            Assert.Contains("COMITÉ DE PILOTAGE", generated.GeneratedSummary.ToUpperInvariant());
            Assert.Contains("Projet Reforestation", generated.GeneratedSummary);
            Assert.NotEmpty(generated.Decisions);
            Assert.NotEmpty(generated.ActionItems);
        }

        [Fact]
        public async Task TestGenerateAiReport()
        {
            var service = new InternalAiAgentService();
            var project = new Project
            {
                Code = "INFRA-01",
                Name = "Construction Centre Médical",
                Manager = "Dr. Bennani",
                BudgetGlobal = 150000,
                Status = "Planification"
            };

            string reportText = await service.GenerateAiReportAsync(
                InternalAiAgentService.AiReportType.RapportAvancementNarratif, 
                project, 
                "Avancement satisfaisant malgré de légères intempéries.");

            Assert.False(string.IsNullOrWhiteSpace(reportText));
            Assert.Contains("RAPPORT NARRATIF D'AVANCEMENT", reportText);
            Assert.Contains("Construction Centre Médical", reportText);
            Assert.Contains("INFRA-01", reportText);
        }

        [Fact]
        public void TestExportMinutesAndReportToWord()
        {
            var exportService = new ExportService();
            string tempDir = Path.GetTempPath();
            string minutesPath = Path.Combine(tempDir, $"TestMinutes_{Guid.NewGuid():N}.docx");
            string reportPath = Path.Combine(tempDir, $"TestReport_{Guid.NewGuid():N}.docx");

            try
            {
                var minutes = new MeetingMinutesModel
                {
                    Title = "CR Réunion Chantier",
                    MeetingDate = DateTime.Today,
                    Organizer = "Ingénieur Travaux",
                    GeneratedSummary = "Synthèse complète de la réunion de chantier...",
                    Decisions = { new MeetingDecision { Reference = "DEC-01", Decision = "Validation coulage dalle" } },
                    ActionItems = { new MeetingActionItem { Action = "Commande ciment", Responsible = "Fournisseur", DueDate = DateTime.Today.AddDays(3) } }
                };

                exportService.ExportMeetingMinutesToWord(minutes, minutesPath);
                Assert.True(File.Exists(minutesPath));
                Assert.True(new FileInfo(minutesPath).Length > 100);

                exportService.ExportAiReportToWord("Rapport Stratégique", "Contenu officiel du rapport...", null, reportPath);
                Assert.True(File.Exists(reportPath));
                Assert.True(new FileInfo(reportPath).Length > 100);
            }
            finally
            {
                if (File.Exists(minutesPath)) File.Delete(minutesPath);
                if (File.Exists(reportPath)) File.Delete(reportPath);
            }
        }

        [Fact]
        public void TestAiAssistantViewInstantiationInSta()
        {
            Exception? caught = null;
            var thread = new Thread(() =>
            {
                try
                {
                    if (System.Windows.Application.Current == null)
                    {
                        var app = new System.Windows.Application();
                        var dict = new System.Windows.ResourceDictionary();
                        dict.Source = new Uri("pack://application:,,,/AFMI Smart Admin;component/Themes/ModernStyles.xaml");
                        app.Resources.MergedDictionaries.Add(dict);
                    }

                    var mainVM = new MainViewModel();
                    mainVM.Navigate("ai_assistant");
                    Assert.NotNull(mainVM.CurrentViewModel);
                    Assert.IsType<AiAssistantViewModel>(mainVM.CurrentViewModel);

                    var view = new AFMI_Gestion_projet.Views.AiAssistantView();
                    view.DataContext = mainVM.CurrentViewModel;
                    Assert.NotNull(view);
                }
                catch (Exception ex)
                {
                    caught = ex;
                }
            });
            thread.SetApartmentState(ApartmentState.STA);
            thread.Start();
            thread.Join();

            if (caught != null)
            {
                throw caught;
            }
        }
    }
}
