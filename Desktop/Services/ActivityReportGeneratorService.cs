using System;
using System.IO;
using System.Linq;
using AFMI_Gestion_projet.Models;
using QuestPDF.Fluent;
using QuestPDF.Helpers;
using QuestPDF.Infrastructure;

namespace AFMI_Gestion_projet.Services
{
    public class ActivityReportGeneratorService
    {
        public void GenerateActivityReportPdf(ActivityReport report, Project project, Funder? funder, string outputPath)
        {
            // Configuration QuestPDF (Licence communautaire)
            QuestPDF.Settings.License = LicenseType.Community;

            string primaryColorHex = funder != null && !string.IsNullOrEmpty(funder.PrimaryColor) ? funder.PrimaryColor : "#2B579A";
            string logoPath = funder?.LogoPath ?? "";

            Document.Create(container =>
            {
                container.Page(page =>
                {
                    page.Size(PageSizes.A4);
                    page.Margin(2, Unit.Centimetre);
                    page.PageColor(Colors.White);
                    page.DefaultTextStyle(x => x.FontSize(11).FontFamily(Fonts.Arial));

                    // HEADER
                    page.Header().Element(headerContainer =>
                    {
                        headerContainer.Row(row =>
                        {
                            row.RelativeItem().Column(col =>
                            {
                                if (funder != null && !string.IsNullOrWhiteSpace(funder.HeaderText))
                                {
                                    col.Item().PaddingBottom(5).Text(funder.HeaderText).FontSize(10).FontColor(primaryColorHex).Italic();
                                }
                                col.Item().Text("Compte Rendu d'Activité").FontSize(20).SemiBold().FontColor(primaryColorHex);
                                col.Item().Text(project.Name).FontSize(14).FontColor(Colors.Grey.Darken2);
                                col.Item().Text($"Date de l'activité: {report.ActivityDate:dd/MM/yyyy}").FontSize(11);
                            });

                            if (!string.IsNullOrEmpty(logoPath) && File.Exists(logoPath))
                            {
                                row.ConstantItem(100).Image(logoPath);
                            }
                        });
                    });

                    // CONTENT
                    page.Content().PaddingVertical(1, Unit.Centimetre).Column(col =>
                    {
                        // Informations générales
                        col.Item().BorderBottom(1).BorderColor(primaryColorHex).PaddingBottom(5).Text("1. Informations Générales").FontSize(14).SemiBold().FontColor(primaryColorHex);
                        col.Item().PaddingTop(10).Table(table =>
                        {
                            table.ColumnsDefinition(columns =>
                            {
                                columns.ConstantColumn(150);
                                columns.RelativeColumn();
                            });
                            
                            table.Cell().Text("Lieu :");
                            table.Cell().Text(report.Location);
                            
                            table.Cell().Text("Participants :");
                            table.Cell().Text(report.ParticipantsCount.ToString());

                            if (report.Indicator != null)
                            {
                                table.Cell().Text("Indicateur visé :");
                                table.Cell().Text(report.Indicator.Name);
                            }
                        });

                        col.Item().PaddingTop(20);

                        // Narratif
                        col.Item().BorderBottom(1).BorderColor(primaryColorHex).PaddingBottom(5).Text("2. Narratif de l'activité").FontSize(14).SemiBold().FontColor(primaryColorHex);
                        col.Item().PaddingTop(10).Text(report.Narrative);

                        col.Item().PaddingTop(20);

                        // Difficultés
                        col.Item().BorderBottom(1).BorderColor(primaryColorHex).PaddingBottom(5).Text("3. Difficultés rencontrées").FontSize(14).SemiBold().FontColor(primaryColorHex);
                        col.Item().PaddingTop(10).Text(report.Difficulties);

                        col.Item().PaddingTop(20);

                        // Recommandations
                        col.Item().BorderBottom(1).BorderColor(primaryColorHex).PaddingBottom(5).Text("4. Recommandations").FontSize(14).SemiBold().FontColor(primaryColorHex);
                        col.Item().PaddingTop(10).Text(report.Recommendations);

                        col.Item().PaddingTop(20);

                        // Photos
                        if (report.Photos != null && report.Photos.Any())
                        {
                            col.Item().PageBreak(); // Photos on a new page to avoid bad cuts
                            col.Item().BorderBottom(1).BorderColor(primaryColorHex).PaddingBottom(5).Text("5. Annexes : Photos").FontSize(14).SemiBold().FontColor(primaryColorHex);
                            col.Item().PaddingTop(10).Grid(grid =>
                            {
                                grid.VerticalSpacing(15);
                                grid.HorizontalSpacing(15);
                                grid.AlignCenter();
                                grid.Columns(2);

                                foreach (var photo in report.Photos)
                                {
                                    if (!string.IsNullOrEmpty(photo.LocalFilePath) && File.Exists(photo.LocalFilePath))
                                    {
                                        grid.Item().Column(imgCol =>
                                        {
                                            imgCol.Item().Height(200).Image(photo.LocalFilePath).FitArea();
                                            imgCol.Item().PaddingTop(5).Text(photo.Caption).FontSize(9).Italic().AlignCenter();
                                        });
                                    }
                                }
                            });
                        }
                    });

                    // FOOTER
                    page.Footer().Element(footerContainer =>
                    {
                        footerContainer.Column(footerCol =>
                        {
                            if (funder != null && !string.IsNullOrWhiteSpace(funder.FooterText))
                            {
                                footerCol.Item().PaddingBottom(2).Text(funder.FooterText).FontSize(9).FontColor(primaryColorHex).AlignCenter().Bold();
                            }
                            if (funder != null && !string.IsNullOrEmpty(funder.LegalMentions))
                            {
                                footerCol.Item().Text(funder.LegalMentions).FontSize(8).FontColor(Colors.Grey.Medium).AlignCenter();
                            }
                            footerCol.Item().PaddingTop(5).AlignCenter().Text(x =>
                            {
                                x.Span("Page ");
                                x.CurrentPageNumber();
                                x.Span(" sur ");
                                x.TotalPages();
                            });
                        });
                    });
                });
            })
            .GeneratePdf(outputPath);
        }
    }
}
