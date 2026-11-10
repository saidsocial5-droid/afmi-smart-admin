using System;
using System.IO;
using Microsoft.EntityFrameworkCore;
using AFMI_Gestion_projet.Models;
using Microsoft.EntityFrameworkCore.Storage.ValueConversion;
using AFMI_Gestion_projet.Services;

namespace AFMI_Gestion_projet.Data
{
    public class AppDbContext : DbContext
    {
        private static bool _schemaEnsured = false;
        private static readonly object _schemaLock = new object();

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


        public AppDbContext()
        {
            EnsureSchemaUpToDate();
        }

        public AppDbContext(DbContextOptions<AppDbContext> options) : base(options)
        {
            EnsureSchemaUpToDate();
        }

        private void EnsureSchemaUpToDate()
        {
            if (!_schemaEnsured)
            {
                lock (_schemaLock)
                {
                    if (!_schemaEnsured)
                    {
                        EnsureDocumentColumnsExist();
                        _schemaEnsured = true;
                    }
                }
            }
        }


        protected override void OnConfiguring(DbContextOptionsBuilder optionsBuilder)
        {
            if (!optionsBuilder.IsConfigured)
            {
                string folder = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "AFMIGestionProjet");
                if (!Directory.Exists(folder))
                {
                    Directory.CreateDirectory(folder);
                }
                string dbPath = Path.Combine(folder, "database.db");
                optionsBuilder.UseSqlite($"Data Source={dbPath}");
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

            // Financial Encryption Value Converters (AES-256)
            var doubleEncryptConverter = new ValueConverter<double, string>(
                v => DoubleToString(v),
                v => StringToDouble(v)
            );

            modelBuilder.Entity<Project>()
                .Property(p => p.BudgetGlobal)
                .HasConversion(doubleEncryptConverter);

            modelBuilder.Entity<ProjectTask>()
                .Property(t => t.Budget)
                .HasConversion(doubleEncryptConverter);

            modelBuilder.Entity<ProjectTask>()
                .Property(t => t.Cost)
                .HasConversion(doubleEncryptConverter);

            modelBuilder.Entity<CostEntry>()
                .Property(c => c.EstimatedCost)
                .HasConversion(doubleEncryptConverter);

            modelBuilder.Entity<CostEntry>()
                .Property(c => c.ActualCost)
                .HasConversion(doubleEncryptConverter);

            modelBuilder.Entity<ProjectDocument>()
                .Property(d => d.ApprovedGrantAmount)
                .HasConversion(doubleEncryptConverter);

            modelBuilder.Entity<ProjectBaseline>()
                .Property(b => b.TotalGrantCommitted)
                .HasConversion(doubleEncryptConverter);

            modelBuilder.Entity<ProjectBaseline>()
                .Property(b => b.CoFinancingShare)
                .HasConversion(doubleEncryptConverter);

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
        }

        /// <summary>
        /// Safely creates missing tables (Documents, Baselines) and adds new columns if upgrading an existing SQLite database.
        /// Called once at application startup / DbContext initialization.
        /// </summary>
        public void EnsureDocumentColumnsExist()
        {
            try
            {
                Database.EnsureCreated();
                var conn = Database.GetDbConnection();
                if (conn.State != System.Data.ConnectionState.Open)
                {
                    conn.Open();
                }
                using var cmd = conn.CreateCommand();

                // 1. Ensure Documents table exists
                cmd.CommandText = @"
                    CREATE TABLE IF NOT EXISTS Documents (
                        Id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        ProjectId INTEGER NOT NULL,
                        Title TEXT NOT NULL DEFAULT '',
                        Category TEXT NOT NULL DEFAULT 'Convention Bailleur',
                        DocumentPhase TEXT NOT NULL DEFAULT 'Montage',
                        Tags TEXT NOT NULL DEFAULT '',
                        IsKeyReference INTEGER NOT NULL DEFAULT 0,
                        DocumentVersion TEXT NOT NULL DEFAULT '',
                        DonorName TEXT NOT NULL DEFAULT '',
                        DocumentReference TEXT NOT NULL DEFAULT '',
                        SignatureDate TEXT,
                        ContractualEndDate TEXT,
                        ApprovedGrantAmount TEXT NOT NULL DEFAULT '',
                        FilePath TEXT NOT NULL DEFAULT '',
                        OriginalFileName TEXT NOT NULL DEFAULT '',
                        FileExtension TEXT NOT NULL DEFAULT '',
                        FileSize INTEGER NOT NULL DEFAULT 0,
                        Notes TEXT NOT NULL DEFAULT '',
                        ExtractedSummary TEXT NOT NULL DEFAULT '',
                        FullExtractedText TEXT NOT NULL DEFAULT '',
                        KeyInsights TEXT NOT NULL DEFAULT '',
                        AnalyzedDate TEXT,
                        UploadedDate TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(ProjectId) REFERENCES Projects(Id) ON DELETE CASCADE
                    );";
                cmd.ExecuteNonQuery();

                // 2. Ensure Baselines table exists
                cmd.CommandText = @"
                    CREATE TABLE IF NOT EXISTS Baselines (
                        Id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        ProjectId INTEGER NOT NULL,
                        DonorName TEXT NOT NULL DEFAULT '',
                        ContractualReference TEXT NOT NULL DEFAULT '',
                        TotalGrantCommitted TEXT NOT NULL DEFAULT '',
                        CoFinancingShare TEXT NOT NULL DEFAULT '',
                        EligibilityDeadline TEXT,
                        NextReportingDeadline TEXT,
                        ReportingFrequency TEXT NOT NULL DEFAULT 'Semestriel',
                        ContractualDeliverables TEXT NOT NULL DEFAULT '',
                        EligibilityRulesNotes TEXT NOT NULL DEFAULT '',
                        ComplianceScore REAL NOT NULL DEFAULT 100,
                        DiagnosticSummary TEXT NOT NULL DEFAULT '',
                        LastAnalyzedDate TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(ProjectId) REFERENCES Projects(Id) ON DELETE CASCADE
                    );";
                cmd.ExecuteNonQuery();

                // 3. Ensure AiSettings table exists
                cmd.CommandText = @"
                    CREATE TABLE IF NOT EXISTS AiSettings (
                        Id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        UseOllama INTEGER NOT NULL DEFAULT 0,
                        OllamaEndpoint TEXT NOT NULL DEFAULT 'http://localhost:11434',
                        OllamaModel TEXT NOT NULL DEFAULT 'mistral',
                        UseCloudApi INTEGER NOT NULL DEFAULT 0,
                        CloudProvider TEXT NOT NULL DEFAULT 'OpenAI',
                        CloudApiKey TEXT NOT NULL DEFAULT ''
                    );";
                cmd.ExecuteNonQuery();

                // 3.5 Ensure Funder, Indicator, ActivityReport tables exist
                cmd.CommandText = @"
                    CREATE TABLE IF NOT EXISTS Funders (
                        Id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        Name TEXT NOT NULL DEFAULT '',
                        PrimaryColor TEXT NOT NULL DEFAULT '#000000',
                        LogoPath TEXT NOT NULL DEFAULT '',
                        LegalMentions TEXT NOT NULL DEFAULT '',
                        HeaderText TEXT NOT NULL DEFAULT '',
                        FooterText TEXT NOT NULL DEFAULT ''
                    );";
                cmd.ExecuteNonQuery();

                try {
                    cmd.CommandText = "ALTER TABLE Funders ADD COLUMN HeaderText TEXT NOT NULL DEFAULT '';";
                    cmd.ExecuteNonQuery();
                } catch { }

                try {
                    cmd.CommandText = "ALTER TABLE Funders ADD COLUMN FooterText TEXT NOT NULL DEFAULT '';";
                    cmd.ExecuteNonQuery();
                } catch { }

                cmd.CommandText = @"
                    CREATE TABLE IF NOT EXISTS Indicators (
                        Id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        Name TEXT NOT NULL DEFAULT '',
                        Description TEXT NOT NULL DEFAULT '',
                        TargetValue REAL NOT NULL DEFAULT 0,
                        CurrentValue REAL NOT NULL DEFAULT 0,
                        Unit TEXT NOT NULL DEFAULT '',
                        ProjectId INTEGER NOT NULL,
                        FOREIGN KEY(ProjectId) REFERENCES Projects(Id) ON DELETE CASCADE
                    );";
                cmd.ExecuteNonQuery();

                cmd.CommandText = @"
                    CREATE TABLE IF NOT EXISTS ActivityReports (
                        Id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        Title TEXT NOT NULL DEFAULT '',
                        ActivityDate TEXT NOT NULL,
                        Location TEXT NOT NULL DEFAULT '',
                        ParticipantsCount INTEGER NOT NULL DEFAULT 0,
                        Narrative TEXT NOT NULL DEFAULT '',
                        Difficulties TEXT NOT NULL DEFAULT '',
                        Recommendations TEXT NOT NULL DEFAULT '',
                        Status TEXT NOT NULL DEFAULT 'Brouillon',
                        ProjectTaskId INTEGER NOT NULL,
                        IndicatorId INTEGER,
                        FOREIGN KEY(ProjectTaskId) REFERENCES Tasks(Id) ON DELETE CASCADE,
                        FOREIGN KEY(IndicatorId) REFERENCES Indicators(Id) ON DELETE SET NULL
                    );";
                cmd.ExecuteNonQuery();

                cmd.CommandText = @"
                    CREATE TABLE IF NOT EXISTS ActivityReportPhotos (
                        Id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        LocalFilePath TEXT NOT NULL DEFAULT '',
                        Caption TEXT NOT NULL DEFAULT '',
                        ActivityReportId INTEGER NOT NULL,
                        FOREIGN KEY(ActivityReportId) REFERENCES ActivityReports(Id) ON DELETE CASCADE
                    );";
                cmd.ExecuteNonQuery();

                // 4. Ensure new columns are added if table existed prior to this version
                var alterStatements = new[]
                {
                    "ALTER TABLE Documents ADD COLUMN DocumentPhase TEXT NOT NULL DEFAULT 'Montage'",
                    "ALTER TABLE Documents ADD COLUMN Tags TEXT NOT NULL DEFAULT ''",
                    "ALTER TABLE Documents ADD COLUMN IsKeyReference INTEGER NOT NULL DEFAULT 0",
                    "ALTER TABLE Documents ADD COLUMN DocumentVersion TEXT NOT NULL DEFAULT ''",
                    "ALTER TABLE Documents ADD COLUMN FullExtractedText TEXT NOT NULL DEFAULT ''",
                    "ALTER TABLE Documents ADD COLUMN KeyInsights TEXT NOT NULL DEFAULT ''",
                    "ALTER TABLE Documents ADD COLUMN AnalyzedDate TEXT",
                    "ALTER TABLE Projects ADD COLUMN LocalFolderPath TEXT NOT NULL DEFAULT ''",
                    "ALTER TABLE AiSettings ADD COLUMN UseCloudApi INTEGER NOT NULL DEFAULT 0",
                    "ALTER TABLE AiSettings ADD COLUMN CloudProvider TEXT NOT NULL DEFAULT 'OpenAI'",
                    "ALTER TABLE AiSettings ADD COLUMN CloudApiKey TEXT NOT NULL DEFAULT ''",
                    "ALTER TABLE Projects ADD COLUMN FunderId INTEGER"
                };

                foreach (var sql in alterStatements)
                {
                    try
                    {
                        cmd.CommandText = sql;
                        cmd.ExecuteNonQuery();
                    }
                    catch
                    {
                        // Column already exists — SQLite throws on duplicate ALTER, which is expected
                    }
                }

                conn.Close();
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"EnsureDocumentColumnsExist warning: {ex.Message}");
            }
        }


        private static string DoubleToString(double val)
        {
            return EncryptionService.Encrypt(val.ToString(System.Globalization.CultureInfo.InvariantCulture));
        }

        private static double StringToDouble(string s)
        {
            string decrypted = EncryptionService.Decrypt(s);
            if (double.TryParse(decrypted, System.Globalization.NumberStyles.Any, System.Globalization.CultureInfo.InvariantCulture, out var val))
            {
                return val;
            }
            return 0;
        }
    }
}
