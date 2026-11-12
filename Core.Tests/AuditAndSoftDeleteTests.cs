using System.Text.Json;
using AFMI_Gestion_projet.Data;
using AFMI_Gestion_projet.Models;
using AFMI_Gestion_projet.Models.Finance;
using Microsoft.EntityFrameworkCore;

namespace AFMI_Gestion_projet.Core.Tests;

public class AuditAndSoftDeleteTests : IDisposable
{
    private readonly TestDatabase _db = new();
    public void Dispose() => _db.Dispose();

    [Fact]
    public void EveryChange_IsJournaled_WithUserAndValues()
    {
        int id;
        using (var ctx = _db.Open())
        {
            var account = new BankAccount { Title = "Caisse", Kind = AccountKind.Cash, OpeningDate = new(2026, 1, 1), OpeningBalanceMinor = 500_00 };
            ctx.BankAccounts.Add(account);
            ctx.SaveChanges();
            id = account.Id;
            account.Title = "Caisse siège";
            ctx.SaveChanges();
            ctx.BankAccounts.Remove(account);
            ctx.SaveChanges();
        }

        using var check = _db.Open();
        var entries = check.AuditEntries.Where(a => a.EntityType == nameof(BankAccount) && a.EntityId == id.ToString()).OrderBy(a => a.Id).ToList();
        Assert.Equal(new[] { AppDbContext.ActionCreate, AppDbContext.ActionUpdate, AppDbContext.ActionSoftDelete }, entries.Select(e => e.Action));
        Assert.Equal(Environment.UserName, entries[0].User);
        Assert.Contains("50000", entries[0].ChangesJson);
        var update = JsonDocument.Parse(entries[1].ChangesJson).RootElement.GetProperty("Title");
        Assert.Equal("Caisse", update.GetProperty("old").GetString());
        Assert.Equal("Caisse siège", update.GetProperty("new").GetString());
        Assert.Single(JsonDocument.Parse(entries[1].ChangesJson).RootElement.EnumerateObject());
        Assert.Null(check.FindFirstTamperedAuditEntry());
    }

    [Fact]
    public void SoftDeletedRows_AreHidden_ButKept()
    {
        using (var ctx = _db.Open())
        {
            ctx.BankAccounts.Add(new BankAccount { Title = "A", OpeningDate = new(2026, 1, 1) });
            ctx.SaveChanges();
            ctx.BankAccounts.Remove(ctx.BankAccounts.Single());
            ctx.SaveChanges();
        }
        using var check = _db.Open();
        Assert.Empty(check.BankAccounts);
        var row = check.BankAccounts.IgnoreQueryFilters().Single();
        Assert.True(row.IsDeleted);
        Assert.NotNull(row.DeletedAtUtc);
    }

    [Fact]
    public void DeletingAProject_KeepsItsTasksAndCosts()
    {
        int projectId;
        using (var ctx = _db.Open())
        {
            var p = new Project { Name = "Pastoralisme", Code = "P2" };
            p.Tasks.Add(new ProjectTask { Name = "Diagnostic" });
            p.CostEntries.Add(new CostEntry { ActualCost = 1200.5 });
            ctx.Projects.Add(p);
            ctx.SaveChanges();
            projectId = p.Id;
        }
        using (var ctx = _db.Open())
        {
            // Comme PortfolioViewModel.DeleteProject, mais avec les enfants chargés (cas le plus exposé à la cascade).
            var p = ctx.Projects.Include(x => x.Tasks).Include(x => x.CostEntries).Single(x => x.Id == projectId);
            ctx.Projects.Remove(p);
            ctx.SaveChanges();
        }
        using var check = _db.Open();
        Assert.Empty(check.Projects);
        Assert.Equal(1, Convert.ToInt32(_db.Scalar("SELECT COUNT(*) FROM Tasks")));
        Assert.Equal(1200.5, (double)_db.Scalar("SELECT ActualCost FROM CostEntries WHERE IsDeleted = 0")!);
        Assert.True(check.Projects.IgnoreQueryFilters().Single().IsDeleted);
    }

    [Fact]
    public void AuditJournal_IsAppendOnly_AndTamperingIsDetected()
    {
        using (var ctx = _db.Open())
        {
            ctx.Categories.Add(new Category { Kind = CategoryKind.Expense, Code = "LOY", Label = "Loyer" });
            ctx.SaveChanges();
            ctx.Categories.Add(new Category { Kind = CategoryKind.Expense, Code = "TEL", Label = "Téléphone" });
            ctx.SaveChanges();

            var entry = ctx.AuditEntries.First();
            ctx.AuditEntries.Remove(entry);
            Assert.Throws<InvalidOperationException>(() => ctx.SaveChanges());
        }

        // Même en SQL direct, la base refuse.
        Assert.ThrowsAny<Exception>(() => _db.Execute("DELETE FROM AuditEntries"));
        Assert.ThrowsAny<Exception>(() => _db.Execute("UPDATE AuditEntries SET User = 'pirate'"));

        // Falsification « hors application » (déclencheurs retirés) : la chaîne d'empreintes la révèle.
        _db.Execute("DROP TRIGGER TR_AuditEntries_NoUpdate; UPDATE AuditEntries SET ChangesJson = '{}' WHERE Id = 2;");
        using var check = _db.Open();
        Assert.Equal(2, check.FindFirstTamperedAuditEntry());
    }

    [Fact]
    public void Secrets_AreNeverWrittenToTheJournal()
    {
        using (var ctx = _db.Open())
        {
            ctx.AppSettings.Add(new AppSetting { Key = "ai.anthropic.key", ValueJson = "\"sk-secret\"", IsSecret = true });
            ctx.AppSettings.Add(new AppSetting { Key = "association.currency", ValueJson = "\"MAD\"" });
            ctx.SaveChanges();
        }
        string journal = string.Join("\n", _db.Open().AuditEntries.Select(a => a.ChangesJson));
        Assert.DoesNotContain("sk-secret", journal);
        Assert.Contains("MAD", journal);
    }

    [Fact]
    public void FailedSave_WritesNoAudit()
    {
        using var ctx = _db.Open();
        ctx.Operations.Add(new Operation { BankAccountId = 999, OperationDate = new(2026, 1, 1), AmountMinor = 1, Nature = OperationNature.Expense, Direction = OperationDirection.Debit });
        Assert.Throws<DbUpdateException>(() => ctx.SaveChanges());
        Assert.Equal(0L, (long)_db.Scalar("SELECT COUNT(*) FROM AuditEntries WHERE EntityType = 'Operation'")!);
    }
}
