using AFMI_Gestion_projet.Models;
using AFMI_Gestion_projet.Models.Finance;
using Microsoft.EntityFrameworkCore;

namespace AFMI_Gestion_projet.Core.Tests;

public class DossierMigrationTests
{
    [Fact]
    public void LogframeRisksRulesCofinancingAndImports_AreStored_AndExistingRowsKeepTheirData()
    {
        using var db = new TestDatabase();
        using (var ctx = db.Open())
        {
            var funder = new Funder { Name = "PNUD" };
            var p = new Project { Name = "APAC", Code = "MOR/ICCA-GSI/2026/03", Funder = funder };
            ctx.Projects.Add(p);
            ctx.SaveChanges();
            var agreement = new FundingAgreement { FunderId = funder.Id, ProjectId = p.Id, Reference = "MOR/ICCA-GSI/2026/03", AmountMinor = 5_000_000, Currency = "USD" };
            agreement.Tranches.Add(new FundingTranche { Label = "Tranche 2", ExpectedDate = new DateOnly(2027, 6, 30), AmountMinor = 2_000_000, Percent = 40m, Condition = "Approbation du rapport n° 2" });
            ctx.FundingAgreements.Add(agreement);
            var line = new BudgetLine { ProjectId = p.Id, Code = "1.2", Label = "Main-d'œuvre locale", DonorCategory = "Personnel", ActivityCode = "2.5", PlannedMinor = 7_200_000, SortOrder = 2 };
            ctx.BudgetLines.Add(line);
            var result = new LogframeNode { ProjectId = p.Id, Level = "Résultat", Code = "R1", Statement = "Agdal réhabilité sur 2400 ha" };
            ctx.LogframeNodes.Add(result);
            ctx.Indicators.Add(new Indicator { ProjectId = p.Id, Name = "Superficie sous Agdal", Unit = "ha", TargetValue = 2400, Code = "I1.1", MeansOfVerification = "Charte signée", LogframeNode = result });
            ctx.Tasks.Add(new ProjectTask { ProjectId = p.Id, Code = "1.1", Name = "Diagnostic participatif" });
            ctx.ProjectRisks.Add(new ProjectRisk { ProjectId = p.Id, Description = "Conflits d'usage", Probability = "Moyen", Mitigation = "Concertation" });
            ctx.DonorRules.Add(new DonorRule { FundingAgreement = agreement, Kind = "CofinancingMinPercent", Value = 100m, Text = "Cofinancement ≥ subvention" });
            var contribution = new CofinancingContribution { ProjectId = p.Id, BudgetLine = line, SourceType = "Communauté", Nature = "Nature", PlannedMinor = 10_000_000, Commitment = "Engagé" };
            contribution.Entries.Add(new CofinancingEntry { Date = new DateOnly(2026, 11, 30), AmountMinor = 450_000, Description = "Gardiennage, novembre", Evidence = "Feuille de présence" });
            ctx.CofinancingContributions.Add(contribution);
            ctx.ProjectImports.Add(new ProjectImport { ProjectId = p.Id, FilesJson = "[{\"name\":\"Formulaire.pdf\"}]", ResultJson = "{}", Engine = "règles" });
            ctx.SaveChanges();
        }
        using (var ctx = db.Open())
        {
            Assert.Equal("Suivi", ctx.Funders.Single().InKindTreatment);
            var tranche = ctx.FundingTranches.Single();
            Assert.Equal((40m, "Approbation du rapport n° 2"), (tranche.Percent, tranche.Condition));
            Assert.Equal("R1", ctx.Indicators.Include(i => i.LogframeNode).Single().LogframeNode!.Code);
            Assert.Equal(450_000, ctx.CofinancingContributions.Include(c => c.Entries).Single().Entries.Single().AmountMinor);
            Assert.Equal("1.1", ctx.Tasks.Single().Code);
            Assert.Equal(100m, ctx.DonorRules.Single().Value);
        }
        Assert.ThrowsAny<Exception>(() => db.Execute("UPDATE Funders SET InKindTreatment = 'Autre'"));
        Assert.ThrowsAny<Exception>(() => db.Execute("UPDATE CofinancingContributions SET Nature = 'Crypto'"));
        Assert.ThrowsAny<Exception>(() => db.Execute("UPDATE LogframeNodes SET Level = 'Inconnu'"));
    }
}
