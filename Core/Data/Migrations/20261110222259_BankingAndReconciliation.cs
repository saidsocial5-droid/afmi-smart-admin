using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

#pragma warning disable CA1814 // Prefer jagged arrays over multidimensional

namespace AFMI_Gestion_projet.Data.Migrations
{
    /// <inheritdoc />
    public partial class BankingAndReconciliation : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<long>(
                name: "LowBalanceThresholdMinor",
                table: "BankAccounts",
                type: "INTEGER",
                nullable: true);

            migrationBuilder.CreateTable(
                name: "BankStatements",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    BankAccountId = table.Column<int>(type: "INTEGER", nullable: false),
                    PeriodStart = table.Column<DateOnly>(type: "TEXT", nullable: false),
                    PeriodEnd = table.Column<DateOnly>(type: "TEXT", nullable: false),
                    OpeningBalanceMinor = table.Column<long>(type: "INTEGER", nullable: false),
                    ClosingBalanceMinor = table.Column<long>(type: "INTEGER", nullable: false),
                    Source = table.Column<string>(type: "TEXT", maxLength: 30, nullable: false),
                    SourceFileId = table.Column<int>(type: "INTEGER", nullable: true),
                    Template = table.Column<string>(type: "TEXT", maxLength: 100, nullable: false),
                    Status = table.Column<string>(type: "TEXT", maxLength: 30, nullable: false),
                    ImportedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: false),
                    Notes = table.Column<string>(type: "TEXT", nullable: false),
                    IsDeleted = table.Column<bool>(type: "INTEGER", nullable: false, defaultValue: false),
                    DeletedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_BankStatements", x => x.Id);
                    table.CheckConstraint("CK_BankStatements_Period", "PeriodEnd >= PeriodStart");
                    table.ForeignKey(
                        name: "FK_BankStatements_BankAccounts_BankAccountId",
                        column: x => x.BankAccountId,
                        principalTable: "BankAccounts",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_BankStatements_StoredFiles_SourceFileId",
                        column: x => x.SourceFileId,
                        principalTable: "StoredFiles",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "StatementLines",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    BankStatementId = table.Column<int>(type: "INTEGER", nullable: false),
                    OperationDate = table.Column<DateOnly>(type: "TEXT", nullable: false),
                    ValueDate = table.Column<DateOnly>(type: "TEXT", nullable: true),
                    Label = table.Column<string>(type: "TEXT", maxLength: 500, nullable: false),
                    Reference = table.Column<string>(type: "TEXT", maxLength: 100, nullable: false),
                    DebitMinor = table.Column<long>(type: "INTEGER", nullable: false),
                    CreditMinor = table.Column<long>(type: "INTEGER", nullable: false),
                    ConfidenceJson = table.Column<string>(type: "TEXT", nullable: false),
                    SuggestedCategoryId = table.Column<int>(type: "INTEGER", nullable: true),
                    SuggestedProjectId = table.Column<int>(type: "INTEGER", nullable: true),
                    SuggestedBudgetLineId = table.Column<int>(type: "INTEGER", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_StatementLines", x => x.Id);
                    table.CheckConstraint("CK_StatementLines_Amounts", "DebitMinor >= 0 AND CreditMinor >= 0 AND (DebitMinor = 0 OR CreditMinor = 0) AND DebitMinor + CreditMinor > 0");
                    table.ForeignKey(
                        name: "FK_StatementLines_BankStatements_BankStatementId",
                        column: x => x.BankStatementId,
                        principalTable: "BankStatements",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "ReconciliationMatches",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    StatementLineId = table.Column<int>(type: "INTEGER", nullable: false),
                    OperationId = table.Column<int>(type: "INTEGER", nullable: false),
                    Mode = table.Column<string>(type: "TEXT", maxLength: 30, nullable: false),
                    Score = table.Column<double>(type: "REAL", nullable: false),
                    MatchedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: false),
                    MatchedBy = table.Column<string>(type: "TEXT", maxLength: 100, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_ReconciliationMatches", x => x.Id);
                    table.ForeignKey(
                        name: "FK_ReconciliationMatches_Operations_OperationId",
                        column: x => x.OperationId,
                        principalTable: "Operations",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_ReconciliationMatches_StatementLines_StatementLineId",
                        column: x => x.StatementLineId,
                        principalTable: "StatementLines",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.InsertData(
                table: "Categories",
                columns: new[] { "Id", "Code", "IsActive", "Kind", "Label", "LedgerAccountId", "ParentId" },
                values: new object[,]
                {
                    { 6, "PERS", true, "Expense", "Personnel (salaires et charges)", null, null },
                    { 7, "ACH", true, "Expense", "Achats et fournitures", null, null },
                    { 8, "HONO", true, "Expense", "Prestations et honoraires", null, null },
                    { 9, "DEPL", true, "Expense", "Déplacements et missions", null, null },
                    { 10, "LOC", true, "Expense", "Loyers et charges locatives", null, null },
                    { 11, "COM", true, "Expense", "Communication et publications", null, null },
                    { 12, "FBQ", true, "Expense", "Frais bancaires", null, null },
                    { 13, "EQP", true, "Expense", "Équipements", null, null },
                    { 14, "AUTD", true, "Expense", "Autres dépenses", null, null }
                });

            migrationBuilder.CreateIndex(
                name: "IX_BankStatements_BankAccountId_PeriodStart",
                table: "BankStatements",
                columns: new[] { "BankAccountId", "PeriodStart" });

            migrationBuilder.CreateIndex(
                name: "IX_BankStatements_SourceFileId",
                table: "BankStatements",
                column: "SourceFileId");

            migrationBuilder.CreateIndex(
                name: "IX_ReconciliationMatches_OperationId",
                table: "ReconciliationMatches",
                column: "OperationId",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_ReconciliationMatches_StatementLineId",
                table: "ReconciliationMatches",
                column: "StatementLineId",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_StatementLines_BankStatementId",
                table: "StatementLines",
                column: "BankStatementId");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "ReconciliationMatches");

            migrationBuilder.DropTable(
                name: "StatementLines");

            migrationBuilder.DropTable(
                name: "BankStatements");

            migrationBuilder.DeleteData(
                table: "Categories",
                keyColumn: "Id",
                keyValue: 6);

            migrationBuilder.DeleteData(
                table: "Categories",
                keyColumn: "Id",
                keyValue: 7);

            migrationBuilder.DeleteData(
                table: "Categories",
                keyColumn: "Id",
                keyValue: 8);

            migrationBuilder.DeleteData(
                table: "Categories",
                keyColumn: "Id",
                keyValue: 9);

            migrationBuilder.DeleteData(
                table: "Categories",
                keyColumn: "Id",
                keyValue: 10);

            migrationBuilder.DeleteData(
                table: "Categories",
                keyColumn: "Id",
                keyValue: 11);

            migrationBuilder.DeleteData(
                table: "Categories",
                keyColumn: "Id",
                keyValue: 12);

            migrationBuilder.DeleteData(
                table: "Categories",
                keyColumn: "Id",
                keyValue: 13);

            migrationBuilder.DeleteData(
                table: "Categories",
                keyColumn: "Id",
                keyValue: 14);

            migrationBuilder.DropColumn(
                name: "LowBalanceThresholdMinor",
                table: "BankAccounts");
        }
    }
}
