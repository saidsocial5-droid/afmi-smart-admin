using System.Collections.Concurrent;
using System.Globalization;
using AFMI_Gestion_projet.Services;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;

namespace AFMI_Gestion_projet.Data
{
    /// <summary>
    /// Met la base à jour au premier accès de chaque processus :
    /// 1. une base antérieure aux migrations (≤ 1.3.0) est complétée puis marquée « Baseline_1_3_0 » ;
    /// 2. si des migrations sont en attente, la base est sauvegardée (API de sauvegarde SQLite, copie cohérente) ;
    /// 3. les migrations sont appliquées.
    /// Une erreur est propagée : on ne travaille jamais sur une base à moitié migrée.
    /// </summary>
    public static class DatabaseMigrator
    {
        public const string BaselineMigrationId = "20261110220128_Baseline_1_3_0";
        /// <summary>Fonction SQL utilisée par la migration qui remet les montants hérités en clair.</summary>
        public const string LegacyAmountFunction = "afmi_legacy_amount";
        private const int BackupsToKeep = 30;

        private static readonly ConcurrentDictionary<string, bool> Migrated = new(StringComparer.OrdinalIgnoreCase);
        private static readonly object Lock = new();

        public static void EnsureUpToDate(AppDbContext context)
        {
            string key = context.Database.GetConnectionString() ?? string.Empty;
            if (Migrated.ContainsKey(key)) return;
            lock (Lock)
            {
                if (Migrated.ContainsKey(key)) return;
                Migrate(context);
                Migrated[key] = true;
            }
        }

        /// <summary>Oublie l'état « déjà migrée » : à appeler après avoir remplacé le fichier de base (import, restauration).</summary>
        public static void ForgetMigrationState() => Migrated.Clear();

        /// <summary>Retourne le chemin de la sauvegarde créée, ou null si aucune migration n'était en attente.</summary>
        public static string? Migrate(AppDbContext context)
        {
            var connection = (SqliteConnection)context.Database.GetDbConnection();
            bool openedHere = connection.State != System.Data.ConnectionState.Open;
            if (openedHere) connection.Open();
            try
            {
                RegisterFunctions(connection);

                if (TableExists(connection, "Projects") && !TableExists(connection, "__EFMigrationsHistory"))
                {
                    LegacySchemaUpgrader.Upgrade(connection);
                    MarkBaselineApplied(connection, context);
                }

                var pending = context.Database.GetPendingMigrations().ToList();
                if (pending.Count == 0) return null;

                string? backup = null;
                if (TableExists(connection, "Projects"))
                {
                    backup = Backup(connection, pending[^1]);
                }

                context.Database.Migrate();
                return backup;
            }
            finally
            {
                if (openedHere) connection.Close();
            }
        }

        private static void RegisterFunctions(SqliteConnection connection)
        {
            // Montants stockés chiffrés (≤ 1.3.0) ou en clair : renvoie toujours le nombre.
            connection.CreateFunction<object?, double>(LegacyAmountFunction, value => LegacyAmount(value), isDeterministic: true);
        }

        internal static double LegacyAmount(object? value)
        {
            switch (value)
            {
                case null or DBNull: return 0;
                case double d: return d;
                case long l: return l;
                case string s:
                    if (s.Length == 0) return 0;
                    string plain = EncryptionService.Decrypt(s);
                    if (double.TryParse(plain, NumberStyles.Any, CultureInfo.InvariantCulture, out double parsed)) return parsed;
                    throw new InvalidOperationException($"Montant illisible lors de la migration : « {s} ». Migration annulée, base inchangée.");
                default:
                    return Convert.ToDouble(value, CultureInfo.InvariantCulture);
            }
        }

        private static bool TableExists(SqliteConnection connection, string table)
        {
            using var cmd = connection.CreateCommand();
            cmd.CommandText = "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = $name";
            cmd.Parameters.AddWithValue("$name", table);
            return Convert.ToInt64(cmd.ExecuteScalar()) > 0;
        }

        private static void MarkBaselineApplied(SqliteConnection connection, AppDbContext context)
        {
            string productVersion = typeof(DbContext).Assembly
                .GetCustomAttributes(typeof(System.Reflection.AssemblyInformationalVersionAttribute), false)
                .OfType<System.Reflection.AssemblyInformationalVersionAttribute>().FirstOrDefault()?.InformationalVersion.Split('+')[0]
                ?? "9.0.8";
            using var cmd = connection.CreateCommand();
            cmd.CommandText = @"
                CREATE TABLE IF NOT EXISTS __EFMigrationsHistory (
                    MigrationId TEXT NOT NULL CONSTRAINT PK___EFMigrationsHistory PRIMARY KEY,
                    ProductVersion TEXT NOT NULL);
                INSERT OR IGNORE INTO __EFMigrationsHistory (MigrationId, ProductVersion) VALUES ($id, $version);";
            cmd.Parameters.AddWithValue("$id", BaselineMigrationId);
            cmd.Parameters.AddWithValue("$version", productVersion);
            cmd.ExecuteNonQuery();
        }

        private static string? Backup(SqliteConnection source, string targetMigration)
        {
            string? dbPath = source.DataSource;
            if (string.IsNullOrEmpty(dbPath) || dbPath == ":memory:" || !File.Exists(dbPath)) return null;

            string dir = DatabasePaths.GetBackupDirectory(Path.GetFullPath(dbPath));
            Directory.CreateDirectory(dir);
            string stamp = DateTime.Now.ToString("yyyyMMdd_HHmmss_fff", CultureInfo.InvariantCulture);
            string name = targetMigration.Contains('_') ? targetMigration[(targetMigration.IndexOf('_') + 1)..] : targetMigration;
            string backupPath = Path.Combine(dir, $"{Path.GetFileNameWithoutExtension(dbPath)}_{stamp}_avant_{name}.db");

            using (var destination = new SqliteConnection($"Data Source={backupPath};Pooling=False"))
            {
                destination.Open();
                source.BackupDatabase(destination);
            }

            foreach (var old in new DirectoryInfo(dir).GetFiles("*_avant_*.db").OrderByDescending(f => f.Name).Skip(BackupsToKeep))
            {
                try { old.Delete(); } catch (IOException) { }
            }
            return backupPath;
        }
    }
}
