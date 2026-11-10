using AFMI_Gestion_projet.Data;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;

namespace AFMI_Gestion_projet.Core.Tests;

/// <summary>Base SQLite jetable dans un dossier temporaire (jamais la base réelle de l'utilisateur).</summary>
public sealed class TestDatabase : IDisposable
{
    public string Directory { get; } = System.IO.Path.Combine(System.IO.Path.GetTempPath(), "afmi-tests", Guid.NewGuid().ToString("N"));
    public string Path => System.IO.Path.Combine(Directory, "database.db");
    public string ConnectionString => $"Data Source={Path};Pooling=False";

    public TestDatabase() => System.IO.Directory.CreateDirectory(Directory);

    public DbContextOptions<AppDbContext> Options =>
        new DbContextOptionsBuilder<AppDbContext>().UseSqlite(ConnectionString).Options;

    /// <summary>Contexte migré automatiquement (comportement de l'application).</summary>
    public AppDbContext Open() => new(Options);

    public AppDbContext OpenWithoutMigration() => AppDbContext.WithoutMigration(Options);

    public SqliteConnection Connect()
    {
        var c = new SqliteConnection(ConnectionString);
        c.Open();
        return c;
    }

    public object? Scalar(string sql)
    {
        using var c = Connect();
        using var cmd = c.CreateCommand();
        cmd.CommandText = sql;
        return cmd.ExecuteScalar();
    }

    public void Execute(string sql)
    {
        using var c = Connect();
        using var cmd = c.CreateCommand();
        cmd.CommandText = sql;
        cmd.ExecuteNonQuery();
    }

    public void Dispose()
    {
        SqliteConnection.ClearAllPools();
        try { System.IO.Directory.Delete(Directory, recursive: true); } catch (IOException) { }
    }
}
