using AFMI_Gestion_projet.Finance;
using AFMI_Gestion_projet.Models.Finance;

namespace AFMI_Gestion_projet.Core.Tests;

public class ReconciliationTests : IDisposable
{
    private readonly TestDatabase _db = new();
    public void Dispose() => _db.Dispose();

    private static BankStatement Statement(int account, DateOnly start, DateOnly end, long opening, long closing, params StatementLine[] lines)
    {
        var s = new BankStatement { BankAccountId = account, PeriodStart = start, PeriodEnd = end, OpeningBalanceMinor = opening, ClosingBalanceMinor = closing };
        foreach (var l in lines) s.Lines.Add(l);
        return s;
    }

    private static StatementLine Line(DateOnly date, long signed, string label = "") =>
        new() { OperationDate = date, Label = label, DebitMinor = signed < 0 ? -signed : 0, CreditMinor = signed > 0 ? signed : 0 };

    [Fact]
    public void Check_DetectsBalanceDuplicateAndContinuityProblems()
    {
        using var ctx = _db.Open();
        var f = Lot2Fixture.Seed(ctx);
        var svc = new ReconciliationService(ctx);

        var jan = Statement(f.Operating, new(2026, 1, 1), new(2026, 1, 31), 10_000_00, 9_500_00, Line(new(2026, 1, 10), -500_00));
        ctx.BankStatements.Add(jan);
        ctx.SaveChanges();
        Assert.Empty(svc.Check(jan.Id).Errors);
        svc.Validate(jan.Id);

        var wrong = Statement(f.Operating, new(2026, 2, 1), new(2026, 2, 28), 9_500_00, 9_000_00, Line(new(2026, 2, 3), -400_00));
        ctx.BankStatements.Add(wrong);
        ctx.SaveChanges();
        var check = svc.Check(wrong.Id);
        Assert.False(check.BalanceOk);
        Assert.Equal(9_100_00, check.ComputedClosingMinor);
        Assert.Throws<FinanceRuleException>(() => svc.Validate(wrong.Id));

        var gap = Statement(f.Operating, new(2026, 4, 1), new(2026, 4, 30), 9_000_00, 9_000_00, Line(new(2026, 4, 2), 1), Line(new(2026, 4, 3), -1));
        ctx.BankStatements.Add(gap);
        ctx.SaveChanges();
        var gapCheck = svc.Check(gap.Id);
        Assert.Contains(gapCheck.Warnings, w => w.Contains("Relevé manquant"));

        var dup = Statement(f.Operating, new(2026, 1, 1), new(2026, 1, 31), 10_000_00, 9_500_00, Line(new(2026, 1, 10), -500_00));
        ctx.BankStatements.Add(dup);
        ctx.SaveChanges();
        Assert.Contains(svc.Check(dup.Id).Errors, e => e.Contains("déjà importé"));

        var broken = Statement(f.Operating, new(2026, 5, 1), new(2026, 5, 31), 1, 1, Line(new(2026, 5, 2), 1), Line(new(2026, 5, 3), -1));
        ctx.BankStatements.Add(broken);
        ctx.SaveChanges();
        Assert.Contains(svc.Check(broken.Id).Errors, e => e.Contains("continuité"));
    }

    [Fact]
    public void AutoMatch_UsesAmountDateAndLabel_AndSkipsAmbiguousCases()
    {
        using var ctx = _db.Open();
        var f = Lot2Fixture.Seed(ctx);
        var loyer = Lot2Fixture.Validated(ctx, f.Operating, new(2026, 3, 5), OperationNature.Expense, 2_000_00, null, f.LineOperating, "Loyer mars siège");
        var plants1 = Lot2Fixture.Validated(ctx, f.Operating, new(2026, 3, 10), OperationNature.Expense, 300_00, null, f.LineOperating, "Pépinière Azrou");
        var plants2 = Lot2Fixture.Validated(ctx, f.Operating, new(2026, 3, 10), OperationNature.Expense, 300_00, null, f.LineOperating, "Pépinière Azrou");
        var late = Lot2Fixture.Validated(ctx, f.Operating, new(2026, 3, 1), OperationNature.Expense, 99_00, null, f.LineOperating, "Frais");

        var st = Statement(f.Operating, new(2026, 3, 1), new(2026, 3, 31), 10_000_00, 7_301_00,
            Line(new(2026, 3, 7), -2_000_00, "PRLV LOYER MARS"),
            Line(new(2026, 3, 11), -300_00, "CHQ PEPINIERE"),
            Line(new(2026, 3, 11), -300_00, "CHQ PEPINIERE"),
            Line(new(2026, 3, 9), -99_00, "FRAIS TENUE"));
        ctx.BankStatements.Add(st);
        ctx.SaveChanges();

        var svc = new ReconciliationService(ctx);
        int matched = svc.AutoMatch(st.Id, "test");
        // Loyer : apparié. Pépinière : deux lignes et deux opérations identiques → ambigu, laissé au manuel.
        // Frais : 8 jours d'écart, hors tolérance (3 jours).
        Assert.Equal(1, matched);
        Assert.Equal(loyer.Id, ctx.ReconciliationMatches.Single().OperationId);

        var report = svc.GetReport(st.Id);
        Assert.Equal(3, report.UnmatchedLines.Count);
        Assert.Equal(3, report.UnmatchedOperations.Count);
        Assert.Equal(0, report.UnexplainedDifferenceMinor);

        var lines = ctx.StatementLines.Where(l => l.BankStatementId == st.Id).OrderBy(l => l.Id).ToList();
        svc.Match(lines[1].Id, plants1.Id, "test");
        svc.Match(lines[2].Id, plants2.Id, "test");
        Assert.Throws<FinanceRuleException>(() => svc.Match(lines[3].Id, plants1.Id, "test"));           // déjà rapprochée
        Assert.Throws<FinanceRuleException>(() => svc.Match(lines[3].Id, loyer.Id, "test"));             // montant différent
        svc.Match(lines[3].Id, late.Id, "test");

        report = svc.GetReport(st.Id);
        Assert.Empty(report.UnmatchedLines);
        Assert.Empty(report.UnmatchedOperations);
        Assert.Equal(report.BookBalanceMinor, report.BankClosingMinor);

        svc.Unmatch(lines[3].Id);
        Assert.Single(svc.GetReport(st.Id).UnmatchedLines);
    }

    [Fact]
    public void Report_RevealsUnexplainedDifference_AndAlertsRaiseIt()
    {
        using var ctx = _db.Open();
        var f = Lot2Fixture.Seed(ctx);
        Lot2Fixture.Validated(ctx, f.Operating, new(2026, 3, 5), OperationNature.Expense, 2_000_00, null, f.LineOperating, "Loyer");
        // La banque a débité 2 000,50 : 0,50 d'écart non expliqué par une ligne non comptabilisée.
        var st = Statement(f.Operating, new(2026, 3, 1), new(2026, 3, 31), 10_000_00, 7_999_50, Line(new(2026, 3, 5), -2_000_50, "Loyer"));
        ctx.BankStatements.Add(st);
        ctx.SaveChanges();

        var report = new ReconciliationService(ctx).GetReport(st.Id);
        // Ligne bancaire non comptabilisée (−2 000,50) et opération non passée en banque (−2 000,00) : écart nul, tout est expliqué.
        Assert.Equal(0, report.UnexplainedDifferenceMinor);

        // Écart réel : solde de relevé faux par rapport à ses lignes et aux livres.
        st.ClosingBalanceMinor = 7_000_00;
        ctx.SaveChanges();
        report = new ReconciliationService(ctx).GetReport(st.Id);
        Assert.Equal(999_50, report.UnexplainedDifferenceMinor);
        var alerts = new TreasuryAlertService(ctx).GetAlerts(new(2026, 4, 1));
        Assert.Contains(alerts, a => a.Code == "RECONCILIATION_GAP" && a.AccountId == f.Operating);
    }

    [Theory]
    [InlineData("Loyer mars siège", "PRLV LOYER MARS", 0.5)]
    [InlineData("Pépinière", "PEPINIERE", 1.0)]
    [InlineData("abc", "xyz", 0.0)]
    public void LabelSimilarity_IgnoresCaseAndAccents(string a, string b, double expected) =>
        Assert.Equal(expected, ReconciliationService.LabelSimilarity(a, b), 2);
}
