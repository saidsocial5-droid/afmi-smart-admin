using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace AFMI_Gestion_projet.Data.Migrations
{
    /// <inheritdoc />
    public partial class EditorChartsAndPhotos : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "DocumentTemplates",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    Name = table.Column<string>(type: "TEXT", maxLength: 200, nullable: false),
                    Description = table.Column<string>(type: "TEXT", nullable: false),
                    Kind = table.Column<string>(type: "TEXT", maxLength: 50, nullable: false),
                    ContentJson = table.Column<string>(type: "TEXT", nullable: false),
                    LayoutJson = table.Column<string>(type: "TEXT", nullable: false),
                    IsShared = table.Column<bool>(type: "INTEGER", nullable: false),
                    CreatedBy = table.Column<string>(type: "TEXT", maxLength: 100, nullable: false),
                    UpdatedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: false),
                    IsDeleted = table.Column<bool>(type: "INTEGER", nullable: false, defaultValue: false),
                    DeletedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_DocumentTemplates", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "GraphicCharts",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    Name = table.Column<string>(type: "TEXT", maxLength: 150, nullable: false),
                    Scope = table.Column<string>(type: "TEXT", maxLength: 30, nullable: false),
                    FunderId = table.Column<int>(type: "INTEGER", nullable: true),
                    ProjectId = table.Column<int>(type: "INTEGER", nullable: true),
                    StyleJson = table.Column<string>(type: "TEXT", nullable: false),
                    UpdatedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: false),
                    IsDeleted = table.Column<bool>(type: "INTEGER", nullable: false, defaultValue: false),
                    DeletedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_GraphicCharts", x => x.Id);
                    table.CheckConstraint("CK_GraphicCharts_Scope", "(Scope = 'Association' AND FunderId IS NULL AND ProjectId IS NULL) OR (Scope = 'Funder' AND FunderId IS NOT NULL AND ProjectId IS NULL) OR (Scope = 'Project' AND ProjectId IS NOT NULL AND FunderId IS NULL)");
                    table.ForeignKey(
                        name: "FK_GraphicCharts_Funders_FunderId",
                        column: x => x.FunderId,
                        principalTable: "Funders",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_GraphicCharts_Projects_ProjectId",
                        column: x => x.ProjectId,
                        principalTable: "Projects",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "Photos",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    StoredFileId = table.Column<int>(type: "INTEGER", nullable: false),
                    ProjectId = table.Column<int>(type: "INTEGER", nullable: true),
                    ProjectTaskId = table.Column<int>(type: "INTEGER", nullable: true),
                    ActivityReportId = table.Column<int>(type: "INTEGER", nullable: true),
                    TakenAt = table.Column<DateTime>(type: "TEXT", nullable: true),
                    Location = table.Column<string>(type: "TEXT", maxLength: 200, nullable: false),
                    Latitude = table.Column<double>(type: "REAL", nullable: true),
                    Longitude = table.Column<double>(type: "REAL", nullable: true),
                    Caption = table.Column<string>(type: "TEXT", maxLength: 500, nullable: false),
                    SuggestedCaption = table.Column<string>(type: "TEXT", maxLength: 500, nullable: false),
                    CaptionValidated = table.Column<bool>(type: "INTEGER", nullable: false),
                    Credit = table.Column<string>(type: "TEXT", maxLength: 150, nullable: false),
                    ConsentGiven = table.Column<bool>(type: "INTEGER", nullable: false),
                    Width = table.Column<int>(type: "INTEGER", nullable: false),
                    Height = table.Column<int>(type: "INTEGER", nullable: false),
                    ImportedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: false),
                    IsDeleted = table.Column<bool>(type: "INTEGER", nullable: false, defaultValue: false),
                    DeletedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Photos", x => x.Id);
                    table.ForeignKey(
                        name: "FK_Photos_ActivityReports_ActivityReportId",
                        column: x => x.ActivityReportId,
                        principalTable: "ActivityReports",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_Photos_Projects_ProjectId",
                        column: x => x.ProjectId,
                        principalTable: "Projects",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_Photos_StoredFiles_StoredFileId",
                        column: x => x.StoredFileId,
                        principalTable: "StoredFiles",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_Photos_Tasks_ProjectTaskId",
                        column: x => x.ProjectTaskId,
                        principalTable: "Tasks",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "EditorDocuments",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    Title = table.Column<string>(type: "TEXT", maxLength: 250, nullable: false),
                    ProjectId = table.Column<int>(type: "INTEGER", nullable: true),
                    FunderId = table.Column<int>(type: "INTEGER", nullable: true),
                    TemplateId = table.Column<int>(type: "INTEGER", nullable: true),
                    Language = table.Column<string>(type: "TEXT", maxLength: 5, nullable: false),
                    ContentJson = table.Column<string>(type: "TEXT", nullable: false),
                    LayoutJson = table.Column<string>(type: "TEXT", nullable: false),
                    CurrentVersion = table.Column<int>(type: "INTEGER", nullable: false),
                    Status = table.Column<string>(type: "TEXT", maxLength: 30, nullable: false),
                    CreatedBy = table.Column<string>(type: "TEXT", maxLength: 100, nullable: false),
                    CreatedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: false),
                    UpdatedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: false),
                    IsDeleted = table.Column<bool>(type: "INTEGER", nullable: false, defaultValue: false),
                    DeletedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_EditorDocuments", x => x.Id);
                    table.ForeignKey(
                        name: "FK_EditorDocuments_DocumentTemplates_TemplateId",
                        column: x => x.TemplateId,
                        principalTable: "DocumentTemplates",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_EditorDocuments_Funders_FunderId",
                        column: x => x.FunderId,
                        principalTable: "Funders",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_EditorDocuments_Projects_ProjectId",
                        column: x => x.ProjectId,
                        principalTable: "Projects",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "DocumentComments",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    EditorDocumentId = table.Column<int>(type: "INTEGER", nullable: false),
                    AnchorId = table.Column<string>(type: "TEXT", maxLength: 40, nullable: false),
                    ParentId = table.Column<int>(type: "INTEGER", nullable: true),
                    Text = table.Column<string>(type: "TEXT", nullable: false),
                    QuotedText = table.Column<string>(type: "TEXT", maxLength: 300, nullable: false),
                    Author = table.Column<string>(type: "TEXT", maxLength: 100, nullable: false),
                    CreatedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: false),
                    ResolvedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_DocumentComments", x => x.Id);
                    table.ForeignKey(
                        name: "FK_DocumentComments_EditorDocuments_EditorDocumentId",
                        column: x => x.EditorDocumentId,
                        principalTable: "EditorDocuments",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "DocumentVersions",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    EditorDocumentId = table.Column<int>(type: "INTEGER", nullable: false),
                    Number = table.Column<int>(type: "INTEGER", nullable: false),
                    ContentJson = table.Column<string>(type: "TEXT", nullable: false),
                    LayoutJson = table.Column<string>(type: "TEXT", nullable: false),
                    Note = table.Column<string>(type: "TEXT", maxLength: 300, nullable: false),
                    CreatedBy = table.Column<string>(type: "TEXT", maxLength: 100, nullable: false),
                    CreatedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_DocumentVersions", x => x.Id);
                    table.ForeignKey(
                        name: "FK_DocumentVersions_EditorDocuments_EditorDocumentId",
                        column: x => x.EditorDocumentId,
                        principalTable: "EditorDocuments",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateIndex(
                name: "IX_DocumentComments_EditorDocumentId_AnchorId",
                table: "DocumentComments",
                columns: new[] { "EditorDocumentId", "AnchorId" });

            migrationBuilder.CreateIndex(
                name: "IX_DocumentVersions_EditorDocumentId_Number",
                table: "DocumentVersions",
                columns: new[] { "EditorDocumentId", "Number" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_EditorDocuments_FunderId",
                table: "EditorDocuments",
                column: "FunderId");

            migrationBuilder.CreateIndex(
                name: "IX_EditorDocuments_ProjectId",
                table: "EditorDocuments",
                column: "ProjectId");

            migrationBuilder.CreateIndex(
                name: "IX_EditorDocuments_TemplateId",
                table: "EditorDocuments",
                column: "TemplateId");

            migrationBuilder.CreateIndex(
                name: "IX_GraphicCharts_FunderId",
                table: "GraphicCharts",
                column: "FunderId");

            migrationBuilder.CreateIndex(
                name: "IX_GraphicCharts_ProjectId",
                table: "GraphicCharts",
                column: "ProjectId");

            migrationBuilder.CreateIndex(
                name: "IX_Photos_ActivityReportId",
                table: "Photos",
                column: "ActivityReportId");

            migrationBuilder.CreateIndex(
                name: "IX_Photos_ProjectId_TakenAt",
                table: "Photos",
                columns: new[] { "ProjectId", "TakenAt" });

            migrationBuilder.CreateIndex(
                name: "IX_Photos_ProjectTaskId",
                table: "Photos",
                column: "ProjectTaskId");

            migrationBuilder.CreateIndex(
                name: "IX_Photos_StoredFileId",
                table: "Photos",
                column: "StoredFileId");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "DocumentComments");

            migrationBuilder.DropTable(
                name: "DocumentVersions");

            migrationBuilder.DropTable(
                name: "GraphicCharts");

            migrationBuilder.DropTable(
                name: "Photos");

            migrationBuilder.DropTable(
                name: "EditorDocuments");

            migrationBuilder.DropTable(
                name: "DocumentTemplates");
        }
    }
}
