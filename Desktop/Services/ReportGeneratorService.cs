using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using QuestPDF.Fluent;
using QuestPDF.Helpers;
using QuestPDF.Infrastructure;
using AFMI_Gestion_projet.Models;

namespace AFMI_Gestion_projet.Services
{
    public class SynthesisResult
    {
        public string ExecutiveSummary { get; set; } = string.Empty;
        public List<string> Risks { get; set; } = new();
        public List<string> Actions { get; set; } = new();
    }

    public class ReportGeneratorService
    {
        private readonly EvmService _evmService;
        private readonly DocumentAnalysisService _documentService;

        static ReportGeneratorService()
        {
            // Initialize QuestPDF License
            QuestPDF.Settings.License = LicenseType.Community;
        }

        public ReportGeneratorService()
        {
            _evmService = new EvmService();
            _documentService = new DocumentAnalysisService();
        }


        /// <summary>
        /// Algorithmic text synthesis (Rédaction assistée) based on actual project metrics
        /// </summary>
        public SynthesisResult GenerateSynthesis(Project project)
        {
            var result = new SynthesisResult();
            var metrics = _evmService.CalculateMetrics(project);
            
            // 1. Calculate general progress and delays
            double progress = 0;
            if (project.Tasks.Any())
            {
                var leafTasks = project.Tasks.Where(t => !project.Tasks.Any(sub => sub.ParentTaskId == t.Id)).ToList();
                progress = leafTasks.Sum(t => t.ProgressPercentage) / Math.Max(1, leafTasks.Count);
            }

            var today = DateTime.Today;
            int lateTasksCount = project.Tasks.Count(t => t.Status != "Terminé" && t.TargetEndDate < today);
            int blockedTasksCount = project.Tasks.Count(t => t.Status == "Bloqué");

            // 2. Build Executive Summary
            var sbSummary = new StringBuilder();
            sbSummary.Append($"Le projet \"{project.Name}\" (code: {project.Code}), piloté par {project.Manager}, est actuellement en phase d'**{project.Status}**. ");
            sbSummary.Append($"L'avancement moyen pondéré est de **{progress:F1}%**. ");

            if (metrics.SPI < 0.9)
            {
                sbSummary.Append($"L'analyse des délais indique un **retard par rapport au planning initial** (SPI = {metrics.SPI:F2}). ");
            }
            else if (metrics.SPI >= 1.05)
            {
                sbSummary.Append($"Le projet est **en avance sur le calendrier** (SPI = {metrics.SPI:F2}). ");
            }
            else
            {
                sbSummary.Append($"L'avancement calendaire respecte globalement les jalons planifiés (SPI = {metrics.SPI:F2}). ");
            }

            if (metrics.CPI < 0.95)
            {
                sbSummary.Append($"Sur le plan budgétaire, le projet connaît un **dépassement des coûts** (CPI = {metrics.CPI:F2}), ");
                sbSummary.Append($"avec un coût estimé à terminaison (EAC) de {metrics.EAC:C0} pour un budget initial de {metrics.BAC:C0}.");
            }
            else if (metrics.CPI >= 1.05)
            {
                sbSummary.Append($"Le projet réalise des **économies sur son budget** (CPI = {metrics.CPI:F2}), ");
                sbSummary.Append($"avec un coût estimé à terminaison de {metrics.EAC:C0} inférieur au budget initial.");
            }
            else
            {
                sbSummary.Append($"Le budget est maîtrisé avec un indice de performance des coûts satisfaisant (CPI = {metrics.CPI:F2}).");
            }

            result.ExecutiveSummary = sbSummary.ToString();

            // 3. Build Risks
            if (metrics.SPI < 0.9)
            {
                result.Risks.Add($"Retard généralisé sur le calendrier : la production est moins rapide que prévu (SPI = {metrics.SPI:F2}).");
            }
            if (metrics.CPI < 0.95)
            {
                result.Risks.Add($"Dérive des coûts : l'indice de rentabilité (CPI = {metrics.CPI:F2}) indique une surconsommation budgétaire.");
            }
            if (lateTasksCount > 0)
            {
                result.Risks.Add($"{lateTasksCount} tâche(s) active(s) ont dépassé leur date d'échéance planifiée.");
            }
            if (blockedTasksCount > 0)
            {
                result.Risks.Add($"{blockedTasksCount} tâche(s) sont signalées comme \"Bloquées\" et nécessitent une intervention.");
            }
            if (project.TargetEndDate < today && progress < 100)
            {
                result.Risks.Add("La date de livraison prévue du projet est dépassée alors que le projet n'est pas encore clôturé.");
            }

            if (!result.Risks.Any())
            {
                result.Risks.Add("Aucun risque majeur identifié. Le projet suit sa trajectoire nominale.");
            }

            // 4. Build Recommended Actions
            if (blockedTasksCount > 0)
            {
                result.Actions.Add("Lever en priorité les verrous opérationnels sur les tâches bloquées.");
            }
            if (metrics.SPI < 0.9)
            {
                result.Actions.Add("Planifier une réunion de cadrage pour réviser le calendrier de livraison ou réaffecter des ressources supplémentaires.");
            }
            if (metrics.CPI < 0.95)
            {
                result.Actions.Add("Auditer les postes de dépenses les plus coûteux et geler les dépenses non indispensables pour stabiliser le CPI.");
            }
            if (lateTasksCount > 0)
            {
                result.Actions.Add("Réaffecter les priorités des collaborateurs sur les tâches en retard pour sécuriser le chemin critique.");
            }
            if (result.Actions.Count == 0)
            {
                result.Actions.Add("Maintenir le plan d'action actuel et assurer le suivi régulier des prochains jalons.");
            }

            return result;
        }

        /// <summary>
        /// Generates a PDF Progress Report
        /// </summary>
        public void GenerateProgressReportPdf(Project project, string destPath, string themeColor = "#2B579A")
        {
            var metrics = _evmService.CalculateMetrics(project);
            var synthesis = GenerateSynthesis(project);
            var color = ConvertHexToQuestColor(themeColor);

            Document.Create(container =>
            {
                container.Page(page =>
                {
                    page.Size(PageSizes.A4);
                    page.Margin(1.5f, Unit.Centimetre);
                    page.PageColor(Colors.White);
                    page.DefaultTextStyle(x => x.FontSize(11).FontColor(Colors.Grey.Darken3));

                    // Header
                    page.Header().Row(row =>
                    {
                        row.RelativeItem().Column(col =>
                        {
                            col.Item().Text($"RAPPORT D'AVANCEMENT").FontSize(20).Bold().FontColor(color);
                            col.Item().Text($"Projet : {project.Name} ({project.Code})").FontSize(14).Medium();
                            col.Item().Text($"Manager : {project.Manager} | Client : {project.Client}").FontSize(10).FontColor(Colors.Grey.Darken1);
                        });
                        row.ConstantItem(80).AlignRight().Column(col =>
                        {
                            col.Item().Text("PORTFOLIO").FontSize(12).Bold().FontColor(Colors.Grey.Lighten1);
                            col.Item().Text(DateTime.Now.ToString("dd/MM/yyyy")).FontSize(9).FontColor(Colors.Grey.Darken1);
                        });
                    });

                    // Content
                    page.Content().PaddingVertical(1, Unit.Centimetre).Column(col =>
                    {
                        // 1. Executive Summary Box
                        col.Item().Background(Colors.Grey.Lighten4).Padding(10).Column(box =>
                        {
                            box.Item().Text("Synthèse Globale").FontSize(12).Bold().FontColor(color);
                            box.Item().PaddingTop(5).Text(synthesis.ExecutiveSummary).Italic();
                        });

                        col.Item().PaddingTop(15);

                        // 2. Key Indicators Grid
                        col.Item().Row(grid =>
                        {
                            grid.RelativeItem().Border(1).BorderColor(Colors.Grey.Lighten2).Padding(8).Column(indicator =>
                            {
                                indicator.Item().Text("AVANCEMENT").FontSize(9).Bold().FontColor(Colors.Grey.Darken1);
                                double prog = project.Tasks.Any() ? project.Tasks.Average(t => t.ProgressPercentage) : 0;
                                indicator.Item().Text($"{prog:F1}%").FontSize(16).Bold().FontColor(color);
                            });
                            grid.ConstantItem(10);
                            grid.RelativeItem().Border(1).BorderColor(Colors.Grey.Lighten2).Padding(8).Column(indicator =>
                            {
                                indicator.Item().Text("BUDGET TOTAL").FontSize(9).Bold().FontColor(Colors.Grey.Darken1);
                                indicator.Item().Text($"{metrics.BAC:C0}").FontSize(16).Bold();
                            });
                            grid.ConstantItem(10);
                            grid.RelativeItem().Border(1).BorderColor(Colors.Grey.Lighten2).Padding(8).Column(indicator =>
                            {
                                indicator.Item().Text("INDICE CALENDRIER (SPI)").FontSize(9).Bold().FontColor(Colors.Grey.Darken1);
                                var spiColor = metrics.SPI >= 1.0 ? Colors.Green.Darken2 : (metrics.SPI >= 0.9 ? Colors.Orange.Darken2 : Colors.Red.Darken2);
                                indicator.Item().Text($"{metrics.SPI:F2}").FontSize(16).Bold().FontColor(spiColor);
                            });
                            grid.ConstantItem(10);
                            grid.RelativeItem().Border(1).BorderColor(Colors.Grey.Lighten2).Padding(8).Column(indicator =>
                            {
                                indicator.Item().Text("INDICE COÛT (CPI)").FontSize(9).Bold().FontColor(Colors.Grey.Darken1);
                                var cpiColor = metrics.CPI >= 1.0 ? Colors.Green.Darken2 : (metrics.CPI >= 0.9 ? Colors.Orange.Darken2 : Colors.Red.Darken2);
                                indicator.Item().Text($"{metrics.CPI:F2}").FontSize(16).Bold().FontColor(cpiColor);
                            });
                        });

                        col.Item().PaddingTop(20);

                        // 3. Risks & Actions
                        col.Item().Row(row =>
                        {
                            row.RelativeItem().Column(risksCol =>
                            {
                                risksCol.Item().Text("Risques Identifiés").FontSize(12).Bold().FontColor(Colors.Red.Medium);
                                foreach (var risk in synthesis.Risks)
                                {
                                    risksCol.Item().PaddingTop(4).Text($"• {risk}").FontSize(9.5f);
                                }
                            });
                            row.ConstantItem(20);
                            row.RelativeItem().Column(actionsCol =>
                            {
                                actionsCol.Item().Text("Actions Recommandées").FontSize(12).Bold().FontColor(Colors.Green.Medium);
                                foreach (var act in synthesis.Actions)
                                {
                                    actionsCol.Item().PaddingTop(4).Text($"• {act}").FontSize(9.5f);
                                }
                            });
                        });

                        col.Item().PaddingTop(20);

                        // 4. Tasks List Table
                        col.Item().Text("Détail des Tâches Principales").FontSize(12).Bold().FontColor(color);
                        col.Item().PaddingTop(5).Table(table =>
                        {
                            table.ColumnsDefinition(columns =>
                            {
                                columns.RelativeColumn(3); // Name
                                columns.RelativeColumn(2); // Assignee
                                columns.RelativeColumn(2); // Dates
                                columns.RelativeColumn(1.5f); // Status
                                columns.RelativeColumn(1.2f); // Progress
                            });

                            // Table Header
                            table.Header(header =>
                            {
                                header.Cell().Background(color).Padding(5).Text("Nom de la tâche").Bold().FontColor(Colors.White).FontSize(9);
                                header.Cell().Background(color).Padding(5).Text("Responsable").Bold().FontColor(Colors.White).FontSize(9);
                                header.Cell().Background(color).Padding(5).Text("Échéance").Bold().FontColor(Colors.White).FontSize(9);
                                header.Cell().Background(color).Padding(5).Text("Statut").Bold().FontColor(Colors.White).FontSize(9);
                                header.Cell().Background(color).Padding(5).AlignRight().Text("Avancement").Bold().FontColor(Colors.White).FontSize(9);
                            });

                            // Table Rows
                            int idx = 0;
                            foreach (var task in project.Tasks.Where(t => t.ParentTaskId == null).Take(15))
                            {
                                var bg = idx++ % 2 == 0 ? Colors.Grey.Lighten5 : Colors.White;
                                table.Cell().Background(bg).Padding(5).Text(task.Name).FontSize(9);
                                table.Cell().Background(bg).Padding(5).Text(task.Assignee).FontSize(9);
                                table.Cell().Background(bg).Padding(5).Text(task.TargetEndDate?.ToString("dd/MM/yyyy") ?? "-").FontSize(9);
                                table.Cell().Background(bg).Padding(5).Text(task.Status).FontSize(9);
                                table.Cell().Background(bg).Padding(5).AlignRight().Text($"{task.ProgressPercentage}%").FontSize(9);
                            }
                        });

                        // 5. Foundation Documents & Contractual Baseline Reference
                        if (project.Documents.Any())
                        {
                            col.Item().PaddingTop(15);
                            col.Item().Text("Référentiel & Documents Fondateurs").FontSize(12).Bold().FontColor(color);
                            col.Item().PaddingTop(5).Background(Colors.Grey.Lighten4).Padding(8).Column(docBox =>
                            {
                                var textInsight = _documentService.GetContextualInsightsForReport(project, "Avancement");
                                docBox.Item().Text(textInsight).FontSize(8.5f);
                            });
                        }
                    });


                    // Footer
                    page.Footer().AlignCenter().Text(t =>
                    {
                        t.Span("Page ");
                        t.CurrentPageNumber();
                        t.Span(" sur ");
                        t.TotalPages();
                    });
                });
            }).GeneratePdf(destPath);
        }

        /// <summary>
        /// Generates a PDF Financial Report
        /// </summary>
        public void GenerateFinancialReportPdf(Project project, string destPath, string themeColor = "#2B579A")
        {
            var metrics = _evmService.CalculateMetrics(project);
            var color = ConvertHexToQuestColor(themeColor);

            Document.Create(container =>
            {
                container.Page(page =>
                {
                    page.Size(PageSizes.A4);
                    page.Margin(1.5f, Unit.Centimetre);
                    page.PageColor(Colors.White);
                    page.DefaultTextStyle(x => x.FontSize(11).FontColor(Colors.Grey.Darken3));

                    // Header
                    page.Header().Row(row =>
                    {
                        row.RelativeItem().Column(col =>
                        {
                            col.Item().Text($"RAPPORT FINANCIER & EVM").FontSize(20).Bold().FontColor(color);
                            col.Item().Text($"Projet : {project.Name} ({project.Code})").FontSize(14).Medium();
                            col.Item().Text($"Manager : {project.Manager}").FontSize(10).FontColor(Colors.Grey.Darken1);
                        });
                        row.ConstantItem(80).AlignRight().Column(col =>
                        {
                            col.Item().Text("PORTFOLIO").FontSize(12).Bold().FontColor(Colors.Grey.Lighten1);
                            col.Item().Text(DateTime.Now.ToString("dd/MM/yyyy")).FontSize(9).FontColor(Colors.Grey.Darken1);
                        });
                    });

                    // Content
                    page.Content().PaddingVertical(1, Unit.Centimetre).Column(col =>
                    {
                        col.Item().Text("Analyse de la Valeur Acquise (Earned Value Management)").FontSize(12).Bold().FontColor(color);
                        col.Item().PaddingTop(5);

                        // EVM Indicators Table
                        col.Item().Table(table =>
                        {
                            table.ColumnsDefinition(columns =>
                            {
                                columns.RelativeColumn(3); // Metric Name
                                columns.RelativeColumn(1); // Abbr
                                columns.RelativeColumn(2); // Value
                                columns.RelativeColumn(4); // Meaning
                            });

                            table.Header(h =>
                            {
                                h.Cell().Background(color).Padding(5).Text("Indicateur").Bold().FontColor(Colors.White).FontSize(9);
                                h.Cell().Background(color).Padding(5).Text("Code").Bold().FontColor(Colors.White).FontSize(9);
                                h.Cell().Background(color).Padding(5).AlignRight().Text("Valeur").Bold().FontColor(Colors.White).FontSize(9);
                                h.Cell().Background(color).Padding(5).Text("Interprétation").Bold().FontColor(Colors.White).FontSize(9);
                            });

                            void AddRow(string name, string code, string val, string desc, bool highlight = false)
                            {
                                var bg = highlight ? Colors.Grey.Lighten3 : Colors.White;
                                
                                var cell1 = table.Cell().Background(bg).Padding(5).Text(name).FontSize(9);
                                if (highlight) cell1.Bold();
                                
                                table.Cell().Background(bg).Padding(5).Text(code).FontSize(9);
                                
                                var cell3 = table.Cell().Background(bg).Padding(5).AlignRight().Text(val).FontSize(9);
                                if (highlight) cell3.Bold();
                                
                                table.Cell().Background(bg).Padding(5).Text(desc).FontSize(9);
                            }

                            AddRow("Budget initial à terminaison", "BAC", $"{metrics.BAC:C0}", "Budget total alloué au projet");
                            AddRow("Valeur Planifiée (Prévu cumulé)", "PV", $"{metrics.PV:C0}", "Budget prévu pour le travail planifié");
                            AddRow("Valeur Acquise (Réalisé cumulé)", "EV", $"{metrics.EV:C0}", "Budget prévu pour le travail réellement fait");
                            AddRow("Coût Réel (Dépense cumulée)", "AC", $"{metrics.AC:C0}", "Dépense réelle engagée");
                            
                            var cvColor = metrics.CV >= 0 ? "Sous-budget" : "Dépassement";
                            AddRow("Écart de Coût (Variance)", "CV", $"{metrics.CV:C0}", $"{cvColor}", true);
                            
                            var svColor = metrics.SV >= 0 ? "En avance" : "En retard";
                            AddRow("Écart de Délai (Variance)", "SV", $"{metrics.SV:C0}", $"{svColor}", true);

                            AddRow("Indice Performance Coût", "CPI", $"{metrics.CPI:F2}", metrics.CPI >= 1.0 ? "Rentable (<= budget)" : "Surconsommation (dépassement)");
                            AddRow("Indice Performance Délai", "SPI", $"{metrics.SPI:F2}", metrics.SPI >= 1.0 ? "En avance / À l'heure" : "En retard sur planning");
                            AddRow("Coût Estimé Final", "EAC", $"{metrics.EAC:C0}", "Estimation du coût final révisé");
                            AddRow("Reste à Dépenser", "ETC", $"{metrics.ETC:C0}", "Coût nécessaire pour finir le projet");
                            AddRow("Écart Final Estimé", "VAC", $"{metrics.VAC:C0}", metrics.VAC >= 0 ? "Économie finale" : "Perte finale");
                        });

                        col.Item().PaddingTop(20);
                        col.Item().Text("Détail du Registre des Dépenses").FontSize(12).Bold().FontColor(color);
                        col.Item().PaddingTop(5);

                        // Cost Ledger Table
                        if (project.CostEntries.Any())
                        {
                            col.Item().Table(table =>
                            {
                                table.ColumnsDefinition(columns =>
                                {
                                    columns.RelativeColumn(1.5f); // Date
                                    columns.RelativeColumn(2); // Category
                                    columns.RelativeColumn(3); // Description
                                    columns.RelativeColumn(2.5f); // Resource/Supplier
                                    columns.RelativeColumn(1.5f); // Est
                                    columns.RelativeColumn(1.5f); // Act
                                });

                                table.Header(h =>
                                {
                                    h.Cell().Background(color).Padding(5).Text("Date").Bold().FontColor(Colors.White).FontSize(9);
                                    h.Cell().Background(color).Padding(5).Text("Catégorie").Bold().FontColor(Colors.White).FontSize(9);
                                    h.Cell().Background(color).Padding(5).Text("Description").Bold().FontColor(Colors.White).FontSize(9);
                                    h.Cell().Background(color).Padding(5).Text("Ressource / Fournisseur").Bold().FontColor(Colors.White).FontSize(9);
                                    h.Cell().Background(color).Padding(5).AlignRight().Text("Est. (MAD)").Bold().FontColor(Colors.White).FontSize(9);
                                    h.Cell().Background(color).Padding(5).AlignRight().Text("Réel (MAD)").Bold().FontColor(Colors.White).FontSize(9);
                                });

                                int idx = 0;
                                foreach (var cost in project.CostEntries.OrderBy(c => c.Date))
                                {
                                    var bg = idx++ % 2 == 0 ? Colors.Grey.Lighten5 : Colors.White;
                                    table.Cell().Background(bg).Padding(4).Text(cost.Date.ToString("dd/MM/yyyy")).FontSize(8.5f);
                                    table.Cell().Background(bg).Padding(4).Text(cost.Category).FontSize(8.5f);
                                    table.Cell().Background(bg).Padding(4).Text(cost.Description).FontSize(8.5f);
                                    table.Cell().Background(bg).Padding(4).Text(string.IsNullOrEmpty(cost.Supplier) ? cost.ResourceName : $"{cost.ResourceName} ({cost.Supplier})").FontSize(8.5f);
                                    table.Cell().Background(bg).Padding(4).AlignRight().Text($"{cost.EstimatedCost:F0}").FontSize(8.5f);
                                    table.Cell().Background(bg).Padding(4).AlignRight().Text($"{cost.ActualCost:F0}").FontSize(8.5f);
                                }
                            });
                        }
                        else
                        {
                            col.Item().Border(1).BorderColor(Colors.Grey.Lighten2).Padding(10).Text("Aucune dépense enregistrée dans le registre des coûts pour ce projet. Le coût réel (AC) est calculé sur la base de l'avancement des tâches.").Italic().FontSize(10);
                        }
                    });

                    // Footer
                    page.Footer().AlignCenter().Text(t =>
                    {
                        t.Span("Page ");
                        t.CurrentPageNumber();
                        t.Span(" sur ");
                        t.TotalPages();
                    });
                });
            }).GeneratePdf(destPath);
        }

        /// <summary>
        /// Generates a PDF Project Closeout Report
        /// </summary>
        public void GenerateCloseoutReportPdf(Project project, string destPath, string themeColor = "#2B579A")
        {
            var metrics = _evmService.CalculateMetrics(project);
            var color = ConvertHexToQuestColor(themeColor);

            Document.Create(container =>
            {
                container.Page(page =>
                {
                    page.Size(PageSizes.A4);
                    page.Margin(1.5f, Unit.Centimetre);
                    page.PageColor(Colors.White);
                    page.DefaultTextStyle(x => x.FontSize(11).FontColor(Colors.Grey.Darken3));

                    // Header
                    page.Header().Row(row =>
                    {
                        row.RelativeItem().Column(col =>
                        {
                            col.Item().Text($"RAPPORT FINAL DE CLÔTURE").FontSize(20).Bold().FontColor(color);
                            col.Item().Text($"Projet : {project.Name} ({project.Code})").FontSize(14).Medium();
                            col.Item().Text($"Manager : {project.Manager} | Client : {project.Client}").FontSize(10).FontColor(Colors.Grey.Darken1);
                        });
                        row.ConstantItem(80).AlignRight().Column(col =>
                        {
                            col.Item().Text("PORTFOLIO").FontSize(12).Bold().FontColor(Colors.Grey.Lighten1);
                            col.Item().Text(DateTime.Now.ToString("dd/MM/yyyy")).FontSize(9).FontColor(Colors.Grey.Darken1);
                        });
                    });

                    // Content
                    page.Content().PaddingVertical(1, Unit.Centimetre).Column(col =>
                    {
                        col.Item().Background(Colors.Grey.Lighten4).Padding(10).Column(box =>
                        {
                            box.Item().Text("Objectif de Clôture").FontSize(12).Bold().FontColor(color);
                            box.Item().PaddingTop(5).Text("Ce document formalise la fin du projet. Il établit le bilan final des objectifs atteints, de la tenue des délais et du budget consommé, et compile les enseignements tirés (Lessons Learned) pour capitaliser sur les futurs projets.").FontSize(9.5f).Italic();
                        });

                        col.Item().PaddingTop(15);
                        col.Item().Text("1. Bilan Financier & Temporel").FontSize(12).Bold().FontColor(color);
                        col.Item().PaddingTop(5);

                        // Budget & Schedule Summary Table
                        col.Item().Table(table =>
                        {
                            table.ColumnsDefinition(columns =>
                            {
                                columns.RelativeColumn(3); // Dimension
                                columns.RelativeColumn(2); // Planified
                                columns.RelativeColumn(2); // Actual
                                columns.RelativeColumn(2); // Variance
                            });

                            table.Header(h =>
                            {
                                h.Cell().Background(color).Padding(5).Text("Dimension").Bold().FontColor(Colors.White).FontSize(9);
                                h.Cell().Background(color).Padding(5).AlignRight().Text("Planifié / Estimé").Bold().FontColor(Colors.White).FontSize(9);
                                h.Cell().Background(color).Padding(5).AlignRight().Text("Réel Constaté").Bold().FontColor(Colors.White).FontSize(9);
                                h.Cell().Background(color).Padding(5).AlignRight().Text("Écart").Bold().FontColor(Colors.White).FontSize(9);
                            });

                            // Budget
                            double budgetVar = metrics.BAC - metrics.AC;
                            table.Cell().Padding(5).Text("Budget Global (MAD)").FontSize(9);
                            table.Cell().Padding(5).AlignRight().Text($"{metrics.BAC:N0}").FontSize(9);
                            table.Cell().Padding(5).AlignRight().Text($"{metrics.AC:N0}").FontSize(9);
                            table.Cell().Padding(5).AlignRight().Text($"{(budgetVar >= 0 ? "+" : "")}{budgetVar:N0}").FontSize(9).Bold().FontColor(budgetVar >= 0 ? Colors.Green.Darken2 : Colors.Red.Darken2);

                            // Start Date
                            table.Cell().Padding(5).Text("Date de Début").FontSize(9);
                            table.Cell().Padding(5).AlignRight().Text(project.TargetStartDate?.ToString("dd/MM/yyyy") ?? "-").FontSize(9);
                            table.Cell().Padding(5).AlignRight().Text(project.ActualStartDate?.ToString("dd/MM/yyyy") ?? "-").FontSize(9);
                            table.Cell().Padding(5).AlignRight().Text("-").FontSize(9);

                            // End Date
                            table.Cell().Padding(5).Text("Date de Fin").FontSize(9);
                            table.Cell().Padding(5).AlignRight().Text(project.TargetEndDate?.ToString("dd/MM/yyyy") ?? "-").FontSize(9);
                            table.Cell().Padding(5).AlignRight().Text(project.ActualEndDate?.ToString("dd/MM/yyyy") ?? "-").FontSize(9);
                            table.Cell().Padding(5).AlignRight().Text("-").FontSize(9);
                        });

                        col.Item().PaddingTop(20);
                        col.Item().Text("2. Enseignements Tirés & Retours d'Expérience (Lessons Learned)").FontSize(12).Bold().FontColor(color);
                        col.Item().PaddingTop(5);

                        col.Item().Border(1).BorderColor(Colors.Grey.Lighten2).Padding(10).Column(lessonsBox =>
                        {
                            if (!string.IsNullOrEmpty(project.LessonsLearned))
                            {
                                lessonsBox.Item().Text(project.LessonsLearned).FontSize(10);
                            }
                            else
                            {
                                lessonsBox.Item().Text("Aucune leçon apprise ou retour d'expérience spécifique n'a été rédigé pour le moment. À remplir par le chef de projet lors du bilan.").Italic().FontSize(10);
                            }
                        });

                        col.Item().PaddingTop(20);
                        col.Item().Text("3. Historique des Décisions Majeures").FontSize(12).Bold().FontColor(color);
                        col.Item().PaddingTop(5);

                        // Fetch audit trail modifications that were flagged as major or just show top 10 modifications
                        var majorLogs = project.AuditLogs.Where(l => l.ChangeType == "Modification").Take(8).ToList();
                        if (majorLogs.Any())
                        {
                            col.Item().Table(table =>
                            {
                                table.ColumnsDefinition(columns =>
                                {
                                    columns.RelativeColumn(1.5f); // Date
                                    columns.RelativeColumn(1.5f); // User
                                    columns.RelativeColumn(2); // Field
                                    columns.RelativeColumn(2.5f); // Old
                                    columns.RelativeColumn(2.5f); // New
                                });

                                table.Header(h =>
                                {
                                    h.Cell().Background(color).Padding(5).Text("Date").Bold().FontColor(Colors.White).FontSize(9);
                                    h.Cell().Background(color).Padding(5).Text("Utilisateur").Bold().FontColor(Colors.White).FontSize(9);
                                    h.Cell().Background(color).Padding(5).Text("Élément modifié").Bold().FontColor(Colors.White).FontSize(9);
                                    h.Cell().Background(color).Padding(5).Text("Ancienne Valeur").Bold().FontColor(Colors.White).FontSize(9);
                                    h.Cell().Background(color).Padding(5).Text("Nouvelle Valeur").Bold().FontColor(Colors.White).FontSize(9);
                                });

                                int idx = 0;
                                foreach (var log in majorLogs)
                                {
                                    var bg = idx++ % 2 == 0 ? Colors.Grey.Lighten5 : Colors.White;
                                    table.Cell().Background(bg).Padding(4).Text(log.Timestamp.ToString("dd/MM/yyyy HH:mm")).FontSize(8.5f);
                                    table.Cell().Background(bg).Padding(4).Text(log.User).FontSize(8.5f);
                                    table.Cell().Background(bg).Padding(4).Text($"{log.EntityType}.{log.FieldName}").FontSize(8.5f);
                                    table.Cell().Background(bg).Padding(4).Text(TruncateString(log.OldValue, 30)).FontSize(8.5f);
                                    table.Cell().Background(bg).Padding(4).Text(TruncateString(log.NewValue, 30)).FontSize(8.5f);
                                }
                            });
                        }
                        else
                        {
                            col.Item().Border(1).BorderColor(Colors.Grey.Lighten2).Padding(10).Text("Aucune modification majeure enregistrée dans l'historique d'audit.").Italic().FontSize(10);
                        }
                    });

                    // Footer
                    page.Footer().AlignCenter().Text(t =>
                    {
                        t.Span("Page ");
                        t.CurrentPageNumber();
                        t.Span(" sur ");
                        t.TotalPages();
                    });
                });
            }).GeneratePdf(destPath);
        }

        /// <summary>
        /// Generates an official Donor Compliance & Grant Monitoring Report in PDF
        /// </summary>
        public void GenerateDonorComplianceReportPdf(Project project, string destPath, string themeColor = "#2B579A")
        {
            var diagnostic = new DocumentAnalysisService().PerformDeepDiagnostic(project);
            var color = ConvertHexToQuestColor(themeColor);

            Document.Create(container =>
            {
                container.Page(page =>
                {
                    page.Size(PageSizes.A4);
                    page.Margin(1.5f, Unit.Centimetre);
                    page.PageColor(Colors.White);
                    page.DefaultTextStyle(x => x.FontSize(10.5f).FontColor(Colors.Grey.Darken3));

                    // Header
                    page.Header().Row(row =>
                    {
                        row.RelativeItem().Column(col =>
                        {
                            col.Item().Text("RAPPORT DE CONFORMITÉ & SUIVI DES CONVENTIONS").FontSize(18).Bold().FontColor(color);
                            col.Item().Text($"Projet : {project.Name} ({project.Code})").FontSize(13).Medium();
                            col.Item().Text($"Responsable : {project.Manager} | Bénéficiaire : {project.Client}").FontSize(9.5f).FontColor(Colors.Grey.Darken1);
                        });
                        row.ConstantItem(90).AlignRight().Column(col =>
                        {
                            col.Item().Text("BAILLEUR").FontSize(12).Bold().FontColor(Colors.Grey.Lighten1);
                            col.Item().Text(DateTime.Now.ToString("dd/MM/yyyy")).FontSize(9).FontColor(Colors.Grey.Darken1);
                        });
                    });

                    // Content
                    page.Content().PaddingVertical(0.8f, Unit.Centimetre).Column(col =>
                    {
                        // 1. Executive Summary Box
                        col.Item().Background(Colors.Grey.Lighten4).Padding(10).Column(box =>
                        {
                            box.Item().Text("Synthèse du Diagnostic Contractuel").FontSize(11.5f).Bold().FontColor(color);
                            box.Item().PaddingTop(4).Text(diagnostic.ExecutiveSummary).Italic().FontSize(9.5f);
                        });

                        col.Item().PaddingTop(12);

                        // 2. Financial Baseline Indicators Grid
                        col.Item().Row(grid =>
                        {
                            grid.RelativeItem().Border(1).BorderColor(Colors.Grey.Lighten2).Padding(8).Column(indicator =>
                            {
                                indicator.Item().Text("SUBVENTION CONVENTIONNÉE").FontSize(8.5f).Bold().FontColor(Colors.Grey.Darken1);
                                indicator.Item().Text($"{diagnostic.TotalGrantCommitted:N0} MAD").FontSize(15).Bold().FontColor(color);
                            });
                            grid.ConstantItem(10);
                            grid.RelativeItem().Border(1).BorderColor(Colors.Grey.Lighten2).Padding(8).Column(indicator =>
                            {
                                indicator.Item().Text("DÉPENSES JUSTIFIÉES").FontSize(8.5f).Bold().FontColor(Colors.Grey.Darken1);
                                indicator.Item().Text($"{diagnostic.GrantConsumedAmount:N0} MAD").FontSize(15).Bold();
                            });
                            grid.ConstantItem(10);
                            grid.RelativeItem().Border(1).BorderColor(Colors.Grey.Lighten2).Padding(8).Column(indicator =>
                            {
                                indicator.Item().Text("TAUX DE CONSOMMATION").FontSize(8.5f).Bold().FontColor(Colors.Grey.Darken1);
                                var rateColor = diagnostic.GrantConsumptionRate <= 100 ? Colors.Green.Darken2 : Colors.Red.Darken2;
                                indicator.Item().Text($"{diagnostic.GrantConsumptionRate:F1}%").FontSize(15).Bold().FontColor(rateColor);
                            });
                            grid.ConstantItem(10);
                            grid.RelativeItem().Border(1).BorderColor(Colors.Grey.Lighten2).Padding(8).Column(indicator =>
                            {
                                indicator.Item().Text("SCORE DE CONFORMITÉ").FontSize(8.5f).Bold().FontColor(Colors.Grey.Darken1);
                                var scoreColor = diagnostic.ComplianceScore >= 80 ? Colors.Green.Darken2 : (diagnostic.ComplianceScore >= 60 ? Colors.Orange.Darken2 : Colors.Red.Darken2);
                                indicator.Item().Text($"{diagnostic.ComplianceScore:F0}/100").FontSize(15).Bold().FontColor(scoreColor);
                            });
                        });

                        col.Item().PaddingTop(15);

                        // 3. Registered Foundation Documents Table
                        col.Item().Text("1. Répertoire des Documents Initiaux & Conventions Enregistrées").FontSize(11.5f).Bold().FontColor(color);
                        col.Item().PaddingTop(4);

                        if (project.Documents != null && project.Documents.Any())
                        {
                            col.Item().Table(table =>
                            {
                                table.ColumnsDefinition(columns =>
                                {
                                    columns.RelativeColumn(3); // Title
                                    columns.RelativeColumn(2); // Category
                                    columns.RelativeColumn(2); // Donor
                                    columns.RelativeColumn(1.8f); // Ref
                                    columns.RelativeColumn(1.6f); // Grant
                                    columns.RelativeColumn(1.6f); // End Date
                                });

                                table.Header(h =>
                                {
                                    h.Cell().Background(color).Padding(4).Text("Intitulé").Bold().FontColor(Colors.White).FontSize(8.5f);
                                    h.Cell().Background(color).Padding(4).Text("Catégorie").Bold().FontColor(Colors.White).FontSize(8.5f);
                                    h.Cell().Background(color).Padding(4).Text("Bailleur").Bold().FontColor(Colors.White).FontSize(8.5f);
                                    h.Cell().Background(color).Padding(4).Text("Réf. Contrat").Bold().FontColor(Colors.White).FontSize(8.5f);
                                    h.Cell().Background(color).Padding(4).AlignRight().Text("Subvention").Bold().FontColor(Colors.White).FontSize(8.5f);
                                    h.Cell().Background(color).Padding(4).AlignRight().Text("Échéance").Bold().FontColor(Colors.White).FontSize(8.5f);
                                });

                                int idx = 0;
                                foreach (var doc in project.Documents)
                                {
                                    var bg = idx++ % 2 == 0 ? Colors.Grey.Lighten5 : Colors.White;
                                    table.Cell().Background(bg).Padding(4).Text(doc.Title).FontSize(8.5f);
                                    table.Cell().Background(bg).Padding(4).Text(doc.Category).FontSize(8.5f);
                                    table.Cell().Background(bg).Padding(4).Text(string.IsNullOrEmpty(doc.DonorName) ? "-" : doc.DonorName).FontSize(8.5f);
                                    table.Cell().Background(bg).Padding(4).Text(string.IsNullOrEmpty(doc.DocumentReference) ? "-" : doc.DocumentReference).FontSize(8.5f);
                                    table.Cell().Background(bg).Padding(4).AlignRight().Text(doc.ApprovedGrantAmount > 0 ? $"{doc.ApprovedGrantAmount:N0} MAD" : "-").FontSize(8.5f);
                                    table.Cell().Background(bg).Padding(4).AlignRight().Text(doc.ContractualEndDate?.ToString("dd/MM/yyyy") ?? "-").FontSize(8.5f);
                                }
                            });
                        }
                        else
                        {
                            col.Item().Border(1).BorderColor(Colors.Grey.Lighten2).Padding(8).Text("Aucun document initial ou convention n'a été rattaché pour le moment.").Italic().FontSize(9);
                        }

                        col.Item().PaddingTop(15);

                        // 4. Compliance Alerts & Strategic Recommendations
                        col.Item().Row(row =>
                        {
                            row.RelativeItem().Column(alertsCol =>
                            {
                                alertsCol.Item().Text("Points de Vigilance & Alertes").FontSize(11.5f).Bold().FontColor(Colors.Red.Medium);
                                foreach (var alert in diagnostic.ComplianceAlerts)
                                {
                                    alertsCol.Item().PaddingTop(3).Text($"• {alert}").FontSize(8.5f);
                                }
                            });
                            row.ConstantItem(15);
                            row.RelativeItem().Column(recsCol =>
                            {
                                recsCol.Item().Text("Recommandations pour le Bailleur").FontSize(11.5f).Bold().FontColor(Colors.Green.Medium);
                                foreach (var rec in diagnostic.StrategicRecommendations)
                                {
                                    recsCol.Item().PaddingTop(3).Text($"• {rec}").FontSize(8.5f);
                                }
                            });
                        });

                        col.Item().PaddingTop(15);

                        // 5. Contractual Deliverables and WBS Progress
                        col.Item().Text("2. État d'Avancement des Livrables Contractuels (WBS)").FontSize(11.5f).Bold().FontColor(color);
                        col.Item().PaddingTop(4);

                        col.Item().Table(table =>
                        {
                            table.ColumnsDefinition(columns =>
                            {
                                columns.RelativeColumn(3.5f); // Name
                                columns.RelativeColumn(2); // Assignee
                                columns.RelativeColumn(1.8f); // Status
                                columns.RelativeColumn(1.5f); // Progress
                                columns.RelativeColumn(1.8f); // Cost
                            });

                            table.Header(h =>
                            {
                                h.Cell().Background(color).Padding(4).Text("Livrable / Activité").Bold().FontColor(Colors.White).FontSize(8.5f);
                                h.Cell().Background(color).Padding(4).Text("Responsable").Bold().FontColor(Colors.White).FontSize(8.5f);
                                h.Cell().Background(color).Padding(4).Text("Statut").Bold().FontColor(Colors.White).FontSize(8.5f);
                                h.Cell().Background(color).Padding(4).AlignRight().Text("Avancement").Bold().FontColor(Colors.White).FontSize(8.5f);
                                h.Cell().Background(color).Padding(4).AlignRight().Text("Coût Engagé").Bold().FontColor(Colors.White).FontSize(8.5f);
                            });

                            int idx = 0;
                            foreach (var task in project.Tasks.Where(t => t.ParentTaskId == null).Take(10))
                            {
                                var bg = idx++ % 2 == 0 ? Colors.Grey.Lighten5 : Colors.White;
                                table.Cell().Background(bg).Padding(4).Text(task.Name).FontSize(8.5f);
                                table.Cell().Background(bg).Padding(4).Text(task.Assignee).FontSize(8.5f);
                                table.Cell().Background(bg).Padding(4).Text(task.Status).FontSize(8.5f);
                                table.Cell().Background(bg).Padding(4).AlignRight().Text($"{task.ProgressPercentage}%").FontSize(8.5f);
                                table.Cell().Background(bg).Padding(4).AlignRight().Text($"{task.Cost:N0} MAD").FontSize(8.5f);
                            }
                        });
                    });

                    // Footer
                    page.Footer().AlignCenter().Text(t =>
                    {
                        t.Span("Page ");
                        t.CurrentPageNumber();
                        t.Span(" sur ");
                        t.TotalPages();
                    });
                });
            }).GeneratePdf(destPath);
        }

        private string TruncateString(string value, int maxChars)
        {
            if (string.IsNullOrEmpty(value)) return string.Empty;
            return value.Length <= maxChars ? value : value.Substring(0, maxChars - 3) + "...";
        }

        private Color ConvertHexToQuestColor(string hex)
        {
            try
            {
                if (!hex.StartsWith("#"))
                {
                    hex = "#" + hex;
                }
                return Color.FromHex(hex);
            }
            catch
            {
                return Color.FromHex("#2B579A"); // Default navy
            }
        }
    }
}
