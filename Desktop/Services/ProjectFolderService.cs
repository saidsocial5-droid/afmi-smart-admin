using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text;
using AFMI_Gestion_projet.Models;

namespace AFMI_Gestion_projet.Services
{
    public class ProjectFolderStructureResult
    {
        public bool Success { get; set; }
        public string RootFolderPath { get; set; } = string.Empty;
        public int CreatedFoldersCount { get; set; }
        public List<string> CreatedSubFolders { get; set; } = new();
        public string Message { get; set; } = string.Empty;
    }

    public class ProjectFolderService
    {
        public static string DefaultBaseProjectsDirectory
        {
            get
            {
                string docs = Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments);
                return Path.Combine(docs, "AFMI_Projets");
            }
        }

        /// <summary>
        /// Crée le dossier du projet ainsi que l'ensemble des sous-dossiers trimestriels
        /// contenant chacun : Comptes Rendus (CR), Rapports d'Avancement, Rapports Financiers
        /// </summary>
        public ProjectFolderStructureResult CreateQuarterlyFolderStructure(Project project, string? customBasePath = null)
        {
            var result = new ProjectFolderStructureResult();

            if (project == null)
            {
                result.Success = false;
                result.Message = "Projet non spécifié.";
                return result;
            }

            try
            {
                string baseDir = !string.IsNullOrWhiteSpace(customBasePath) && Directory.Exists(customBasePath)
                    ? customBasePath
                    : DefaultBaseProjectsDirectory;

                if (!Directory.Exists(baseDir))
                {
                    Directory.CreateDirectory(baseDir);
                }

                // Nom du dossier sécurisé pour le système de fichiers
                string safeCode = SanitizeFolderName(project.Code);
                string safeName = SanitizeFolderName(project.Name);
                string projectFolderName = string.IsNullOrWhiteSpace(safeCode) 
                    ? safeName 
                    : $"{safeCode} - {safeName}";

                if (string.IsNullOrWhiteSpace(projectFolderName))
                {
                    projectFolderName = $"Projet_{project.Id}";
                }

                string projectRoot = Path.Combine(baseDir, projectFolderName);
                if (!Directory.Exists(projectRoot))
                {
                    Directory.CreateDirectory(projectRoot);
                }
                result.RootFolderPath = projectRoot;

                // Déterminer les années à couvrir selon les dates du projet
                int startYear = project.TargetStartDate?.Year ?? project.ActualStartDate?.Year ?? DateTime.Today.Year;
                int endYear = project.TargetEndDate?.Year ?? project.ActualEndDate?.Year ?? startYear;
                if (endYear < startYear) endYear = startYear;
                // Si la durée dépasse 10 ans (cas d'erreur de saisie), on limite
                if (endYear - startYear > 10) endYear = startYear + 2;

                var quarters = new (string qName, string period)[]
                {
                    ("T1 - Premier Trimestre", "Janvier à Mars"),
                    ("T2 - Deuxième Trimestre", "Avril à Juin"),
                    ("T3 - Troisième Trimestre", "Juillet à Septembre"),
                    ("T4 - Quatrième Trimestre", "Octobre à Décembre")
                };

                var subCategories = new[]
                {
                    "Comptes Rendus (CR)",
                    "Rapports d'Avancement",
                    "Rapports Financiers"
                };

                // Dossier général
                string generalDocsDir = Path.Combine(projectRoot, "Documents Généraux & Conventions");
                if (!Directory.Exists(generalDocsDir))
                {
                    Directory.CreateDirectory(generalDocsDir);
                    result.CreatedFoldersCount++;
                    result.CreatedSubFolders.Add("Documents Généraux & Conventions");
                }

                // Pour chaque année du projet
                for (int year = startYear; year <= endYear; year++)
                {
                    string yearDirName = (startYear == endYear) ? $"Année {year}" : $"Année {year}";
                    string yearPath = Path.Combine(projectRoot, yearDirName);
                    if (!Directory.Exists(yearPath))
                    {
                        Directory.CreateDirectory(yearPath);
                        result.CreatedFoldersCount++;
                        result.CreatedSubFolders.Add(yearDirName);
                    }

                    // Pour chaque trimestre
                    foreach (var (qName, period) in quarters)
                    {
                        string qDirName = $"{qName} ({period})";
                        string qPath = Path.Combine(yearPath, qDirName);
                        if (!Directory.Exists(qPath))
                        {
                            Directory.CreateDirectory(qPath);
                            result.CreatedFoldersCount++;
                            result.CreatedSubFolders.Add($"{yearDirName}/{qDirName}");
                        }

                        // Créer les 3 sous-dossiers requis pour chaque trimestre :
                        // 1. Comptes Rendus (CR)
                        // 2. Rapports d'Avancement
                        // 3. Rapports Financiers
                        foreach (var cat in subCategories)
                        {
                            string catPath = Path.Combine(qPath, cat);
                            if (!Directory.Exists(catPath))
                            {
                                Directory.CreateDirectory(catPath);
                                result.CreatedFoldersCount++;
                                result.CreatedSubFolders.Add($"{yearDirName}/{qDirName}/{cat}");
                            }
                        }
                    }
                }

                // Générer un fichier descriptif d'information dans le dossier racine
                string infoFile = Path.Combine(projectRoot, "Informations_Organisation_Projet.txt");
                var sb = new StringBuilder();
                sb.AppendLine("================================================================================");
                sb.AppendLine($"DOSSIER DE PROJET : {project.Name}");
                sb.AppendLine($"Code Projet        : {project.Code}");
                sb.AppendLine($"Chef de Projet     : {project.Manager}");
                sb.AppendLine($"Commanditaire      : {project.Client}");
                sb.AppendLine($"Budget Global      : {project.BudgetGlobal:N0} €");
                sb.AppendLine($"Période Couverte   : {startYear} à {endYear}");
                sb.AppendLine($"Arborescence créée : {DateTime.Now:dd/MM/yyyy HH:mm}");
                sb.AppendLine("================================================================================");
                sb.AppendLine();
                sb.AppendLine("ORGANISATION DES SOUS-DOSSIERS TRIMESTRIELS :");
                sb.AppendLine("Chaque trimestre contient 3 sous-dossiers dédiés :");
                sb.AppendLine("  1. Comptes Rendus (CR)      : Procès-verbaux de réunions de suivi, COPIL, chantiers");
                sb.AppendLine("  2. Rapports d'Avancement    : Rapports narratifs périodiques, états d'avancement");
                sb.AppendLine("  3. Rapports Financiers      : Suivis budgétaires, états de dépenses, factures");
                sb.AppendLine();
                sb.AppendLine("Ce dossier est synchronisé avec l'application AFMI Gestion Projet.");
                File.WriteAllText(infoFile, sb.ToString(), Encoding.UTF8);

                result.Success = true;
                result.Message = $"Arborescence créée avec succès dans :\n{projectRoot}\n({result.CreatedFoldersCount} dossiers et sous-dossiers trimestriels initialisés).";
            }
            catch (Exception ex)
            {
                result.Success = false;
                result.Message = $"Erreur lors de la création des dossiers : {ex.Message}";
            }

            return result;
        }

        /// <summary>
        /// Ouvre un dossier directement dans l'Explorateur Windows
        /// </summary>
        public bool OpenFolderInExplorer(string folderPath)
        {
            if (string.IsNullOrWhiteSpace(folderPath) || !Directory.Exists(folderPath))
            {
                return false;
            }

            try
            {
                Process.Start(new ProcessStartInfo
                {
                    FileName = folderPath,
                    UseShellExecute = true,
                    Verb = "open"
                });
                return true;
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"Failed to open folder: {ex.Message}");
                return false;
            }
        }

        /// <summary>
        /// Récupère le chemin du dossier trimestriel pour une catégorie donnée
        /// </summary>
        public string GetQuarterSubfolder(string projectRoot, int year, int quarter, string categoryName)
        {
            if (quarter < 1) quarter = 1;
            if (quarter > 4) quarter = 4;

            string[] quarterNames = {
                "T1 - Premier Trimestre (Janvier à Mars)",
                "T2 - Deuxième Trimestre (Avril à Juin)",
                "T3 - Troisième Trimestre (Juillet à Septembre)",
                "T4 - Quatrième Trimestre (Octobre à Décembre)"
            };

            string qFolder = quarterNames[quarter - 1];
            return Path.Combine(projectRoot, $"Année {year}", qFolder, categoryName);
        }

        private static string SanitizeFolderName(string? name)
        {
            if (string.IsNullOrWhiteSpace(name)) return string.Empty;
            string invalidChars = new string(Path.GetInvalidFileNameChars()) + new string(Path.GetInvalidPathChars());
            var sb = new StringBuilder();
            foreach (char c in name)
            {
                if (!invalidChars.Contains(c))
                {
                    sb.Append(c);
                }
                else
                {
                    sb.Append('_');
                }
            }
            return sb.ToString().Trim();
        }
    }
}
