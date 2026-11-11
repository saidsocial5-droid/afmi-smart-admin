using System.Text.Json;
using Microsoft.Data.Sqlite;

namespace AFMI_Gestion_projet.Services
{
    /// <summary>
    /// Base de démonstration (Lot 8) : association fictive livrée avec l'application (dossier « demo » : database.db,
    /// data\, demo.json), construite par SmartOffice/demo/build_demo.py. Elle est copiée dans un dossier séparé du poste
    /// et ouverte dans une seconde fenêtre (variables AFMI_DESKTOP_DB, AFMI_DATA_DIR, AFMI_DEMO) : la base réelle n'est
    /// jamais lue ni modifiée.
    /// </summary>
    public static class DemoService
    {
        public const string ModeVariable = "AFMI_DEMO";
        public const string PackageVariable = "AFMI_DEMO_PACKAGE";

        public static bool IsDemoMode => Environment.GetEnvironmentVariable(ModeVariable) == "1";

        /// <summary>Dossier de démonstration livré (installation) ou désigné par AFMI_DEMO_PACKAGE.</summary>
        public static string? FindPackage(string applicationDirectory)
        {
            foreach (var dir in new[] { Environment.GetEnvironmentVariable(PackageVariable), Path.Combine(applicationDirectory, "demo") })
            {
                if (!string.IsNullOrWhiteSpace(dir) && File.Exists(Path.Combine(dir, "database.db")) && File.Exists(Path.Combine(dir, "demo.json")))
                    return dir;
            }
            return null;
        }

        public static string DefaultTarget() =>
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "AFMIGestionProjet", "demonstration");

        /// <summary>
        /// Copie le paquet dans <paramref name="target"/> (remplacé si <paramref name="reset"/>, sinon conservé s'il existe)
        /// et corrige les chemins absolus enregistrés à la construction (documents de la GED, logos des bailleurs).
        /// Retourne (base, dossier de données).
        /// </summary>
        public static (string Database, string DataDirectory) Install(string package, string target, bool reset)
        {
            string fullTarget = Path.GetFullPath(target);
            string realDb = Path.GetFullPath(AFMI_Gestion_projet.Data.DatabasePaths.GetDatabasePath());
            if (string.Equals(Path.Combine(fullTarget, "database.db"), realDb, StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("Le dossier de démonstration ne peut pas être celui de la base réelle.");
            string db = Path.Combine(fullTarget, "database.db"), data = Path.Combine(fullTarget, "data");
            if (reset && Directory.Exists(fullTarget)) Directory.Delete(fullTarget, recursive: true);
            if (File.Exists(db)) return (db, data);

            CopyDirectory(package, fullTarget);
            using var manifest = JsonDocument.Parse(File.ReadAllText(Path.Combine(package, "demo.json")));
            string built = manifest.RootElement.GetProperty("build_data_dir").GetString() ?? "";
            if (built.Length > 0 && !string.Equals(built, data, StringComparison.Ordinal))
            {
                using var conn = new SqliteConnection($"Data Source={db};Pooling=False");
                conn.Open();
                using var tx = conn.BeginTransaction();
                foreach (var (table, column) in new[] { ("Documents", "FilePath"), ("Funders", "LogoPath") })
                {
                    using var cmd = conn.CreateCommand();
                    cmd.Transaction = tx;
                    // Préfixe remplacé uniquement en tête de chemin ; séparateurs normalisés pour le poste courant
                    cmd.CommandText = $"UPDATE \"{table}\" SET \"{column}\" = $new || substr(\"{column}\", length($old) + 1) " +
                                      $"WHERE substr(\"{column}\", 1, length($old)) = $old";
                    cmd.Parameters.AddWithValue("$old", built);
                    cmd.Parameters.AddWithValue("$new", data);
                    cmd.ExecuteNonQuery();
                    using var sep = conn.CreateCommand();
                    sep.Transaction = tx;
                    sep.CommandText = $"UPDATE \"{table}\" SET \"{column}\" = replace(\"{column}\", $from, $to) WHERE substr(\"{column}\", 1, length($new)) = $new";
                    sep.Parameters.AddWithValue("$from", Path.DirectorySeparatorChar == '\\' ? "/" : "\\");
                    sep.Parameters.AddWithValue("$to", Path.DirectorySeparatorChar.ToString());
                    sep.Parameters.AddWithValue("$new", data);
                    sep.ExecuteNonQuery();
                }
                tx.Commit();
            }
            return (db, data);
        }

        private static void CopyDirectory(string source, string target)
        {
            Directory.CreateDirectory(target);
            foreach (var dir in Directory.GetDirectories(source, "*", SearchOption.AllDirectories))
                Directory.CreateDirectory(Path.Combine(target, Path.GetRelativePath(source, dir)));
            foreach (var file in Directory.GetFiles(source, "*", SearchOption.AllDirectories))
                File.Copy(file, Path.Combine(target, Path.GetRelativePath(source, file)), overwrite: true);
        }
    }
}
