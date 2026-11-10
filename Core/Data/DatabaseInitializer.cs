using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using AFMI_Gestion_projet.Models;

namespace AFMI_Gestion_projet.Data
{
    public static class DatabaseInitializer
    {
        public static void Initialize(AppDbContext context)
        {
            // Le schéma est créé et mis à jour par les migrations EF Core (DatabaseMigrator), dès la création du contexte.

            // Seed Templates if empty
            if (!context.Templates.Any())
            {
                SeedTemplates(context);
            }

            // Seed Sample Projects if empty
            if (!context.Projects.Any())
            {
                SeedSampleProjects(context);
            }
        }

        private static void SeedTemplates(AppDbContext context)
        {
            var templates = new List<ProjectTemplate>
            {
                new ProjectTemplate
                {
                    Name = "Méthodologie PM² (Standard Européen)",
                    Description = "Modèle officiel PM² comprenant les phases d'Initiation, Planification, Exécution et Clôture avec ses livrables clés.",
                    ProjectDataJson = JsonSerializer.Serialize(new TemplateData
                    {
                        Steps = new List<string> { "Initiation", "Planification", "Exécution", "Clôture" },
                        Tasks = new List<TemplateTask>
                        {
                            new TemplateTask { Name = "Charte de Projet (Project Charter)", Description = "Définition des objectifs et approbation initiale du projet.", Budget = 5000 },
                            new TemplateTask { Name = "Plan de Conduite de Projet (PCP)", Description = "Document de référence décrivant la gestion du projet.", Budget = 10000 },
                            new TemplateTask { Name = "Organigramme des Tâches (WBS)", Description = "Structure arborescente du travail à réaliser.", Budget = 4000 },
                            new TemplateTask { Name = "Exécution des travaux", Description = "Réalisation des livrables techniques.", Budget = 50000 },
                            new TemplateTask { Name = "Livrables intermédiaires & Validation", Description = "Validation par le client des jalons clés.", Budget = 15000 },
                            new TemplateTask { Name = "Rapport final de clôture (Project End Report)", Description = "Bilan et leçons apprises.", Budget = 5000 }
                        }
                    })
                },
                new ProjectTemplate
                {
                    Name = "Développement Agile (Scrum)",
                    Description = "Modèle pour projets logiciels avec sprints itératifs, backlog de produit, réunions quotidiennes et revues de sprints.",
                    ProjectDataJson = JsonSerializer.Serialize(new TemplateData
                    {
                        Steps = new List<string> { "Cadrage & Backlog", "Sprint 1", "Sprint 2", "Sprint 3", "Sprint 4", "Rétrospective globale" },
                        Tasks = new List<TemplateTask>
                        {
                            new TemplateTask { Name = "Spécification des User Stories", Description = "Rédaction du product backlog initial.", Budget = 8000 },
                            new TemplateTask { Name = "Sprint 1 : Architecture & Fondations", Description = "Mise en place de l'infrastructure et de la base de données.", Budget = 20000 },
                            new TemplateTask { Name = "Sprint 2 : Fonctionnalités Core", Description = "Développement des fonctionnalités principales de l'application.", Budget = 25000 },
                            new TemplateTask { Name = "Sprint 3 : UI & Intégration", Description = "Design de l'interface et intégration des services.", Budget = 25000 },
                            new TemplateTask { Name = "Sprint 4 : Recette & Correction", Description = "Stabilisation, tests de charge et correction des anomalies.", Budget = 15000 },
                            new TemplateTask { Name = "Déploiement en Production & Review", Description = "Mise en ligne et démonstration finale.", Budget = 7000 }
                        }
                    })
                },
                new ProjectTemplate
                {
                    Name = "Cycle en Cascade (Waterfall)",
                    Description = "Modèle classique séquentiel comprenant les phases d'Analyse, Conception, Réalisation, Tests et Déploiement.",
                    ProjectDataJson = JsonSerializer.Serialize(new TemplateData
                    {
                        Steps = new List<string> { "Spécifications", "Conception", "Réalisation", "Intégration", "Recette", "Déploiement" },
                        Tasks = new List<TemplateTask>
                        {
                            new TemplateTask { Name = "Étude d'opportunité & CDC", Description = "Rédaction du cahier des charges.", Budget = 12000 },
                            new TemplateTask { Name = "Conception Générale & Détaillée", Description = "Architecture technique et maquettage UI.", Budget = 18000 },
                            new TemplateTask { Name = "Développement des modules", Description = "Codage et tests unitaires.", Budget = 60000 },
                            new TemplateTask { Name = "Phase de Recette (UAT)", Description = "Validation par les utilisateurs finaux.", Budget = 15000 },
                            new TemplateTask { Name = "Mise en service & Formation", Description = "Transfert de compétences et démarrage.", Budget = 10000 }
                        }
                    })
                }
            };

            context.Templates.AddRange(templates);
            context.SaveChanges();
        }

        private static void SeedSampleProjects(AppDbContext context)
        {
            // Sample Project 1: Nouveau CRM d'Entreprise (PM² Hybride)
            var p1 = new Project
            {
                Name = "Déploiement CRM Corporate",
                Code = "CRM-2026",
                Description = "Migration de l'ancien outil commercial vers une plateforme moderne SaaS avec intégration ERP.",
                Manager = "Sophie Martin",
                Owner = "Jean-Pierre Durand",
                Client = "Direction Commerciale",
                Department = "DSI - Systèmes d'Information",
                TargetStartDate = DateTime.Now.AddDays(-60),
                TargetEndDate = DateTime.Now.AddDays(120),
                ActualStartDate = DateTime.Now.AddDays(-58),
                Status = "Exécution",
                Priority = "Critique",
                BudgetGlobal = 150000,
                LessonsLearned = ""
            };

            context.Projects.Add(p1);
            context.SaveChanges(); // Save to get ID

            // Add PM2 workflow steps
            var steps = new List<WorkflowStep>
            {
                new WorkflowStep { ProjectId = p1.Id, StepName = "Initiation", Order = 1, IsCompleted = true, CompletedDate = DateTime.Now.AddDays(-50) },
                new WorkflowStep { ProjectId = p1.Id, StepName = "Planification", Order = 2, IsCompleted = true, CompletedDate = DateTime.Now.AddDays(-30) },
                new WorkflowStep { ProjectId = p1.Id, StepName = "Exécution", Order = 3, IsCompleted = false },
                new WorkflowStep { ProjectId = p1.Id, StepName = "Clôture", Order = 4, IsCompleted = false }
            };
            context.WorkflowSteps.AddRange(steps);

            // Add Tasks with hierarchy and dependency
            // Parent Task 1: Initiation (Completed)
            var t1 = new ProjectTask
            {
                ProjectId = p1.Id,
                Name = "Phase d'Initiation CRM",
                Description = "Lancement et cadrage commercial",
                ProgressPercentage = 100,
                Status = "Terminé",
                Budget = 20000,
                Cost = 19500,
                TargetStartDate = DateTime.Now.AddDays(-60),
                TargetEndDate = DateTime.Now.AddDays(-45),
                ActualStartDate = DateTime.Now.AddDays(-60),
                ActualEndDate = DateTime.Now.AddDays(-46)
            };
            context.Tasks.Add(t1);
            context.SaveChanges();

            var t1_1 = new ProjectTask
            {
                ProjectId = p1.Id,
                ParentTaskId = t1.Id,
                Name = "Charte de Projet CRM",
                Description = "Rédaction et signature de la charte de projet.",
                ProgressPercentage = 100,
                Status = "Terminé",
                Budget = 10000,
                Cost = 9800,
                TargetStartDate = DateTime.Now.AddDays(-60),
                TargetEndDate = DateTime.Now.AddDays(-52),
                ActualStartDate = DateTime.Now.AddDays(-60),
                ActualEndDate = DateTime.Now.AddDays(-53)
            };
            var t1_2 = new ProjectTask
            {
                ProjectId = p1.Id,
                ParentTaskId = t1.Id,
                Name = "Analyse d'impact commerciale",
                Description = "Ateliers avec les équipes de vente.",
                ProgressPercentage = 100,
                Status = "Terminé",
                Budget = 10000,
                Cost = 9700,
                TargetStartDate = DateTime.Now.AddDays(-52),
                TargetEndDate = DateTime.Now.AddDays(-45),
                ActualStartDate = DateTime.Now.AddDays(-53),
                ActualEndDate = DateTime.Now.AddDays(-46)
            };
            context.Tasks.AddRange(t1_1, t1_2);

            // Parent Task 2: Planification (Completed)
            var t2 = new ProjectTask
            {
                ProjectId = p1.Id,
                Name = "Planification & Architecture",
                Description = "Définition de l'architecture technique et du plan de conduite de projet",
                ProgressPercentage = 100,
                Status = "Terminé",
                Budget = 30000,
                Cost = 31000,
                TargetStartDate = DateTime.Now.AddDays(-45),
                TargetEndDate = DateTime.Now.AddDays(-15),
                ActualStartDate = DateTime.Now.AddDays(-45),
                ActualEndDate = DateTime.Now.AddDays(-13),
                Predecessors = t1.Id.ToString()
            };
            context.Tasks.Add(t2);
            context.SaveChanges();

            var t2_1 = new ProjectTask
            {
                ProjectId = p1.Id,
                ParentTaskId = t2.Id,
                Name = "Plan de Conduite de Projet",
                Description = "Validation des process de gouvernance.",
                ProgressPercentage = 100,
                Status = "Terminé",
                Budget = 15000,
                Cost = 15000,
                TargetStartDate = DateTime.Now.AddDays(-45),
                TargetEndDate = DateTime.Now.AddDays(-30),
                ActualStartDate = DateTime.Now.AddDays(-45),
                ActualEndDate = DateTime.Now.AddDays(-30)
            };
            var t2_2 = new ProjectTask
            {
                ProjectId = p1.Id,
                ParentTaskId = t2.Id,
                Name = "Modélisation de la base de données CRM",
                Description = "Schémas conceptuels et physiques.",
                ProgressPercentage = 100,
                Status = "Terminé",
                Budget = 15000,
                Cost = 16000,
                TargetStartDate = DateTime.Now.AddDays(-30),
                TargetEndDate = DateTime.Now.AddDays(-15),
                ActualStartDate = DateTime.Now.AddDays(-30),
                ActualEndDate = DateTime.Now.AddDays(-13)
            };
            context.Tasks.AddRange(t2_1, t2_2);

            // Parent Task 3: Conception & Développement API (In Progress)
            var t3 = new ProjectTask
            {
                ProjectId = p1.Id,
                Name = "Développement Backend & API",
                Description = "Développement des connecteurs ERP et base de données",
                ProgressPercentage = 60,
                Status = "En cours",
                Budget = 50000,
                Cost = 42000,
                TargetStartDate = DateTime.Now.AddDays(-15),
                TargetEndDate = DateTime.Now.AddDays(30),
                ActualStartDate = DateTime.Now.AddDays(-13),
                Predecessors = t2.Id.ToString()
            };
            context.Tasks.Add(t3);
            context.SaveChanges();

            var t3_1 = new ProjectTask
            {
                ProjectId = p1.Id,
                ParentTaskId = t3.Id,
                Name = "Développement des connecteurs ERP",
                Description = "Intégration SAP/Oracle.",
                ProgressPercentage = 90,
                Status = "En cours",
                Budget = 25000,
                Cost = 28000,
                TargetStartDate = DateTime.Now.AddDays(-15),
                TargetEndDate = DateTime.Now.AddDays(5),
                ActualStartDate = DateTime.Now.AddDays(-13)
            };
            var t3_2 = new ProjectTask
            {
                ProjectId = p1.Id,
                ParentTaskId = t3.Id,
                Name = "API d'exposition des données CRM",
                Description = "Sécurisation et endpoints REST.",
                ProgressPercentage = 30,
                Status = "En cours",
                Budget = 25000,
                Cost = 14000,
                TargetStartDate = DateTime.Now.AddDays(5),
                TargetEndDate = DateTime.Now.AddDays(30),
                ActualStartDate = DateTime.Now.AddDays(3)
            };
            context.Tasks.AddRange(t3_1, t3_2);

            // Parent Task 4: Intégration UI & Recette (Not Started)
            var t4 = new ProjectTask
            {
                ProjectId = p1.Id,
                Name = "Développement Frontend & Tests",
                Description = "Interface utilisateur et phase d'UAT",
                ProgressPercentage = 0,
                Status = "À faire",
                Budget = 50000,
                Cost = 0,
                TargetStartDate = DateTime.Now.AddDays(30),
                TargetEndDate = DateTime.Now.AddDays(120),
                Predecessors = t3.Id.ToString()
            };
            context.Tasks.Add(t4);
            context.SaveChanges();

            // Add Cost Entries
            var costs = new List<CostEntry>
            {
                new CostEntry { ProjectId = p1.Id, Category = "Ressources", ResourceName = "Sophie Martin (Chef de Projet)", Supplier = "", Description = "Honoraires de pilotage de projet", EstimatedCost = 15000, ActualCost = 15500, Date = DateTime.Now.AddDays(-40) },
                new CostEntry { ProjectId = p1.Id, Category = "Prestataires", ResourceName = "Consultant CRM externe", Supplier = "CRM Solutions SAS", Description = "Conseil en architecture et modélisation", EstimatedCost = 20000, ActualCost = 21000, Date = DateTime.Now.AddDays(-30) },
                new CostEntry { ProjectId = p1.Id, Category = "Matériel", ResourceName = "Serveurs de test AWS", Supplier = "Amazon Web Services", Description = "Hébergement de l'environnement de dev", EstimatedCost = 5000, ActualCost = 4200, Date = DateTime.Now.AddDays(-15) },
                new CostEntry { ProjectId = p1.Id, Category = "Divers", ResourceName = "Licences Dev", Supplier = "Microsoft", Description = "Licences outils de dev", EstimatedCost = 2000, ActualCost = 1800, Date = DateTime.Now.AddDays(-55) }
            };
            context.CostEntries.AddRange(costs);

            // Add Audit Log
            var logs = new List<AuditLog>
            {
                new AuditLog { ProjectId = p1.Id, EntityType = "Projet", EntityId = p1.Id, ChangeType = "Création", FieldName = "Projet", OldValue = "", NewValue = "Déploiement CRM Corporate", User = "Admin", Timestamp = DateTime.Now.AddDays(-60) },
                new AuditLog { ProjectId = p1.Id, EntityType = "Tâche", EntityId = t1.Id, ChangeType = "Création", FieldName = "Nom", OldValue = "", NewValue = "Phase d'Initiation CRM", User = "Sophie Martin", Timestamp = DateTime.Now.AddDays(-59) },
                new AuditLog { ProjectId = p1.Id, EntityType = "Projet", EntityId = p1.Id, ChangeType = "Modification", FieldName = "BudgetGlobal", OldValue = "120000", NewValue = "150000", User = "Jean-Pierre Durand", Timestamp = DateTime.Now.AddDays(-30) }
            };
            context.AuditLogs.AddRange(logs);

            // Sample Project 2: Nouveau Site Web Vitrine (Waterfall court)
            var p2 = new Project
            {
                Name = "Refonte Site Web Institutionnel",
                Code = "WEB-2026",
                Description = "Création d'un site web responsive moderne pour la communication externe du groupe.",
                Manager = "Thomas Dubois",
                Owner = "Valérie Leclerc",
                Client = "Direction de la Communication",
                Department = "Communication & Marketing",
                TargetStartDate = DateTime.Now.AddDays(-20),
                TargetEndDate = DateTime.Now.AddDays(25),
                ActualStartDate = DateTime.Now.AddDays(-18),
                Status = "Planification",
                Priority = "Moyenne",
                BudgetGlobal = 40000,
                LessonsLearned = ""
            };
            context.Projects.Add(p2);
            context.SaveChanges();

            // Add steps
            var steps2 = new List<WorkflowStep>
            {
                new WorkflowStep { ProjectId = p2.Id, StepName = "Cadrage", Order = 1, IsCompleted = true, CompletedDate = DateTime.Now.AddDays(-10) },
                new WorkflowStep { ProjectId = p2.Id, StepName = "Conception", Order = 2, IsCompleted = false },
                new WorkflowStep { ProjectId = p2.Id, StepName = "Développement", Order = 3, IsCompleted = false },
                new WorkflowStep { ProjectId = p2.Id, StepName = "Lancement", Order = 4, IsCompleted = false }
            };
            context.WorkflowSteps.AddRange(steps2);

            var tp1 = new ProjectTask
            {
                ProjectId = p2.Id,
                Name = "Spécifications & Maquettage",
                Description = "Cahier des charges et maquettes Figma",
                ProgressPercentage = 100,
                Status = "Terminé",
                Budget = 10000,
                Cost = 9500,
                TargetStartDate = DateTime.Now.AddDays(-20),
                TargetEndDate = DateTime.Now.AddDays(-5),
                ActualStartDate = DateTime.Now.AddDays(-18),
                ActualEndDate = DateTime.Now.AddDays(-6)
            };
            context.Tasks.Add(tp1);
            context.SaveChanges();

            var tp2 = new ProjectTask
            {
                ProjectId = p2.Id,
                Name = "Développement du Thème",
                Description = "Développement du CMS et de l'intégration HTML/CSS",
                ProgressPercentage = 20,
                Status = "En cours",
                Budget = 20000,
                Cost = 5000,
                TargetStartDate = DateTime.Now.AddDays(-5),
                TargetEndDate = DateTime.Now.AddDays(15),
                ActualStartDate = DateTime.Now.AddDays(-5),
                Predecessors = tp1.Id.ToString()
            };
            context.Tasks.Add(tp2);
            context.SaveChanges();

            var tp3 = new ProjectTask
            {
                ProjectId = p2.Id,
                Name = "Intégration de contenu & Recette",
                Description = "Saisie des pages institutionnelles et recette finale",
                ProgressPercentage = 0,
                Status = "À faire",
                Budget = 10000,
                Cost = 0,
                TargetStartDate = DateTime.Now.AddDays(15),
                TargetEndDate = DateTime.Now.AddDays(25),
                Predecessors = tp2.Id.ToString()
            };
            context.Tasks.Add(tp3);

            var costs2 = new List<CostEntry>
            {
                new CostEntry { ProjectId = p2.Id, Category = "Prestataires", ResourceName = "Agence Web Externe", Supplier = "Digital Factory", Description = "Création des maquettes graphiques", EstimatedCost = 8000, ActualCost = 8000, Date = DateTime.Now.AddDays(-10) }
            };
            context.CostEntries.AddRange(costs2);

            context.SaveChanges();
        }

        private class TemplateData
        {
            public List<string> Steps { get; set; } = new();
            public List<TemplateTask> Tasks { get; set; } = new();
        }

        private class TemplateTask
        {
            public string Name { get; set; } = string.Empty;
            public string Description { get; set; } = string.Empty;
            public double Budget { get; set; }
        }
    }
}
