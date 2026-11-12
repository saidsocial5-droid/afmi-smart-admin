using AFMI_Gestion_projet.Data;
using AFMI_Gestion_projet.Finance;
using AFMI_Gestion_projet.Models;
using AFMI_Gestion_projet.Models.Finance;
using Microsoft.EntityFrameworkCore;

namespace AFMI_Gestion_projet.Core.Tests;

public class FinanceServiceTests : IDisposable
{
    private readonly TestDatabase _db = new();
    public void Dispose() => _db.Dispose();

    private (int main, int project, int eur, int projectId, int lineProject, int lineOperating) Seed()
    {
        using var ctx = _db.Open();
        var project = new Project { Name = "Reboisement Ifrane", Code = "P1" };
        ctx.Projects.Add(project);
        ctx.SaveChanges();
        var main = new BankAccount { Title = "Fonctionnement", Currency = "MAD", OpeningBalanceMinor = 10_000_00, OpeningDate = new(2026, 1, 1) };
        var proj = new BankAccount { Title = "Compte projet", Purpose = AccountPurpose.Project, Currency = "MAD", OpeningBalanceMinor = 0, OpeningDate = new(2026, 1, 1) };
        var eur = new BankAccount { Title = "Compte EUR", Currency = "EUR", OpeningBalanceMinor = 1_000_00, OpeningDate = new(2026, 1, 1) };
        ctx.BankAccounts.AddRange(main, proj, eur);
        var lineP = new BudgetLine { ProjectId = project.Id, Code = "1.1", Label = "Plants", PlannedMinor = 50_000_00 };
        var lineF = new BudgetLine { ProjectId = null, Code = "F1", Label = "Loyer", PlannedMinor = 24_000_00 };
        ctx.BudgetLines.AddRange(lineP, lineF);
        ctx.CurrencyRates.Add(new CurrencyRate { Currency = "EUR", Date = new(2026, 1, 1), RateToMad = 10.90m, Source = "test" });
        ctx.SaveChanges();
        return (main.Id, proj.Id, eur.Id, project.Id, lineP.Id, lineF.Id);
    }

    private static Operation Op(int account, DateOnly date, OperationNature nature, long amount, string currency = "MAD", params OperationAllocation[] allocations)
    {
        var op = new Operation
        {
            BankAccountId = account, OperationDate = date, Nature = nature, AmountMinor = amount, Currency = currency, Label = nature.ToString(),
            Direction = nature == OperationNature.Income ? OperationDirection.Credit : OperationDirection.Debit,
        };
        foreach (var a in allocations) op.Allocations.Add(a);
        return op;
    }

    [Fact]
    public void Balance_IsOpeningPlusCreditsMinusDebits_AtAnyDate()
    {
        var s = Seed();
        using var ctx = _db.Open();
        var svc = new FinanceService(ctx);

        var income = svc.AddDraft(Op(s.main, new(2026, 2, 10), OperationNature.Income, 5_000_00, "MAD",
            new OperationAllocation { ProjectId = null, BudgetLineId = s.lineOperating, AmountMinor = 5_000_00, CategoryId = 3 }));
        var expense = svc.AddDraft(Op(s.main, new(2026, 3, 5), OperationNature.Expense, 1_234_56, "MAD",
            new OperationAllocation { ProjectId = s.projectId, BudgetLineId = s.lineProject, AmountMinor = 1_000_00 },
            new OperationAllocation { ProjectId = null, BudgetLineId = s.lineOperating, AmountMinor = 234_56 }));

        // Les brouillons ne comptent pas.
        Assert.Equal(10_000_00, svc.GetBalanceMinor(s.main, new(2026, 12, 31)));
        svc.Validate(income.Id, "test");
        svc.Validate(expense.Id, "test");

        Assert.Equal(0, svc.GetBalanceMinor(s.main, new(2025, 12, 31)));          // avant l'ouverture
        Assert.Equal(10_000_00, svc.GetBalanceMinor(s.main, new(2026, 1, 1)));    // jour d'ouverture
        Assert.Equal(10_000_00, svc.GetBalanceMinor(s.main, new(2026, 2, 9)));
        Assert.Equal(15_000_00, svc.GetBalanceMinor(s.main, new(2026, 2, 10)));   // opération du jour incluse
        Assert.Equal(13_765_44, svc.GetBalanceMinor(s.main, new(2026, 3, 5)));
        Assert.Equal(13_765_44, svc.GetBalanceMinor(s.main, new(2027, 1, 1)));

        // Une opération supprimée (logiquement) ne compte plus.
        ctx.Operations.Remove(ctx.Operations.Single(o => o.Id == expense.Id));
        ctx.SaveChanges();
        Assert.Equal(15_000_00, svc.GetBalanceMinor(s.main, new(2027, 1, 1)));
    }

    [Fact]
    public void InternalTransfer_MovesBalances_ButIsNeitherIncomeNorExpense()
    {
        var s = Seed();
        using var ctx = _db.Open();
        var svc = new FinanceService(ctx);
        var income = svc.AddDraft(Op(s.project, new(2026, 4, 1), OperationNature.Income, 20_000_00, "MAD",
            new OperationAllocation { ProjectId = s.projectId, BudgetLineId = s.lineProject, AmountMinor = 20_000_00, CategoryId = 1 }));
        svc.Validate(income.Id, "test");

        var group = svc.CreateInternalTransfer(s.main, s.project, new(2026, 4, 2), 3_000_00, "Avance de trésorerie", "test");

        Assert.Equal(7_000_00, svc.GetBalanceMinor(s.main, new(2026, 4, 30)));
        Assert.Equal(23_000_00, svc.GetBalanceMinor(s.project, new(2026, 4, 30)));
        Assert.Equal(new IncomeExpenseTotals(20_000_00, 0), svc.GetIncomeAndExpenses(new(2026, 1, 1), new(2026, 12, 31)));
        Assert.Equal(2, ctx.Operations.Count(o => o.TransferGroupId == group));
        Assert.Empty(svc.FindUnpairedTransfers());

        // Consolidé : le virement est neutre.
        long consolidated = svc.GetConsolidatedBalanceMadMinor(new(2026, 4, 30));
        Assert.Equal(7_000_00 + 23_000_00 + 10_900_00, consolidated);

        // Jambe supprimée → anomalie détectée.
        ctx.Operations.Remove(ctx.Operations.First(o => o.TransferGroupId == group));
        ctx.SaveChanges();
        Assert.Equal(new[] { group }, svc.FindUnpairedTransfers());
    }

    [Fact]
    public void InternalTransfer_BetweenCurrencies_RequiresReceivedAmount()
    {
        var s = Seed();
        using var ctx = _db.Open();
        var svc = new FinanceService(ctx);
        Assert.Throws<ArgumentException>(() => svc.CreateInternalTransfer(s.eur, s.main, new(2026, 5, 1), 100_00, "Change", "test"));
        Assert.Throws<ArgumentException>(() => svc.CreateInternalTransfer(s.main, s.main, new(2026, 5, 1), 100_00, "x", "test"));

        svc.CreateInternalTransfer(s.eur, s.main, new(2026, 5, 1), 100_00, "Change", "test", receivedAmountMinor: 1_088_00);
        Assert.Equal(900_00, svc.GetBalanceMinor(s.eur, new(2026, 5, 1)));
        Assert.Equal(11_088_00, svc.GetBalanceMinor(s.main, new(2026, 5, 1)));
        var eurLeg = ctx.Operations.Single(o => o.BankAccountId == s.eur);
        Assert.Equal(10.90m, eurLeg.RateToMad);
        Assert.Equal(1_090_00, eurLeg.AmountMadMinor);
    }

    [Fact]
    public void ForeignCurrencyOperation_StoresRateAndMadValue_AndNeedsAKnownRate()
    {
        var s = Seed();
        using var ctx = _db.Open();
        var svc = new FinanceService(ctx);
        var op = svc.AddDraft(Op(s.eur, new(2026, 6, 1), OperationNature.Income, 250_00, "EUR"));
        Assert.Equal(10.90m, op.RateToMad);
        Assert.Equal(2_725_00, op.AmountMadMinor);

        ctx.CurrencyRates.RemoveRange(ctx.CurrencyRates);
        ctx.SaveChanges();
        Assert.Throws<MissingExchangeRateException>(() => svc.AddDraft(Op(s.eur, new(2026, 6, 2), OperationNature.Income, 1_00, "EUR")));
    }

    [Fact]
    public void Validation_IsRefusedForIncompleteOperation_AndDatabaseRejectsInvalidRows()
    {
        var s = Seed();
        using var ctx = _db.Open();
        var svc = new FinanceService(ctx);
        var op = svc.AddDraft(Op(s.main, new(2026, 2, 1), OperationNature.Expense, 100_00));
        var ex = Assert.Throws<OperationValidationException>(() => svc.Validate(op.Id, "test"));
        Assert.Contains(ex.Issues, i => i.Code == "NOT_ALLOCATED");

        // Contraintes en base, même si le code applicatif était contourné.
        ctx.ChangeTracker.Clear();
        ctx.Operations.Add(new Operation { BankAccountId = s.main, OperationDate = new(2026, 2, 1), AmountMinor = -5, Nature = OperationNature.Expense, Direction = OperationDirection.Debit });
        Assert.Throws<DbUpdateException>(() => ctx.SaveChanges());
        ctx.ChangeTracker.Clear();
        ctx.Operations.Add(new Operation { BankAccountId = s.main, OperationDate = new(2026, 2, 1), AmountMinor = 5, Nature = OperationNature.InternalTransfer, Direction = OperationDirection.Debit });
        Assert.Throws<DbUpdateException>(() => ctx.SaveChanges());
    }
}
