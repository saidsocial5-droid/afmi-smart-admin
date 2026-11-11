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
        public DbSet<ReportingObligation> ReportingObligations { get; set; } = null!;
        public DbSet<ProjectMilestone> ProjectMilestones { get; set; } = null!;
        public DbSet<DocumentChunk> DocumentChunks { get; set; } = null!;
        public DbSet<Meeting> Meetings { get; set; } = null!;
        public DbSet<MeetingParticipant> MeetingParticipants { get; set; } = null!;
        public DbSet<MeetingResolution> MeetingResolutions { get; set; } = null!;
        public DbSet<MeetingAction> MeetingActions { get; set; } = null!;
        public DbSet<DocumentFolder> DocumentFolders { get; set; } = null!;

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

            b.Entity<ProjectDocument>(e =>
            {
                e.Property(x => x.DocType).HasMaxLength(50).HasDefaultValue("");
                e.Property(x => x.LifecyclePhase).HasMaxLength(30).HasDefaultValue("");
                e.Property(x => x.MetadataJson).HasDefaultValue("{}");
                e.Property(x => x.Language).HasMaxLength(5).HasDefaultValue("");
                e.HasOne(x => x.StoredFile).WithMany().HasForeignKey(x => x.StoredFileId).OnDelete(DeleteBehavior.Restrict);
            });

            b.Entity<ReportingObligation>(e =>
            {
                e.HasOne(x => x.Project).WithMany().HasForeignKey(x => x.ProjectId).OnDelete(DeleteBehavior.Restrict);
                e.HasOne(x => x.FundingAgreement).WithMany().HasForeignKey(x => x.FundingAgreementId).OnDelete(DeleteBehavior.Restrict);
                e.HasOne(x => x.DeliveredDocument).WithMany().HasForeignKey(x => x.DeliveredDocumentId).OnDelete(DeleteBehavior.Restrict);
                e.HasOne(x => x.SourceDocument).WithMany().HasForeignKey(x => x.SourceDocumentId).OnDelete(DeleteBehavior.Restrict);
                e.HasIndex(x => new { x.ProjectId, x.DueDate });
            });

            b.Entity<Meeting>(e =>
            {
                e.HasOne(x => x.Project).WithMany().HasForeignKey(x => x.ProjectId).OnDelete(DeleteBehavior.Restrict);
                e.HasOne(x => x.ProjectTask).WithMany().HasForeignKey(x => x.ProjectTaskId).OnDelete(DeleteBehavior.SetNull);
                e.HasOne(x => x.ActivityReport).WithMany().HasForeignKey(x => x.ActivityReportId).OnDelete(DeleteBehavior.SetNull);
                e.HasOne(x => x.EditorDocument).WithMany().HasForeignKey(x => x.EditorDocumentId).OnDelete(DeleteBehavior.Restrict);
                e.HasOne(x => x.ArchivedDocument).WithMany().HasForeignKey(x => x.ArchivedDocumentId).OnDelete(DeleteBehavior.Restrict);
                e.HasIndex(x => new { x.ProjectId, x.Date });
                e.ToTable(t => t.HasCheckConstraint("CK_Meetings_Kind", "Kind IN ('Réunion', 'COPIL', 'AG', 'CA', 'Rencontre', 'Visite', 'Activité')"));
            });
            b.Entity<MeetingParticipant>(e =>
            {
                e.HasOne(x => x.Meeting).WithMany(m => m.Participants).HasForeignKey(x => x.MeetingId).OnDelete(DeleteBehavior.Cascade);
                e.ToTable(t => t.HasCheckConstraint("CK_MeetingParticipants_Sex", "Sex IN ('', 'F', 'M')"));
            });
            b.Entity<MeetingResolution>(e => e.HasOne(x => x.Meeting).WithMany(m => m.Decisions).HasForeignKey(x => x.MeetingId).OnDelete(DeleteBehavior.Cascade));
            b.Entity<MeetingAction>(e =>
            {
                e.HasOne(x => x.Meeting).WithMany(m => m.Actions).HasForeignKey(x => x.MeetingId).OnDelete(DeleteBehavior.Cascade);
                e.HasOne(x => x.ProjectTask).WithMany().HasForeignKey(x => x.ProjectTaskId).OnDelete(DeleteBehavior.SetNull);
                e.HasIndex(x => new { x.Status, x.DueDate });
            });
            b.Entity<DocumentFolder>(e =>
            {
                e.HasOne(x => x.Parent).WithMany().HasForeignKey(x => x.ParentId).OnDelete(DeleteBehavior.Restrict);
                e.HasOne(x => x.Project).WithMany().HasForeignKey(x => x.ProjectId).OnDelete(DeleteBehavior.Restrict);
            });
            b.Entity<ProjectDocument>().HasOne(x => x.Folder).WithMany().HasForeignKey(x => x.FolderId).OnDelete(DeleteBehavior.SetNull);

            b.Entity<ProjectMilestone>(e =>
            {
                e.HasOne(x => x.Project).WithMany().HasForeignKey(x => x.ProjectId).OnDelete(DeleteBehavior.Restrict);
                e.HasOne(x => x.SourceDocument).WithMany().HasForeignKey(x => x.SourceDocumentId).OnDelete(DeleteBehavior.Restrict);
            });

            b.Entity<DocumentChunk>(e =>
            {
                e.HasOne(x => x.Document).WithMany().HasForeignKey(x => x.DocumentId).OnDelete(DeleteBehavior.Cascade);
                e.HasIndex(x => new { x.DocumentId, x.Ordinal });
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
