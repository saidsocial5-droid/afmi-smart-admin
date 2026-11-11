CREATE TABLE IF NOT EXISTS "__EFMigrationsHistory" (
    "MigrationId" TEXT NOT NULL CONSTRAINT "PK___EFMigrationsHistory" PRIMARY KEY,
    "ProductVersion" TEXT NOT NULL
);

BEGIN TRANSACTION;
CREATE TABLE "AiSettings" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_AiSettings" PRIMARY KEY AUTOINCREMENT,
    "UseOllama" INTEGER NOT NULL,
    "OllamaEndpoint" TEXT NOT NULL,
    "OllamaModel" TEXT NOT NULL,
    "UseCloudApi" INTEGER NOT NULL,
    "CloudProvider" TEXT NOT NULL,
    "CloudApiKey" TEXT NOT NULL
);

CREATE TABLE "Funders" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_Funders" PRIMARY KEY AUTOINCREMENT,
    "Name" TEXT NOT NULL,
    "PrimaryColor" TEXT NOT NULL,
    "LogoPath" TEXT NOT NULL,
    "LegalMentions" TEXT NOT NULL,
    "HeaderText" TEXT NOT NULL,
    "FooterText" TEXT NOT NULL
);

CREATE TABLE "SmtpSettings" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_SmtpSettings" PRIMARY KEY AUTOINCREMENT,
    "Server" TEXT NOT NULL,
    "Port" INTEGER NOT NULL,
    "Username" TEXT NOT NULL,
    "Password" TEXT NOT NULL,
    "RecipientEmail" TEXT NOT NULL,
    "ScheduleType" TEXT NOT NULL,
    "LastSentDate" TEXT NULL,
    "LastSentSuccess" INTEGER NOT NULL
);

CREATE TABLE "Templates" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_Templates" PRIMARY KEY AUTOINCREMENT,
    "Name" TEXT NOT NULL,
    "Description" TEXT NOT NULL,
    "ProjectDataJson" TEXT NOT NULL
);

CREATE TABLE "Projects" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_Projects" PRIMARY KEY AUTOINCREMENT,
    "Name" TEXT NOT NULL,
    "Code" TEXT NOT NULL,
    "Description" TEXT NOT NULL,
    "Manager" TEXT NOT NULL,
    "Owner" TEXT NOT NULL,
    "Client" TEXT NOT NULL,
    "Department" TEXT NOT NULL,
    "FunderId" INTEGER NULL,
    "TargetStartDate" TEXT NULL,
    "TargetEndDate" TEXT NULL,
    "ActualStartDate" TEXT NULL,
    "ActualEndDate" TEXT NULL,
    "Status" TEXT NOT NULL,
    "Priority" TEXT NOT NULL,
    "BudgetGlobal" TEXT NOT NULL,
    "ParentProjectId" INTEGER NULL,
    "LessonsLearned" TEXT NOT NULL,
    "LocalFolderPath" TEXT NOT NULL,
    CONSTRAINT "FK_Projects_Funders_FunderId" FOREIGN KEY ("FunderId") REFERENCES "Funders" ("Id"),
    CONSTRAINT "FK_Projects_Projects_ParentProjectId" FOREIGN KEY ("ParentProjectId") REFERENCES "Projects" ("Id") ON DELETE RESTRICT
);

CREATE TABLE "AuditLogs" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_AuditLogs" PRIMARY KEY AUTOINCREMENT,
    "ProjectId" INTEGER NOT NULL,
    "EntityType" TEXT NOT NULL,
    "EntityId" INTEGER NOT NULL,
    "ChangeType" TEXT NOT NULL,
    "FieldName" TEXT NOT NULL,
    "OldValue" TEXT NOT NULL,
    "NewValue" TEXT NOT NULL,
    "Timestamp" TEXT NOT NULL,
    "User" TEXT NOT NULL,
    CONSTRAINT "FK_AuditLogs_Projects_ProjectId" FOREIGN KEY ("ProjectId") REFERENCES "Projects" ("Id") ON DELETE CASCADE
);

CREATE TABLE "Baselines" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_Baselines" PRIMARY KEY AUTOINCREMENT,
    "ProjectId" INTEGER NOT NULL,
    "DonorName" TEXT NOT NULL,
    "ContractualReference" TEXT NOT NULL,
    "TotalGrantCommitted" TEXT NOT NULL,
    "CoFinancingShare" TEXT NOT NULL,
    "EligibilityDeadline" TEXT NULL,
    "NextReportingDeadline" TEXT NULL,
    "ReportingFrequency" TEXT NOT NULL,
    "ContractualDeliverables" TEXT NOT NULL,
    "EligibilityRulesNotes" TEXT NOT NULL,
    "ComplianceScore" REAL NOT NULL,
    "DiagnosticSummary" TEXT NOT NULL,
    "LastAnalyzedDate" TEXT NOT NULL,
    CONSTRAINT "FK_Baselines_Projects_ProjectId" FOREIGN KEY ("ProjectId") REFERENCES "Projects" ("Id") ON DELETE CASCADE
);

CREATE TABLE "CostEntries" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_CostEntries" PRIMARY KEY AUTOINCREMENT,
    "ProjectId" INTEGER NOT NULL,
    "Category" TEXT NOT NULL,
    "ResourceName" TEXT NOT NULL,
    "Supplier" TEXT NOT NULL,
    "Description" TEXT NOT NULL,
    "EstimatedCost" TEXT NOT NULL,
    "ActualCost" TEXT NOT NULL,
    "Date" TEXT NOT NULL,
    CONSTRAINT "FK_CostEntries_Projects_ProjectId" FOREIGN KEY ("ProjectId") REFERENCES "Projects" ("Id") ON DELETE CASCADE
);

CREATE TABLE "Documents" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_Documents" PRIMARY KEY AUTOINCREMENT,
    "ProjectId" INTEGER NOT NULL,
    "Title" TEXT NOT NULL,
    "Category" TEXT NOT NULL,
    "DocumentPhase" TEXT NOT NULL,
    "Tags" TEXT NOT NULL,
    "IsKeyReference" INTEGER NOT NULL,
    "DocumentVersion" TEXT NOT NULL,
    "DonorName" TEXT NOT NULL,
    "DocumentReference" TEXT NOT NULL,
    "SignatureDate" TEXT NULL,
    "ContractualEndDate" TEXT NULL,
    "ApprovedGrantAmount" TEXT NOT NULL,
    "FilePath" TEXT NOT NULL,
    "OriginalFileName" TEXT NOT NULL,
    "FileExtension" TEXT NOT NULL,
    "FileSize" INTEGER NOT NULL,
    "Notes" TEXT NOT NULL,
    "ExtractedSummary" TEXT NOT NULL,
    "FullExtractedText" TEXT NOT NULL,
    "KeyInsights" TEXT NOT NULL,
    "AnalyzedDate" TEXT NULL,
    "UploadedDate" TEXT NOT NULL,
    CONSTRAINT "FK_Documents_Projects_ProjectId" FOREIGN KEY ("ProjectId") REFERENCES "Projects" ("Id") ON DELETE CASCADE
);

CREATE TABLE "Indicators" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_Indicators" PRIMARY KEY AUTOINCREMENT,
    "Name" TEXT NOT NULL,
    "Description" TEXT NOT NULL,
    "TargetValue" REAL NOT NULL,
    "CurrentValue" REAL NOT NULL,
    "Unit" TEXT NOT NULL,
    "ProjectId" INTEGER NOT NULL,
    CONSTRAINT "FK_Indicators_Projects_ProjectId" FOREIGN KEY ("ProjectId") REFERENCES "Projects" ("Id") ON DELETE CASCADE
);

CREATE TABLE "ReportHistories" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_ReportHistories" PRIMARY KEY AUTOINCREMENT,
    "ProjectId" INTEGER NOT NULL,
    "ReportType" TEXT NOT NULL,
    "Title" TEXT NOT NULL,
    "GeneratedDate" TEXT NOT NULL,
    "FilePath" TEXT NOT NULL,
    "ContentJson" TEXT NOT NULL,
    CONSTRAINT "FK_ReportHistories_Projects_ProjectId" FOREIGN KEY ("ProjectId") REFERENCES "Projects" ("Id") ON DELETE CASCADE
);

CREATE TABLE "Tasks" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_Tasks" PRIMARY KEY AUTOINCREMENT,
    "ProjectId" INTEGER NOT NULL,
    "ParentTaskId" INTEGER NULL,
    "Name" TEXT NOT NULL,
    "Description" TEXT NOT NULL,
    "Assignee" TEXT NOT NULL,
    "TargetStartDate" TEXT NULL,
    "TargetEndDate" TEXT NULL,
    "ActualStartDate" TEXT NULL,
    "ActualEndDate" TEXT NULL,
    "ProgressPercentage" REAL NOT NULL,
    "Status" TEXT NOT NULL,
    "Budget" TEXT NOT NULL,
    "Cost" TEXT NOT NULL,
    "Predecessors" TEXT NOT NULL,
    CONSTRAINT "FK_Tasks_Projects_ProjectId" FOREIGN KEY ("ProjectId") REFERENCES "Projects" ("Id") ON DELETE CASCADE,
    CONSTRAINT "FK_Tasks_Tasks_ParentTaskId" FOREIGN KEY ("ParentTaskId") REFERENCES "Tasks" ("Id") ON DELETE CASCADE
);

CREATE TABLE "WorkflowSteps" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_WorkflowSteps" PRIMARY KEY AUTOINCREMENT,
    "ProjectId" INTEGER NOT NULL,
    "StepName" TEXT NOT NULL,
    "Order" INTEGER NOT NULL,
    "IsCompleted" INTEGER NOT NULL,
    "CompletedDate" TEXT NULL,
    CONSTRAINT "FK_WorkflowSteps_Projects_ProjectId" FOREIGN KEY ("ProjectId") REFERENCES "Projects" ("Id") ON DELETE CASCADE
);

CREATE TABLE "ActivityReports" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_ActivityReports" PRIMARY KEY AUTOINCREMENT,
    "Title" TEXT NOT NULL,
    "ActivityDate" TEXT NOT NULL,
    "Location" TEXT NOT NULL,
    "ParticipantsCount" INTEGER NOT NULL,
    "Narrative" TEXT NOT NULL,
    "Difficulties" TEXT NOT NULL,
    "Recommendations" TEXT NOT NULL,
    "Status" TEXT NOT NULL,
    "ProjectTaskId" INTEGER NOT NULL,
    "IndicatorId" INTEGER NULL,
    CONSTRAINT "FK_ActivityReports_Indicators_IndicatorId" FOREIGN KEY ("IndicatorId") REFERENCES "Indicators" ("Id"),
    CONSTRAINT "FK_ActivityReports_Tasks_ProjectTaskId" FOREIGN KEY ("ProjectTaskId") REFERENCES "Tasks" ("Id") ON DELETE CASCADE
);

CREATE TABLE "ActivityReportPhotos" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_ActivityReportPhotos" PRIMARY KEY AUTOINCREMENT,
    "LocalFilePath" TEXT NOT NULL,
    "Caption" TEXT NOT NULL,
    "ActivityReportId" INTEGER NOT NULL,
    CONSTRAINT "FK_ActivityReportPhotos_ActivityReports_ActivityReportId" FOREIGN KEY ("ActivityReportId") REFERENCES "ActivityReports" ("Id") ON DELETE CASCADE
);

CREATE INDEX "IX_ActivityReportPhotos_ActivityReportId" ON "ActivityReportPhotos" ("ActivityReportId");

CREATE INDEX "IX_ActivityReports_IndicatorId" ON "ActivityReports" ("IndicatorId");

CREATE INDEX "IX_ActivityReports_ProjectTaskId" ON "ActivityReports" ("ProjectTaskId");

CREATE INDEX "IX_AuditLogs_ProjectId" ON "AuditLogs" ("ProjectId");

CREATE UNIQUE INDEX "IX_Baselines_ProjectId" ON "Baselines" ("ProjectId");

CREATE INDEX "IX_CostEntries_ProjectId" ON "CostEntries" ("ProjectId");

CREATE INDEX "IX_Documents_ProjectId" ON "Documents" ("ProjectId");

CREATE INDEX "IX_Indicators_ProjectId" ON "Indicators" ("ProjectId");

CREATE INDEX "IX_Projects_FunderId" ON "Projects" ("FunderId");

CREATE INDEX "IX_Projects_ParentProjectId" ON "Projects" ("ParentProjectId");

CREATE INDEX "IX_ReportHistories_ProjectId" ON "ReportHistories" ("ProjectId");

CREATE INDEX "IX_Tasks_ParentTaskId" ON "Tasks" ("ParentTaskId");

CREATE INDEX "IX_Tasks_ProjectId" ON "Tasks" ("ProjectId");

CREATE INDEX "IX_WorkflowSteps_ProjectId" ON "WorkflowSteps" ("ProjectId");

INSERT INTO "__EFMigrationsHistory" ("MigrationId", "ProductVersion")
VALUES ('20261110220128_Baseline_1_3_0', '9.0.8');

CREATE TABLE "ef_temp_Tasks" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_Tasks" PRIMARY KEY AUTOINCREMENT,
    "ActualEndDate" TEXT NULL,
    "ActualStartDate" TEXT NULL,
    "Assignee" TEXT NOT NULL,
    "Budget" REAL NOT NULL,
    "Cost" REAL NOT NULL,
    "Description" TEXT NOT NULL,
    "Name" TEXT NOT NULL,
    "ParentTaskId" INTEGER NULL,
    "Predecessors" TEXT NOT NULL,
    "ProgressPercentage" REAL NOT NULL,
    "ProjectId" INTEGER NOT NULL,
    "Status" TEXT NOT NULL,
    "TargetEndDate" TEXT NULL,
    "TargetStartDate" TEXT NULL,
    CONSTRAINT "FK_Tasks_Projects_ProjectId" FOREIGN KEY ("ProjectId") REFERENCES "Projects" ("Id") ON DELETE CASCADE,
    CONSTRAINT "FK_Tasks_Tasks_ParentTaskId" FOREIGN KEY ("ParentTaskId") REFERENCES "Tasks" ("Id") ON DELETE CASCADE
);

INSERT INTO "ef_temp_Tasks" ("Id", "ActualEndDate", "ActualStartDate", "Assignee", "Budget", "Cost", "Description", "Name", "ParentTaskId", "Predecessors", "ProgressPercentage", "ProjectId", "Status", "TargetEndDate", "TargetStartDate")
SELECT "Id", "ActualEndDate", "ActualStartDate", "Assignee", "Budget", "Cost", "Description", "Name", "ParentTaskId", "Predecessors", "ProgressPercentage", "ProjectId", "Status", "TargetEndDate", "TargetStartDate"
FROM "Tasks";

CREATE TABLE "ef_temp_Projects" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_Projects" PRIMARY KEY AUTOINCREMENT,
    "ActualEndDate" TEXT NULL,
    "ActualStartDate" TEXT NULL,
    "BudgetGlobal" REAL NOT NULL,
    "Client" TEXT NOT NULL,
    "Code" TEXT NOT NULL,
    "Department" TEXT NOT NULL,
    "Description" TEXT NOT NULL,
    "FunderId" INTEGER NULL,
    "LessonsLearned" TEXT NOT NULL,
    "LocalFolderPath" TEXT NOT NULL,
    "Manager" TEXT NOT NULL,
    "Name" TEXT NOT NULL,
    "Owner" TEXT NOT NULL,
    "ParentProjectId" INTEGER NULL,
    "Priority" TEXT NOT NULL,
    "Status" TEXT NOT NULL,
    "TargetEndDate" TEXT NULL,
    "TargetStartDate" TEXT NULL,
    CONSTRAINT "FK_Projects_Funders_FunderId" FOREIGN KEY ("FunderId") REFERENCES "Funders" ("Id"),
    CONSTRAINT "FK_Projects_Projects_ParentProjectId" FOREIGN KEY ("ParentProjectId") REFERENCES "Projects" ("Id") ON DELETE RESTRICT
);

INSERT INTO "ef_temp_Projects" ("Id", "ActualEndDate", "ActualStartDate", "BudgetGlobal", "Client", "Code", "Department", "Description", "FunderId", "LessonsLearned", "LocalFolderPath", "Manager", "Name", "Owner", "ParentProjectId", "Priority", "Status", "TargetEndDate", "TargetStartDate")
SELECT "Id", "ActualEndDate", "ActualStartDate", "BudgetGlobal", "Client", "Code", "Department", "Description", "FunderId", "LessonsLearned", "LocalFolderPath", "Manager", "Name", "Owner", "ParentProjectId", "Priority", "Status", "TargetEndDate", "TargetStartDate"
FROM "Projects";

CREATE TABLE "ef_temp_Documents" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_Documents" PRIMARY KEY AUTOINCREMENT,
    "AnalyzedDate" TEXT NULL,
    "ApprovedGrantAmount" REAL NOT NULL,
    "Category" TEXT NOT NULL,
    "ContractualEndDate" TEXT NULL,
    "DocumentPhase" TEXT NOT NULL,
    "DocumentReference" TEXT NOT NULL,
    "DocumentVersion" TEXT NOT NULL,
    "DonorName" TEXT NOT NULL,
    "ExtractedSummary" TEXT NOT NULL,
    "FileExtension" TEXT NOT NULL,
    "FilePath" TEXT NOT NULL,
    "FileSize" INTEGER NOT NULL,
    "FullExtractedText" TEXT NOT NULL,
    "IsKeyReference" INTEGER NOT NULL,
    "KeyInsights" TEXT NOT NULL,
    "Notes" TEXT NOT NULL,
    "OriginalFileName" TEXT NOT NULL,
    "ProjectId" INTEGER NOT NULL,
    "SignatureDate" TEXT NULL,
    "Tags" TEXT NOT NULL,
    "Title" TEXT NOT NULL,
    "UploadedDate" TEXT NOT NULL,
    CONSTRAINT "FK_Documents_Projects_ProjectId" FOREIGN KEY ("ProjectId") REFERENCES "Projects" ("Id") ON DELETE CASCADE
);

INSERT INTO "ef_temp_Documents" ("Id", "AnalyzedDate", "ApprovedGrantAmount", "Category", "ContractualEndDate", "DocumentPhase", "DocumentReference", "DocumentVersion", "DonorName", "ExtractedSummary", "FileExtension", "FilePath", "FileSize", "FullExtractedText", "IsKeyReference", "KeyInsights", "Notes", "OriginalFileName", "ProjectId", "SignatureDate", "Tags", "Title", "UploadedDate")
SELECT "Id", "AnalyzedDate", "ApprovedGrantAmount", "Category", "ContractualEndDate", "DocumentPhase", "DocumentReference", "DocumentVersion", "DonorName", "ExtractedSummary", "FileExtension", "FilePath", "FileSize", "FullExtractedText", "IsKeyReference", "KeyInsights", "Notes", "OriginalFileName", "ProjectId", "SignatureDate", "Tags", "Title", "UploadedDate"
FROM "Documents";

CREATE TABLE "ef_temp_CostEntries" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_CostEntries" PRIMARY KEY AUTOINCREMENT,
    "ActualCost" REAL NOT NULL,
    "Category" TEXT NOT NULL,
    "Date" TEXT NOT NULL,
    "Description" TEXT NOT NULL,
    "EstimatedCost" REAL NOT NULL,
    "ProjectId" INTEGER NOT NULL,
    "ResourceName" TEXT NOT NULL,
    "Supplier" TEXT NOT NULL,
    CONSTRAINT "FK_CostEntries_Projects_ProjectId" FOREIGN KEY ("ProjectId") REFERENCES "Projects" ("Id") ON DELETE CASCADE
);

INSERT INTO "ef_temp_CostEntries" ("Id", "ActualCost", "Category", "Date", "Description", "EstimatedCost", "ProjectId", "ResourceName", "Supplier")
SELECT "Id", "ActualCost", "Category", "Date", "Description", "EstimatedCost", "ProjectId", "ResourceName", "Supplier"
FROM "CostEntries";

CREATE TABLE "ef_temp_Baselines" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_Baselines" PRIMARY KEY AUTOINCREMENT,
    "CoFinancingShare" REAL NOT NULL,
    "ComplianceScore" REAL NOT NULL,
    "ContractualDeliverables" TEXT NOT NULL,
    "ContractualReference" TEXT NOT NULL,
    "DiagnosticSummary" TEXT NOT NULL,
    "DonorName" TEXT NOT NULL,
    "EligibilityDeadline" TEXT NULL,
    "EligibilityRulesNotes" TEXT NOT NULL,
    "LastAnalyzedDate" TEXT NOT NULL,
    "NextReportingDeadline" TEXT NULL,
    "ProjectId" INTEGER NOT NULL,
    "ReportingFrequency" TEXT NOT NULL,
    "TotalGrantCommitted" REAL NOT NULL,
    CONSTRAINT "FK_Baselines_Projects_ProjectId" FOREIGN KEY ("ProjectId") REFERENCES "Projects" ("Id") ON DELETE CASCADE
);

INSERT INTO "ef_temp_Baselines" ("Id", "CoFinancingShare", "ComplianceScore", "ContractualDeliverables", "ContractualReference", "DiagnosticSummary", "DonorName", "EligibilityDeadline", "EligibilityRulesNotes", "LastAnalyzedDate", "NextReportingDeadline", "ProjectId", "ReportingFrequency", "TotalGrantCommitted")
SELECT "Id", "CoFinancingShare", "ComplianceScore", "ContractualDeliverables", "ContractualReference", "DiagnosticSummary", "DonorName", "EligibilityDeadline", "EligibilityRulesNotes", "LastAnalyzedDate", "NextReportingDeadline", "ProjectId", "ReportingFrequency", "TotalGrantCommitted"
FROM "Baselines";

COMMIT;

PRAGMA foreign_keys = 0;

BEGIN TRANSACTION;
DROP TABLE "Tasks";

ALTER TABLE "ef_temp_Tasks" RENAME TO "Tasks";

DROP TABLE "Projects";

ALTER TABLE "ef_temp_Projects" RENAME TO "Projects";

DROP TABLE "Documents";

ALTER TABLE "ef_temp_Documents" RENAME TO "Documents";

DROP TABLE "CostEntries";

ALTER TABLE "ef_temp_CostEntries" RENAME TO "CostEntries";

DROP TABLE "Baselines";

ALTER TABLE "ef_temp_Baselines" RENAME TO "Baselines";

COMMIT;

PRAGMA foreign_keys = 1;

BEGIN TRANSACTION;
CREATE INDEX "IX_Tasks_ParentTaskId" ON "Tasks" ("ParentTaskId");

CREATE INDEX "IX_Tasks_ProjectId" ON "Tasks" ("ProjectId");

CREATE INDEX "IX_Projects_FunderId" ON "Projects" ("FunderId");

CREATE INDEX "IX_Projects_ParentProjectId" ON "Projects" ("ParentProjectId");

CREATE INDEX "IX_Documents_ProjectId" ON "Documents" ("ProjectId");

CREATE INDEX "IX_CostEntries_ProjectId" ON "CostEntries" ("ProjectId");

CREATE UNIQUE INDEX "IX_Baselines_ProjectId" ON "Baselines" ("ProjectId");

COMMIT;

INSERT INTO "__EFMigrationsHistory" ("MigrationId", "ProductVersion")
VALUES ('20261110220143_LegacyAmountsInClear', '9.0.8');

BEGIN TRANSACTION;
UPDATE "Projects" SET "BudgetGlobal" = afmi_legacy_amount("BudgetGlobal") WHERE typeof("BudgetGlobal") <> 'real';

UPDATE "Tasks" SET "Budget" = afmi_legacy_amount("Budget") WHERE typeof("Budget") <> 'real';

UPDATE "Tasks" SET "Cost" = afmi_legacy_amount("Cost") WHERE typeof("Cost") <> 'real';

UPDATE "CostEntries" SET "EstimatedCost" = afmi_legacy_amount("EstimatedCost") WHERE typeof("EstimatedCost") <> 'real';

UPDATE "CostEntries" SET "ActualCost" = afmi_legacy_amount("ActualCost") WHERE typeof("ActualCost") <> 'real';

UPDATE "Documents" SET "ApprovedGrantAmount" = afmi_legacy_amount("ApprovedGrantAmount") WHERE typeof("ApprovedGrantAmount") <> 'real';

UPDATE "Baselines" SET "TotalGrantCommitted" = afmi_legacy_amount("TotalGrantCommitted") WHERE typeof("TotalGrantCommitted") <> 'real';

UPDATE "Baselines" SET "CoFinancingShare" = afmi_legacy_amount("CoFinancingShare") WHERE typeof("CoFinancingShare") <> 'real';

INSERT INTO "__EFMigrationsHistory" ("MigrationId", "ProductVersion")
VALUES ('20261110220144_DecryptLegacyAmounts', '9.0.8');

ALTER TABLE "Projects" ADD "Currency" TEXT NOT NULL DEFAULT 'MAD';

ALTER TABLE "Projects" ADD "DeletedAtUtc" TEXT NULL;

ALTER TABLE "Projects" ADD "IsDeleted" INTEGER NOT NULL DEFAULT 0;

ALTER TABLE "CostEntries" ADD "DeletedAtUtc" TEXT NULL;

ALTER TABLE "CostEntries" ADD "IsDeleted" INTEGER NOT NULL DEFAULT 0;

CREATE TABLE "AppSettings" (
    "Key" TEXT NOT NULL CONSTRAINT "PK_AppSettings" PRIMARY KEY,
    "ValueJson" TEXT NOT NULL,
    "IsSecret" INTEGER NOT NULL,
    "UpdatedAtUtc" TEXT NOT NULL
);

CREATE TABLE "AuditEntries" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_AuditEntries" PRIMARY KEY AUTOINCREMENT,
    "TimestampUtc" TEXT NOT NULL,
    "User" TEXT NOT NULL,
    "Machine" TEXT NOT NULL,
    "EntityType" TEXT NOT NULL,
    "EntityId" TEXT NOT NULL,
    "Action" TEXT NOT NULL,
    "ChangesJson" TEXT NOT NULL,
    "PreviousHash" TEXT NOT NULL,
    "Hash" TEXT NOT NULL
);

CREATE TABLE "BankAccounts" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_BankAccounts" PRIMARY KEY AUTOINCREMENT,
    "Kind" TEXT NOT NULL,
    "Purpose" TEXT NOT NULL,
    "BankName" TEXT NOT NULL,
    "Branch" TEXT NOT NULL,
    "Title" TEXT NOT NULL,
    "Rib" TEXT NULL,
    "Currency" TEXT NOT NULL,
    "OpeningBalanceMinor" INTEGER NOT NULL,
    "OpeningDate" TEXT NOT NULL,
    "Status" TEXT NOT NULL,
    "ClosedDate" TEXT NULL,
    "Notes" TEXT NOT NULL,
    "IsDeleted" INTEGER NOT NULL DEFAULT 0,
    "DeletedAtUtc" TEXT NULL
);

CREATE TABLE "CurrencyRates" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_CurrencyRates" PRIMARY KEY AUTOINCREMENT,
    "Currency" TEXT NOT NULL,
    "Date" TEXT NOT NULL,
    "RateToMad" TEXT NOT NULL,
    "Source" TEXT NOT NULL,
    CONSTRAINT "CK_CurrencyRates_Positive" CHECK (CAST(RateToMad AS REAL) > 0)
);

CREATE TABLE "FiscalYears" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_FiscalYears" PRIMARY KEY AUTOINCREMENT,
    "Year" INTEGER NOT NULL,
    "StartDate" TEXT NOT NULL,
    "EndDate" TEXT NOT NULL,
    "Status" TEXT NOT NULL,
    "ClosedAtUtc" TEXT NULL,
    CONSTRAINT "CK_FiscalYears_Dates" CHECK (EndDate >= StartDate)
);

CREATE TABLE "FundingAgreements" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_FundingAgreements" PRIMARY KEY AUTOINCREMENT,
    "FunderId" INTEGER NOT NULL,
    "ProjectId" INTEGER NOT NULL,
    "Reference" TEXT NOT NULL,
    "Title" TEXT NOT NULL,
    "AmountMinor" INTEGER NOT NULL,
    "Currency" TEXT NOT NULL,
    "ContractualRateToMad" TEXT NULL,
    "SignatureDate" TEXT NULL,
    "StartDate" TEXT NULL,
    "EndDate" TEXT NULL,
    "Notes" TEXT NOT NULL,
    "IsDeleted" INTEGER NOT NULL DEFAULT 0,
    "DeletedAtUtc" TEXT NULL,
    CONSTRAINT "CK_FundingAgreements_Amount" CHECK (AmountMinor >= 0),
    CONSTRAINT "FK_FundingAgreements_Funders_FunderId" FOREIGN KEY ("FunderId") REFERENCES "Funders" ("Id") ON DELETE RESTRICT,
    CONSTRAINT "FK_FundingAgreements_Projects_ProjectId" FOREIGN KEY ("ProjectId") REFERENCES "Projects" ("Id") ON DELETE RESTRICT
);

CREATE TABLE "LedgerAccounts" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_LedgerAccounts" PRIMARY KEY AUTOINCREMENT,
    "Code" TEXT NOT NULL,
    "Label" TEXT NOT NULL,
    "Type" TEXT NOT NULL,
    "ParentId" INTEGER NULL,
    "IsActive" INTEGER NOT NULL,
    CONSTRAINT "FK_LedgerAccounts_LedgerAccounts_ParentId" FOREIGN KEY ("ParentId") REFERENCES "LedgerAccounts" ("Id") ON DELETE RESTRICT
);

CREATE TABLE "StoredFiles" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_StoredFiles" PRIMARY KEY AUTOINCREMENT,
    "Sha256" TEXT NOT NULL,
    "RelativePath" TEXT NOT NULL,
    "OriginalName" TEXT NOT NULL,
    "MimeType" TEXT NOT NULL,
    "SizeBytes" INTEGER NOT NULL,
    "ImportedAtUtc" TEXT NOT NULL
);

CREATE TABLE "AccountProjectLinks" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_AccountProjectLinks" PRIMARY KEY AUTOINCREMENT,
    "BankAccountId" INTEGER NOT NULL,
    "ProjectId" INTEGER NOT NULL,
    "ValidFrom" TEXT NOT NULL,
    "ValidTo" TEXT NULL,
    "AllocationMode" TEXT NOT NULL,
    "AllocationPercent" TEXT NULL,
    "AllocationAmountMinor" INTEGER NULL,
    "IsDeleted" INTEGER NOT NULL DEFAULT 0,
    "DeletedAtUtc" TEXT NULL,
    CONSTRAINT "FK_AccountProjectLinks_BankAccounts_BankAccountId" FOREIGN KEY ("BankAccountId") REFERENCES "BankAccounts" ("Id") ON DELETE RESTRICT,
    CONSTRAINT "FK_AccountProjectLinks_Projects_ProjectId" FOREIGN KEY ("ProjectId") REFERENCES "Projects" ("Id") ON DELETE RESTRICT
);

CREATE TABLE "Operations" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_Operations" PRIMARY KEY AUTOINCREMENT,
    "BankAccountId" INTEGER NOT NULL,
    "OperationDate" TEXT NOT NULL,
    "ValueDate" TEXT NULL,
    "Label" TEXT NOT NULL,
    "Reference" TEXT NOT NULL,
    "ThirdParty" TEXT NOT NULL,
    "Direction" TEXT NOT NULL,
    "Nature" TEXT NOT NULL,
    "AmountMinor" INTEGER NOT NULL,
    "Currency" TEXT NOT NULL,
    "RateToMad" TEXT NULL,
    "AmountMadMinor" INTEGER NOT NULL,
    "TransferGroupId" TEXT NULL,
    "Status" TEXT NOT NULL,
    "ValidatedAtUtc" TEXT NULL,
    "ValidatedBy" TEXT NOT NULL,
    "Notes" TEXT NOT NULL,
    "IsDeleted" INTEGER NOT NULL DEFAULT 0,
    "DeletedAtUtc" TEXT NULL,
    CONSTRAINT "CK_Operations_Amount" CHECK (AmountMinor > 0 AND AmountMadMinor >= 0),
    CONSTRAINT "CK_Operations_Transfer" CHECK ((Nature = 'InternalTransfer' AND TransferGroupId IS NOT NULL) OR (Nature <> 'InternalTransfer' AND TransferGroupId IS NULL)),
    CONSTRAINT "FK_Operations_BankAccounts_BankAccountId" FOREIGN KEY ("BankAccountId") REFERENCES "BankAccounts" ("Id") ON DELETE RESTRICT
);

CREATE TABLE "Categories" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_Categories" PRIMARY KEY AUTOINCREMENT,
    "Kind" TEXT NOT NULL,
    "Code" TEXT NOT NULL,
    "Label" TEXT NOT NULL,
    "ParentId" INTEGER NULL,
    "LedgerAccountId" INTEGER NULL,
    "IsActive" INTEGER NOT NULL,
    CONSTRAINT "FK_Categories_Categories_ParentId" FOREIGN KEY ("ParentId") REFERENCES "Categories" ("Id") ON DELETE RESTRICT,
    CONSTRAINT "FK_Categories_LedgerAccounts_LedgerAccountId" FOREIGN KEY ("LedgerAccountId") REFERENCES "LedgerAccounts" ("Id") ON DELETE RESTRICT
);

CREATE TABLE "FundingTranches" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_FundingTranches" PRIMARY KEY AUTOINCREMENT,
    "FundingAgreementId" INTEGER NOT NULL,
    "Label" TEXT NOT NULL,
    "ExpectedDate" TEXT NOT NULL,
    "AmountMinor" INTEGER NOT NULL,
    "ReceivedOperationId" INTEGER NULL,
    "IsDeleted" INTEGER NOT NULL DEFAULT 0,
    "DeletedAtUtc" TEXT NULL,
    CONSTRAINT "CK_FundingTranches_Amount" CHECK (AmountMinor >= 0),
    CONSTRAINT "FK_FundingTranches_FundingAgreements_FundingAgreementId" FOREIGN KEY ("FundingAgreementId") REFERENCES "FundingAgreements" ("Id") ON DELETE RESTRICT,
    CONSTRAINT "FK_FundingTranches_Operations_ReceivedOperationId" FOREIGN KEY ("ReceivedOperationId") REFERENCES "Operations" ("Id") ON DELETE RESTRICT
);

CREATE TABLE "OperationAttachments" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_OperationAttachments" PRIMARY KEY AUTOINCREMENT,
    "OperationId" INTEGER NOT NULL,
    "StoredFileId" INTEGER NULL,
    "ProjectDocumentId" INTEGER NULL,
    "Label" TEXT NOT NULL,
    CONSTRAINT "FK_OperationAttachments_Documents_ProjectDocumentId" FOREIGN KEY ("ProjectDocumentId") REFERENCES "Documents" ("Id") ON DELETE RESTRICT,
    CONSTRAINT "FK_OperationAttachments_Operations_OperationId" FOREIGN KEY ("OperationId") REFERENCES "Operations" ("Id") ON DELETE CASCADE,
    CONSTRAINT "FK_OperationAttachments_StoredFiles_StoredFileId" FOREIGN KEY ("StoredFileId") REFERENCES "StoredFiles" ("Id") ON DELETE RESTRICT
);

CREATE TABLE "BudgetLines" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_BudgetLines" PRIMARY KEY AUTOINCREMENT,
    "ProjectId" INTEGER NULL,
    "FundingAgreementId" INTEGER NULL,
    "FiscalYearId" INTEGER NULL,
    "Code" TEXT NOT NULL,
    "Label" TEXT NOT NULL,
    "CategoryId" INTEGER NULL,
    "PlannedMinor" INTEGER NOT NULL,
    "Currency" TEXT NOT NULL,
    "IsDeleted" INTEGER NOT NULL DEFAULT 0,
    "DeletedAtUtc" TEXT NULL,
    CONSTRAINT "CK_BudgetLines_Planned" CHECK (PlannedMinor >= 0),
    CONSTRAINT "FK_BudgetLines_Categories_CategoryId" FOREIGN KEY ("CategoryId") REFERENCES "Categories" ("Id") ON DELETE RESTRICT,
    CONSTRAINT "FK_BudgetLines_FiscalYears_FiscalYearId" FOREIGN KEY ("FiscalYearId") REFERENCES "FiscalYears" ("Id") ON DELETE RESTRICT,
    CONSTRAINT "FK_BudgetLines_FundingAgreements_FundingAgreementId" FOREIGN KEY ("FundingAgreementId") REFERENCES "FundingAgreements" ("Id") ON DELETE RESTRICT,
    CONSTRAINT "FK_BudgetLines_Projects_ProjectId" FOREIGN KEY ("ProjectId") REFERENCES "Projects" ("Id") ON DELETE RESTRICT
);

CREATE TABLE "CategorizationRules" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_CategorizationRules" PRIMARY KEY AUTOINCREMENT,
    "Pattern" TEXT NOT NULL,
    "MatchType" TEXT NOT NULL,
    "Direction" TEXT NULL,
    "CategoryId" INTEGER NULL,
    "ProjectId" INTEGER NULL,
    "BudgetLineId" INTEGER NULL,
    "Source" TEXT NOT NULL,
    "Priority" INTEGER NOT NULL,
    "HitCount" INTEGER NOT NULL,
    "IsActive" INTEGER NOT NULL,
    CONSTRAINT "FK_CategorizationRules_Categories_CategoryId" FOREIGN KEY ("CategoryId") REFERENCES "Categories" ("Id") ON DELETE RESTRICT
);

CREATE TABLE "OperationAllocations" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_OperationAllocations" PRIMARY KEY AUTOINCREMENT,
    "OperationId" INTEGER NOT NULL,
    "ProjectId" INTEGER NULL,
    "BudgetLineId" INTEGER NULL,
    "CategoryId" INTEGER NULL,
    "AmountMinor" INTEGER NOT NULL,
    CONSTRAINT "CK_OperationAllocations_Amount" CHECK (AmountMinor > 0),
    CONSTRAINT "FK_OperationAllocations_BudgetLines_BudgetLineId" FOREIGN KEY ("BudgetLineId") REFERENCES "BudgetLines" ("Id") ON DELETE RESTRICT,
    CONSTRAINT "FK_OperationAllocations_Categories_CategoryId" FOREIGN KEY ("CategoryId") REFERENCES "Categories" ("Id") ON DELETE RESTRICT,
    CONSTRAINT "FK_OperationAllocations_Operations_OperationId" FOREIGN KEY ("OperationId") REFERENCES "Operations" ("Id") ON DELETE CASCADE,
    CONSTRAINT "FK_OperationAllocations_Projects_ProjectId" FOREIGN KEY ("ProjectId") REFERENCES "Projects" ("Id") ON DELETE RESTRICT
);

INSERT INTO "Categories" ("Id", "Code", "IsActive", "Kind", "Label", "LedgerAccountId", "ParentId")
VALUES (1, 'SUBV', 1, 'Income', 'Subventions', NULL, NULL);
SELECT changes();

INSERT INTO "Categories" ("Id", "Code", "IsActive", "Kind", "Label", "LedgerAccountId", "ParentId")
VALUES (2, 'COTIS', 1, 'Income', 'Cotisations', NULL, NULL);
SELECT changes();

INSERT INTO "Categories" ("Id", "Code", "IsActive", "Kind", "Label", "LedgerAccountId", "ParentId")
VALUES (3, 'DONS', 1, 'Income', 'Dons', NULL, NULL);
SELECT changes();

INSERT INTO "Categories" ("Id", "Code", "IsActive", "Kind", "Label", "LedgerAccountId", "ParentId")
VALUES (4, 'PREST', 1, 'Income', 'Prestations', NULL, NULL);
SELECT changes();

INSERT INTO "Categories" ("Id", "Code", "IsActive", "Kind", "Label", "LedgerAccountId", "ParentId")
VALUES (5, 'PFIN', 1, 'Income', 'Produits financiers', NULL, NULL);
SELECT changes();


CREATE INDEX "IX_AccountProjectLinks_BankAccountId_ProjectId" ON "AccountProjectLinks" ("BankAccountId", "ProjectId");

CREATE INDEX "IX_AccountProjectLinks_ProjectId" ON "AccountProjectLinks" ("ProjectId");

CREATE INDEX "IX_AuditEntries_EntityType_EntityId" ON "AuditEntries" ("EntityType", "EntityId");

CREATE INDEX "IX_AuditEntries_TimestampUtc" ON "AuditEntries" ("TimestampUtc");

CREATE UNIQUE INDEX "IX_BankAccounts_Rib" ON "BankAccounts" ("Rib") WHERE Rib IS NOT NULL AND IsDeleted = 0;

CREATE INDEX "IX_BudgetLines_CategoryId" ON "BudgetLines" ("CategoryId");

CREATE INDEX "IX_BudgetLines_FiscalYearId" ON "BudgetLines" ("FiscalYearId");

CREATE INDEX "IX_BudgetLines_FundingAgreementId" ON "BudgetLines" ("FundingAgreementId");

CREATE INDEX "IX_BudgetLines_ProjectId" ON "BudgetLines" ("ProjectId");

CREATE INDEX "IX_Categories_Kind_Code" ON "Categories" ("Kind", "Code");

CREATE INDEX "IX_Categories_LedgerAccountId" ON "Categories" ("LedgerAccountId");

CREATE INDEX "IX_Categories_ParentId" ON "Categories" ("ParentId");

CREATE INDEX "IX_CategorizationRules_CategoryId" ON "CategorizationRules" ("CategoryId");

CREATE UNIQUE INDEX "IX_CurrencyRates_Currency_Date" ON "CurrencyRates" ("Currency", "Date");

CREATE UNIQUE INDEX "IX_FiscalYears_Year" ON "FiscalYears" ("Year");

CREATE INDEX "IX_FundingAgreements_FunderId" ON "FundingAgreements" ("FunderId");

CREATE INDEX "IX_FundingAgreements_ProjectId" ON "FundingAgreements" ("ProjectId");

CREATE INDEX "IX_FundingTranches_FundingAgreementId" ON "FundingTranches" ("FundingAgreementId");

CREATE INDEX "IX_FundingTranches_ReceivedOperationId" ON "FundingTranches" ("ReceivedOperationId");

CREATE UNIQUE INDEX "IX_LedgerAccounts_Code" ON "LedgerAccounts" ("Code");

CREATE INDEX "IX_LedgerAccounts_ParentId" ON "LedgerAccounts" ("ParentId");

CREATE INDEX "IX_OperationAllocations_BudgetLineId" ON "OperationAllocations" ("BudgetLineId");

CREATE INDEX "IX_OperationAllocations_CategoryId" ON "OperationAllocations" ("CategoryId");

CREATE INDEX "IX_OperationAllocations_OperationId" ON "OperationAllocations" ("OperationId");

CREATE INDEX "IX_OperationAllocations_ProjectId" ON "OperationAllocations" ("ProjectId");

CREATE INDEX "IX_OperationAttachments_OperationId" ON "OperationAttachments" ("OperationId");

CREATE INDEX "IX_OperationAttachments_ProjectDocumentId" ON "OperationAttachments" ("ProjectDocumentId");

CREATE INDEX "IX_OperationAttachments_StoredFileId" ON "OperationAttachments" ("StoredFileId");

CREATE INDEX "IX_Operations_BankAccountId_OperationDate" ON "Operations" ("BankAccountId", "OperationDate");

CREATE INDEX "IX_Operations_TransferGroupId" ON "Operations" ("TransferGroupId");

CREATE UNIQUE INDEX "IX_StoredFiles_Sha256" ON "StoredFiles" ("Sha256");

CREATE TRIGGER TR_AuditEntries_NoUpdate BEFORE UPDATE ON AuditEntries
                BEGIN SELECT RAISE(ABORT, 'Journal d''audit : modification interdite.'); END;

CREATE TRIGGER TR_AuditEntries_NoDelete BEFORE DELETE ON AuditEntries
                BEGIN SELECT RAISE(ABORT, 'Journal d''audit : suppression interdite.'); END;

INSERT INTO "__EFMigrationsHistory" ("MigrationId", "ProductVersion")
VALUES ('20261110221414_FinanceFoundation', '9.0.8');

ALTER TABLE "BankAccounts" ADD "LowBalanceThresholdMinor" INTEGER NULL;

CREATE TABLE "BankStatements" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_BankStatements" PRIMARY KEY AUTOINCREMENT,
    "BankAccountId" INTEGER NOT NULL,
    "PeriodStart" TEXT NOT NULL,
    "PeriodEnd" TEXT NOT NULL,
    "OpeningBalanceMinor" INTEGER NOT NULL,
    "ClosingBalanceMinor" INTEGER NOT NULL,
    "Source" TEXT NOT NULL,
    "SourceFileId" INTEGER NULL,
    "Template" TEXT NOT NULL,
    "Status" TEXT NOT NULL,
    "ImportedAtUtc" TEXT NOT NULL,
    "Notes" TEXT NOT NULL,
    "IsDeleted" INTEGER NOT NULL DEFAULT 0,
    "DeletedAtUtc" TEXT NULL,
    CONSTRAINT "CK_BankStatements_Period" CHECK (PeriodEnd >= PeriodStart),
    CONSTRAINT "FK_BankStatements_BankAccounts_BankAccountId" FOREIGN KEY ("BankAccountId") REFERENCES "BankAccounts" ("Id") ON DELETE RESTRICT,
    CONSTRAINT "FK_BankStatements_StoredFiles_SourceFileId" FOREIGN KEY ("SourceFileId") REFERENCES "StoredFiles" ("Id") ON DELETE RESTRICT
);

CREATE TABLE "StatementLines" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_StatementLines" PRIMARY KEY AUTOINCREMENT,
    "BankStatementId" INTEGER NOT NULL,
    "OperationDate" TEXT NOT NULL,
    "ValueDate" TEXT NULL,
    "Label" TEXT NOT NULL,
    "Reference" TEXT NOT NULL,
    "DebitMinor" INTEGER NOT NULL,
    "CreditMinor" INTEGER NOT NULL,
    "ConfidenceJson" TEXT NOT NULL,
    "SuggestedCategoryId" INTEGER NULL,
    "SuggestedProjectId" INTEGER NULL,
    "SuggestedBudgetLineId" INTEGER NULL,
    CONSTRAINT "CK_StatementLines_Amounts" CHECK (DebitMinor >= 0 AND CreditMinor >= 0 AND (DebitMinor = 0 OR CreditMinor = 0) AND DebitMinor + CreditMinor > 0),
    CONSTRAINT "FK_StatementLines_BankStatements_BankStatementId" FOREIGN KEY ("BankStatementId") REFERENCES "BankStatements" ("Id") ON DELETE RESTRICT
);

CREATE TABLE "ReconciliationMatches" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_ReconciliationMatches" PRIMARY KEY AUTOINCREMENT,
    "StatementLineId" INTEGER NOT NULL,
    "OperationId" INTEGER NOT NULL,
    "Mode" TEXT NOT NULL,
    "Score" REAL NOT NULL,
    "MatchedAtUtc" TEXT NOT NULL,
    "MatchedBy" TEXT NOT NULL,
    CONSTRAINT "FK_ReconciliationMatches_Operations_OperationId" FOREIGN KEY ("OperationId") REFERENCES "Operations" ("Id") ON DELETE RESTRICT,
    CONSTRAINT "FK_ReconciliationMatches_StatementLines_StatementLineId" FOREIGN KEY ("StatementLineId") REFERENCES "StatementLines" ("Id") ON DELETE RESTRICT
);

INSERT INTO "Categories" ("Id", "Code", "IsActive", "Kind", "Label", "LedgerAccountId", "ParentId")
VALUES (6, 'PERS', 1, 'Expense', 'Personnel (salaires et charges)', NULL, NULL);
SELECT changes();

INSERT INTO "Categories" ("Id", "Code", "IsActive", "Kind", "Label", "LedgerAccountId", "ParentId")
VALUES (7, 'ACH', 1, 'Expense', 'Achats et fournitures', NULL, NULL);
SELECT changes();

INSERT INTO "Categories" ("Id", "Code", "IsActive", "Kind", "Label", "LedgerAccountId", "ParentId")
VALUES (8, 'HONO', 1, 'Expense', 'Prestations et honoraires', NULL, NULL);
SELECT changes();

INSERT INTO "Categories" ("Id", "Code", "IsActive", "Kind", "Label", "LedgerAccountId", "ParentId")
VALUES (9, 'DEPL', 1, 'Expense', 'Déplacements et missions', NULL, NULL);
SELECT changes();

INSERT INTO "Categories" ("Id", "Code", "IsActive", "Kind", "Label", "LedgerAccountId", "ParentId")
VALUES (10, 'LOC', 1, 'Expense', 'Loyers et charges locatives', NULL, NULL);
SELECT changes();

INSERT INTO "Categories" ("Id", "Code", "IsActive", "Kind", "Label", "LedgerAccountId", "ParentId")
VALUES (11, 'COM', 1, 'Expense', 'Communication et publications', NULL, NULL);
SELECT changes();

INSERT INTO "Categories" ("Id", "Code", "IsActive", "Kind", "Label", "LedgerAccountId", "ParentId")
VALUES (12, 'FBQ', 1, 'Expense', 'Frais bancaires', NULL, NULL);
SELECT changes();

INSERT INTO "Categories" ("Id", "Code", "IsActive", "Kind", "Label", "LedgerAccountId", "ParentId")
VALUES (13, 'EQP', 1, 'Expense', 'Équipements', NULL, NULL);
SELECT changes();

INSERT INTO "Categories" ("Id", "Code", "IsActive", "Kind", "Label", "LedgerAccountId", "ParentId")
VALUES (14, 'AUTD', 1, 'Expense', 'Autres dépenses', NULL, NULL);
SELECT changes();


CREATE INDEX "IX_BankStatements_BankAccountId_PeriodStart" ON "BankStatements" ("BankAccountId", "PeriodStart");

CREATE INDEX "IX_BankStatements_SourceFileId" ON "BankStatements" ("SourceFileId");

CREATE UNIQUE INDEX "IX_ReconciliationMatches_OperationId" ON "ReconciliationMatches" ("OperationId");

CREATE UNIQUE INDEX "IX_ReconciliationMatches_StatementLineId" ON "ReconciliationMatches" ("StatementLineId");

CREATE INDEX "IX_StatementLines_BankStatementId" ON "StatementLines" ("BankStatementId");

INSERT INTO "__EFMigrationsHistory" ("MigrationId", "ProductVersion")
VALUES ('20261110222259_BankingAndReconciliation', '9.0.8');

CREATE TABLE "DocumentTemplates" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_DocumentTemplates" PRIMARY KEY AUTOINCREMENT,
    "Name" TEXT NOT NULL,
    "Description" TEXT NOT NULL,
    "Kind" TEXT NOT NULL,
    "ContentJson" TEXT NOT NULL,
    "LayoutJson" TEXT NOT NULL,
    "IsShared" INTEGER NOT NULL,
    "CreatedBy" TEXT NOT NULL,
    "UpdatedAtUtc" TEXT NOT NULL,
    "IsDeleted" INTEGER NOT NULL DEFAULT 0,
    "DeletedAtUtc" TEXT NULL
);

CREATE TABLE "GraphicCharts" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_GraphicCharts" PRIMARY KEY AUTOINCREMENT,
    "Name" TEXT NOT NULL,
    "Scope" TEXT NOT NULL,
    "FunderId" INTEGER NULL,
    "ProjectId" INTEGER NULL,
    "StyleJson" TEXT NOT NULL,
    "UpdatedAtUtc" TEXT NOT NULL,
    "IsDeleted" INTEGER NOT NULL DEFAULT 0,
    "DeletedAtUtc" TEXT NULL,
    CONSTRAINT "CK_GraphicCharts_Scope" CHECK ((Scope = 'Association' AND FunderId IS NULL AND ProjectId IS NULL) OR (Scope = 'Funder' AND FunderId IS NOT NULL AND ProjectId IS NULL) OR (Scope = 'Project' AND ProjectId IS NOT NULL AND FunderId IS NULL)),
    CONSTRAINT "FK_GraphicCharts_Funders_FunderId" FOREIGN KEY ("FunderId") REFERENCES "Funders" ("Id") ON DELETE RESTRICT,
    CONSTRAINT "FK_GraphicCharts_Projects_ProjectId" FOREIGN KEY ("ProjectId") REFERENCES "Projects" ("Id") ON DELETE RESTRICT
);

CREATE TABLE "Photos" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_Photos" PRIMARY KEY AUTOINCREMENT,
    "StoredFileId" INTEGER NOT NULL,
    "ProjectId" INTEGER NULL,
    "ProjectTaskId" INTEGER NULL,
    "ActivityReportId" INTEGER NULL,
    "TakenAt" TEXT NULL,
    "Location" TEXT NOT NULL,
    "Latitude" REAL NULL,
    "Longitude" REAL NULL,
    "Caption" TEXT NOT NULL,
    "SuggestedCaption" TEXT NOT NULL,
    "CaptionValidated" INTEGER NOT NULL,
    "Credit" TEXT NOT NULL,
    "ConsentGiven" INTEGER NOT NULL,
    "Width" INTEGER NOT NULL,
    "Height" INTEGER NOT NULL,
    "ImportedAtUtc" TEXT NOT NULL,
    "IsDeleted" INTEGER NOT NULL DEFAULT 0,
    "DeletedAtUtc" TEXT NULL,
    CONSTRAINT "FK_Photos_ActivityReports_ActivityReportId" FOREIGN KEY ("ActivityReportId") REFERENCES "ActivityReports" ("Id") ON DELETE RESTRICT,
    CONSTRAINT "FK_Photos_Projects_ProjectId" FOREIGN KEY ("ProjectId") REFERENCES "Projects" ("Id") ON DELETE RESTRICT,
    CONSTRAINT "FK_Photos_StoredFiles_StoredFileId" FOREIGN KEY ("StoredFileId") REFERENCES "StoredFiles" ("Id") ON DELETE RESTRICT,
    CONSTRAINT "FK_Photos_Tasks_ProjectTaskId" FOREIGN KEY ("ProjectTaskId") REFERENCES "Tasks" ("Id") ON DELETE RESTRICT
);

CREATE TABLE "EditorDocuments" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_EditorDocuments" PRIMARY KEY AUTOINCREMENT,
    "Title" TEXT NOT NULL,
    "ProjectId" INTEGER NULL,
    "FunderId" INTEGER NULL,
    "TemplateId" INTEGER NULL,
    "Language" TEXT NOT NULL,
    "ContentJson" TEXT NOT NULL,
    "LayoutJson" TEXT NOT NULL,
    "CurrentVersion" INTEGER NOT NULL,
    "Status" TEXT NOT NULL,
    "CreatedBy" TEXT NOT NULL,
    "CreatedAtUtc" TEXT NOT NULL,
    "UpdatedAtUtc" TEXT NOT NULL,
    "IsDeleted" INTEGER NOT NULL DEFAULT 0,
    "DeletedAtUtc" TEXT NULL,
    CONSTRAINT "FK_EditorDocuments_DocumentTemplates_TemplateId" FOREIGN KEY ("TemplateId") REFERENCES "DocumentTemplates" ("Id") ON DELETE RESTRICT,
    CONSTRAINT "FK_EditorDocuments_Funders_FunderId" FOREIGN KEY ("FunderId") REFERENCES "Funders" ("Id") ON DELETE RESTRICT,
    CONSTRAINT "FK_EditorDocuments_Projects_ProjectId" FOREIGN KEY ("ProjectId") REFERENCES "Projects" ("Id") ON DELETE RESTRICT
);

CREATE TABLE "DocumentComments" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_DocumentComments" PRIMARY KEY AUTOINCREMENT,
    "EditorDocumentId" INTEGER NOT NULL,
    "AnchorId" TEXT NOT NULL,
    "ParentId" INTEGER NULL,
    "Text" TEXT NOT NULL,
    "QuotedText" TEXT NOT NULL,
    "Author" TEXT NOT NULL,
    "CreatedAtUtc" TEXT NOT NULL,
    "ResolvedAtUtc" TEXT NULL,
    CONSTRAINT "FK_DocumentComments_EditorDocuments_EditorDocumentId" FOREIGN KEY ("EditorDocumentId") REFERENCES "EditorDocuments" ("Id") ON DELETE RESTRICT
);

CREATE TABLE "DocumentVersions" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_DocumentVersions" PRIMARY KEY AUTOINCREMENT,
    "EditorDocumentId" INTEGER NOT NULL,
    "Number" INTEGER NOT NULL,
    "ContentJson" TEXT NOT NULL,
    "LayoutJson" TEXT NOT NULL,
    "Note" TEXT NOT NULL,
    "CreatedBy" TEXT NOT NULL,
    "CreatedAtUtc" TEXT NOT NULL,
    CONSTRAINT "FK_DocumentVersions_EditorDocuments_EditorDocumentId" FOREIGN KEY ("EditorDocumentId") REFERENCES "EditorDocuments" ("Id") ON DELETE RESTRICT
);

CREATE INDEX "IX_DocumentComments_EditorDocumentId_AnchorId" ON "DocumentComments" ("EditorDocumentId", "AnchorId");

CREATE UNIQUE INDEX "IX_DocumentVersions_EditorDocumentId_Number" ON "DocumentVersions" ("EditorDocumentId", "Number");

CREATE INDEX "IX_EditorDocuments_FunderId" ON "EditorDocuments" ("FunderId");

CREATE INDEX "IX_EditorDocuments_ProjectId" ON "EditorDocuments" ("ProjectId");

CREATE INDEX "IX_EditorDocuments_TemplateId" ON "EditorDocuments" ("TemplateId");

CREATE INDEX "IX_GraphicCharts_FunderId" ON "GraphicCharts" ("FunderId");

CREATE INDEX "IX_GraphicCharts_ProjectId" ON "GraphicCharts" ("ProjectId");

CREATE INDEX "IX_Photos_ActivityReportId" ON "Photos" ("ActivityReportId");

CREATE INDEX "IX_Photos_ProjectId_TakenAt" ON "Photos" ("ProjectId", "TakenAt");

CREATE INDEX "IX_Photos_ProjectTaskId" ON "Photos" ("ProjectTaskId");

CREATE INDEX "IX_Photos_StoredFileId" ON "Photos" ("StoredFileId");

INSERT INTO "__EFMigrationsHistory" ("MigrationId", "ProductVersion")
VALUES ('20261111100250_EditorChartsAndPhotos', '9.0.8');

ALTER TABLE "Indicators" ADD "Aggregation" TEXT NOT NULL DEFAULT 'Somme';

ALTER TABLE "Indicators" ADD "BaselineValue" REAL NULL;

ALTER TABLE "Indicators" ADD "Level" TEXT NOT NULL DEFAULT 'Extrant';

CREATE TABLE "IndicatorMeasurements" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_IndicatorMeasurements" PRIMARY KEY AUTOINCREMENT,
    "IndicatorId" INTEGER NOT NULL,
    "PeriodEnd" TEXT NOT NULL,
    "Value" REAL NOT NULL,
    "Sex" TEXT NOT NULL,
    "AgeGroup" TEXT NOT NULL,
    "Zone" TEXT NOT NULL,
    "Source" TEXT NOT NULL,
    "Notes" TEXT NOT NULL,
    "CreatedAtUtc" TEXT NOT NULL,
    CONSTRAINT "CK_IndicatorMeasurements_Sex" CHECK (Sex IN ('', 'F', 'M')),
    CONSTRAINT "FK_IndicatorMeasurements_Indicators_IndicatorId" FOREIGN KEY ("IndicatorId") REFERENCES "Indicators" ("Id") ON DELETE RESTRICT
);

CREATE INDEX "IX_IndicatorMeasurements_IndicatorId_PeriodEnd" ON "IndicatorMeasurements" ("IndicatorId", "PeriodEnd");

INSERT INTO "__EFMigrationsHistory" ("MigrationId", "ProductVersion")
VALUES ('20261111102355_ResultsIndicators', '9.0.8');

ALTER TABLE "Documents" ADD "ClassificationConfidence" REAL NOT NULL DEFAULT 0.0;

ALTER TABLE "Documents" ADD "DeletedAtUtc" TEXT NULL;

ALTER TABLE "Documents" ADD "DocType" TEXT NOT NULL DEFAULT '';

ALTER TABLE "Documents" ADD "IndexedAtUtc" TEXT NULL;

ALTER TABLE "Documents" ADD "IsDeleted" INTEGER NOT NULL DEFAULT 0;

ALTER TABLE "Documents" ADD "Language" TEXT NOT NULL DEFAULT '';

ALTER TABLE "Documents" ADD "LifecyclePhase" TEXT NOT NULL DEFAULT '';

ALTER TABLE "Documents" ADD "MetadataJson" TEXT NOT NULL DEFAULT '{}';

ALTER TABLE "Documents" ADD "StoredFileId" INTEGER NULL;

CREATE TABLE "DocumentChunks" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_DocumentChunks" PRIMARY KEY AUTOINCREMENT,
    "DocumentId" INTEGER NOT NULL,
    "Ordinal" INTEGER NOT NULL,
    "Page" INTEGER NULL,
    "Text" TEXT NOT NULL,
    "Embedding" BLOB NULL,
    "EmbeddingModel" TEXT NOT NULL,
    CONSTRAINT "FK_DocumentChunks_Documents_DocumentId" FOREIGN KEY ("DocumentId") REFERENCES "Documents" ("Id") ON DELETE CASCADE
);

CREATE TABLE "ProjectMilestones" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_ProjectMilestones" PRIMARY KEY AUTOINCREMENT,
    "ProjectId" INTEGER NOT NULL,
    "Title" TEXT NOT NULL,
    "Date" TEXT NOT NULL,
    "Phase" TEXT NOT NULL,
    "Done" INTEGER NOT NULL,
    "SourceDocumentId" INTEGER NULL,
    "IsDeleted" INTEGER NOT NULL DEFAULT 0,
    "DeletedAtUtc" TEXT NULL,
    CONSTRAINT "FK_ProjectMilestones_Documents_SourceDocumentId" FOREIGN KEY ("SourceDocumentId") REFERENCES "Documents" ("Id") ON DELETE RESTRICT,
    CONSTRAINT "FK_ProjectMilestones_Projects_ProjectId" FOREIGN KEY ("ProjectId") REFERENCES "Projects" ("Id") ON DELETE RESTRICT
);

CREATE TABLE "ReportingObligations" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_ReportingObligations" PRIMARY KEY AUTOINCREMENT,
    "ProjectId" INTEGER NOT NULL,
    "FundingAgreementId" INTEGER NULL,
    "Title" TEXT NOT NULL,
    "Kind" TEXT NOT NULL,
    "DueDate" TEXT NOT NULL,
    "Status" TEXT NOT NULL,
    "DeliveredDocumentId" INTEGER NULL,
    "SourceDocumentId" INTEGER NULL,
    "SourceExcerpt" TEXT NOT NULL,
    "Notes" TEXT NOT NULL,
    "IsDeleted" INTEGER NOT NULL DEFAULT 0,
    "DeletedAtUtc" TEXT NULL,
    CONSTRAINT "FK_ReportingObligations_Documents_DeliveredDocumentId" FOREIGN KEY ("DeliveredDocumentId") REFERENCES "Documents" ("Id") ON DELETE RESTRICT,
    CONSTRAINT "FK_ReportingObligations_Documents_SourceDocumentId" FOREIGN KEY ("SourceDocumentId") REFERENCES "Documents" ("Id") ON DELETE RESTRICT,
    CONSTRAINT "FK_ReportingObligations_FundingAgreements_FundingAgreementId" FOREIGN KEY ("FundingAgreementId") REFERENCES "FundingAgreements" ("Id") ON DELETE RESTRICT,
    CONSTRAINT "FK_ReportingObligations_Projects_ProjectId" FOREIGN KEY ("ProjectId") REFERENCES "Projects" ("Id") ON DELETE RESTRICT
);

CREATE INDEX "IX_Documents_StoredFileId" ON "Documents" ("StoredFileId");

CREATE INDEX "IX_DocumentChunks_DocumentId_Ordinal" ON "DocumentChunks" ("DocumentId", "Ordinal");

CREATE INDEX "IX_ProjectMilestones_ProjectId" ON "ProjectMilestones" ("ProjectId");

CREATE INDEX "IX_ProjectMilestones_SourceDocumentId" ON "ProjectMilestones" ("SourceDocumentId");

CREATE INDEX "IX_ReportingObligations_DeliveredDocumentId" ON "ReportingObligations" ("DeliveredDocumentId");

CREATE INDEX "IX_ReportingObligations_FundingAgreementId" ON "ReportingObligations" ("FundingAgreementId");

CREATE INDEX "IX_ReportingObligations_ProjectId_DueDate" ON "ReportingObligations" ("ProjectId", "DueDate");

CREATE INDEX "IX_ReportingObligations_SourceDocumentId" ON "ReportingObligations" ("SourceDocumentId");

UPDATE Documents SET DocType = CASE Category
                    WHEN 'Convention Bailleur' THEN 'Convention' WHEN 'Dossier Projet' THEN 'Document de projet'
                    WHEN 'Budget Initial' THEN 'Budget' WHEN 'Étude de Diagnostic' THEN 'Étude ou diagnostic'
                    WHEN 'Cadre Logique' THEN 'Cadre logique' WHEN 'Avenant' THEN 'Avenant' ELSE 'Autre' END,
                LifecyclePhase = CASE DocumentPhase
                    WHEN 'Diagnostic' THEN 'Identification' WHEN 'Montage' THEN 'Formulation' WHEN 'Rédaction' THEN 'Formulation'
                    WHEN 'Exécution' THEN 'Mise en œuvre' WHEN 'Évaluation' THEN 'Évaluation' WHEN 'Clôture' THEN 'Clôture' ELSE 'Formulation' END,
                ClassificationConfidence = 100
                WHERE DocType = '';

CREATE VIRTUAL TABLE DocumentChunksFts USING fts5(Text, content='DocumentChunks', content_rowid='Id',
                tokenize='unicode61 remove_diacritics 2');

CREATE TRIGGER TR_DocumentChunks_Ai AFTER INSERT ON DocumentChunks BEGIN
                INSERT INTO DocumentChunksFts(rowid, Text) VALUES (new.Id, new.Text); END;

CREATE TRIGGER TR_DocumentChunks_Ad AFTER DELETE ON DocumentChunks BEGIN
                INSERT INTO DocumentChunksFts(DocumentChunksFts, rowid, Text) VALUES ('delete', old.Id, old.Text); END;

CREATE TRIGGER TR_DocumentChunks_Au AFTER UPDATE OF Text ON DocumentChunks BEGIN
                INSERT INTO DocumentChunksFts(DocumentChunksFts, rowid, Text) VALUES ('delete', old.Id, old.Text);
                INSERT INTO DocumentChunksFts(rowid, Text) VALUES (new.Id, new.Text); END;

CREATE TABLE "ef_temp_Documents" (
    "Id" INTEGER NOT NULL CONSTRAINT "PK_Documents" PRIMARY KEY AUTOINCREMENT,
    "AnalyzedDate" TEXT NULL,
    "ApprovedGrantAmount" REAL NOT NULL,
    "Category" TEXT NOT NULL,
    "ClassificationConfidence" REAL NOT NULL,
    "ContractualEndDate" TEXT NULL,
    "DeletedAtUtc" TEXT NULL,
    "DocType" TEXT NOT NULL DEFAULT '',
    "DocumentPhase" TEXT NOT NULL,
    "DocumentReference" TEXT NOT NULL,
    "DocumentVersion" TEXT NOT NULL,
    "DonorName" TEXT NOT NULL,
    "ExtractedSummary" TEXT NOT NULL,
    "FileExtension" TEXT NOT NULL,
    "FilePath" TEXT NOT NULL,
    "FileSize" INTEGER NOT NULL,
    "FullExtractedText" TEXT NOT NULL,
    "IndexedAtUtc" TEXT NULL,
    "IsDeleted" INTEGER NOT NULL DEFAULT 0,
    "IsKeyReference" INTEGER NOT NULL,
    "KeyInsights" TEXT NOT NULL,
    "Language" TEXT NOT NULL DEFAULT '',
    "LifecyclePhase" TEXT NOT NULL DEFAULT '',
    "MetadataJson" TEXT NOT NULL DEFAULT '{}',
    "Notes" TEXT NOT NULL,
    "OriginalFileName" TEXT NOT NULL,
    "ProjectId" INTEGER NOT NULL,
    "SignatureDate" TEXT NULL,
    "StoredFileId" INTEGER NULL,
    "Tags" TEXT NOT NULL,
    "Title" TEXT NOT NULL,
    "UploadedDate" TEXT NOT NULL,
    CONSTRAINT "FK_Documents_Projects_ProjectId" FOREIGN KEY ("ProjectId") REFERENCES "Projects" ("Id") ON DELETE CASCADE,
    CONSTRAINT "FK_Documents_StoredFiles_StoredFileId" FOREIGN KEY ("StoredFileId") REFERENCES "StoredFiles" ("Id") ON DELETE RESTRICT
);

INSERT INTO "ef_temp_Documents" ("Id", "AnalyzedDate", "ApprovedGrantAmount", "Category", "ClassificationConfidence", "ContractualEndDate", "DeletedAtUtc", "DocType", "DocumentPhase", "DocumentReference", "DocumentVersion", "DonorName", "ExtractedSummary", "FileExtension", "FilePath", "FileSize", "FullExtractedText", "IndexedAtUtc", "IsDeleted", "IsKeyReference", "KeyInsights", "Language", "LifecyclePhase", "MetadataJson", "Notes", "OriginalFileName", "ProjectId", "SignatureDate", "StoredFileId", "Tags", "Title", "UploadedDate")
SELECT "Id", "AnalyzedDate", "ApprovedGrantAmount", "Category", "ClassificationConfidence", "ContractualEndDate", "DeletedAtUtc", "DocType", "DocumentPhase", "DocumentReference", "DocumentVersion", "DonorName", "ExtractedSummary", "FileExtension", "FilePath", "FileSize", "FullExtractedText", "IndexedAtUtc", "IsDeleted", "IsKeyReference", "KeyInsights", "Language", "LifecyclePhase", "MetadataJson", "Notes", "OriginalFileName", "ProjectId", "SignatureDate", "StoredFileId", "Tags", "Title", "UploadedDate"
FROM "Documents";

COMMIT;

PRAGMA foreign_keys = 0;

BEGIN TRANSACTION;
DROP TABLE "Documents";

ALTER TABLE "ef_temp_Documents" RENAME TO "Documents";

COMMIT;

PRAGMA foreign_keys = 1;

BEGIN TRANSACTION;
CREATE INDEX "IX_Documents_ProjectId" ON "Documents" ("ProjectId");

CREATE INDEX "IX_Documents_StoredFileId" ON "Documents" ("StoredFileId");

COMMIT;

INSERT INTO "__EFMigrationsHistory" ("MigrationId", "ProductVersion")
VALUES ('20261111105158_DocumentManagement', '9.0.8');

