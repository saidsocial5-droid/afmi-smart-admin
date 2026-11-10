using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

#pragma warning disable CA1814 // Prefer jagged arrays over multidimensional

namespace AFMI_Gestion_projet.Data.Migrations
{
    /// <inheritdoc />
    public partial class FinanceFoundation : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "Currency",
                table: "Projects",
                type: "TEXT",
                maxLength: 3,
                nullable: false,
                defaultValue: "MAD");

            migrationBuilder.AddColumn<DateTime>(
                name: "DeletedAtUtc",
                table: "Projects",
                type: "TEXT",
                nullable: true);

            migrationBuilder.AddColumn<bool>(
                name: "IsDeleted",
                table: "Projects",
                type: "INTEGER",
                nullable: false,
                defaultValue: false);

            migrationBuilder.AddColumn<DateTime>(
                name: "DeletedAtUtc",
                table: "CostEntries",
                type: "TEXT",
                nullable: true);

            migrationBuilder.AddColumn<bool>(
                name: "IsDeleted",
                table: "CostEntries",
                type: "INTEGER",
                nullable: false,
                defaultValue: false);

            migrationBuilder.CreateTable(
                name: "AppSettings",
                columns: table => new
                {
                    Key = table.Column<string>(type: "TEXT", maxLength: 150, nullable: false),
                    ValueJson = table.Column<string>(type: "TEXT", nullable: false),
                    IsSecret = table.Column<bool>(type: "INTEGER", nullable: false),
                    UpdatedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_AppSettings", x => x.Key);
                });

            migrationBuilder.CreateTable(
                name: "AuditEntries",
                columns: table => new
                {
                    Id = table.Column<long>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    TimestampUtc = table.Column<DateTime>(type: "TEXT", nullable: false),
                    User = table.Column<string>(type: "TEXT", maxLength: 100, nullable: false),
                    Machine = table.Column<string>(type: "TEXT", maxLength: 100, nullable: false),
                    EntityType = table.Column<string>(type: "TEXT", maxLength: 100, nullable: false),
                    EntityId = table.Column<string>(type: "TEXT", maxLength: 100, nullable: false),
                    Action = table.Column<string>(type: "TEXT", maxLength: 30, nullable: false),
                    ChangesJson = table.Column<string>(type: "TEXT", nullable: false),
                    PreviousHash = table.Column<string>(type: "TEXT", maxLength: 64, nullable: false),
                    Hash = table.Column<string>(type: "TEXT", maxLength: 64, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_AuditEntries", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "BankAccounts",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    Kind = table.Column<string>(type: "TEXT", maxLength: 30, nullable: false),
                    Purpose = table.Column<string>(type: "TEXT", maxLength: 30, nullable: false),
                    BankName = table.Column<string>(type: "TEXT", maxLength: 150, nullable: false),
                    Branch = table.Column<string>(type: "TEXT", maxLength: 150, nullable: false),
                    Title = table.Column<string>(type: "TEXT", maxLength: 200, nullable: false),
                    Rib = table.Column<string>(type: "TEXT", maxLength: 24, nullable: true),
                    Currency = table.Column<string>(type: "TEXT", maxLength: 3, nullable: false),
                    OpeningBalanceMinor = table.Column<long>(type: "INTEGER", nullable: false),
                    OpeningDate = table.Column<DateOnly>(type: "TEXT", nullable: false),
                    Status = table.Column<string>(type: "TEXT", maxLength: 30, nullable: false),
                    ClosedDate = table.Column<DateOnly>(type: "TEXT", nullable: true),
                    Notes = table.Column<string>(type: "TEXT", nullable: false),
                    IsDeleted = table.Column<bool>(type: "INTEGER", nullable: false, defaultValue: false),
                    DeletedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_BankAccounts", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "CurrencyRates",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    Currency = table.Column<string>(type: "TEXT", maxLength: 3, nullable: false),
                    Date = table.Column<DateOnly>(type: "TEXT", nullable: false),
                    RateToMad = table.Column<decimal>(type: "TEXT", nullable: false),
                    Source = table.Column<string>(type: "TEXT", maxLength: 100, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_CurrencyRates", x => x.Id);
                    table.CheckConstraint("CK_CurrencyRates_Positive", "CAST(RateToMad AS REAL) > 0");
                });

            migrationBuilder.CreateTable(
                name: "FiscalYears",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    Year = table.Column<int>(type: "INTEGER", nullable: false),
                    StartDate = table.Column<DateOnly>(type: "TEXT", nullable: false),
                    EndDate = table.Column<DateOnly>(type: "TEXT", nullable: false),
                    Status = table.Column<string>(type: "TEXT", maxLength: 30, nullable: false),
                    ClosedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_FiscalYears", x => x.Id);
                    table.CheckConstraint("CK_FiscalYears_Dates", "EndDate >= StartDate");
                });

            migrationBuilder.CreateTable(
                name: "FundingAgreements",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    FunderId = table.Column<int>(type: "INTEGER", nullable: false),
                    ProjectId = table.Column<int>(type: "INTEGER", nullable: false),
                    Reference = table.Column<string>(type: "TEXT", maxLength: 100, nullable: false),
                    Title = table.Column<string>(type: "TEXT", maxLength: 250, nullable: false),
                    AmountMinor = table.Column<long>(type: "INTEGER", nullable: false),
                    Currency = table.Column<string>(type: "TEXT", maxLength: 3, nullable: false),
                    ContractualRateToMad = table.Column<decimal>(type: "TEXT", nullable: true),
                    SignatureDate = table.Column<DateOnly>(type: "TEXT", nullable: true),
                    StartDate = table.Column<DateOnly>(type: "TEXT", nullable: true),
                    EndDate = table.Column<DateOnly>(type: "TEXT", nullable: true),
                    Notes = table.Column<string>(type: "TEXT", nullable: false),
                    IsDeleted = table.Column<bool>(type: "INTEGER", nullable: false, defaultValue: false),
                    DeletedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_FundingAgreements", x => x.Id);
                    table.CheckConstraint("CK_FundingAgreements_Amount", "AmountMinor >= 0");
                    table.ForeignKey(
                        name: "FK_FundingAgreements_Funders_FunderId",
                        column: x => x.FunderId,
                        principalTable: "Funders",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_FundingAgreements_Projects_ProjectId",
                        column: x => x.ProjectId,
                        principalTable: "Projects",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "LedgerAccounts",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    Code = table.Column<string>(type: "TEXT", maxLength: 20, nullable: false),
                    Label = table.Column<string>(type: "TEXT", maxLength: 200, nullable: false),
                    Type = table.Column<string>(type: "TEXT", maxLength: 30, nullable: false),
                    ParentId = table.Column<int>(type: "INTEGER", nullable: true),
                    IsActive = table.Column<bool>(type: "INTEGER", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_LedgerAccounts", x => x.Id);
                    table.ForeignKey(
                        name: "FK_LedgerAccounts_LedgerAccounts_ParentId",
                        column: x => x.ParentId,
                        principalTable: "LedgerAccounts",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "StoredFiles",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    Sha256 = table.Column<string>(type: "TEXT", maxLength: 64, nullable: false),
                    RelativePath = table.Column<string>(type: "TEXT", maxLength: 500, nullable: false),
                    OriginalName = table.Column<string>(type: "TEXT", maxLength: 255, nullable: false),
                    MimeType = table.Column<string>(type: "TEXT", maxLength: 100, nullable: false),
                    SizeBytes = table.Column<long>(type: "INTEGER", nullable: false),
                    ImportedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_StoredFiles", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "AccountProjectLinks",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    BankAccountId = table.Column<int>(type: "INTEGER", nullable: false),
                    ProjectId = table.Column<int>(type: "INTEGER", nullable: false),
                    ValidFrom = table.Column<DateOnly>(type: "TEXT", nullable: false),
                    ValidTo = table.Column<DateOnly>(type: "TEXT", nullable: true),
                    AllocationMode = table.Column<string>(type: "TEXT", maxLength: 30, nullable: false),
                    AllocationPercent = table.Column<decimal>(type: "TEXT", nullable: true),
                    AllocationAmountMinor = table.Column<long>(type: "INTEGER", nullable: true),
                    IsDeleted = table.Column<bool>(type: "INTEGER", nullable: false, defaultValue: false),
                    DeletedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_AccountProjectLinks", x => x.Id);
                    table.ForeignKey(
                        name: "FK_AccountProjectLinks_BankAccounts_BankAccountId",
                        column: x => x.BankAccountId,
                        principalTable: "BankAccounts",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_AccountProjectLinks_Projects_ProjectId",
                        column: x => x.ProjectId,
                        principalTable: "Projects",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "Operations",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    BankAccountId = table.Column<int>(type: "INTEGER", nullable: false),
                    OperationDate = table.Column<DateOnly>(type: "TEXT", nullable: false),
                    ValueDate = table.Column<DateOnly>(type: "TEXT", nullable: true),
                    Label = table.Column<string>(type: "TEXT", maxLength: 500, nullable: false),
                    Reference = table.Column<string>(type: "TEXT", maxLength: 100, nullable: false),
                    ThirdParty = table.Column<string>(type: "TEXT", maxLength: 200, nullable: false),
                    Direction = table.Column<string>(type: "TEXT", maxLength: 30, nullable: false),
                    Nature = table.Column<string>(type: "TEXT", maxLength: 30, nullable: false),
                    AmountMinor = table.Column<long>(type: "INTEGER", nullable: false),
                    Currency = table.Column<string>(type: "TEXT", maxLength: 3, nullable: false),
                    RateToMad = table.Column<decimal>(type: "TEXT", nullable: true),
                    AmountMadMinor = table.Column<long>(type: "INTEGER", nullable: false),
                    TransferGroupId = table.Column<Guid>(type: "TEXT", nullable: true),
                    Status = table.Column<string>(type: "TEXT", maxLength: 30, nullable: false),
                    ValidatedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: true),
                    ValidatedBy = table.Column<string>(type: "TEXT", maxLength: 100, nullable: false),
                    Notes = table.Column<string>(type: "TEXT", nullable: false),
                    IsDeleted = table.Column<bool>(type: "INTEGER", nullable: false, defaultValue: false),
                    DeletedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Operations", x => x.Id);
                    table.CheckConstraint("CK_Operations_Amount", "AmountMinor > 0 AND AmountMadMinor >= 0");
                    table.CheckConstraint("CK_Operations_Transfer", "(Nature = 'InternalTransfer' AND TransferGroupId IS NOT NULL) OR (Nature <> 'InternalTransfer' AND TransferGroupId IS NULL)");
                    table.ForeignKey(
                        name: "FK_Operations_BankAccounts_BankAccountId",
                        column: x => x.BankAccountId,
                        principalTable: "BankAccounts",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "Categories",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    Kind = table.Column<string>(type: "TEXT", maxLength: 30, nullable: false),
                    Code = table.Column<string>(type: "TEXT", maxLength: 30, nullable: false),
                    Label = table.Column<string>(type: "TEXT", maxLength: 200, nullable: false),
                    ParentId = table.Column<int>(type: "INTEGER", nullable: true),
                    LedgerAccountId = table.Column<int>(type: "INTEGER", nullable: true),
                    IsActive = table.Column<bool>(type: "INTEGER", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_Categories", x => x.Id);
                    table.ForeignKey(
                        name: "FK_Categories_Categories_ParentId",
                        column: x => x.ParentId,
                        principalTable: "Categories",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_Categories_LedgerAccounts_LedgerAccountId",
                        column: x => x.LedgerAccountId,
                        principalTable: "LedgerAccounts",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "FundingTranches",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    FundingAgreementId = table.Column<int>(type: "INTEGER", nullable: false),
                    Label = table.Column<string>(type: "TEXT", maxLength: 100, nullable: false),
                    ExpectedDate = table.Column<DateOnly>(type: "TEXT", nullable: false),
                    AmountMinor = table.Column<long>(type: "INTEGER", nullable: false),
                    ReceivedOperationId = table.Column<int>(type: "INTEGER", nullable: true),
                    IsDeleted = table.Column<bool>(type: "INTEGER", nullable: false, defaultValue: false),
                    DeletedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_FundingTranches", x => x.Id);
                    table.CheckConstraint("CK_FundingTranches_Amount", "AmountMinor >= 0");
                    table.ForeignKey(
                        name: "FK_FundingTranches_FundingAgreements_FundingAgreementId",
                        column: x => x.FundingAgreementId,
                        principalTable: "FundingAgreements",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_FundingTranches_Operations_ReceivedOperationId",
                        column: x => x.ReceivedOperationId,
                        principalTable: "Operations",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "OperationAttachments",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    OperationId = table.Column<int>(type: "INTEGER", nullable: false),
                    StoredFileId = table.Column<int>(type: "INTEGER", nullable: true),
                    ProjectDocumentId = table.Column<int>(type: "INTEGER", nullable: true),
                    Label = table.Column<string>(type: "TEXT", maxLength: 200, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_OperationAttachments", x => x.Id);
                    table.ForeignKey(
                        name: "FK_OperationAttachments_Documents_ProjectDocumentId",
                        column: x => x.ProjectDocumentId,
                        principalTable: "Documents",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_OperationAttachments_Operations_OperationId",
                        column: x => x.OperationId,
                        principalTable: "Operations",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "FK_OperationAttachments_StoredFiles_StoredFileId",
                        column: x => x.StoredFileId,
                        principalTable: "StoredFiles",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "BudgetLines",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    ProjectId = table.Column<int>(type: "INTEGER", nullable: true),
                    FundingAgreementId = table.Column<int>(type: "INTEGER", nullable: true),
                    FiscalYearId = table.Column<int>(type: "INTEGER", nullable: true),
                    Code = table.Column<string>(type: "TEXT", maxLength: 30, nullable: false),
                    Label = table.Column<string>(type: "TEXT", maxLength: 250, nullable: false),
                    CategoryId = table.Column<int>(type: "INTEGER", nullable: true),
                    PlannedMinor = table.Column<long>(type: "INTEGER", nullable: false),
                    Currency = table.Column<string>(type: "TEXT", maxLength: 3, nullable: false),
                    IsDeleted = table.Column<bool>(type: "INTEGER", nullable: false, defaultValue: false),
                    DeletedAtUtc = table.Column<DateTime>(type: "TEXT", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_BudgetLines", x => x.Id);
                    table.CheckConstraint("CK_BudgetLines_Planned", "PlannedMinor >= 0");
                    table.ForeignKey(
                        name: "FK_BudgetLines_Categories_CategoryId",
                        column: x => x.CategoryId,
                        principalTable: "Categories",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_BudgetLines_FiscalYears_FiscalYearId",
                        column: x => x.FiscalYearId,
                        principalTable: "FiscalYears",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_BudgetLines_FundingAgreements_FundingAgreementId",
                        column: x => x.FundingAgreementId,
                        principalTable: "FundingAgreements",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_BudgetLines_Projects_ProjectId",
                        column: x => x.ProjectId,
                        principalTable: "Projects",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "CategorizationRules",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    Pattern = table.Column<string>(type: "TEXT", maxLength: 300, nullable: false),
                    MatchType = table.Column<string>(type: "TEXT", maxLength: 30, nullable: false),
                    Direction = table.Column<string>(type: "TEXT", maxLength: 30, nullable: true),
                    CategoryId = table.Column<int>(type: "INTEGER", nullable: true),
                    ProjectId = table.Column<int>(type: "INTEGER", nullable: true),
                    BudgetLineId = table.Column<int>(type: "INTEGER", nullable: true),
                    Source = table.Column<string>(type: "TEXT", maxLength: 30, nullable: false),
                    Priority = table.Column<int>(type: "INTEGER", nullable: false),
                    HitCount = table.Column<int>(type: "INTEGER", nullable: false),
                    IsActive = table.Column<bool>(type: "INTEGER", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_CategorizationRules", x => x.Id);
                    table.ForeignKey(
                        name: "FK_CategorizationRules_Categories_CategoryId",
                        column: x => x.CategoryId,
                        principalTable: "Categories",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "OperationAllocations",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    OperationId = table.Column<int>(type: "INTEGER", nullable: false),
                    ProjectId = table.Column<int>(type: "INTEGER", nullable: true),
                    BudgetLineId = table.Column<int>(type: "INTEGER", nullable: true),
                    CategoryId = table.Column<int>(type: "INTEGER", nullable: true),
                    AmountMinor = table.Column<long>(type: "INTEGER", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_OperationAllocations", x => x.Id);
                    table.CheckConstraint("CK_OperationAllocations_Amount", "AmountMinor > 0");
                    table.ForeignKey(
                        name: "FK_OperationAllocations_BudgetLines_BudgetLineId",
                        column: x => x.BudgetLineId,
                        principalTable: "BudgetLines",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_OperationAllocations_Categories_CategoryId",
                        column: x => x.CategoryId,
                        principalTable: "Categories",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "FK_OperationAllocations_Operations_OperationId",
                        column: x => x.OperationId,
                        principalTable: "Operations",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "FK_OperationAllocations_Projects_ProjectId",
                        column: x => x.ProjectId,
                        principalTable: "Projects",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.InsertData(
                table: "Categories",
                columns: new[] { "Id", "Code", "IsActive", "Kind", "Label", "LedgerAccountId", "ParentId" },
                values: new object[,]
                {
                    { 1, "SUBV", true, "Income", "Subventions", null, null },
                    { 2, "COTIS", true, "Income", "Cotisations", null, null },
                    { 3, "DONS", true, "Income", "Dons", null, null },
                    { 4, "PREST", true, "Income", "Prestations", null, null },
                    { 5, "PFIN", true, "Income", "Produits financiers", null, null }
                });

            migrationBuilder.CreateIndex(
                name: "IX_AccountProjectLinks_BankAccountId_ProjectId",
                table: "AccountProjectLinks",
                columns: new[] { "BankAccountId", "ProjectId" });

            migrationBuilder.CreateIndex(
                name: "IX_AccountProjectLinks_ProjectId",
                table: "AccountProjectLinks",
                column: "ProjectId");

            migrationBuilder.CreateIndex(
                name: "IX_AuditEntries_EntityType_EntityId",
                table: "AuditEntries",
                columns: new[] { "EntityType", "EntityId" });

            migrationBuilder.CreateIndex(
                name: "IX_AuditEntries_TimestampUtc",
                table: "AuditEntries",
                column: "TimestampUtc");

            migrationBuilder.CreateIndex(
                name: "IX_BankAccounts_Rib",
                table: "BankAccounts",
                column: "Rib",
                unique: true,
                filter: "Rib IS NOT NULL AND IsDeleted = 0");

            migrationBuilder.CreateIndex(
                name: "IX_BudgetLines_CategoryId",
                table: "BudgetLines",
                column: "CategoryId");

            migrationBuilder.CreateIndex(
                name: "IX_BudgetLines_FiscalYearId",
                table: "BudgetLines",
                column: "FiscalYearId");

            migrationBuilder.CreateIndex(
                name: "IX_BudgetLines_FundingAgreementId",
                table: "BudgetLines",
                column: "FundingAgreementId");

            migrationBuilder.CreateIndex(
                name: "IX_BudgetLines_ProjectId",
                table: "BudgetLines",
                column: "ProjectId");

            migrationBuilder.CreateIndex(
                name: "IX_Categories_Kind_Code",
                table: "Categories",
                columns: new[] { "Kind", "Code" });

            migrationBuilder.CreateIndex(
                name: "IX_Categories_LedgerAccountId",
                table: "Categories",
                column: "LedgerAccountId");

            migrationBuilder.CreateIndex(
                name: "IX_Categories_ParentId",
                table: "Categories",
                column: "ParentId");

            migrationBuilder.CreateIndex(
                name: "IX_CategorizationRules_CategoryId",
                table: "CategorizationRules",
                column: "CategoryId");

            migrationBuilder.CreateIndex(
                name: "IX_CurrencyRates_Currency_Date",
                table: "CurrencyRates",
                columns: new[] { "Currency", "Date" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_FiscalYears_Year",
                table: "FiscalYears",
                column: "Year",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_FundingAgreements_FunderId",
                table: "FundingAgreements",
                column: "FunderId");

            migrationBuilder.CreateIndex(
                name: "IX_FundingAgreements_ProjectId",
                table: "FundingAgreements",
                column: "ProjectId");

            migrationBuilder.CreateIndex(
                name: "IX_FundingTranches_FundingAgreementId",
                table: "FundingTranches",
                column: "FundingAgreementId");

            migrationBuilder.CreateIndex(
                name: "IX_FundingTranches_ReceivedOperationId",
                table: "FundingTranches",
                column: "ReceivedOperationId");

            migrationBuilder.CreateIndex(
                name: "IX_LedgerAccounts_Code",
                table: "LedgerAccounts",
                column: "Code",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_LedgerAccounts_ParentId",
                table: "LedgerAccounts",
                column: "ParentId");

            migrationBuilder.CreateIndex(
                name: "IX_OperationAllocations_BudgetLineId",
                table: "OperationAllocations",
                column: "BudgetLineId");

            migrationBuilder.CreateIndex(
                name: "IX_OperationAllocations_CategoryId",
                table: "OperationAllocations",
                column: "CategoryId");

            migrationBuilder.CreateIndex(
                name: "IX_OperationAllocations_OperationId",
                table: "OperationAllocations",
                column: "OperationId");

            migrationBuilder.CreateIndex(
                name: "IX_OperationAllocations_ProjectId",
                table: "OperationAllocations",
                column: "ProjectId");

            migrationBuilder.CreateIndex(
                name: "IX_OperationAttachments_OperationId",
                table: "OperationAttachments",
                column: "OperationId");

            migrationBuilder.CreateIndex(
                name: "IX_OperationAttachments_ProjectDocumentId",
                table: "OperationAttachments",
                column: "ProjectDocumentId");

            migrationBuilder.CreateIndex(
                name: "IX_OperationAttachments_StoredFileId",
                table: "OperationAttachments",
                column: "StoredFileId");

            migrationBuilder.CreateIndex(
                name: "IX_Operations_BankAccountId_OperationDate",
                table: "Operations",
                columns: new[] { "BankAccountId", "OperationDate" });

            migrationBuilder.CreateIndex(
                name: "IX_Operations_TransferGroupId",
                table: "Operations",
                column: "TransferGroupId");

            migrationBuilder.CreateIndex(
                name: "IX_StoredFiles_Sha256",
                table: "StoredFiles",
                column: "Sha256",
                unique: true);

            // Journal d'audit en ajout seul : toute modification ou suppression est refusée par la base elle-même.
            migrationBuilder.Sql(@"CREATE TRIGGER TR_AuditEntries_NoUpdate BEFORE UPDATE ON AuditEntries
                BEGIN SELECT RAISE(ABORT, 'Journal d''audit : modification interdite.'); END;");
            migrationBuilder.Sql(@"CREATE TRIGGER TR_AuditEntries_NoDelete BEFORE DELETE ON AuditEntries
                BEGIN SELECT RAISE(ABORT, 'Journal d''audit : suppression interdite.'); END;");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "AccountProjectLinks");

            migrationBuilder.DropTable(
                name: "AppSettings");

            migrationBuilder.DropTable(
                name: "AuditEntries");

            migrationBuilder.DropTable(
                name: "CategorizationRules");

            migrationBuilder.DropTable(
                name: "CurrencyRates");

            migrationBuilder.DropTable(
                name: "FundingTranches");

            migrationBuilder.DropTable(
                name: "OperationAllocations");

            migrationBuilder.DropTable(
                name: "OperationAttachments");

            migrationBuilder.DropTable(
                name: "BudgetLines");

            migrationBuilder.DropTable(
                name: "Operations");

            migrationBuilder.DropTable(
                name: "StoredFiles");

            migrationBuilder.DropTable(
                name: "Categories");

            migrationBuilder.DropTable(
                name: "FiscalYears");

            migrationBuilder.DropTable(
                name: "FundingAgreements");

            migrationBuilder.DropTable(
                name: "BankAccounts");

            migrationBuilder.DropTable(
                name: "LedgerAccounts");

            migrationBuilder.DropColumn(
                name: "Currency",
                table: "Projects");

            migrationBuilder.DropColumn(
                name: "DeletedAtUtc",
                table: "Projects");

            migrationBuilder.DropColumn(
                name: "IsDeleted",
                table: "Projects");

            migrationBuilder.DropColumn(
                name: "DeletedAtUtc",
                table: "CostEntries");

            migrationBuilder.DropColumn(
                name: "IsDeleted",
                table: "CostEntries");
        }
    }
}
