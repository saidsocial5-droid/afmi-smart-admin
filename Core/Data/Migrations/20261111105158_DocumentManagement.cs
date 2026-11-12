using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace AFMI_Gestion_projet.Data.Migrations
{
    /// <inheritdoc />
    public partial class DocumentManagement : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<double>(
                name: "ClassificationConfidence",
                table: "Documents",
                type: "REAL",
                nullable: false,
                defaultValue: 0.0);

            migrationBuilder.AddColumn<DateTime>(
                name: "DeletedAtUtc",
                table: "Documents",
                type: "TEXT",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "DocType",
                table: "Documents",
                type: "TEXT",
                maxLength: 50,
                nullable: false,
                defaultValue: "");

            migrationBuilder.AddColumn<DateTime>(
                name: "IndexedAtUtc",
                table: "Documents",
                type: "TEXT",
                nullable: true);

            migrationBuilder.AddColumn<bool>(
                name: "IsDeleted",
                table: "Documents",
                type: "INTEGER",
                nullable: false,
                defaultValue: false);

            migrationBuilder.AddColumn<string>(
                name: "Language",
                table: "Documents",
                type: "TEXT",
                maxLength: 5,
                nullable: false,
                defaultValue: "");

            migrationBuilder.AddColumn<string>(
                name: "LifecyclePhase",
                table: "Documents",
                type: "TEXT",
                maxLength: 30,
                nullable: false,
                defaultValue: "");

            migrationBuilder.AddColumn<string>(
                name: "MetadataJson",
                table: "Documents",
                type: "TEXT",
                nullable: false,
                defaultValue: "{}");

            migrationBuilder.AddColumn<int>(
                name: "StoredFileId",
                table: "Documents",
                type: "INTEGER",
                nullable: true);

            migrationBuilder.CreateTable(
                name: "DocumentChunks",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    DocumentId = table.Column<int>(type: "INTEGER", nullable: false),
                    Ordinal = table.Column<int>(type: "INTEGER", nullable: false),
                    Page = table.Column<int>(type: "INTEGER", nullable: true),
                    Text = table.Column<string>(type: "TEXT", nullable: false),
                    Embedding = table.Column<byte[]>(type: "BLOB", nullable: true),
                    EmbeddingModel = table.Column<string>(type: "TEXT", maxLength: 100, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_DocumentChunks", x => x.Id);
                    table.ForeignKey(
                        name: "FK_DocumentChunks_Documents_DocumentId",
                        column: x => x.DocumentId,
                        principalTable: "Documents",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "ProjectMilestones",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    ProjectId = table.Column<int>(type: "INTEGER", nullable: false),
                    Title = table.Column<string>(type: "TEXT", maxLength: 250, nullable: false),
                    Date = table.Column<DateOnly>(type: "TEXT", nullable: false),
                    Phase = table.Column<string>(type: "TEXT", maxLength: 30, nullable: false),
                    Done = table.Column<bool>(type: "INTEGER", nullable: false),
                    SourceDocumentId = table.Column<int>(type: "INTEGER", nullable: true),
                    IsDeleted = table.Column<bool>(type: "INTEGER", nullable: false, defaultValue: false),
                    DeletedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_ProjectMilestones", x => x.Id);
                    table.ForeignKey(
                        name: "FK_ProjectMilestones_Documents_SourceDocumentId",
                        column: x => x.SourceDocumentId,
                        principalTable: "Documents",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_ProjectMilestones_Projects_ProjectId",
                        column: x => x.ProjectId,
                        principalTable: "Projects",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "ReportingObligations",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    ProjectId = table.Column<int>(type: "INTEGER", nullable: false),
                    FundingAgreementId = table.Column<int>(type: "INTEGER", nullable: true),
                    Title = table.Column<string>(type: "TEXT", maxLength: 250, nullable: false),
                    Kind = table.Column<string>(type: "TEXT", maxLength: 50, nullable: false),
                    DueDate = table.Column<DateOnly>(type: "TEXT", nullable: false),
                    Status = table.Column<string>(type: "TEXT", maxLength: 20, nullable: false),
                    DeliveredDocumentId = table.Column<int>(type: "INTEGER", nullable: true),
                    SourceDocumentId = table.Column<int>(type: "INTEGER", nullable: true),
                    SourceExcerpt = table.Column<string>(type: "TEXT", nullable: false),
                    Notes = table.Column<string>(type: "TEXT", nullable: false),
                    IsDeleted = table.Column<bool>(type: "INTEGER", nullable: false, defaultValue: false),
                    DeletedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_ReportingObligations", x => x.Id);
                    table.ForeignKey(
                        name: "FK_ReportingObligations_Documents_DeliveredDocumentId",
                        column: x => x.DeliveredDocumentId,
                        principalTable: "Documents",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_ReportingObligations_Documents_SourceDocumentId",
                        column: x => x.SourceDocumentId,
                        principalTable: "Documents",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_ReportingObligations_FundingAgreements_FundingAgreementId",
                        column: x => x.FundingAgreementId,
                        principalTable: "FundingAgreements",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_ReportingObligations_Projects_ProjectId",
                        column: x => x.ProjectId,
                        principalTable: "Projects",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateIndex(
                name: "IX_Documents_StoredFileId",
                table: "Documents",
                column: "StoredFileId");

            migrationBuilder.CreateIndex(
                name: "IX_DocumentChunks_DocumentId_Ordinal",
                table: "DocumentChunks",
                columns: new[] { "DocumentId", "Ordinal" });

            migrationBuilder.CreateIndex(
                name: "IX_ProjectMilestones_ProjectId",
                table: "ProjectMilestones",
                column: "ProjectId");

            migrationBuilder.CreateIndex(
                name: "IX_ProjectMilestones_SourceDocumentId",
                table: "ProjectMilestones",
                column: "SourceDocumentId");

            migrationBuilder.CreateIndex(
                name: "IX_ReportingObligations_DeliveredDocumentId",
                table: "ReportingObligations",
                column: "DeliveredDocumentId");

            migrationBuilder.CreateIndex(
                name: "IX_ReportingObligations_FundingAgreementId",
                table: "ReportingObligations",
                column: "FundingAgreementId");

            migrationBuilder.CreateIndex(
                name: "IX_ReportingObligations_ProjectId_DueDate",
                table: "ReportingObligations",
                columns: new[] { "ProjectId", "DueDate" });

            migrationBuilder.CreateIndex(
                name: "IX_ReportingObligations_SourceDocumentId",
                table: "ReportingObligations",
                column: "SourceDocumentId");

            migrationBuilder.AddForeignKey(
                name: "FK_Documents_StoredFiles_StoredFileId",
                table: "Documents",
                column: "StoredFileId",
                principalTable: "StoredFiles",
                principalColumn: "Id",
                onDelete: ReferentialAction.Restrict);

            // Reprise des documents existants : anciennes catégories et phases → types et phases du cycle de vie (Lot 6).
            migrationBuilder.Sql(@"UPDATE Documents SET DocType = CASE Category
                    WHEN 'Convention Bailleur' THEN 'Convention' WHEN 'Dossier Projet' THEN 'Document de projet'
                    WHEN 'Budget Initial' THEN 'Budget' WHEN 'Étude de Diagnostic' THEN 'Étude ou diagnostic'
                    WHEN 'Cadre Logique' THEN 'Cadre logique' WHEN 'Avenant' THEN 'Avenant' ELSE 'Autre' END,
                LifecyclePhase = CASE DocumentPhase
                    WHEN 'Diagnostic' THEN 'Identification' WHEN 'Montage' THEN 'Formulation' WHEN 'Rédaction' THEN 'Formulation'
                    WHEN 'Exécution' THEN 'Mise en œuvre' WHEN 'Évaluation' THEN 'Évaluation' WHEN 'Clôture' THEN 'Clôture' ELSE 'Formulation' END,
                ClassificationConfidence = 100
                WHERE DocType = '';");

            // Index plein texte (SQLite FTS5) des passages de documents, synchronisé par déclencheurs.
            migrationBuilder.Sql(@"CREATE VIRTUAL TABLE DocumentChunksFts USING fts5(Text, content='DocumentChunks', content_rowid='Id',
                tokenize='unicode61 remove_diacritics 2');");
            migrationBuilder.Sql(@"CREATE TRIGGER TR_DocumentChunks_Ai AFTER INSERT ON DocumentChunks BEGIN
                INSERT INTO DocumentChunksFts(rowid, Text) VALUES (new.Id, new.Text); END;");
            migrationBuilder.Sql(@"CREATE TRIGGER TR_DocumentChunks_Ad AFTER DELETE ON DocumentChunks BEGIN
                INSERT INTO DocumentChunksFts(DocumentChunksFts, rowid, Text) VALUES ('delete', old.Id, old.Text); END;");
            migrationBuilder.Sql(@"CREATE TRIGGER TR_DocumentChunks_Au AFTER UPDATE OF Text ON DocumentChunks BEGIN
                INSERT INTO DocumentChunksFts(DocumentChunksFts, rowid, Text) VALUES ('delete', old.Id, old.Text);
                INSERT INTO DocumentChunksFts(rowid, Text) VALUES (new.Id, new.Text); END;");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql("DROP TRIGGER IF EXISTS TR_DocumentChunks_Ai;");
            migrationBuilder.Sql("DROP TRIGGER IF EXISTS TR_DocumentChunks_Ad;");
            migrationBuilder.Sql("DROP TRIGGER IF EXISTS TR_DocumentChunks_Au;");
            migrationBuilder.Sql("DROP TABLE IF EXISTS DocumentChunksFts;");
            migrationBuilder.DropForeignKey(
                name: "FK_Documents_StoredFiles_StoredFileId",
                table: "Documents");

            migrationBuilder.DropTable(
                name: "DocumentChunks");

            migrationBuilder.DropTable(
                name: "ProjectMilestones");

            migrationBuilder.DropTable(
                name: "ReportingObligations");

            migrationBuilder.DropIndex(
                name: "IX_Documents_StoredFileId",
                table: "Documents");

            migrationBuilder.DropColumn(
                name: "ClassificationConfidence",
                table: "Documents");

            migrationBuilder.DropColumn(
                name: "DeletedAtUtc",
                table: "Documents");

            migrationBuilder.DropColumn(
                name: "DocType",
                table: "Documents");

            migrationBuilder.DropColumn(
                name: "IndexedAtUtc",
                table: "Documents");

            migrationBuilder.DropColumn(
                name: "IsDeleted",
                table: "Documents");

            migrationBuilder.DropColumn(
                name: "Language",
                table: "Documents");

            migrationBuilder.DropColumn(
                name: "LifecyclePhase",
                table: "Documents");

            migrationBuilder.DropColumn(
                name: "MetadataJson",
                table: "Documents");

            migrationBuilder.DropColumn(
                name: "StoredFileId",
                table: "Documents");
        }
    }
}
