using System;
using System.IO;
using Microsoft.EntityFrameworkCore;
using AFMI_Gestion_projet.Models;
using Microsoft.EntityFrameworkCore.Storage.ValueConversion;
using AFMI_Gestion_projet.Services;

namespace AFMI_Gestion_projet.Data
{
    public partial class AppDbContext : DbContext
    {
        public DbSet<Project> Projects { get; set; } = null!;
        public DbSet<ProjectTask> Tasks { get; set; } = null!;
        public DbSet<CostEntry> CostEntries { get; set; } = null!;
        public DbSet<WorkflowStep> WorkflowSteps { get; set; } = null!;
        public DbSet<AuditLog> AuditLogs { get; set; } = null!;
        public DbSet<ReportHistory> ReportHistories { get; set; } = null!;
        public DbSet<ProjectTemplate> Templates { get; set; } = null!;
        public DbSet<SmtpSettings> SmtpSettings { get; set; } = null!;
        public DbSet<ProjectDocument> Documents { get; set; } = null!;
        public DbSet<ProjectBaseline> Baselines { get; set; } = null!;
        public DbSet<AiSettings> AiSettings { get; set; } = null!;
        
        // Modules ONG / Bailleurs
        public DbSet<Funder> Funders { get; set; } = null!;
        public DbSet<Indicator> Indicators { get; set; } = null!;
        public DbSet<ActivityReport> ActivityReports { get; set; } = null!;
        public DbSet<ActivityReportPhoto> ActivityReportPhotos { get; set; } = null!;


        /// <summary>Base de l'utilisateur (voir <see cref="DatabasePaths"/>). La base est migrée au premier accès.</summary>
        public AppDbContext() : this(migrate: true) { }

        public AppDbContext(DbContextOptions<AppDbContext> options) : this(options, migrate: true) { }

        private AppDbContext(bool migrate)
        {
            ConfigureTracking();
            if (migrate) DatabaseMigrator.EnsureUpToDate(this);
        }

        private AppDbContext(DbContextOptions<AppDbContext> options, bool migrate) : base(options)
        {
            ConfigureTracking();
            if (migrate) DatabaseMigrator.EnsureUpToDate(this);
        }

        /// <summary>
        /// Les suppressions en cascade sont résolues au moment de SaveChanges, après la conversion en suppression logique :
        /// supprimer un projet ne supprime donc plus ses tâches ni ses dépenses.
        /// </summary>
        private void ConfigureTracking()
        {
            ChangeTracker.CascadeDeleteTiming = Microsoft.EntityFrameworkCore.ChangeTracking.CascadeTiming.OnSaveChanges;
            ChangeTracker.DeleteOrphansTiming = Microsoft.EntityFrameworkCore.ChangeTracking.CascadeTiming.OnSaveChanges;
        }

        /// <summary>Contexte sans migration automatique : outils EF (design) et migrateur lui-même.</summary>
        internal static AppDbContext WithoutMigration(DbContextOptions<AppDbContext> options) => new(options, migrate: false);

        protected override void OnConfiguring(DbContextOptionsBuilder optionsBuilder)
        {
            if (!optionsBuilder.IsConfigured)
            {
                optionsBuilder.UseSqlite($"Data Source={DatabasePaths.GetDatabasePath()}");
            }
        }

        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            base.OnModelCreating(modelBuilder);

            // Configure Project self-referencing hierarchy
            modelBuilder.Entity<Project>()
                .HasOne(p => p.ParentProject)
                .WithMany(p => p.SubProjects)
                .HasForeignKey(p => p.ParentProjectId)
                .OnDelete(DeleteBehavior.Restrict);

            // Configure Task self-referencing hierarchy
            modelBuilder.Entity<ProjectTask>()
                .HasOne(t => t.ParentTask)
                .WithMany(t => t.SubTasks)
                .HasForeignKey(t => t.ParentTaskId)
                .OnDelete(DeleteBehavior.Cascade);

            // Cascade delete tasks, costs, workflows, audit logs, report histories when project is deleted
            modelBuilder.Entity<Project>()
                .HasMany(p => p.Tasks)
                .WithOne(t => t.Project)
                .HasForeignKey(t => t.ProjectId)
                .OnDelete(DeleteBehavior.Cascade);

            modelBuilder.Entity<Project>()
                .HasMany(p => p.CostEntries)
                .WithOne(c => c.Project)
                .HasForeignKey(c => c.ProjectId)
                .OnDelete(DeleteBehavior.Cascade);

            modelBuilder.Entity<Project>()
                .HasMany(p => p.WorkflowSteps)
                .WithOne(w => w.Project)
                .HasForeignKey(w => w.ProjectId)
                .OnDelete(DeleteBehavior.Cascade);

            modelBuilder.Entity<Project>()
                .HasMany(p => p.AuditLogs)
                .WithOne(a => a.Project)
                .HasForeignKey(a => a.ProjectId)
                .OnDelete(DeleteBehavior.Cascade);

            modelBuilder.Entity<Project>()
                .HasMany(p => p.ReportHistories)
                .WithOne(r => r.Project)
                .HasForeignKey(r => r.ProjectId)
                .OnDelete(DeleteBehavior.Cascade);

            modelBuilder.Entity<Project>()
                .HasMany(p => p.Documents)
                .WithOne(d => d.Project)
                .HasForeignKey(d => d.ProjectId)
                .OnDelete(DeleteBehavior.Cascade);

            modelBuilder.Entity<Project>()
                .HasOne(p => p.Baseline)
                .WithOne(b => b.Project)
                .HasForeignKey<ProjectBaseline>(b => b.ProjectId)
                .OnDelete(DeleteBehavior.Cascade);

            // Montants hérités : stockés en clair (REAL) depuis la migration LegacyAmountsInClear.
            // L'ancien chiffrement AES utilisait une clé fixe écrite dans le code et empêchait tout calcul SQL.

            // Secrets (mot de passe SMTP, clé API cloud) protégés par DPAPI, liés au compte Windows
            var secretConverter = new ValueConverter<string, string>(
                v => SecretProtector.Protect(v),
                v => SecretProtector.Unprotect(v)
            );

            modelBuilder.Entity<SmtpSettings>()
                .Property(s => s.Password)
                .HasConversion(secretConverter);

            modelBuilder.Entity<AiSettings>()
                .Property(s => s.CloudApiKey)
                .HasConversion(secretConverter);

            ConfigureFinance(modelBuilder);
            ConfigureEditor(modelBuilder);
            ConfigureSoftDelete(modelBuilder);
        }
    }
}
