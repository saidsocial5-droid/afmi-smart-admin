using AFMI_Gestion_projet.Finance;
using AFMI_Gestion_projet.Models.Finance;

namespace AFMI_Gestion_projet.Core.Tests;

public class AccountServiceTests : IDisposable
{
    private readonly TestDatabase _db = new();
    public void Dispose() => _db.Dispose();

    private static string ValidRib(string first22 = "0073300001234567890123") => first22 + Rib.ComputeKey(first22).ToString("00");

    [Fact]
    public void Save_ValidatesRib_AndWarnsOnWrongKey()
    {
        using var ctx = _db.Open();
        var svc = new AccountService(ctx);
        Assert.Throws<FinanceRuleException>(() => svc.Save(new BankAccount { Title = "A", Rib = "12345", OpeningDate = new(2026, 1, 1) }));
        Assert.Throws<FinanceRuleException>(() => svc.Save(new BankAccount { Title = " ", OpeningDate = new(2026, 1, 1) }));

        string good = ValidRib();
        var ok = new BankAccount { Title = "BP", Rib = $"{good[..3]} {good[3..6]} {good[6..22]} {good[22..]}", OpeningDate = new(2026, 1, 1), Currency = "dh" };
        Assert.Empty(svc.Save(ok));
        Assert.Equal(good, ok.Rib);
        Assert.Equal("MAD", ok.Currency);

        string wrongKey = good[..22] + (good[22..] == "01" ? "02" : "01");
        var warn = svc.Save(new BankAccount { Title = "CIH", Rib = wrongKey, OpeningDate = new(2026, 1, 1) });
        Assert.Single(warn);

        var cash = new BankAccount { Title = "Caisse", Kind = AccountKind.Cash, Rib = good, OpeningDate = new(2026, 1, 1) };
        svc.Save(cash);
        Assert.Null(cash.Rib);
    }

    [Fact]
    public void Close_RequiresZeroBalance()
    {
        using var ctx = _db.Open();
        var f = Lot2Fixture.Seed(ctx);
        var svc = new AccountService(ctx);
        Assert.Throws<FinanceRuleException>(() => svc.Close(f.Operating, new(2026, 6, 30)));
        svc.Close(f.ProjectAccount, new(2026, 6, 30));
        Assert.Equal(AccountStatus.Closed, ctx.BankAccounts.Single(a => a.Id == f.ProjectAccount).Status);
    }

    [Fact]
    public void Links_RejectOverlapsAndOver100Percent()
    {
        using var ctx = _db.Open();
        var f = Lot2Fixture.Seed(ctx);
        var other = new AFMI_Gestion_projet.Models.Project { Name = "P2", Code = "P2" };
        ctx.Projects.Add(other);
        ctx.SaveChanges();
        var svc = new AccountService(ctx);

        svc.SaveLink(new AccountProjectLink { BankAccountId = f.Operating, ProjectId = f.ProjectId, ValidFrom = new(2026, 1, 1), ValidTo = new(2026, 6, 30),
            AllocationMode = AllocationMode.Percentage, AllocationPercent = 60 });
        Assert.Throws<FinanceRuleException>(() => svc.SaveLink(new AccountProjectLink { BankAccountId = f.Operating, ProjectId = f.ProjectId, ValidFrom = new(2026, 6, 1) }));
        Assert.Throws<FinanceRuleException>(() => svc.SaveLink(new AccountProjectLink { BankAccountId = f.Operating, ProjectId = other.Id, ValidFrom = new(2026, 3, 1),
            AllocationMode = AllocationMode.Percentage, AllocationPercent = 50 }));
        Assert.Throws<FinanceRuleException>(() => svc.SaveLink(new AccountProjectLink { BankAccountId = f.Operating, ProjectId = other.Id, ValidFrom = new(2026, 3, 1), ValidTo = new(2026, 2, 1) }));

        // Même projet après la fin de la première liaison : accepté.
        svc.SaveLink(new AccountProjectLink { BankAccountId = f.Operating, ProjectId = f.ProjectId, ValidFrom = new(2026, 7, 1) });
        svc.SaveLink(new AccountProjectLink { BankAccountId = f.Operating, ProjectId = other.Id, ValidFrom = new(2026, 1, 1), ValidTo = new(2026, 6, 30),
            AllocationMode = AllocationMode.Percentage, AllocationPercent = 40 });

        var split = svc.SuggestAllocations(f.Operating, new(2026, 3, 15), 1_000_01);
        Assert.Equal(2, split.Count);
        Assert.Equal(1_000_01, split.Sum(a => a.AmountMinor));
        Assert.Equal(600_01, split.Single(a => a.ProjectId == f.ProjectId).AmountMinor);

        var single = svc.SuggestAllocations(f.Operating, new(2026, 8, 1), 500);
        Assert.Equal(f.ProjectId, Assert.Single(single).ProjectId);
    }

    [Fact]
    public void Suggestion_FallsBackToOperatingForUnlinkedOperatingAccount()
    {
        using var ctx = _db.Open();
        var f = Lot2Fixture.Seed(ctx);
        var svc = new AccountService(ctx);
        var a = Assert.Single(svc.SuggestAllocations(f.Operating, new(2026, 2, 1), 700));
        Assert.Null(a.ProjectId);
        Assert.Empty(svc.SuggestAllocations(f.ProjectAccount, new(2026, 2, 1), 700));
    }
}
