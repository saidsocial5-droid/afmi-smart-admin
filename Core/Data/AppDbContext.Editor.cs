using AFMI_Gestion_projet.Models;
using AFMI_Gestion_projet.Models.Editor;
using Microsoft.EntityFrameworkCore;

namespace AFMI_Gestion_projet.Data
{
    public partial class AppDbContext
    {
        public DbSet<GraphicChart> GraphicCharts { get; set; } = null!;
        public DbSet<DocumentTemplate> DocumentTemplates { get; set; } = null!;
        public DbSet<EditorDocument> EditorDocuments { get; set; } = null!;
        public DbSet<DocumentVersion> DocumentVersions { get; set; } = null!;
        public DbSet<DocumentComment> DocumentComments { get; set; } = null!;
        public DbSet<Photo> Photos { get; set; } = null!;
        public DbSet<IndicatorMeasurement> IndicatorMeasurements { get; set; } = null!;

        private static void ConfigureEditor(ModelBuilder b)
        {
            b.Entity<GraphicChart>(e =>
            {
                e.Property(x => x.Scope).HasConversion<string>().HasMaxLength(30);
                e.HasOne(x => x.Funder).WithMany().HasForeignKey(x => x.FunderId).OnDelete(DeleteBehavior.Restrict);
                e.HasOne(x => x.Project).WithMany().HasForeignKey(x => x.ProjectId).OnDelete(DeleteBehavior.Restrict);
                e.ToTable(t => t.HasCheckConstraint("CK_GraphicCharts_Scope",
                    "(Scope = 'Association' AND FunderId IS NULL AND ProjectId IS NULL) OR " +
                    "(Scope = 'Funder' AND FunderId IS NOT NULL AND ProjectId IS NULL) OR " +
                    "(Scope = 'Project' AND ProjectId IS NOT NULL AND FunderId IS NULL)"));
            });

            b.Entity<EditorDocument>(e =>
            {
                e.HasOne(x => x.Project).WithMany().HasForeignKey(x => x.ProjectId).OnDelete(DeleteBehavior.Restrict);
                e.HasOne(x => x.Funder).WithMany().HasForeignKey(x => x.FunderId).OnDelete(DeleteBehavior.Restrict);
                e.HasOne(x => x.Template).WithMany().HasForeignKey(x => x.TemplateId).OnDelete(DeleteBehavior.Restrict);
            });

            b.Entity<DocumentVersion>(e =>
            {
                e.HasOne(x => x.EditorDocument).WithMany(d => d.Versions).HasForeignKey(x => x.EditorDocumentId).OnDelete(DeleteBehavior.Restrict);
                e.HasIndex(x => new { x.EditorDocumentId, x.Number }).IsUnique();
            });

            b.Entity<DocumentComment>(e =>
            {
                e.HasOne(x => x.EditorDocument).WithMany(d => d.Comments).HasForeignKey(x => x.EditorDocumentId).OnDelete(DeleteBehavior.Restrict);
                e.HasIndex(x => new { x.EditorDocumentId, x.AnchorId });
            });

            b.Entity<Indicator>(e =>
            {
                e.Property(x => x.Level).HasMaxLength(20).HasDefaultValue("Extrant");
                e.Property(x => x.Aggregation).HasMaxLength(20).HasDefaultValue("Somme");
            });

            b.Entity<IndicatorMeasurement>(e =>
            {
                e.HasOne(x => x.Indicator).WithMany(i => i.Measurements).HasForeignKey(x => x.IndicatorId).OnDelete(DeleteBehavior.Restrict);
                e.HasIndex(x => new { x.IndicatorId, x.PeriodEnd });
                e.ToTable(t => t.HasCheckConstraint("CK_IndicatorMeasurements_Sex", "Sex IN ('', 'F', 'M')"));
            });

            b.Entity<Photo>(e =>
            {
                e.HasOne(x => x.StoredFile).WithMany().HasForeignKey(x => x.StoredFileId).OnDelete(DeleteBehavior.Restrict);
                e.HasOne(x => x.Project).WithMany().HasForeignKey(x => x.ProjectId).OnDelete(DeleteBehavior.Restrict);
                e.HasOne(x => x.ProjectTask).WithMany().HasForeignKey(x => x.ProjectTaskId).OnDelete(DeleteBehavior.Restrict);
                e.HasOne(x => x.ActivityReport).WithMany().HasForeignKey(x => x.ActivityReportId).OnDelete(DeleteBehavior.Restrict);
                e.HasIndex(x => new { x.ProjectId, x.TakenAt });
            });
        }
    }
}
