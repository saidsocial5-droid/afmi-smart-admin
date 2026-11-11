using AFMI_Gestion_projet.Services;

namespace AFMI_Gestion_projet.Core.Tests;

public class BackupServiceTests : IDisposable
{
    private readonly TestDatabase _db = new();
    private string Folder => System.IO.Path.Combine(_db.Directory, "sauvegardes");
    public void Dispose() => _db.Dispose();

    private void Seed(string name)
    {
        using var ctx = _db.Open();
        new SettingsService(ctx).Set(SettingKeys.AssociationName, name);
    }

    [Fact]
    public void Create_IsAConsistentCopy_AndListsNewestFirst()
    {
        Seed("Avant");
        var first = BackupService.Create(_db.Path, Folder, "manuel", new DateTime(2026, 11, 1, 9, 0, 0));
        var second = BackupService.Create(_db.Path, Folder, "auto", new DateTime(2026, 11, 2, 9, 0, 0));
        var list = BackupService.List(Folder);
        Assert.Equal([second, first], list.Select(b => b.Path));
        Assert.Equal("auto", list[0].Reason);
        Assert.Equal(new DateTime(2026, 11, 2, 9, 0, 0), list[0].CreatedAt);
        using var copy = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={first};Mode=ReadOnly;Pooling=False");
        copy.Open();
        using var cmd = copy.CreateCommand();
        cmd.CommandText = "SELECT ValueJson FROM AppSettings WHERE Key = 'association.name'";
        Assert.Equal("\"Avant\"", cmd.ExecuteScalar());
    }

    [Fact]
    public void Retention_KeepsNewest_AndNeverDeletesSafetyCopies()
    {
        Seed("x");
        for (int d = 1; d <= 5; d++) BackupService.Create(_db.Path, Folder, "auto", new DateTime(2026, 11, d, 8, 0, 0));
        BackupService.Create(_db.Path, Folder, "avant_restauration", new DateTime(2026, 10, 1, 8, 0, 0));
        Assert.Equal(3, BackupService.ApplyRetention(Folder, 2));
        var left = BackupService.List(Folder);
        Assert.Equal(3, left.Count);
        Assert.Contains(left, b => b.Reason == "avant_restauration");
        Assert.Throws<ArgumentOutOfRangeException>(() => BackupService.ApplyRetention(Folder, 0));
    }

    [Theory]
    [InlineData("daily", "2026-11-10 23:00", "2026-11-11 08:00", false, true)]
    [InlineData("daily", "2026-11-11 07:00", "2026-11-11 18:00", false, false)]
    [InlineData("weekly", "2026-11-05 08:00", "2026-11-11 08:00", false, false)]
    [InlineData("weekly", "2026-11-04 08:00", "2026-11-11 08:00", false, true)]
    [InlineData("startup", "2026-11-11 07:00", "2026-11-11 08:00", true, true)]
    [InlineData("startup", "2026-11-11 07:00", "2026-11-11 08:00", false, false)]
    [InlineData("manual", "2026-01-01 07:00", "2026-11-11 08:00", true, false)]
    public void Schedule(string frequency, string last, string now, bool atStartup, bool due)
    {
        Seed("x");
        BackupService.Create(_db.Path, Folder, "auto", DateTime.Parse(last));
        Assert.Equal(due, BackupService.IsDue(Folder, frequency, DateTime.Parse(now), atStartup));
    }

    [Fact]
    public void PendingRestore_ReplacesDatabase_AfterSafetyBackup()
    {
        Seed("Version A");
        var backup = BackupService.Create(_db.Path, Folder, "manuel");
        Seed("Version B");
        File.WriteAllText(System.IO.Path.Combine(_db.Directory, BackupService.PendingRestoreFile),
            System.Text.Json.JsonSerializer.Serialize(new { path = backup }));
        Assert.Equal(backup, BackupService.ApplyPendingRestore(_db.Path, Folder));
        Assert.Equal("\"Version A\"", _db.Scalar("SELECT ValueJson FROM AppSettings WHERE Key = 'association.name'"));
        Assert.Contains(BackupService.List(Folder), b => b.Reason == "avant_restauration");
        Assert.False(File.Exists(System.IO.Path.Combine(_db.Directory, BackupService.PendingRestoreFile)));
        Assert.Null(BackupService.ApplyPendingRestore(_db.Path, Folder));     // demande consommée
    }

    [Fact]
    public void PendingRestore_RefusesFilesOutsideTheBackupFolder()
    {
        Seed("Intacte");
        string outside = System.IO.Path.Combine(_db.Directory, "autre.db");
        File.Copy(_db.Path, outside);
        File.WriteAllText(System.IO.Path.Combine(_db.Directory, BackupService.PendingRestoreFile),
            System.Text.Json.JsonSerializer.Serialize(new { path = outside }));
        Assert.Throws<InvalidOperationException>(() => BackupService.ApplyPendingRestore(_db.Path, Folder));
        Assert.Equal("\"Intacte\"", _db.Scalar("SELECT ValueJson FROM AppSettings WHERE Key = 'association.name'"));
        Assert.False(File.Exists(System.IO.Path.Combine(_db.Directory, BackupService.PendingRestoreFile)));
    }
}
