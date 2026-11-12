using AFMI_Gestion_projet.Data;
using AFMI_Gestion_projet.Finance;
using AFMI_Gestion_projet.Models;
using AFMI_Gestion_projet.Models.Finance;

namespace AFMI_Gestion_projet.Core.Tests;

/// <summary>Association fictive : un projet, un compte de fonctionnement, un compte projet, des lignes budgétaires.</summary>
internal sealed class Lot2Fixture
{
    public int ProjectId, Operating, ProjectAccount, LineProject, LineOperating, FunderId;

    public static Lot2Fixture Seed(AppDbContext ctx)
    {
        var f = new Lot2Fixture();
        var funder = new Funder { Name = "Bailleur test" };
        var project = new Project { Name = "Reboisement", Code = "P1", Status = "Exécution", TargetEndDate = new DateTime(2026, 12, 31) };
        ctx.Funders.Add(funder);
        ctx.Projects.Add(project);
        ctx.SaveChanges();
        var operating = new BankAccount { Title = "Fonctionnement", Purpose = AccountPurpose.Operating, OpeningDate = new(2026, 1, 1), OpeningBalanceMinor = 10_000_00 };
        var projectAccount = new BankAccount { Title = "Compte projet", Purpose = AccountPurpose.Project, OpeningDate = new(2026, 1, 1) };
        ctx.BankAccounts.AddRange(operating, projectAccount);
        var lineP = new BudgetLine { ProjectId = project.Id, Code = "1.1", Label = "Plants", PlannedMinor = 12_000_00 };
        var lineF = new BudgetLine { Code = "F1", Label = "Loyer", PlannedMinor = 24_000_00 };
        ctx.BudgetLines.AddRange(lineP, lineF);
        ctx.SaveChanges();
        f.ProjectId = project.Id; f.Operating = operating.Id; f.ProjectAccount = projectAccount.Id;
        f.LineProject = lineP.Id; f.LineOperating = lineF.Id; f.FunderId = funder.Id;
        return f;
    }

    /// <summary>Opération validée entièrement ventilée.</summary>
    public static Operation Validated(AppDbContext ctx, int account, DateOnly date, OperationNature nature, long amount,
        int? projectId, int lineId, string label = "", OperationDirection? direction = null)
    {
        var svc = new FinanceService(ctx);
        var op = new Operation
        {
            BankAccountId = account, OperationDate = date, Nature = nature, AmountMinor = amount, Label = label,
            Direction = direction ?? (nature == OperationNature.Income ? OperationDirection.Credit : OperationDirection.Debit),
        };
        op.Allocations.Add(new OperationAllocation { ProjectId = projectId, BudgetLineId = lineId, AmountMinor = amount });
        svc.AddDraft(op);
        return svc.Validate(op.Id, "test");
    }
}
