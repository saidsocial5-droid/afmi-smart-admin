using System.Data.Common;

namespace AFMI_Gestion_projet.Data
{
    /// <summary>
    /// Mise à niveau des bases créées avant les migrations EF Core (versions ≤ 1.3.0, schéma créé par
    /// <c>EnsureCreated</c> puis complété par des <c>ALTER TABLE</c>). Amène une telle base exactement au schéma
    /// de la migration <c>Baseline_1_3_0</c>, qui est ensuite marquée comme appliquée.
    /// Reprise à l'identique de l'ancien <c>AppDbContext.EnsureDocumentColumnsExist</c>.
    /// </summary>
    internal static class LegacySchemaUpgrader
    {
        public static void Upgrade(DbConnection conn)
        {
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

        }
    }
}
