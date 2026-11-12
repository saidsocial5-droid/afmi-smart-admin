using System.Globalization;
using System.Text.Json;
using AFMI_Gestion_projet.Data;
using Microsoft.Data.Sqlite;

namespace AFMI_Gestion_projet.Services
{
    /// <summary>Sauvegarde présente dans le dossier des sauvegardes.</summary>
    public sealed record BackupInfo(string Path, string Name, DateTime CreatedAt, long Size, string Reason);

    /// <summary>
    /// Sauvegardes de la base (Lot 7) : copies cohérentes par l'API de sauvegarde SQLite (jamais une copie de fichier
    /// pendant l'utilisation), planification (au démarrage, quotidienne, hebdomadaire, manuelle), conservation des N
    /// dernières, et restauration différée : la restauration demandée depuis les paramètres est appliquée au démarrage
    /// suivant, avant toute ouverture de la base, après une sauvegarde de sécurité de la base courante.
    /// Nom des fichiers : afmi_AAAAMMJJ_HHMMSS_motif.db (motifs : auto, manuel, avant_restauration).
    /// </summary>
    public static class BackupService
    {
        public const string PendingRestoreFile = "restore.pending";
        public const string FilePrefix = "afmi_";
        private static readonly string[] Frequencies = ["startup", "daily", "weekly", "manual"];

        public static string ResolveFolder(string databasePath, string? configured) =>
            string.IsNullOrWhiteSpace(configured) ? DatabasePaths.GetBackupDirectory(databasePath) : Path.GetFullPath(configured);

        /// <summary>Copie cohérente de la base dans le dossier ; retourne le chemin créé.</summary>
        public static string Create(string databasePath, string folder, string reason, DateTime? now = null)
        {
            if (!File.Exists(databasePath)) throw new FileNotFoundException("Base introuvable.", databasePath);
            Directory.CreateDirectory(folder);
            var stamp = (now ?? DateTime.Now).ToString("yyyyMMdd_HHmmss", CultureInfo.InvariantCulture);
            string target = Path.Combine(folder, $"{FilePrefix}{stamp}_{reason}.db");
            for (int k = 2; File.Exists(target); k++)
                target = Path.Combine(folder, $"{FilePrefix}{stamp}_{reason}_{k}.db");
            using (var source = new SqliteConnection($"Data Source={databasePath};Mode=ReadOnly;Pooling=False"))
            using (var destination = new SqliteConnection($"Data Source={target};Pooling=False"))
            {
                source.Open();
                destination.Open();
                source.BackupDatabase(destination);
            }
            return target;
        }

        public static IReadOnlyList<BackupInfo> List(string folder)
        {
            if (!Directory.Exists(folder)) return [];
            return new DirectoryInfo(folder).GetFiles($"{FilePrefix}*.db")
                .Select(f => new BackupInfo(f.FullName, f.Name, ParseDate(f.Name) ?? f.LastWriteTime, f.Length, ParseReason(f.Name)))
                .OrderByDescending(b => b.CreatedAt).ThenByDescending(b => b.Name, StringComparer.Ordinal)
                .ToList();
        }

        /// <summary>Supprime les sauvegardes au-delà des <paramref name="keep"/> plus récentes (motifs auto et manuel seulement).</summary>
        public static int ApplyRetention(string folder, int keep)
        {
            if (keep < 1) throw new ArgumentOutOfRangeException(nameof(keep), "Au moins une sauvegarde est conservée.");
            int n = 0;
            foreach (var old in List(folder).Where(b => b.Reason is "auto" or "manuel").Skip(keep))
            {
                File.Delete(old.Path);
                n++;
            }
            return n;
        }

        /// <summary>Une sauvegarde automatique est-elle due selon la fréquence choisie ?</summary>
        public static bool IsDue(string folder, string frequency, DateTime now, bool atStartup)
        {
            if (!Frequencies.Contains(frequency)) frequency = "daily";
            if (frequency == "manual") return false;
            if (frequency == "startup") return atStartup;
            var last = List(folder).Where(b => b.Reason is "auto" or "manuel").Select(b => (DateTime?)b.CreatedAt).FirstOrDefault();
            if (last is null) return true;
            return frequency == "weekly" ? now - last.Value >= TimeSpan.FromDays(7) : now.Date > last.Value.Date;
        }

        /// <summary>Sauvegarde planifiée : création si due, puis conservation. Retourne le fichier créé ou null.</summary>
        public static string? RunScheduled(string databasePath, string folder, string frequency, int retention, bool atStartup, DateTime? now = null)
        {
            var t = now ?? DateTime.Now;
            if (!IsDue(folder, frequency, t, atStartup)) return null;
            string created = Create(databasePath, folder, "auto", t);
            ApplyRetention(folder, Math.Max(1, retention));
            return created;
        }

        /// <summary>
        /// Applique une restauration demandée (fichier restore.pending à côté de la base). La sauvegarde à restaurer doit
        /// être une base SQLite intègre ; la base courante est d'abord sauvegardée (motif avant_restauration).
        /// Retourne le chemin restauré, ou null si aucune restauration n'était demandée.
        /// </summary>
        public static string? ApplyPendingRestore(string databasePath, string folder)
        {
            string flag = Path.Combine(Path.GetDirectoryName(databasePath)!, PendingRestoreFile);
            if (!File.Exists(flag)) return null;
            string source;
            try
            {
                using var doc = JsonDocument.Parse(File.ReadAllText(flag));
                source = Path.GetFullPath(doc.RootElement.GetProperty("path").GetString() ?? "");
            }
            finally
            {
                File.Delete(flag);       // une demande illisible ou refusée n'est jamais rejouée
            }
            string root = Path.GetFullPath(folder).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
            if (!source.StartsWith(root, StringComparison.OrdinalIgnoreCase) || !File.Exists(source))
                throw new InvalidOperationException("La sauvegarde à restaurer doit se trouver dans le dossier des sauvegardes.");
            using (var check = new SqliteConnection($"Data Source={source};Mode=ReadOnly;Pooling=False"))
            {
                check.Open();
                using var cmd = check.CreateCommand();
                cmd.CommandText = "PRAGMA integrity_check";
                if (!string.Equals(cmd.ExecuteScalar() as string, "ok", StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException("La sauvegarde choisie est endommagée : restauration annulée.");
            }
            if (File.Exists(databasePath)) Create(databasePath, folder, "avant_restauration");
            using (var src = new SqliteConnection($"Data Source={source};Mode=ReadOnly;Pooling=False"))
            using (var dst = new SqliteConnection($"Data Source={databasePath};Pooling=False"))
            {
                src.Open();
                dst.Open();
                src.BackupDatabase(dst);
            }
            return source;
        }

        /// <summary>
        /// Dossier des sauvegardes lu directement dans la base (avant l'ouverture d'EF Core et les migrations, pour la
        /// restauration différée). Dossier par défaut si la base ou le paramètre est absent.
        /// </summary>
        public static string FolderFromDatabase(string databasePath)
        {
            string? configured = null;
            try
            {
                if (File.Exists(databasePath))
                {
                    using var c = new SqliteConnection($"Data Source={databasePath};Mode=ReadOnly;Pooling=False");
                    c.Open();
                    using var cmd = c.CreateCommand();
                    cmd.CommandText = "SELECT ValueJson FROM AppSettings WHERE Key = $k";
                    cmd.Parameters.AddWithValue("$k", SettingKeys.BackupFolder);
                    if (cmd.ExecuteScalar() is string json) configured = JsonSerializer.Deserialize<string>(json);
                }
            }
            catch (SqliteException) { /* base antérieure aux paramètres : dossier par défaut */ }
            catch (JsonException) { }
            return ResolveFolder(databasePath, configured);
        }

        private static DateTime? ParseDate(string name)
        {
            // afmi_20261111_093000_auto.db
            if (name.Length < FilePrefix.Length + 15) return null;
            return DateTime.TryParseExact(name.Substring(FilePrefix.Length, 15), "yyyyMMdd_HHmmss", CultureInfo.InvariantCulture,
                DateTimeStyles.None, out var d) ? d : null;
        }

        private static string ParseReason(string name)
        {
            string core = Path.GetFileNameWithoutExtension(name);
            if (core.Length <= FilePrefix.Length + 16) return "";
            string rest = core[(FilePrefix.Length + 16)..];
            int k = rest.LastIndexOf('_');
            return k > 0 && int.TryParse(rest[(k + 1)..], out _) ? rest[..k] : rest;
        }
    }
}
