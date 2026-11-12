namespace AFMI_Gestion_projet.Data
{
    /// <summary>Emplacement de la base du poste. <c>AFMI_DESKTOP_DB</c> permet de la remplacer (tests, démonstration).</summary>
    public static class DatabasePaths
    {
        public const string OverrideVariable = "AFMI_DESKTOP_DB";

        public static string GetDatabasePath()
        {
            string? overridePath = Environment.GetEnvironmentVariable(OverrideVariable);
            string path = string.IsNullOrWhiteSpace(overridePath)
                ? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "AFMIGestionProjet", "database.db")
                : Path.GetFullPath(overridePath);
            Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            return path;
        }

        /// <summary>Dossier des sauvegardes automatiques, à côté de la base.</summary>
        public static string GetBackupDirectory(string databasePath) =>
            Path.Combine(Path.GetDirectoryName(databasePath)!, "backups");
    }
}
