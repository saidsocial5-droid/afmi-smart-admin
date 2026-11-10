using System.Linq.Expressions;
using AFMI_Gestion_projet.Models;
using AFMI_Gestion_projet.Models.Finance;
using Microsoft.EntityFrameworkCore;

namespace AFMI_Gestion_projet.Data
{
    public partial class AppDbContext
    {
        public DbSet<FiscalYear> FiscalYears { get; set; } = null!;
        public DbSet<CurrencyRate> CurrencyRates { get; set; } = null!;
        public DbSet<BankAccount> BankAccounts { get; set; } = null!;
        public DbSet<AccountProjectLink> AccountProjectLinks { get; set; } = null!;
        public DbSet<LedgerAccount> LedgerAccounts { get; set; } = null!;
        public DbSet<Category> Categories { get; set; } = null!;
        public DbSet<FundingAgreement> FundingAgreements { get; set; } = null!;
        public DbSet<FundingTranche> FundingTranches { get; set; } = null!;
        public DbSet<BudgetLine> BudgetLines { get; set; } = null!;
        public DbSet<Operation> Operations { get; set; } = null!;
        public DbSet<OperationAllocation> OperationAllocations { get; set; } = null!;
        public DbSet<StoredFile> StoredFiles { get; set; } = null!;
        public DbSet<OperationAttachment> OperationAttachments { get; set; } = null!;
        public DbSet<CategorizationRule> CategorizationRules { get; set; } = null!;
        public DbSet<AppSetting> AppSettings { get; set; } = null!;
        public DbSet<AuditEntry> AuditEntries { get; set; } = null!;

        private static void ConfigureFinance(ModelBuilder b)
        {
            // Énumérations en texte, lisibles par le backend Python et dans les exports.
            foreach (var entity in b.Model.GetEntityTypes())
            {
                foreach (var property in entity.GetProperties())
                {
                    var type = Nullable.GetUnderlyingType(property.ClrType) ?? property.ClrType;
                    if (type.IsEnum && type.Namespace == typeof(OperationNature).Namespace)
                    {
                        property.SetProviderClrType(typeof(string));
                        property.SetMaxLength(30);
                    }
                }
            }

            b.Entity<Project>().Property(p => p.Currency).HasMaxLength(3).HasDefaultValue("MAD");

            b.Entity<FiscalYear>(e =>
            {
                e.HasIndex(x => x.Year).IsUnique();
                e.ToTable(t => t.HasCheckConstraint("CK_FiscalYears_Dates", "EndDate >= StartDate"));
            });

            b.Entity<CurrencyRate>(e =>
            {
                e.HasIndex(x => new { x.Currency, x.Date }).IsUnique();
                e.ToTable(t => t.HasCheckConstraint("CK_CurrencyRates_Positive", "CAST(RateToMad AS REAL) > 0"));
            });

            b.Entity<BankAccount>(e =>
            {
                e.HasIndex(x => x.Rib).IsUnique().HasFilter("Rib IS NOT NULL AND IsDeleted = 0");
            });

            b.Entity<AccountProjectLink>(e =>
            {
                e.HasOne(x => x.BankAccount).WithMany(a => a.ProjectLinks).HasForeignKey(x => x.BankAccountId).OnDelete(DeleteBehavior.Restrict);
                e.HasOne(x => x.Project).WithMany().HasForeignKey(x => x.ProjectId).OnDelete(DeleteBehavior.Restrict);
                e.HasIndex(x => new { x.BankAccountId, x.ProjectId });
            });

            b.Entity<LedgerAccount>(e =>
            {
                e.HasIndex(x => x.Code).IsUnique();
                e.HasOne(x => x.Parent).WithMany().HasForeignKey(x => x.ParentId).OnDelete(DeleteBehavior.Restrict);
            });

            b.Entity<Category>(e =>
            {
                e.HasOne(x => x.Parent).WithMany().HasForeignKey(x => x.ParentId).OnDelete(DeleteBehavior.Restrict);
                e.HasOne(x => x.LedgerAccount).WithMany().HasForeignKey(x => x.LedgerAccountId).OnDelete(DeleteBehavior.Restrict);
                e.HasIndex(x => new { x.Kind, x.Code });
                // Catégories de recettes citées dans le cahier des charges ; les natures de dépenses et le plan de
                // comptes sont à importer depuis le référentiel de l'expert-comptable (aucun n'est inventé).
                e.HasData(
                    new Category { Id = 1, Kind = CategoryKind.Income, Code = "SUBV", Label = "Subventions" },
                    new Category { Id = 2, Kind = CategoryKind.Income, Code = "COTIS", Label = "Cotisations" },
                    new Category { Id = 3, Kind = CategoryKind.Income, Code = "DONS", Label = "Dons" },
                    new Category { Id = 4, Kind = CategoryKind.Income, Code = "PREST", Label = "Prestations" },
                    new Category { Id = 5, Kind = CategoryKind.Income, Code = "PFIN", Label = "Produits financiers" });
            });

            b.Entity<FundingAgreement>(e =>
            {
                e.HasOne(x => x.Funder).WithMany().HasForeignKey(x => x.FunderId).OnDelete(DeleteBehavior.Restrict);
                e.HasOne(x => x.Project).WithMany().HasForeignKey(x => x.ProjectId).OnDelete(DeleteBehavior.Restrict);
                e.ToTable(t => t.HasCheckConstraint("CK_FundingAgreements_Amount", "AmountMinor >= 0"));
            });

            b.Entity<FundingTranche>(e =>
            {
                e.HasOne(x => x.FundingAgreement).WithMany(a => a.Tranches).HasForeignKey(x => x.FundingAgreementId).OnDelete(DeleteBehavior.Restrict);
                e.HasOne(x => x.ReceivedOperation).WithMany().HasForeignKey(x => x.ReceivedOperationId).OnDelete(DeleteBehavior.Restrict);
                e.ToTable(t => t.HasCheckConstraint("CK_FundingTranches_Amount", "AmountMinor >= 0"));
            });

            b.Entity<BudgetLine>(e =>
            {
                e.HasOne(x => x.Project).WithMany().HasForeignKey(x => x.ProjectId).OnDelete(DeleteBehavior.Restrict);
                e.HasOne(x => x.FundingAgreement).WithMany().HasForeignKey(x => x.FundingAgreementId).OnDelete(DeleteBehavior.Restrict);
                e.HasOne(x => x.FiscalYear).WithMany().HasForeignKey(x => x.FiscalYearId).OnDelete(DeleteBehavior.Restrict);
                e.HasOne(x => x.Category).WithMany().HasForeignKey(x => x.CategoryId).OnDelete(DeleteBehavior.Restrict);
                e.ToTable(t => t.HasCheckConstraint("CK_BudgetLines_Planned", "PlannedMinor >= 0"));
            });

            b.Entity<Operation>(e =>
            {
                e.HasOne(x => x.BankAccount).WithMany(a => a.Operations).HasForeignKey(x => x.BankAccountId).OnDelete(DeleteBehavior.Restrict);
                e.HasIndex(x => new { x.BankAccountId, x.OperationDate });
                e.HasIndex(x => x.TransferGroupId);
                e.Ignore(x => x.SignedAmountMinor);
                e.ToTable(t =>
                {
                    t.HasCheckConstraint("CK_Operations_Amount", "AmountMinor > 0 AND AmountMadMinor >= 0");
                    t.HasCheckConstraint("CK_Operations_Transfer",
                        "(Nature = 'InternalTransfer' AND TransferGroupId IS NOT NULL) OR (Nature <> 'InternalTransfer' AND TransferGroupId IS NULL)");
                });
            });

            b.Entity<OperationAllocation>(e =>
            {
                e.HasOne(x => x.Operation).WithMany(o => o.Allocations).HasForeignKey(x => x.OperationId).OnDelete(DeleteBehavior.Cascade);
                e.HasOne(x => x.Project).WithMany().HasForeignKey(x => x.ProjectId).OnDelete(DeleteBehavior.Restrict);
                e.HasOne(x => x.BudgetLine).WithMany().HasForeignKey(x => x.BudgetLineId).OnDelete(DeleteBehavior.Restrict);
                e.HasOne(x => x.Category).WithMany().HasForeignKey(x => x.CategoryId).OnDelete(DeleteBehavior.Restrict);
                e.ToTable(t => t.HasCheckConstraint("CK_OperationAllocations_Amount", "AmountMinor > 0"));
            });

            b.Entity<StoredFile>(e => e.HasIndex(x => x.Sha256).IsUnique());

            b.Entity<OperationAttachment>(e =>
            {
                e.HasOne(x => x.Operation).WithMany(o => o.Attachments).HasForeignKey(x => x.OperationId).OnDelete(DeleteBehavior.Cascade);
                e.HasOne(x => x.StoredFile).WithMany().HasForeignKey(x => x.StoredFileId).OnDelete(DeleteBehavior.Restrict);
                e.HasOne(x => x.ProjectDocument).WithMany().HasForeignKey(x => x.ProjectDocumentId).OnDelete(DeleteBehavior.Restrict);
            });

            b.Entity<CategorizationRule>(e =>
            {
                e.HasOne(x => x.Category).WithMany().HasForeignKey(x => x.CategoryId).OnDelete(DeleteBehavior.Restrict);
            });

            b.Entity<AuditEntry>(e =>
            {
                e.HasIndex(x => new { x.EntityType, x.EntityId });
                e.HasIndex(x => x.TimestampUtc);
            });
        }

        /// <summary>Filtre global : les lignes supprimées logiquement sont invisibles (IgnoreQueryFilters pour l'audit).</summary>
        private static void ConfigureSoftDelete(ModelBuilder b)
        {
            foreach (var entity in b.Model.GetEntityTypes().Where(t => typeof(ISoftDeletable).IsAssignableFrom(t.ClrType)))
            {
                var parameter = Expression.Parameter(entity.ClrType, "e");
                var body = Expression.Not(Expression.Property(parameter, nameof(ISoftDeletable.IsDeleted)));
                entity.SetQueryFilter(Expression.Lambda(body, parameter));
                entity.FindProperty(nameof(ISoftDeletable.IsDeleted))!.SetDefaultValue(false);
            }
        }
    }
}
