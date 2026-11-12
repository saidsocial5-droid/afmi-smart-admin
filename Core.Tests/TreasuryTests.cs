using AFMI_Gestion_projet.Finance;
using AFMI_Gestion_projet.Models.Finance;

namespace AFMI_Gestion_projet.Core.Tests;

public class TreasuryTests : IDisposable
{
    private readonly TestDatabase _db = new();
    public void Dispose() => _db.Dispose();

    [Fact]
    public void Forecast_AddsExpectedTranches_AndSpreadsRemainingBudget()
    {
        using var ctx = _db.Open();
        var f = Lot2Fixture.Seed(ctx);
        ctx.CurrencyRates.Add(new CurrencyRate { Currency = "EUR", Date = new(2026, 1, 1), RateToMad = 11m });
        var agreement = new FundingAgreement { FunderId = f.FunderId, ProjectId = f.ProjectId, Reference = "CONV-1", AmountMinor = 10_000_00, Currency = "EUR" };
        agreement.Tranches.Add(new FundingTranche { Label = "T1", ExpectedDate = new(2026, 6, 15), AmountMinor = 2_000_00 });  // en retard au 30/06
        agreement.Tranches.Add(new FundingTranche { Label = "T2", ExpectedDate = new(2026, 9, 1), AmountMinor = 3_000_00 });
        agreement.Tranches.Add(new FundingTranche { Label = "T3", ExpectedDate = new(2027, 3, 1), AmountMinor = 5_000_00 }); // hors horizon 6 mois
        ctx.FundingAgreements.Add(agreement);
        ctx.SaveChanges();
        // 2 000 déjà dépensés sur la ligne projet (12 000 prévus) → 10 000 à répartir de juillet à décembre (fin du projet).
        Lot2Fixture.Validated(ctx, f.Operating, new(2026, 2, 1), OperationNature.Expense, 2_000_00, f.ProjectId, f.LineProject);
        // Ligne de fonctionnement sans date de fin : 24 000 répartis sur l'horizon de 6 mois.

        var forecast = new TreasuryForecastService(ctx).Forecast(new(2026, 6, 30), 6);
        Assert.Equal(8_000_00, forecast.StartingMadMinor);
        Assert.Equal(6, forecast.Months.Count);
        Assert.Equal((2026, 7), (forecast.Months[0].Year, forecast.Months[0].Month));
        Assert.Equal(22_000_00, forecast.Months[0].InflowMadMinor);   // T1 en retard : 2 000 EUR × 11
        Assert.Equal(33_000_00, forecast.Months[2].InflowMadMinor);   // T2 en septembre
        Assert.Equal(55_000_00, forecast.Months.Sum(m => m.InflowMadMinor));
        Assert.Equal(10_000_00 + 24_000_00, forecast.Months.Sum(m => m.OutflowMadMinor));
        Assert.Equal(1_666_67 + 4_000_00, forecast.Months[0].OutflowMadMinor);
        Assert.Equal(8_000_00 + 55_000_00 - 34_000_00, forecast.Months[^1].ClosingMadMinor);
        Assert.Contains(forecast.Notes, n => n.Contains("en retard"));
    }

    [Fact]
    public void Forecast_UsesContractualRate_AndReportsMissingRates()
    {
        using var ctx = _db.Open();
        var f = Lot2Fixture.Seed(ctx);
        var withRate = new FundingAgreement { FunderId = f.FunderId, ProjectId = f.ProjectId, Reference = "A", AmountMinor = 1, Currency = "EUR", ContractualRateToMad = 10.5m };
        withRate.Tranches.Add(new FundingTranche { Label = "TA", ExpectedDate = new(2026, 2, 10), AmountMinor = 100_00 });
        var noRate = new FundingAgreement { FunderId = f.FunderId, ProjectId = f.ProjectId, Reference = "B", AmountMinor = 1, Currency = "USD" };
        noRate.Tranches.Add(new FundingTranche { Label = "TB", ExpectedDate = new(2026, 2, 10), AmountMinor = 100_00 });
        ctx.FundingAgreements.AddRange(withRate, noRate);
        ctx.SaveChanges();

        var forecast = new TreasuryForecastService(ctx).Forecast(new(2026, 1, 31), 3);
        Assert.Equal(1_050_00, forecast.Months[0].InflowMadMinor);
        Assert.Contains(forecast.Notes, n => n.Contains("USD"));
        Assert.Throws<ArgumentOutOfRangeException>(() => new TreasuryForecastService(ctx).Forecast(new(2026, 1, 31), 0));
    }

    [Fact]
    public void Alerts_CoverLowNegativeInactiveOverdueAndDrafts()
    {
        using var ctx = _db.Open();
        var f = Lot2Fixture.Seed(ctx);
        var operating = ctx.BankAccounts.Single(a => a.Id == f.Operating);
        operating.LowBalanceThresholdMinor = 20_000_00;
        ctx.SaveChanges();
        Lot2Fixture.Validated(ctx, f.ProjectAccount, new(2026, 1, 15), OperationNature.Expense, 100_00, f.ProjectId, f.LineProject);
        var agreement = new FundingAgreement { FunderId = f.FunderId, ProjectId = f.ProjectId, Reference = "C1", AmountMinor = 1 };
        agreement.Tranches.Add(new FundingTranche { Label = "T1", ExpectedDate = new(2026, 3, 1), AmountMinor = 1 });
        ctx.FundingAgreements.Add(agreement);
        ctx.SaveChanges();
        new FinanceService(ctx).AddDraft(new Operation { BankAccountId = f.Operating, OperationDate = new(2026, 2, 1), Nature = OperationNature.Expense, Direction = OperationDirection.Debit, AmountMinor = 1 });

        var codes = new TreasuryAlertService(ctx).GetAlerts(new(2026, 6, 1)).Select(a => a.Code).ToList();
        Assert.Contains("LOW_BALANCE", codes);
        Assert.Contains("NEGATIVE_BALANCE", codes);           // compte projet à −100
        Assert.Contains("INACTIVE_PROJECT_ACCOUNT", codes);   // dernier mouvement le 15/01
        Assert.Contains("TRANCHE_OVERDUE", codes);
        Assert.Contains("DRAFT_OPERATIONS", codes);
    }

    [Fact]
    public void ContraEntries_ReduceIncomeAndExpenses()
    {
        using var ctx = _db.Open();
        var f = Lot2Fixture.Seed(ctx);
        Lot2Fixture.Validated(ctx, f.Operating, new(2026, 2, 1), OperationNature.Income, 5_000_00, null, f.LineOperating);
        Lot2Fixture.Validated(ctx, f.Operating, new(2026, 2, 2), OperationNature.Income, 1_000_00, null, f.LineOperating, "Restitution", OperationDirection.Debit);
        Lot2Fixture.Validated(ctx, f.Operating, new(2026, 2, 3), OperationNature.Expense, 800_00, null, f.LineOperating);
        Lot2Fixture.Validated(ctx, f.Operating, new(2026, 2, 4), OperationNature.Expense, 300_00, null, f.LineOperating, "Avoir", OperationDirection.Credit);

        var totals = new FinanceService(ctx).GetIncomeAndExpenses(new(2026, 1, 1), new(2026, 12, 31));
        Assert.Equal(new IncomeExpenseTotals(4_000_00, 500_00), totals);
        Assert.Equal(10_000_00 + 4_000_00 - 500_00, new FinanceService(ctx).GetBalanceMinor(f.Operating, new(2026, 12, 31)));
        Assert.Equal(500_00, new TreasuryForecastService(ctx).RealizedMadByBudgetLine(new[] { f.LineOperating })[f.LineOperating]);
    }
}
