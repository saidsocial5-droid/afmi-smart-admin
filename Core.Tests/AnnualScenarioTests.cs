using System.Text.Json;
using AFMI_Gestion_projet.Finance;
using AFMI_Gestion_projet.Models;
using AFMI_Gestion_projet.Models.Finance;

namespace AFMI_Gestion_projet.Core.Tests;

/// <summary>
/// Même scénario que les tests Python des rapports annuels (SharedTestCases/annual_scenario.json) :
/// les totaux des états financiers (Python) doivent concorder avec FinanceService et ReconciliationService.
/// </summary>
public class AnnualScenarioTests : IDisposable
{
    private readonly TestDatabase _db = new();
    public void Dispose() => _db.Dispose();

    [Fact]
    public void SharedScenario_TotalsBalanceAndReconciliation()
    {
        var s = JsonDocument.Parse(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "SharedTestCases", "annual_scenario.json"))).RootElement;
        using var ctx = _db.Open();
        var project = new Project { Name = "Projet 1", Code = "P1" };
        ctx.Projects.Add(project);
        ctx.SaveChanges();
        foreach (var r in s.GetProperty("rates").EnumerateArray())
            ctx.CurrencyRates.Add(new CurrencyRate { Currency = r.GetProperty("currency").GetString()!, Date = DateOnly.Parse(r.GetProperty("date").GetString()!),
                RateToMad = decimal.Parse(r.GetProperty("rate").GetString()!, System.Globalization.CultureInfo.InvariantCulture) });
        var accounts = new Dictionary<string, BankAccount>();
        foreach (var a in s.GetProperty("accounts").EnumerateArray())
        {
            var acc = new BankAccount { Title = a.GetProperty("title").GetString()!, Currency = a.GetProperty("currency").GetString()!,
                OpeningBalanceMinor = a.GetProperty("opening").GetInt64(), OpeningDate = DateOnly.Parse(a.GetProperty("opening_date").GetString()!) };
            ctx.BankAccounts.Add(acc);
            accounts[a.GetProperty("key").GetString()!] = acc;
        }
        var lineP = new BudgetLine { ProjectId = project.Id, Code = "1", Label = "Projet", PlannedMinor = 1 };
        var lineF = new BudgetLine { Code = "F", Label = "Fonctionnement", PlannedMinor = 1 };
        ctx.BudgetLines.AddRange(lineP, lineF);
        ctx.SaveChanges();

        var svc = new FinanceService(ctx);
        var ops = new Dictionary<string, int>();
        foreach (var o in s.GetProperty("operations").EnumerateArray())
        {
            var op = new Operation
            {
                BankAccountId = accounts[o.GetProperty("account").GetString()!].Id, OperationDate = DateOnly.Parse(o.GetProperty("date").GetString()!),
                Label = o.GetProperty("label").GetString()!, Nature = Enum.Parse<OperationNature>(o.GetProperty("nature").GetString()!),
                Direction = Enum.Parse<OperationDirection>(o.GetProperty("direction").GetString()!), AmountMinor = o.GetProperty("amount").GetInt64(),
                Currency = accounts[o.GetProperty("account").GetString()!].Currency,
            };
            foreach (var al in o.GetProperty("allocations").EnumerateArray())
            {
                bool isProject = al.GetProperty("project").ValueKind == JsonValueKind.String;
                op.Allocations.Add(new OperationAllocation { ProjectId = isProject ? project.Id : null, BudgetLineId = isProject ? lineP.Id : lineF.Id,
                    AmountMinor = al.GetProperty("amount").GetInt64() });
            }
            svc.AddDraft(op);
            svc.Validate(op.Id, "test");
            ops[o.GetProperty("key").GetString()!] = op.Id;
        }
        var tr = s.GetProperty("transfer");
        var group = svc.CreateInternalTransfer(accounts[tr.GetProperty("from").GetString()!].Id, accounts[tr.GetProperty("to").GetString()!].Id,
            DateOnly.Parse(tr.GetProperty("date").GetString()!), tr.GetProperty("amount").GetInt64(), "Virement", "test", tr.GetProperty("received").GetInt64());
        ops["transfer_debit"] = ctx.Operations.Single(o => o.TransferGroupId == group && o.Direction == OperationDirection.Debit).Id;

        var st = s.GetProperty("statement");
        var statement = new BankStatement
        {
            BankAccountId = accounts[st.GetProperty("account").GetString()!].Id, PeriodStart = DateOnly.Parse(st.GetProperty("start").GetString()!),
            PeriodEnd = DateOnly.Parse(st.GetProperty("end").GetString()!), OpeningBalanceMinor = st.GetProperty("opening").GetInt64(),
            ClosingBalanceMinor = st.GetProperty("closing").GetInt64(),
        };
        var lineMatches = new List<(StatementLine Line, string? Match)>();
        foreach (var l in st.GetProperty("lines").EnumerateArray())
        {
            long signed = l.GetProperty("signed").GetInt64();
            var line = new StatementLine { OperationDate = DateOnly.Parse(l.GetProperty("date").GetString()!), Label = "x",
                DebitMinor = signed < 0 ? -signed : 0, CreditMinor = signed > 0 ? signed : 0 };
            statement.Lines.Add(line);
            lineMatches.Add((line, l.GetProperty("match").ValueKind == JsonValueKind.String ? l.GetProperty("match").GetString() : null));
        }
        ctx.BankStatements.Add(statement);
        ctx.SaveChanges();
        var rec = new ReconciliationService(ctx);
        foreach (var (line, match) in lineMatches.Where(x => x.Match != null)) rec.Match(line.Id, ops[match!], "test");

        var expected = s.GetProperty("expected");
        int year = s.GetProperty("year").GetInt32();
        var totals = svc.GetIncomeAndExpenses(new DateOnly(year, 1, 1), new DateOnly(year, 12, 31));
        Assert.Equal(expected.GetProperty("income_mad").GetInt64(), totals.IncomeMadMinor);
        Assert.Equal(expected.GetProperty("expense_mad").GetInt64(), totals.ExpenseMadMinor);
        Assert.Equal(expected.GetProperty("balance_A_2026-03-31").GetInt64(), svc.GetBalanceMinor(accounts["A"].Id, new DateOnly(2026, 3, 31)));
        var report = rec.GetReport(statement.Id);
        Assert.Equal(expected.GetProperty("reconciliation_difference").GetInt64(), report.UnexplainedDifferenceMinor);
        Assert.Equal(expected.GetProperty("unmatched_lines").GetInt32(), report.UnmatchedLines.Count);
    }
}
