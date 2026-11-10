using System.Collections.ObjectModel;
using AFMI_Gestion_projet.Data;
using AFMI_Gestion_projet.Finance;
using AFMI_Gestion_projet.Models.Finance;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Microsoft.EntityFrameworkCore;

namespace AFMI_Gestion_projet.ViewModels.Treasury
{
    /// <summary>Lignes budgétaires, conventions et échéanciers (données des imputations et de la prévision), taux de change.</summary>
    public partial class TreasuryViewModel
    {
        public ObservableCollection<Option<int>> FunderOptions { get; } = new();
        public ObservableCollection<Option<int>> ExpenseCategoryOptions { get; } = new();

        [ObservableProperty] private Option<int?>? _budgetProject;
        public ObservableCollection<BudgetLineRow> BudgetLines { get; } = new();
        [ObservableProperty] private BudgetLineRow? _selectedBudgetLine;
        [ObservableProperty] private string _lineCode = string.Empty;
        [ObservableProperty] private string _lineLabel = string.Empty;
        [ObservableProperty] private Option<int>? _lineCategory;
        [ObservableProperty] private string _linePlanned = string.Empty;
        [ObservableProperty] private string _lineCurrency = "MAD";

        public ObservableCollection<Option<int>> Agreements { get; } = new();
        [ObservableProperty] private Option<int>? _selectedAgreement;
        [ObservableProperty] private Option<int>? _agreementFunder;
        [ObservableProperty] private string _agreementReference = string.Empty;
        [ObservableProperty] private string _agreementAmount = string.Empty;
        [ObservableProperty] private string _agreementCurrency = "MAD";
        [ObservableProperty] private string _agreementRate = string.Empty;
        [ObservableProperty] private DateTime? _agreementStart;
        [ObservableProperty] private DateTime? _agreementEnd;

        public ObservableCollection<TrancheRow> Tranches { get; } = new();
        [ObservableProperty] private TrancheRow? _selectedTranche;
        [ObservableProperty] private string _trancheLabel = string.Empty;
        [ObservableProperty] private DateTime? _trancheDate = DateTime.Today;
        [ObservableProperty] private string _trancheAmount = string.Empty;
        public ObservableCollection<Option<int>> IncomeOperationOptions { get; } = new();
        [ObservableProperty] private Option<int>? _trancheOperation;

        [ObservableProperty] private string _rateCurrency = "EUR";
        [ObservableProperty] private DateTime? _rateDate = DateTime.Today;
        [ObservableProperty] private string _rateValue = string.Empty;
        [ObservableProperty] private string _ratesText = string.Empty;

        private void LoadBudgetReferenceData(AppDbContext db)
        {
            FunderOptions.Clear();
            foreach (var f in db.Funders.AsNoTracking().OrderBy(f => f.Name)) FunderOptions.Add(new Option<int>(f.Id, f.Name));
            ExpenseCategoryOptions.Clear();
            foreach (var c in _allCategories) ExpenseCategoryOptions.Add(new Option<int>(c.Id, (c.Kind == CategoryKind.Income ? "Recette — " : "Dépense — ") + c.Label));
            RatesText = string.Join("   ", db.CurrencyRates.AsNoTracking().OrderByDescending(r => r.Date).Take(8).ToList()
                .Select(r => $"{r.Currency} {r.Date:dd/MM/yyyy} : {r.RateToMad}"));
            BudgetProject ??= ProjectOptions.FirstOrDefault();
            LoadBudget();
        }

        partial void OnBudgetProjectChanged(Option<int?>? value) => LoadBudget();
        partial void OnSelectedAgreementChanged(Option<int>? value) => LoadTranches();

        private void LoadBudget()
        {
            BudgetLines.Clear();
            Agreements.Clear();
            if (BudgetProject == null) return;
            using var db = new AppDbContext();
            int? project = BudgetProject.Value;
            var lines = db.BudgetLines.Include(l => l.Category).AsNoTracking().Where(l => l.ProjectId == project).OrderBy(l => l.Code).ToList();
            var realized = new TreasuryForecastService(db).RealizedMadByBudgetLine(lines.Select(l => l.Id).ToList());
            foreach (var l in lines) BudgetLines.Add(new BudgetLineRow(l, realized.GetValueOrDefault(l.Id)));

            if (project is { } pid)
            {
                foreach (var a in db.FundingAgreements.Include(a => a.Funder).AsNoTracking().Where(a => a.ProjectId == pid))
                    Agreements.Add(new Option<int>(a.Id, $"{a.Reference} — {a.Funder?.Name} — {Money.Format(a.AmountMinor, a.Currency)}"));
                IncomeOperationOptions.Clear();
                foreach (var o in db.Operations.AsNoTracking()
                             .Where(o => o.Nature == OperationNature.Income && o.Status == OperationStatus.Validated
                                         && o.Allocations.Any(al => al.ProjectId == pid))
                             .OrderByDescending(o => o.OperationDate).Take(100))
                    IncomeOperationOptions.Add(new Option<int>(o.Id, $"{o.OperationDate:dd/MM/yyyy} — {o.Label} — {Money.Format(o.AmountMinor, o.Currency)}"));
            }
            SelectedAgreement = Agreements.FirstOrDefault();
        }

        private void LoadTranches()
        {
            Tranches.Clear();
            if (SelectedAgreement == null) return;
            using var db = new AppDbContext();
            foreach (var t in db.FundingTranches.Include(t => t.FundingAgreement).AsNoTracking()
                         .Where(t => t.FundingAgreementId == SelectedAgreement.Value).OrderBy(t => t.ExpectedDate))
                Tranches.Add(new TrancheRow(t));
        }

        [RelayCommand]
        private void AddBudgetLine()
        {
            Run(() =>
            {
                if (string.IsNullOrWhiteSpace(LineLabel)) throw new FinanceRuleException("Libellé de la ligne obligatoire.");
                using var db = new AppDbContext();
                db.BudgetLines.Add(new BudgetLine
                {
                    ProjectId = BudgetProject?.Value, FundingAgreementId = SelectedAgreement?.Value,
                    Code = LineCode.Trim(), Label = LineLabel.Trim(), CategoryId = LineCategory?.Value,
                    PlannedMinor = ParseAmount(LinePlanned, "Montant prévu"), Currency = Money.NormalizeCurrency(LineCurrency),
                });
                db.SaveChanges();
                LineCode = LineLabel = LinePlanned = string.Empty;
                LoadReferenceData(db);
            }, "Ligne budgétaire ajoutée.");
        }

        [RelayCommand]
        private void DeleteBudgetLine()
        {
            if (SelectedBudgetLine == null) return;
            Run(() =>
            {
                using var db = new AppDbContext();
                if (db.OperationAllocations.Any(a => a.BudgetLineId == SelectedBudgetLine.Line.Id))
                    throw new FinanceRuleException("Des opérations sont imputées sur cette ligne : elle ne peut pas être supprimée.");
                db.BudgetLines.Remove(db.BudgetLines.Single(l => l.Id == SelectedBudgetLine.Line.Id));
                db.SaveChanges();
                LoadReferenceData(db);
            }, "Ligne budgétaire supprimée.");
        }

        [RelayCommand]
        private void AddAgreement()
        {
            Run(() =>
            {
                if (BudgetProject?.Value is not { } projectId) throw new FinanceRuleException("Une convention concerne un projet : choisissez-le.");
                if (AgreementFunder == null) throw new FinanceRuleException("Choisissez le bailleur (menu Bailleurs de fonds pour en créer un).");
                decimal? rate = null;
                if (!string.IsNullOrWhiteSpace(AgreementRate))
                    rate = decimal.TryParse(AgreementRate.Replace(',', '.'), System.Globalization.NumberStyles.Number, System.Globalization.CultureInfo.InvariantCulture, out var r) && r > 0
                        ? r : throw new FinanceRuleException("Taux contractuel illisible.");
                using var db = new AppDbContext();
                db.FundingAgreements.Add(new FundingAgreement
                {
                    ProjectId = projectId, FunderId = AgreementFunder.Value, Reference = AgreementReference.Trim(),
                    AmountMinor = ParseAmount(AgreementAmount, "Montant de la convention"), Currency = Money.NormalizeCurrency(AgreementCurrency),
                    ContractualRateToMad = rate,
                    StartDate = AgreementStart is { } s ? DateOnly.FromDateTime(s) : null,
                    EndDate = AgreementEnd is { } e ? DateOnly.FromDateTime(e) : null,
                });
                db.SaveChanges();
                AgreementReference = AgreementAmount = AgreementRate = string.Empty;
            }, "Convention ajoutée.");
            LoadBudget();
        }

        [RelayCommand]
        private void AddTranche()
        {
            Run(() =>
            {
                if (SelectedAgreement == null) throw new FinanceRuleException("Choisissez une convention.");
                using var db = new AppDbContext();
                db.FundingTranches.Add(new FundingTranche
                {
                    FundingAgreementId = SelectedAgreement.Value, Label = TrancheLabel.Trim(),
                    ExpectedDate = RequireDate(TrancheDate, "Date prévue"), AmountMinor = ParseAmount(TrancheAmount, "Montant de la tranche"),
                });
                db.SaveChanges();
                TrancheLabel = TrancheAmount = string.Empty;
            }, "Tranche ajoutée à l'échéancier.");
            LoadTranches();
        }

        [RelayCommand]
        private void MarkTrancheReceived()
        {
            Run(() =>
            {
                if (SelectedTranche == null || TrancheOperation == null) throw new FinanceRuleException("Choisissez la tranche et l'opération de recette qui l'a encaissée.");
                using var db = new AppDbContext();
                if (db.FundingTranches.Any(t => t.ReceivedOperationId == TrancheOperation.Value))
                    throw new FinanceRuleException("Cette opération encaisse déjà une autre tranche.");
                db.FundingTranches.Single(t => t.Id == SelectedTranche.Tranche.Id).ReceivedOperationId = TrancheOperation.Value;
                db.SaveChanges();
            }, "Tranche marquée comme encaissée.");
            LoadTranches();
            RefreshForecast();
        }

        [RelayCommand]
        private void AddRate()
        {
            Run(() =>
            {
                if (!decimal.TryParse(RateValue.Replace(',', '.'), System.Globalization.NumberStyles.Number, System.Globalization.CultureInfo.InvariantCulture, out var rate) || rate <= 0)
                    throw new FinanceRuleException("Taux illisible.");
                using var db = new AppDbContext();
                string currency = Money.NormalizeCurrency(RateCurrency);
                if (currency == Money.DefaultCurrency) throw new FinanceRuleException("Le MAD est la devise de référence.");
                var date = RequireDate(RateDate, "Date du taux");
                var existing = db.CurrencyRates.SingleOrDefault(r => r.Currency == currency && r.Date == date);
                if (existing != null) existing.RateToMad = rate;
                else db.CurrencyRates.Add(new CurrencyRate { Currency = currency, Date = date, RateToMad = rate, Source = "Saisie" });
                db.SaveChanges();
                RateValue = string.Empty;
            }, "Taux enregistré.");
            Refresh();
        }
    }
}
