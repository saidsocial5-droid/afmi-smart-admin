using System.Runtime.CompilerServices;

namespace AFMI_Gestion_projet.Tests;

/// <summary>
/// Les tests ouvrent <c>new AppDbContext()</c> : sans cette redirection ils écriraient dans la base réelle de
/// l'utilisateur (%LocalAppData%\AFMIGestionProjet\database.db). Chaque exécution utilise une base jetable.
/// </summary>
internal static class TestDatabaseSetup
{
    [ModuleInitializer]
    internal static void UseThrowawayDatabase()
    {
        string dir = Path.Combine(Path.GetTempPath(), "afmi-desktop-tests", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(dir);
        Environment.SetEnvironmentVariable("AFMI_DESKTOP_DB", Path.Combine(dir, "database.db"));
    }
}
