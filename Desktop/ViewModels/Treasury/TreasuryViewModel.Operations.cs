using System.Collections.ObjectModel;
using AFMI_Gestion_projet.Data;
using AFMI_Gestion_projet.Finance;
using AFMI_Gestion_projet.Models.Finance;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Microsoft.EntityFrameworkCore;

namespace AFMI_Gestion_projet.ViewModels.Treasury
{
    public partial class TreasuryViewModel
    {
        public static IReadOnlyList<Option<OperationNature>> NatureOptions { get; } = new[]
        {
            new Option<OperationNature>(OperationNature.Expense, "Dépense"),
            new Option<OperationNature>(OperationNature.Income, "Recette"),
        };

        private List<BudgetLine> _allBudgetLines = new();
        private List<Category> _allCategories = new();

        public ObservableCollection<OperationRow> Operations { get; } = new();
        [ObservableProperty] private OperationRow? _selectedOperation;

        // Formulaire d'opération ; ventilation sur une ou plusieurs lignes (projet ou fonctionnement, ligne budgétaire, catégorie)
        [ObservableProperty] private DateTime? _opDate = DateTime.Today;
        [ObservableProperty] private string _opLabel = string.Empty;
        [ObservableProperty] private string _opReference = string.Empty;
        [ObservableProperty] private string _opThirdParty = string.Empty;
        [ObservableProperty] private Option<OperationNature>? _opNature;
        [ObservableProperty] private bool _opIsContra;
        [ObservableProperty] private string _opAmount = string.Empty;
        public ObservableCollection<Option<int>> OpCategoryOptions { get; } = new();
        public ObservableCollection<AllocationRowViewModel> AllocationRows { get; } = new();
        [ObservableProperty] private string _allocationSummary = string.Empty;

        // Virement interne
        [ObservableProperty] private Option<int>? _transferFrom;
        [ObservableProperty] private Option<int>? _transferTo;
        [ObservableProperty] private DateTime? _transferDate = DateTime.Today;
        [ObservableProperty] private string _transferAmount = string.Empty;
        [ObservableProperty] private string _transferReceived = string.Empty;
        [ObservableProperty] private string _transferLabel = "Virement interne";

        private void InitOperationDefaults()
        {
            _opNature = NatureOptions[0];
            AllocationRows.Add(NewRow(null));
        }

        private AllocationRowViewModel NewRow(Option<int?>? project)
        {
            var row = new AllocationRowViewModel(() => _allBudgetLines, project ?? ProjectOptions.FirstOrDefault(),
                () => OpNature?.Value == OperationNature.Income);
            row.Category = OpCategoryOptions.FirstOrDefault();
            row.PropertyChanged += (_, e) => { if (e.PropertyName == nameof(AllocationRowViewModel.Amount)) UpdateAllocationSummary(); };
            return row;
        }

        partial void OnOpAmountChanged(string value) => UpdateAllocationSummary();

        private void UpdateAllocationSummary()
        {
            if (AllocationRows.Count <= 1 || !Money.TryParse(OpAmount, out long total)) { AllocationSummary = string.Empty; return; }
            long sum = AllocationRows.Sum(r => Money.TryParse(r.Amount, out long a) ? a : 0);
            AllocationSummary = sum == total ? "✔ Ventilation complète." : $"Reste à ventiler : {Money.Format(total - sum, SelectedAccount?.Account.Currency ?? "MAD")}";
        }

        [RelayCommand]
        private void AddAllocationRow()
        {
            AllocationRows.Add(NewRow(null));
            UpdateAllocationSummary();
        }

        [RelayCommand]
        private void RemoveAllocationRow(AllocationRowViewModel? row)
        {
            if (row == null || AllocationRows.Count <= 1) return;
            AllocationRows.Remove(row);
            UpdateAllocationSummary();
        }

        private void LoadReferenceData(AppDbContext db)
        {
            _allBudgetLines = db.BudgetLines.AsNoTracking().OrderBy(l => l.Code).ToList();
            _allCategories = db.Categories.AsNoTracking().Where(c => c.IsActive).OrderBy(c => c.Label).ToList();
            LoadBudgetReferenceData(db);
            RefreshOperationChoices();
        }

        partial void OnOpNatureChanged(Option<OperationNature>? value)
        {
            RefreshOperationChoices();
            // passage dépense ↔ recette : la ligne proposée suit la nature (ligne « recette » pour un encaissement)
            foreach (var row in AllocationRows) row.RefreshLines(row.Category?.Value, keepCurrent: false);
        }

        private void RefreshOperationChoices()
        {
            var kind = OpNature?.Value == OperationNature.Income ? CategoryKind.Income : CategoryKind.Expense;
            OpCategoryOptions.Clear();
            foreach (var c in _allCategories.Where(c => c.Kind == kind))
                OpCategoryOptions.Add(new Option<int>(c.Id, c.Label));
            foreach (var row in AllocationRows)
            {
                if (row.Category == null || !OpCategoryOptions.Contains(row.Category)) row.Category = OpCategoryOptions.FirstOrDefault();
                if (row.Project == null || !ProjectOptions.Contains(row.Project)) row.Project = ProjectOptions.FirstOrDefault();
                row.RefreshLines(row.Category?.Value);
            }
        }

        private void LoadOperations()
        {
            Operations.Clear();
            if (SelectedAccount == null) return;
            using var db = new AppDbContext();
            var projects = db.Projects.AsNoTracking().ToDictionary(p => p.Id, p => p.Code);
            foreach (var o in db.Operations.Include(o => o.Allocations).AsNoTracking()
                         .Where(o => o.BankAccountId == SelectedAccount.Account.Id)
                         .OrderByDescending(o => o.OperationDate).ThenByDescending(o => o.Id).Take(500).ToList())
            {
                string allocation = o.Nature == OperationNature.InternalTransfer ? "—"
                    : o.Allocations.Count == 0 ? "Non ventilée"
                    : string.Join(", ", o.Allocations.Select(a => a.ProjectId is { } id && projects.TryGetValue(id, out var code) ? code : "Fonctionnement"));
                Operations.Add(new OperationRow(o, allocation));
            }
        }

        /// <summary>
        /// Propose la ventilation d'après les liaisons du compte : projet unique, répartition selon les clés (%),
        /// ou fonctionnement. La ligne budgétaire retenue est celle de la catégorie choisie quand elle est unique.
        /// </summary>
        [RelayCommand]
        private void SplitByKeys()
        {
            if (SelectedAccount == null) return;
            Run(() =>
            {
                using var db = new AppDbContext();
                long amount = Money.TryParse(OpAmount, out long m) && m > 0 ? m : throw new FinanceRuleException("Saisissez d'abord le montant.");
                var suggestion = new AccountService(db).SuggestAllocations(SelectedAccount.Account.Id, RequireDate(OpDate, "Date"), amount);
                if (suggestion.Count == 0) { StatusMessage = "Aucune proposition : le compte n'est lié à aucun projet à cette date."; return; }
                var category = AllocationRows.FirstOrDefault()?.Category;
                AllocationRows.Clear();
                foreach (var s in suggestion)
                {
                    var row = NewRow(ProjectOptions.FirstOrDefault(p => p.Value == s.ProjectId));
                    row.Category = category ?? OpCategoryOptions.FirstOrDefault();
                    row.RefreshLines(row.Category?.Value);
                    row.Amount = suggestion.Count == 1 ? string.Empty : Money.FromMinor(s.AmountMinor).ToString("0.00");
                    AllocationRows.Add(row);
                }
                UpdateAllocationSummary();
                StatusMessage = suggestion.Count == 1 ? "Imputation proposée d'après la liaison du compte." : $"Répartition selon les clés du compte sur {suggestion.Count} projets.";
            });
        }

        private Operation BuildOperation()
        {
            if (SelectedAccount == null) throw new FinanceRuleException("Sélectionnez un compte.");
            long amount = ParseAmount(OpAmount, "Montant");
            if (amount <= 0) throw new FinanceRuleException("Le montant doit être positif (le sens est donné par la nature).");
            var nature = OpNature?.Value ?? OperationNature.Expense;
            bool normalCredit = nature == OperationNature.Income;
            var op = new Operation
            {
                BankAccountId = SelectedAccount.Account.Id,
                OperationDate = RequireDate(OpDate, "Date"),
                Label = OpLabel.Trim(), Reference = OpReference.Trim(), ThirdParty = OpThirdParty.Trim(),
                Nature = nature,
                Direction = normalCredit ^ OpIsContra ? OperationDirection.Credit : OperationDirection.Debit,
                AmountMinor = amount, Currency = SelectedAccount.Account.Currency,
            };
            var rows = AllocationRows.Where(r => r.BudgetLine != null).ToList();
            foreach (var row in rows)
            {
                long part = rows.Count == 1 && string.IsNullOrWhiteSpace(row.Amount) ? amount : ParseAmount(row.Amount, "Montant de la ventilation");
                op.Allocations.Add(new OperationAllocation
                {
                    ProjectId = row.Project?.Value, BudgetLineId = row.BudgetLine!.Value, CategoryId = row.Category?.Value, AmountMinor = part,
                });
            }
            return op;
        }

        [RelayCommand]
        private void SaveDraft()
        {
            RunWrite(() =>
            {
                using var db = new AppDbContext();
                new FinanceService(db).AddDraft(BuildOperation());
                ClearOperationForm();
            }, "Brouillon enregistré.");
            AfterOperationChange();
        }

        [RelayCommand]
        private void SaveAndValidate()
        {
            RunWrite(() =>
            {
                using var db = new AppDbContext();
                using var tx = db.Database.BeginTransaction();
                var svc = new FinanceService(db);
                var op = svc.AddDraft(BuildOperation());
                svc.Validate(op.Id, User);
                tx.Commit();
                ClearOperationForm();
            }, "Opération enregistrée et validée.");
            AfterOperationChange();
        }

        [RelayCommand]
        private void ValidateSelected()
        {
            if (SelectedOperation is not { IsDraft: true }) return;
            RunWrite(() =>
            {
                using var db = new AppDbContext();
                new FinanceService(db).Validate(SelectedOperation.Id, User);
            }, "Opération validée.");
            AfterOperationChange();
        }

        [RelayCommand]
        private void DeleteSelectedOperation()
        {
            if (SelectedOperation == null) return;
            var confirm = System.Windows.MessageBox.Show(
                $"Supprimer l'opération « {SelectedOperation.Label} » du {SelectedOperation.Date} ?\n\nElle reste conservée dans l'historique (suppression logique).",
                "Supprimer une opération", System.Windows.MessageBoxButton.YesNo, System.Windows.MessageBoxImage.Warning);
            if (confirm != System.Windows.MessageBoxResult.Yes) return;
            RunWrite(() =>
            {
                using var db = new AppDbContext();
                var op = db.Operations.Single(o => o.Id == SelectedOperation.Id);
                if (db.ReconciliationMatches.Any(m => m.OperationId == op.Id))
                    throw new FinanceRuleException("Opération rapprochée d'un relevé : annulez d'abord le rapprochement.");
                db.Operations.Remove(op);
                db.SaveChanges();
            }, "Opération supprimée.");
            AfterOperationChange();
        }

        [RelayCommand]
        private void ExecuteTransfer()
        {
            RunWrite(() =>
            {
                if (TransferFrom == null || TransferTo == null) throw new FinanceRuleException("Choisissez les comptes source et destination.");
                long amount = ParseAmount(TransferAmount, "Montant");
                long? received = string.IsNullOrWhiteSpace(TransferReceived) ? null : ParseAmount(TransferReceived, "Montant reçu");
                using var db = new AppDbContext();
                new FinanceService(db).CreateInternalTransfer(TransferFrom.Value, TransferTo.Value, RequireDate(TransferDate, "Date"),
                    amount, string.IsNullOrWhiteSpace(TransferLabel) ? "Virement interne" : TransferLabel.Trim(), User, received);
                TransferAmount = TransferReceived = string.Empty;
            }, "Virement enregistré : il n'apparaît ni en recette ni en dépense.");
            Refresh();
        }

        private void ClearOperationForm()
        {
            OpLabel = OpReference = OpThirdParty = OpAmount = string.Empty;
            OpIsContra = false;
            while (AllocationRows.Count > 1) AllocationRows.RemoveAt(AllocationRows.Count - 1);
            if (AllocationRows.Count == 1) AllocationRows[0].Amount = string.Empty;
        }

        private void AfterOperationChange()
        {
            int? id = SelectedAccount?.Account.Id;
            Refresh();
            if (id != null) SelectedAccount = Accounts.FirstOrDefault(a => a.Account.Id == id);
        }
    }
}
