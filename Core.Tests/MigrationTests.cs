using AFMI_Gestion_projet.Data;
using AFMI_Gestion_projet.Services;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;

namespace AFMI_Gestion_projet.Core.Tests;

public class MigrationTests
{
    /// <summary>Reproduit une base 1.3.0 : schéma de référence, montants chiffrés, pas d'historique de migrations.</summary>
    private static void CreateLegacyDatabase(TestDatabase db, string budgetCipher, string costCipher)
    {
        using (var ctx = db.OpenWithoutMigration())
        {
            ctx.GetService<IMigrator>().Migrate(DatabaseMigrator.BaselineMigrationId);
        }
        db.Execute("DROP TABLE __EFMigrationsHistory;");
        db.Execute($@"
            INSERT INTO Projects (Id, Name, Code, Description, Manager, Owner, Client, Department, Status, Priority,
                                  BudgetGlobal, LessonsLearned, LocalFolderPath)
            VALUES (1, 'Reboisement', 'P1', '', '', '', '', '', 'Exécution', 'Haute', '{budgetCipher}', '', '');
            INSERT INTO CostEntries (Id, ProjectId, Category, ResourceName, Supplier, Description, EstimatedCost, ActualCost, Date)
            VALUES (1, 1, 'Matériel', '', '', '', '{costCipher}', '{EncryptionService.Encrypt("80.5")}', '2026-03-01');");
    }

    [Fact]
    public void NewDatabase_IsCreatedByMigrations()
    {
        using var db = new TestDatabase();
        using (var ctx = db.Open())
        {
            Assert.Empty(ctx.Database.GetPendingMigrations());
            Assert.Empty(ctx.Projects.ToList());
        }
        Assert.False(System.IO.Directory.Exists(DatabasePaths.GetBackupDirectory(db.Path)), "Pas de sauvegarde pour une base neuve.");
    }

    [Fact]
    public void LegacyDatabase_IsBackedUpThenMigrated_AndAmountsDecrypted()
    {
        using var db = new TestDatabase();
        CreateLegacyDatabase(db, EncryptionService.Encrypt("150000.75"), EncryptionService.Encrypt("100"));

        using (var ctx = db.Open())
        {
            Assert.Empty(ctx.Database.GetPendingMigrations());
            var project = ctx.Projects.Include(p => p.CostEntries).Single();
            Assert.Equal(150000.75, project.BudgetGlobal);
            Assert.Equal(100, project.CostEntries.Single().EstimatedCost);
            Assert.Equal(80.5, project.CostEntries.Single().ActualCost);
        }

        Assert.Equal("real", db.Scalar("SELECT typeof(BudgetGlobal) FROM Projects"));
        Assert.Equal(150000.75, (double)db.Scalar("SELECT SUM(BudgetGlobal) FROM Projects")!);

        var backups = System.IO.Directory.GetFiles(DatabasePaths.GetBackupDirectory(db.Path));
        var backup = Assert.Single(backups);
        // La sauvegarde est la base d'origine, intacte (montant toujours chiffré).
        using var original = new TestDatabase();
        File.Copy(backup, original.Path);
        Assert.Equal(EncryptionService.Encrypt("150000.75"), original.Scalar("SELECT BudgetGlobal FROM Projects"));
    }

    [Fact]
    public void LegacyDatabase_WithPlainAmounts_IsMigrated()
    {
        // Ancien chiffrement en échec : la 1.3.0 enregistrait alors la valeur en clair.
        using var db = new TestDatabase();
        CreateLegacyDatabase(db, "2500", "12.5");
        using var ctx = db.Open();
        Assert.Equal(2500, ctx.Projects.Single().BudgetGlobal);
        Assert.Equal(12.5, ctx.CostEntries.Single().EstimatedCost);
    }

    [Fact]
    public void UnreadableAmount_StopsMigrationBeforeDecryption_AndKeepsTheValue()
    {
        using var db = new TestDatabase();
        CreateLegacyDatabase(db, "pas-un-montant", EncryptionService.Encrypt("1"));

        Assert.ThrowsAny<Exception>(() => db.Open());

        // La migration de données est annulée en bloc : aucune valeur n'a été déchiffrée ni perdue.
        Assert.EndsWith("_LegacyAmountsInClear",
            (string)db.Scalar("SELECT MigrationId FROM __EFMigrationsHistory ORDER BY MigrationId DESC LIMIT 1")!);
        Assert.Equal("pas-un-montant", db.Scalar("SELECT BudgetGlobal FROM Projects"));
        Assert.Equal(EncryptionService.Encrypt("1"), db.Scalar("SELECT EstimatedCost FROM CostEntries"));
        Assert.Single(System.IO.Directory.GetFiles(DatabasePaths.GetBackupDirectory(db.Path)));
    }

    [Fact]
    public void AllMigrations_GoDownToBaseline_AndUpAgain_KeepingAmounts()
    {
        using var db = new TestDatabase();
        CreateLegacyDatabase(db, EncryptionService.Encrypt("42.25"), EncryptionService.Encrypt("7"));
        using (var ctx = db.Open()) { Assert.Equal(42.25, ctx.Projects.Single().BudgetGlobal); }

        using (var ctx = db.OpenWithoutMigration())
        {
            ctx.GetService<IMigrator>().Migrate(DatabaseMigrator.BaselineMigrationId);
        }
        // Après retour en 1.3.0, la valeur (texte en clair) reste lisible par l'ancien déchiffrement.
        string stored = (string)db.Scalar("SELECT BudgetGlobal FROM Projects")!;
        Assert.Equal("42.25", EncryptionService.Decrypt(stored));

        using (var ctx = db.OpenWithoutMigration())
        {
            DatabaseMigrator.Migrate(ctx);
            Assert.Empty(ctx.Database.GetPendingMigrations());
            Assert.Equal(42.25, ctx.Projects.Single().BudgetGlobal);
        }
    }

    [Fact]
    public void LegacyDocuments_AreReclassified_ByTheMigrationChain()
    {
        using var db = new TestDatabase();
        CreateLegacyDatabase(db, EncryptionService.Encrypt("1"), EncryptionService.Encrypt("1"));
        db.Execute($@"INSERT INTO Documents (ProjectId, Title, Category, DocumentPhase, Tags, IsKeyReference, DocumentVersion, DonorName,
            DocumentReference, ApprovedGrantAmount, FilePath, OriginalFileName, FileExtension, FileSize, Notes, ExtractedSummary,
            FullExtractedText, KeyInsights, UploadedDate)
            VALUES (1, 'Convention FV', 'Convention Bailleur', 'Exécution', '', 1, '', '', '', '{EncryptionService.Encrypt("500000")}',
                    '', '', '', 0, '', '', '', '', '2025-05-01');");
        using var ctx = db.Open();
        var doc = ctx.Documents.Single();
        Assert.Equal("Convention", doc.DocType);
        Assert.Equal("Mise en œuvre", doc.LifecyclePhase);
        Assert.Equal(500000, doc.ApprovedGrantAmount);
        Assert.False(doc.IsDeleted);
    }

    [Theory]
    [InlineData(null, 0)]
    [InlineData("", 0)]
    [InlineData("12.5", 12.5)]
    [InlineData(3.5, 3.5)]
    [InlineData(4L, 4)]
    public void LegacyAmount_AcceptsPlainValues(object? value, double expected) =>
        Assert.Equal(expected, DatabaseMigrator.LegacyAmount(value));
}

public class DocumentManagementMigrationTests
{
    [Fact]
    public void LegacyDocuments_AreMapped_AndFullTextIndexIsSynchronised()
    {
        using var db = new TestDatabase();
        using (var ctx = db.Open())
        {
            var p = new AFMI_Gestion_projet.Models.Project { Name = "P", Code = "P" };
            ctx.Projects.Add(p);
            ctx.SaveChanges();
            var doc = new AFMI_Gestion_projet.Models.ProjectDocument { ProjectId = p.Id, Title = "Convention", Category = "Convention Bailleur", DocumentPhase = "Montage" };
            ctx.Documents.Add(doc);
            ctx.SaveChanges();
            ctx.DocumentChunks.Add(new AFMI_Gestion_projet.Models.DocumentChunk { DocumentId = doc.Id, Ordinal = 0, Text = "Le rapport financier intermédiaire est dû le 30 juin." });
            ctx.SaveChanges();
        }
        // Recherche plein texte insensible aux accents (remove_diacritics).
        Assert.Equal(1L, (long)db.Scalar("SELECT COUNT(*) FROM DocumentChunksFts WHERE DocumentChunksFts MATCH 'intermediaire'")!);
        db.Execute("UPDATE DocumentChunks SET Text = 'Autre texte'");
        Assert.Equal(0L, (long)db.Scalar("SELECT COUNT(*) FROM DocumentChunksFts WHERE DocumentChunksFts MATCH 'intermediaire'")!);
        Assert.Equal(1L, (long)db.Scalar("SELECT COUNT(*) FROM DocumentChunksFts WHERE DocumentChunksFts MATCH 'autre'")!);
    }

    [Fact]
    public void DeletingADocument_IsLogical()
    {
        using var db = new TestDatabase();
        using var ctx = db.Open();
        var p = new AFMI_Gestion_projet.Models.Project { Name = "P", Code = "P" };
        ctx.Projects.Add(p);
        ctx.SaveChanges();
        var doc = new AFMI_Gestion_projet.Models.ProjectDocument { ProjectId = p.Id, Title = "PV" };
        ctx.Documents.Add(doc);
        ctx.SaveChanges();
        ctx.Documents.Remove(doc);
        ctx.SaveChanges();
        Assert.Empty(ctx.Documents);
        Assert.Equal(1L, (long)db.Scalar("SELECT COUNT(*) FROM Documents WHERE IsDeleted = 1")!);
    }
}
