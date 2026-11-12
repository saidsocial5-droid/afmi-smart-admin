using AFMI_Gestion_projet.Models;
using Microsoft.EntityFrameworkCore;

namespace AFMI_Gestion_projet.Data
{
    public partial class AppDbContext
    {
        public DbSet<LogframeNode> LogframeNodes { get; set; } = null!;
        public DbSet<ProjectRisk> ProjectRisks { get; set; } = null!;
        public DbSet<DonorRule> DonorRules { get; set; } = null!;
        public DbSet<CofinancingContribution> CofinancingContributions { get; set; } = null!;
        public DbSet<CofinancingEntry> CofinancingEntries { get; set; } = null!;
        public DbSet<ProjectImport> ProjectImports { get; set; } = null!;

        private static void ConfigureDossier(ModelBuilder b)
        {
            b.Entity<Funder>(e =>
            {
                e.Property(x => x.InKindTreatment).HasMaxLength(20).HasDefaultValue("Suivi");
                e.ToTable(t => t.HasCheckConstraint("CK_Funders_InKindTreatment", "InKindTreatment IN ('Suivi', 'Comptabilité')"));
            });
            b.Entity<LogframeNode>(e =>
            {
                e.HasOne(x => x.Project).WithMany().HasForeignKey(x => x.ProjectId).OnDelete(DeleteBehavior.Restrict);
                e.HasOne(x => x.Parent).WithMany().HasForeignKey(x => x.ParentId).OnDelete(DeleteBehavior.Restrict);
                e.HasIndex(x => new { x.ProjectId, x.SortOrder });
                e.ToTable(t => t.HasCheckConstraint("CK_LogframeNodes_Level",
                    "Level IN ('Objectif global', 'Objectif spécifique', 'Résultat', 'Produit')"));
            });
            // Colonnes ajoutées à des tables existantes : valeurs par défaut en base, pour que les insertions du backend
            // Python (qui ne les connaît pas toutes) et les tables reconstruites par SQLite restent valides.
            b.Entity<Indicator>(e =>
            {
                e.Property(x => x.Code).HasDefaultValue("");
                e.Property(x => x.MeansOfVerification).HasDefaultValue("");
                e.HasOne(x => x.LogframeNode).WithMany().HasForeignKey(x => x.LogframeNodeId).OnDelete(DeleteBehavior.SetNull);
            });
            b.Entity<ProjectTask>(e => e.Property(x => x.Code).HasDefaultValue(""));
            b.Entity<Models.Finance.BudgetLine>(e =>
            {
                e.Property(x => x.DonorCategory).HasDefaultValue("");
                e.Property(x => x.ActivityCode).HasDefaultValue("");
                e.Property(x => x.SortOrder).HasDefaultValue(0);
            });
            b.Entity<Models.Finance.FundingTranche>(e => e.Property(x => x.Condition).HasDefaultValue(""));
            b.Entity<ProjectRisk>(e =>
                e.HasOne(x => x.Project).WithMany().HasForeignKey(x => x.ProjectId).OnDelete(DeleteBehavior.Restrict));
            b.Entity<DonorRule>(e =>
                e.HasOne(x => x.FundingAgreement).WithMany().HasForeignKey(x => x.FundingAgreementId).OnDelete(DeleteBehavior.Restrict));
            b.Entity<CofinancingContribution>(e =>
            {
                e.HasOne(x => x.Project).WithMany().HasForeignKey(x => x.ProjectId).OnDelete(DeleteBehavior.Restrict);
                e.HasOne(x => x.FundingAgreement).WithMany().HasForeignKey(x => x.FundingAgreementId).OnDelete(DeleteBehavior.Restrict);
                e.HasOne(x => x.BudgetLine).WithMany().HasForeignKey(x => x.BudgetLineId).OnDelete(DeleteBehavior.Restrict);
                e.ToTable(t =>
                {
                    t.HasCheckConstraint("CK_Cofinancing_Nature", "Nature IN ('Espèces', 'Nature')");
                    t.HasCheckConstraint("CK_Cofinancing_Planned", "PlannedMinor >= 0");
                });
            });
            b.Entity<CofinancingEntry>(e =>
            {
                e.HasOne(x => x.Contribution).WithMany(c => c.Entries).HasForeignKey(x => x.ContributionId).OnDelete(DeleteBehavior.Restrict);
                e.ToTable(t => t.HasCheckConstraint("CK_CofinancingEntries_Amount", "AmountMinor > 0"));
            });
            b.Entity<ProjectImport>(e =>
                e.HasOne(x => x.Project).WithMany().HasForeignKey(x => x.ProjectId).OnDelete(DeleteBehavior.SetNull));
        }
    }
}
