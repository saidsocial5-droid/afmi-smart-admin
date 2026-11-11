using System.IO;
using System.Collections.ObjectModel;
using AFMI_Gestion_projet.Data;
using AFMI_Gestion_projet.Finance;
using AFMI_Gestion_projet.Services;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Microsoft.EntityFrameworkCore;

namespace AFMI_Gestion_projet.ViewModels.Treasury
{
    /// <summary>Relevés (import CSV), contrôles, rapprochement automatique et manuel, état de rapprochement.</summary>
    public partial class TreasuryViewModel
    {
        public ObservableCollection<StatementRow> Statements { get; } = new();
        [ObservableProperty] private StatementRow? _selectedStatement;
        public ObservableCollection<StatementLineRow> StatementLines { get; } = new();
        [ObservableProperty] private StatementLineRow? _selectedStatementLine;
        public ObservableCollection<OperationRow> UnmatchedOperations { get; } = new();
        [ObservableProperty] private OperationRow? _selectedUnmatchedOperation;

        [ObservableProperty] private string _importOpening = string.Empty;
        [ObservableProperty] private string _importClosing = string.Empty;
        // Valeur initiale : Paramètres › Banques (modifiable ponctuellement à l'écran)
        [ObservableProperty] private string _toleranceDays = ReadToleranceDays().ToString();

        private static int ReadToleranceDays()
        {
            try
            {
                using var db = new AppDbContext();
                return new SettingsService(db).Get<int>(SettingKeys.ReconciliationToleranceDays);
            }
            catch (Exception)
            {
                return ReconciliationService.DefaultToleranceDays;
            }
        }
        [ObservableProperty] private string _statementCheckText = string.Empty;
        [ObservableProperty] private string _reconciliationSummary = string.Empty;

        partial void OnSelectedStatementChanged(StatementRow? value) => LoadReconciliation();

        private void LoadStatements()
        {
            Statements.Clear();
            if (SelectedAccount == null) { LoadReconciliation(); return; }
            using var db = new AppDbContext();
            foreach (var s in db.BankStatements.AsNoTracking().Where(s => s.BankAccountId == SelectedAccount.Account.Id).OrderByDescending(s => s.PeriodEnd))
                Statements.Add(new StatementRow(s));
            SelectedStatement = Statements.FirstOrDefault();
        }

        private void LoadReconciliation()
        {
            StatementLines.Clear();
            UnmatchedOperations.Clear();
            StatementCheckText = ReconciliationSummary = string.Empty;
            if (SelectedStatement == null) return;
            using var db = new AppDbContext();
            var svc = new ReconciliationService(db);
            int id = SelectedStatement.Statement.Id;

            foreach (var l in db.StatementLines.Include(l => l.Match).ThenInclude(m => m!.Operation).AsNoTracking()
                         .Where(l => l.BankStatementId == id).OrderBy(l => l.OperationDate).ThenBy(l => l.Id))
                StatementLines.Add(new StatementLineRow(l, l.Match?.Operation is { } op
                    ? $"{(l.Match.Mode == Models.Finance.MatchMode.Auto ? "Auto" : "Manuel")} : {op.OperationDate:dd/MM} {op.Label}" : "Non rapprochée"));

            var check = svc.Check(id);
            StatementCheckText = check.Errors.Count + check.Warnings.Count == 0
                ? "✔ Contrôles du relevé : soldes cohérents, pas de doublon, continuité respectée."
                : string.Join("\n", check.Errors.Select(e => "⛔ " + e).Concat(check.Warnings.Select(w => "⚠️ " + w)));

            var report = svc.GetReport(id);
            foreach (var o in report.UnmatchedOperations) UnmatchedOperations.Add(new OperationRow(o, ""));
            ReconciliationSummary =
                $"Solde relevé : {Money.Format(report.BankClosingMinor)}   |   Solde comptable : {Money.Format(report.BookBalanceMinor)}\n" +
                $"Opérations non passées en banque : {report.UnmatchedOperations.Count}   |   Mouvements bancaires non comptabilisés : {report.UnmatchedLines.Count}\n" +
                (report.UnexplainedDifferenceMinor == 0 ? "✔ Écart inexpliqué : aucun." : $"⛔ Écart inexpliqué : {Money.Format(report.UnexplainedDifferenceMinor)}");
        }

        [RelayCommand]
        private void ImportCsvStatement()
        {
            if (SelectedAccount == null) { ErrorMessage = "Sélectionnez le compte du relevé."; return; }
            var dialog = new Microsoft.Win32.OpenFileDialog { Filter = "Relevé exporté par la banque (*.csv;*.txt)|*.csv;*.txt", Title = "Importer un relevé CSV" };
            if (dialog.ShowDialog() != true) return;
            Run(() =>
            {
                long opening = ParseAmount(ImportOpening, "Solde initial du relevé");
                long closing = ParseAmount(ImportClosing, "Solde final du relevé");
                string content = ReadText(dialog.FileName);
                var parsed = StatementCsvImporter.Parse(content);
                if (parsed.Lines.Count == 0) throw new FinanceRuleException("Aucune ligne lue. " + string.Join(" ", parsed.Errors.Take(3)));
                using var db = new AppDbContext();
                var st = StatementCsvImporter.Import(db, SelectedAccount.Account.Id, parsed, opening, closing);
                StatusMessage = $"{parsed.Lines.Count} ligne(s) importée(s) en brouillon." +
                                (parsed.Errors.Count > 0 ? $" {parsed.Errors.Count} ligne(s) ignorée(s) : " + string.Join(" ", parsed.Errors.Take(3)) : "");
                ImportOpening = ImportClosing = string.Empty;
            });
            LoadStatements();
        }

        /// <summary>UTF-8 si le fichier est valide en UTF-8, sinon Windows-1252 (exports bancaires courants).</summary>
        private static string ReadText(string path)
        {
            byte[] bytes = File.ReadAllBytes(path);
            try { return new System.Text.UTF8Encoding(false, true).GetString(bytes).TrimStart('﻿'); }
            catch (System.Text.DecoderFallbackException)
            {
                System.Text.Encoding.RegisterProvider(System.Text.CodePagesEncodingProvider.Instance);
                return System.Text.Encoding.GetEncoding(1252).GetString(bytes);
            }
        }

        [RelayCommand]
        private void ValidateStatement()
        {
            if (SelectedStatement == null) return;
            Run(() =>
            {
                using var db = new AppDbContext();
                new ReconciliationService(db).Validate(SelectedStatement.Statement.Id);
            }, "Relevé validé.");
            LoadStatements();
        }

        [RelayCommand]
        private void AutoMatch()
        {
            if (SelectedStatement == null) return;
            Run(() =>
            {
                if (!int.TryParse(ToleranceDays, out int days) || days is < 0 or > 30) throw new FinanceRuleException("Tolérance de 0 à 30 jours.");
                using var db = new AppDbContext();
                int n = new ReconciliationService(db).AutoMatch(SelectedStatement.Statement.Id, User, days);
                StatusMessage = $"{n} rapprochement(s) automatique(s). Les cas ambigus restent à rapprocher manuellement.";
            });
            LoadReconciliation();
        }

        [RelayCommand]
        private void ManualMatch()
        {
            Run(() =>
            {
                if (SelectedStatementLine == null || SelectedUnmatchedOperation == null)
                    throw new FinanceRuleException("Sélectionnez une ligne de relevé et une opération non rapprochée.");
                using var db = new AppDbContext();
                new ReconciliationService(db).Match(SelectedStatementLine.Id, SelectedUnmatchedOperation.Id, User);
            }, "Rapprochement manuel enregistré.");
            LoadReconciliation();
        }

        [RelayCommand]
        private void Unmatch()
        {
            if (SelectedStatementLine is not { IsMatched: true }) return;
            Run(() =>
            {
                using var db = new AppDbContext();
                new ReconciliationService(db).Unmatch(SelectedStatementLine.Id);
            }, "Rapprochement annulé.");
            LoadReconciliation();
        }

        [RelayCommand]
        private void ExportReconciliation(string? format)
        {
            if (SelectedStatement == null) return;
            bool pdf = !string.Equals(format, "csv", StringComparison.OrdinalIgnoreCase);
            var dialog = new Microsoft.Win32.SaveFileDialog
            {
                Filter = pdf ? "PDF (*.pdf)|*.pdf" : "CSV (*.csv)|*.csv",
                FileName = $"AFMI_EtatRapprochement_{SelectedAccount?.Title}_{SelectedStatement.Statement.PeriodEnd:yyyyMMdd}".Replace(' ', '_') + (pdf ? ".pdf" : ".csv"),
            };
            if (dialog.ShowDialog() != true) return;
            Run(() =>
            {
                using var db = new AppDbContext();
                var report = new ReconciliationService(db).GetReport(SelectedStatement.Statement.Id);
                if (pdf) ReconciliationExportService.ExportPdf(report, dialog.FileName);
                else ReconciliationExportService.ExportCsv(report, dialog.FileName);
            }, $"État de rapprochement exporté : {dialog.FileName}");
        }
    }
}
