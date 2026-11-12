using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace AFMI_Gestion_projet.Data.Migrations
{
    /// <inheritdoc />
    public partial class DossierImport : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "Code",
                table: "Tasks",
                type: "TEXT",
                nullable: false,
                defaultValue: "");

            migrationBuilder.AddColumn<string>(
                name: "Code",
                table: "Indicators",
                type: "TEXT",
                nullable: false,
                defaultValue: "");

            migrationBuilder.AddColumn<int>(
                name: "LogframeNodeId",
                table: "Indicators",
                type: "INTEGER",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "MeansOfVerification",
                table: "Indicators",
                type: "TEXT",
                nullable: false,
                defaultValue: "");

            migrationBuilder.AddColumn<string>(
                name: "Condition",
                table: "FundingTranches",
                type: "TEXT",
                nullable: false,
                defaultValue: "");

            migrationBuilder.AddColumn<decimal>(
                name: "Percent",
                table: "FundingTranches",
                type: "TEXT",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "InKindTreatment",
                table: "Funders",
                type: "TEXT",
                maxLength: 20,
                nullable: false,
                defaultValue: "Suivi");

            migrationBuilder.AddColumn<string>(
                name: "ActivityCode",
                table: "BudgetLines",
                type: "TEXT",
                maxLength: 30,
                nullable: false,
                defaultValue: "");

            migrationBuilder.AddColumn<string>(
                name: "DonorCategory",
                table: "BudgetLines",
                type: "TEXT",
                maxLength: 150,
                nullable: false,
                defaultValue: "");

            migrationBuilder.AddColumn<int>(
                name: "SortOrder",
                table: "BudgetLines",
                type: "INTEGER",
                nullable: false,
                defaultValue: 0);

            migrationBuilder.CreateTable(
                name: "CofinancingContributions",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    ProjectId = table.Column<int>(type: "INTEGER", nullable: false),
                    FundingAgreementId = table.Column<int>(type: "INTEGER", nullable: true),
                    BudgetLineId = table.Column<int>(type: "INTEGER", nullable: true),
                    SourceType = table.Column<string>(type: "TEXT", maxLength: 30, nullable: false),
                    SourceName = table.Column<string>(type: "TEXT", maxLength: 150, nullable: false),
                    Nature = table.Column<string>(type: "TEXT", maxLength: 10, nullable: false),
                    Description = table.Column<string>(type: "TEXT", nullable: false),
                    PlannedMinor = table.Column<long>(type: "INTEGER", nullable: false),
                    Currency = table.Column<string>(type: "TEXT", maxLength: 3, nullable: false),
                    Commitment = table.Column<string>(type: "TEXT", maxLength: 10, nullable: false),
                    IsDeleted = table.Column<bool>(type: "INTEGER", nullable: false, defaultValue: false),
                    DeletedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_CofinancingContributions", x => x.Id);
                    table.CheckConstraint("CK_Cofinancing_Nature", "Nature IN ('Espèces', 'Nature')");
                    table.CheckConstraint("CK_Cofinancing_Planned", "PlannedMinor >= 0");
                    table.ForeignKey(
                        name: "FK_CofinancingContributions_BudgetLines_BudgetLineId",
                        column: x => x.BudgetLineId,
                        principalTable: "BudgetLines",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_CofinancingContributions_FundingAgreements_FundingAgreementId",
                        column: x => x.FundingAgreementId,
                        principalTable: "FundingAgreements",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_CofinancingContributions_Projects_ProjectId",
                        column: x => x.ProjectId,
                        principalTable: "Projects",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "DonorRules",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    FundingAgreementId = table.Column<int>(type: "INTEGER", nullable: false),
                    Kind = table.Column<string>(type: "TEXT", maxLength: 40, nullable: false),
                    Value = table.Column<decimal>(type: "TEXT", nullable: true),
                    Text = table.Column<string>(type: "TEXT", nullable: false),
                    SourceExcerpt = table.Column<string>(type: "TEXT", nullable: false),
                    IsDeleted = table.Column<bool>(type: "INTEGER", nullable: false, defaultValue: false),
                    DeletedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_DonorRules", x => x.Id);
                    table.ForeignKey(
                        name: "FK_DonorRules_FundingAgreements_FundingAgreementId",
                        column: x => x.FundingAgreementId,
                        principalTable: "FundingAgreements",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "LogframeNodes",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    ProjectId = table.Column<int>(type: "INTEGER", nullable: false),
                    ParentId = table.Column<int>(type: "INTEGER", nullable: true),
                    Level = table.Column<string>(type: "TEXT", maxLength: 30, nullable: false),
                    Code = table.Column<string>(type: "TEXT", maxLength: 30, nullable: false),
                    Statement = table.Column<string>(type: "TEXT", nullable: false),
                    SortOrder = table.Column<int>(type: "INTEGER", nullable: false),
                    IsDeleted = table.Column<bool>(type: "INTEGER", nullable: false, defaultValue: false),
                    DeletedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_LogframeNodes", x => x.Id);
                    table.CheckConstraint("CK_LogframeNodes_Level", "Level IN ('Objectif global', 'Objectif spécifique', 'Résultat', 'Produit')");
                    table.ForeignKey(
                        name: "FK_LogframeNodes_LogframeNodes_ParentId",
                        column: x => x.ParentId,
                        principalTable: "LogframeNodes",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_LogframeNodes_Projects_ProjectId",
                        column: x => x.ProjectId,
                        principalTable: "Projects",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "ProjectImports",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    ProjectId = table.Column<int>(type: "INTEGER", nullable: true),
                    CreatedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: false),
                    CreatedBy = table.Column<string>(type: "TEXT", maxLength: 150, nullable: false),
                    FilesJson = table.Column<string>(type: "TEXT", nullable: false),
                    ResultJson = table.Column<string>(type: "TEXT", nullable: false),
                    Engine = table.Column<string>(type: "TEXT", maxLength: 80, nullable: false),
                    Status = table.Column<string>(type: "TEXT", maxLength: 20, nullable: false),
                    AppliedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: true),
                    AppliedSummary = table.Column<string>(type: "TEXT", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_ProjectImports", x => x.Id);
                    table.ForeignKey(
                        name: "FK_ProjectImports_Projects_ProjectId",
                        column: x => x.ProjectId,
                        principalTable: "Projects",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.SetNull);
                });

            migrationBuilder.CreateTable(
                name: "ProjectRisks",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    ProjectId = table.Column<int>(type: "INTEGER", nullable: false),
                    Description = table.Column<string>(type: "TEXT", nullable: false),
                    Probability = table.Column<string>(type: "TEXT", maxLength: 20, nullable: false),
                    Impact = table.Column<string>(type: "TEXT", maxLength: 20, nullable: false),
                    Mitigation = table.Column<string>(type: "TEXT", nullable: false),
                    Owner = table.Column<string>(type: "TEXT", maxLength: 150, nullable: false),
                    Status = table.Column<string>(type: "TEXT", maxLength: 20, nullable: false),
                    IsDeleted = table.Column<bool>(type: "INTEGER", nullable: false, defaultValue: false),
                    DeletedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_ProjectRisks", x => x.Id);
                    table.ForeignKey(
                        name: "FK_ProjectRisks_Projects_ProjectId",
                        column: x => x.ProjectId,
                        principalTable: "Projects",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "CofinancingEntries",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    ContributionId = table.Column<int>(type: "INTEGER", nullable: false),
                    Date = table.Column<DateOnly>(type: "TEXT", nullable: false),
                    AmountMinor = table.Column<long>(type: "INTEGER", nullable: false),
                    Description = table.Column<string>(type: "TEXT", nullable: false),
                    Evidence = table.Column<string>(type: "TEXT", nullable: false),
                    CreatedBy = table.Column<string>(type: "TEXT", maxLength: 150, nullable: false),
                    CreatedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: false),
                    IsDeleted = table.Column<bool>(type: "INTEGER", nullable: false, defaultValue: false),
                    DeletedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_CofinancingEntries", x => x.Id);
                    table.CheckConstraint("CK_CofinancingEntries_Amount", "AmountMinor > 0");
                    table.ForeignKey(
                        name: "FK_CofinancingEntries_CofinancingContributions_ContributionId",
                        column: x => x.ContributionId,
                        principalTable: "CofinancingContributions",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateIndex(
                name: "IX_Indicators_LogframeNodeId",
                table: "Indicators",
                column: "LogframeNodeId");

            migrationBuilder.AddCheckConstraint(
                name: "CK_Funders_InKindTreatment",
                table: "Funders",
                sql: "InKindTreatment IN ('Suivi', 'Comptabilité')");

            migrationBuilder.CreateIndex(
                name: "IX_CofinancingContributions_BudgetLineId",
                table: "CofinancingContributions",
                column: "BudgetLineId");

            migrationBuilder.CreateIndex(
                name: "IX_CofinancingContributions_FundingAgreementId",
                table: "CofinancingContributions",
                column: "FundingAgreementId");

            migrationBuilder.CreateIndex(
                name: "IX_CofinancingContributions_ProjectId",
                table: "CofinancingContributions",
                column: "ProjectId");

            migrationBuilder.CreateIndex(
                name: "IX_CofinancingEntries_ContributionId",
                table: "CofinancingEntries",
                column: "ContributionId");

            migrationBuilder.CreateIndex(
                name: "IX_DonorRules_FundingAgreementId",
                table: "DonorRules",
                column: "FundingAgreementId");

            migrationBuilder.CreateIndex(
                name: "IX_LogframeNodes_ParentId",
                table: "LogframeNodes",
                column: "ParentId");

            migrationBuilder.CreateIndex(
                name: "IX_LogframeNodes_ProjectId_SortOrder",
                table: "LogframeNodes",
                columns: new[] { "ProjectId", "SortOrder" });

            migrationBuilder.CreateIndex(
                name: "IX_ProjectImports_ProjectId",
                table: "ProjectImports",
                column: "ProjectId");

            migrationBuilder.CreateIndex(
                name: "IX_ProjectRisks_ProjectId",
                table: "ProjectRisks",
                column: "ProjectId");

            migrationBuilder.AddForeignKey(
                name: "FK_Indicators_LogframeNodes_LogframeNodeId",
                table: "Indicators",
                column: "LogframeNodeId",
                principalTable: "LogframeNodes",
                principalColumn: "Id",
                onDelete: ReferentialAction.SetNull);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_Indicators_LogframeNodes_LogframeNodeId",
                table: "Indicators");

            migrationBuilder.DropTable(
                name: "CofinancingEntries");

            migrationBuilder.DropTable(
                name: "DonorRules");

            migrationBuilder.DropTable(
                name: "LogframeNodes");

            migrationBuilder.DropTable(
                name: "ProjectImports");

            migrationBuilder.DropTable(
                name: "ProjectRisks");

            migrationBuilder.DropTable(
                name: "CofinancingContributions");

            migrationBuilder.DropIndex(
                name: "IX_Indicators_LogframeNodeId",
                table: "Indicators");

            migrationBuilder.DropCheckConstraint(
                name: "CK_Funders_InKindTreatment",
                table: "Funders");

            migrationBuilder.DropColumn(
                name: "Code",
                table: "Tasks");

            migrationBuilder.DropColumn(
                name: "Code",
                table: "Indicators");

            migrationBuilder.DropColumn(
                name: "LogframeNodeId",
                table: "Indicators");

            migrationBuilder.DropColumn(
                name: "MeansOfVerification",
                table: "Indicators");

            migrationBuilder.DropColumn(
                name: "Condition",
                table: "FundingTranches");

            migrationBuilder.DropColumn(
                name: "Percent",
                table: "FundingTranches");

            migrationBuilder.DropColumn(
                name: "InKindTreatment",
                table: "Funders");

            migrationBuilder.DropColumn(
                name: "ActivityCode",
                table: "BudgetLines");

            migrationBuilder.DropColumn(
                name: "DonorCategory",
                table: "BudgetLines");

            migrationBuilder.DropColumn(
                name: "SortOrder",
                table: "BudgetLines");
        }
    }
}
