using System;
using System.Collections.Generic;
using System.IO;
using Xunit;
using Microsoft.EntityFrameworkCore;
using AFMI_Gestion_projet.Models;
using AFMI_Gestion_projet.Services;
using AFMI_Gestion_projet.ViewModels;

[assembly: CollectionBehavior(DisableTestParallelization = true)]

namespace AFMI_Gestion_projet.Tests
{
    public class EvmTests
    {
        [Fact]
        public void TestEvmCalculations()
        {
            // 1. Arrange
            var project = new Project
            {
                Id = 1,
                Name = "Test Project",
                BudgetGlobal = 100000,
                TargetStartDate = DateTime.Today.AddDays(-10),
                TargetEndDate = DateTime.Today.AddDays(10)
            };

            var t1 = new ProjectTask
            {
                Id = 1,
                ProjectId = 1,
                Name = "Task 1",
                Budget = 40000,
                Cost = 35000,
                ProgressPercentage = 75, // EV = 30000
                TargetStartDate = DateTime.Today.AddDays(-10),
                TargetEndDate = DateTime.Today.AddDays(10)
            };

            var t2 = new ProjectTask
            {
                Id = 2,
                ProjectId = 1,
                Name = "Task 2",
                Budget = 60000,
                Cost = 15000,
                ProgressPercentage = 50, // EV = 30000
                TargetStartDate = DateTime.Today.AddDays(-10),
                TargetEndDate = DateTime.Today.AddDays(10)
            };

            project.Tasks = new List<ProjectTask> { t1, t2 };

            var service = new EvmService();

            // 2. Act
            var metrics = service.CalculateMetrics(project);

            // 3. Assert
            // BAC = 100,000 (specified in project)
            // EV = 30,000 (t1) + 30,000 (t2) = 60,000
            // AC = 35,000 (t1) + 15,000 (t2) = 50,000
            // CPI = EV / AC = 60,000 / 50,000 = 1.2
            // CV = EV - AC = 10,000
            // EAC = BAC / CPI = 100,000 / 1.2 = 83,333.33
            
            Assert.Equal(100000, metrics.BAC);
            Assert.Equal(60000, metrics.EV);
            Assert.Equal(50000, metrics.AC);
            Assert.Equal(1.2, metrics.CPI, 2);
            Assert.Equal(10000, metrics.CV);
            Assert.Equal(83333.33, metrics.EAC, 2);
        }

        [Fact]
        public void TestPerformance500Projects()
        {
            // 1. Arrange - base propre à ce test (jamais la base partagée des autres tests, exécutés en parallèle)
            string perfDb = Path.Combine(Path.GetTempPath(), "afmi-desktop-tests", $"perf_{Guid.NewGuid():N}.db");
            Directory.CreateDirectory(Path.GetDirectoryName(perfDb)!);
            var options = new Microsoft.EntityFrameworkCore.DbContextOptionsBuilder<AFMI_Gestion_projet.Data.AppDbContext>()
                .UseSqlite($"Data Source={perfDb};Pooling=False")
                .Options;

            using (var context = new AFMI_Gestion_projet.Data.AppDbContext(options))   // migrée à l'ouverture
            {

                // 2. Act - Insert 500 projects in a single transaction for speed
                var rand = new Random();
                var projects = new List<Project>();
                for (int i = 1; i <= 500; i++)
                {
                    projects.Add(new Project
                    {
                        Name = $"Projet Test Performance {i}",
                        Code = $"PERF-{1000 + i}",
                        Manager = "Directeur de test",
                        Client = "Client test",
                        BudgetGlobal = 50000 + (rand.Next(10) * 10000),
                        Status = i % 2 == 0 ? "Exécution" : "Planification",
                        Priority = "Moyenne",
                        TargetStartDate = DateTime.Today.AddDays(-rand.Next(30)),
                        TargetEndDate = DateTime.Today.AddDays(30 + rand.Next(60))
                    });
                }

                var stopwatch = System.Diagnostics.Stopwatch.StartNew();
                
                context.Projects.AddRange(projects);
                context.SaveChanges();

                stopwatch.Stop();
                long insertTimeMs = stopwatch.ElapsedMilliseconds;
                System.Diagnostics.Debug.WriteLine($"Inserted 500 projects in {insertTimeMs}ms");

                // 3. Act - Measure Portfolio Grid Loading Time (loading all projects with task counting)
                stopwatch.Restart();
                
                // Une seule requête, comme le portefeuille (500 requêtes successives mesuraient surtout la lenteur du poste de build)
                var loadedProjects = context.Projects.Include(proj => proj.Tasks).AsSplitQuery().ToList();

                stopwatch.Stop();
                long loadTimeMs = stopwatch.ElapsedMilliseconds;

                // 4. Assert load time is under 2000 milliseconds (2 seconds)
                Assert.True(loadTimeMs < 2000, $"Load time was too slow: {loadTimeMs}ms (must be < 2000ms)");

                // 5. Act - Measure PDF Generation Time for a project
                var targetProject = loadedProjects.First();
                // Add a few dummy tasks to have a realistic report
                targetProject.Tasks.Add(new ProjectTask { Name = "Tâche A", Budget = 10000, ProgressPercentage = 100, Status = "Terminé" });
                targetProject.Tasks.Add(new ProjectTask { Name = "Tâche B", Budget = 20000, ProgressPercentage = 50, Status = "En cours" });
                context.SaveChanges();

                var reportService = new ReportGeneratorService();
                string testPdfPath = "performance_report_test.pdf";

                stopwatch.Restart();
                reportService.GenerateProgressReportPdf(targetProject, testPdfPath);
                stopwatch.Stop();
                long pdfTimeMs = stopwatch.ElapsedMilliseconds;

                // Cleanup
                if (File.Exists(testPdfPath))
                {
                    File.Delete(testPdfPath);
                }
                context.Database.EnsureDeleted();

                // 6. Assert report generation is under 5000 milliseconds (5 seconds)
                Assert.True(pdfTimeMs < 5000, $"PDF generation was too slow: {pdfTimeMs}ms (must be < 5000ms)");
            }
        }

        /// <summary>
        /// Décision D2-a (v2, Lot 1) : les montants sont stockés en clair (la migration DecryptLegacyAmounts a déchiffré
        /// ceux de la 1.3.0) ; la confidentialité repose sur le profil Windows et BitLocker. Remplace l'ancien test du
        /// chiffrement, qui lisait en outre la base réelle de l'utilisateur au lieu de la base jetable des tests.
        /// </summary>
        [Fact]
        public void TestBudgetStoredInClear_InThrowawayDatabase()
        {
            string dbPath = AFMI_Gestion_projet.Data.DatabasePaths.GetDatabasePath();
            string realDb = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "AFMIGestionProjet", "database.db");
            Assert.NotEqual(Path.GetFullPath(realDb), Path.GetFullPath(dbPath));          // jamais la base réelle

            using (var context = new AFMI_Gestion_projet.Data.AppDbContext())
            {
                context.Projects.Add(new Project { Name = "Projet budget", Code = "CLR-001", BudgetGlobal = 999999 });
                context.SaveChanges();
            }
            using (var connection = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={dbPath};Pooling=False"))
            {
                connection.Open();
                using var command = connection.CreateCommand();
                command.CommandText = "SELECT BudgetGlobal FROM Projects WHERE Code = 'CLR-001' LIMIT 1";
                Assert.Equal(999999d, Convert.ToDouble(command.ExecuteScalar(), System.Globalization.CultureInfo.InvariantCulture));
            }
        }

        [Fact]
        public void TestWordAndExcelReportExporters()
        {
            var project = new Project
            {
                Name = "Test Export Project",
                Code = "EXP-101",
                Manager = "John Doe",
                Client = "Client ACME"
            };

            var vm = new ProjectDetailViewModel(new MainViewModel(), 0);
            vm.Project = project;

            // 1. Test Word Export
            string testDocPath = Path.Combine(Path.GetTempPath(), "test_report_doc.doc");
            if (File.Exists(testDocPath)) File.Delete(testDocPath);

            vm.ExportToWordHtml(testDocPath, "TITRE TEST", "Contenu de test pour la synthèse.");

            Assert.True(File.Exists(testDocPath), "Word file was not created.");
            string docContent = File.ReadAllText(testDocPath);
            Assert.Contains("TITRE TEST", docContent);
            Assert.Contains("Contenu de test pour la synthèse.", docContent);

            // 2. Test Excel Export
            string testXlsPath = Path.Combine(Path.GetTempPath(), "test_report_xls.xls");
            if (File.Exists(testXlsPath)) File.Delete(testXlsPath);

            vm.ExportToExcelTsv(testXlsPath);

            Assert.True(File.Exists(testXlsPath), "Excel file was not created.");
            string xlsContent = File.ReadAllText(testXlsPath);
            Assert.Contains("RAPPORT FINANCIER & ANALYSE EVM", xlsContent);
            Assert.Contains("EXP-101", xlsContent);

            // Cleanup
            if (File.Exists(testDocPath)) File.Delete(testDocPath);
            if (File.Exists(testXlsPath)) File.Delete(testXlsPath);
        }
    }
}
