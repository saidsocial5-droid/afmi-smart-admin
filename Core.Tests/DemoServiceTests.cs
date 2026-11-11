using AFMI_Gestion_projet.Services;

namespace AFMI_Gestion_projet.Core.Tests;

public class DemoServiceTests : IDisposable
{
    private readonly TestDatabase _package = new();
    private readonly string _target = System.IO.Path.Combine(System.IO.Path.GetTempPath(), "afmi-tests", Guid.NewGuid().ToString("N"), "demo");
    public void Dispose()
    {
        _package.Dispose();
        if (Directory.Exists(_target)) Directory.Delete(_target, true);
    }

    private void BuildPackage(string builtDataDir)
    {
        using (_package.Open()) { }   // base migrée
        _package.Execute("INSERT INTO Projects (Id, Name, Code, Description, Manager, Owner, Client, Department, Status, Priority, BudgetGlobal, " +
                         "LessonsLearned, LocalFolderPath, Currency, IsDeleted) VALUES (1, 'P', 'P', '', '', '', '', '', 'Exécution', 'Haute', 0, '', '', 'MAD', 0)");
        _package.Execute($"INSERT INTO Documents (ProjectId, Title, Category, DocumentPhase, Tags, IsKeyReference, DocumentVersion, DonorName, DocumentReference, " +
                         $"ApprovedGrantAmount, FilePath, OriginalFileName, FileExtension, FileSize, Notes, ExtractedSummary, FullExtractedText, KeyInsights, UploadedDate, " +
                         $"ClassificationConfidence, DocType, LifecyclePhase, MetadataJson, Language, IsDeleted) " +
                         $"VALUES (1, 'Convention', '', '', '', 0, '', '', '', '0', '{builtDataDir}/archives/ged/conv.pdf', 'conv.pdf', '.pdf', 1, '', '', '', '', '2026-01-01', 0, '', '', '{{}}', '', 0)");
        _package.Execute($"INSERT INTO Funders (Name, PrimaryColor, LogoPath, LegalMentions, HeaderText, FooterText) VALUES ('F', '#000000', '/autre/logo.png', '', '', '')");
        File.WriteAllText(System.IO.Path.Combine(_package.Directory, "demo.json"), $"{{\"build_data_dir\": \"{builtDataDir}\"}}");
        Directory.CreateDirectory(System.IO.Path.Combine(_package.Directory, "data", "archives", "ged"));
        File.WriteAllText(System.IO.Path.Combine(_package.Directory, "data", "archives", "ged", "conv.pdf"), "pdf");
    }

    [Fact]
    public void Install_CopiesPackage_AndRewritesBuildPaths()
    {
        BuildPackage("/build/demo/data");
        Environment.SetEnvironmentVariable(DemoService.PackageVariable, _package.Directory);
        try { Assert.Equal(_package.Directory, DemoService.FindPackage("/inexistant")); }
        finally { Environment.SetEnvironmentVariable(DemoService.PackageVariable, null); }
        var (db, data) = DemoService.Install(_package.Directory, _target, reset: false);
        Assert.True(File.Exists(System.IO.Path.Combine(data, "archives", "ged", "conv.pdf")));
        using var c = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={db};Pooling=False");
        c.Open();
        using var cmd = c.CreateCommand();
        cmd.CommandText = "SELECT FilePath FROM Documents";
        string path = (string)cmd.ExecuteScalar()!;
        Assert.StartsWith(data, path);
        Assert.True(File.Exists(path));
        cmd.CommandText = "SELECT LogoPath FROM Funders";
        Assert.Equal("/autre/logo.png", cmd.ExecuteScalar());          // chemin hors du paquet : inchangé
    }

    [Fact]
    public void Install_KeepsExistingDemo_UnlessReset()
    {
        BuildPackage("/build/demo/data");
        var (db, _) = DemoService.Install(_package.Directory, _target, reset: false);
        File.WriteAllText(System.IO.Path.Combine(_target, "marque.txt"), "modifiée");
        DemoService.Install(_package.Directory, _target, reset: false);
        Assert.True(File.Exists(System.IO.Path.Combine(_target, "marque.txt")));
        DemoService.Install(_package.Directory, _target, reset: true);
        Assert.False(File.Exists(System.IO.Path.Combine(_target, "marque.txt")));
        Assert.True(File.Exists(db));
    }

    [Fact]
    public void FindPackage_RequiresDatabaseAndManifest()
    {
        Assert.Null(DemoService.FindPackage(_package.Directory));
    }
}
