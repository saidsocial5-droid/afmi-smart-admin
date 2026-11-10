using System.IO;
using System.Collections.ObjectModel;
using AFMI_Gestion_projet.Data;
using AFMI_Gestion_projet.Finance;
using AFMI_Gestion_projet.Models;
using AFMI_Gestion_projet.Models.Finance;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Microsoft.EntityFrameworkCore;

namespace AFMI_Gestion_projet.ViewModels.Treasury
{
    /// <summary>
    /// Écran Trésorerie (Lot 2). Toute règle financière est dans Core/Finance (testée) : ce ViewModel ne fait que
    /// collecter les saisies, appeler les services et afficher leurs résultats ou leurs refus.
    /// </summary>
    public partial class TreasuryViewModel : ObservableObject
    {
        public static IReadOnlyList<Option<AccountKind>> KindOptions { get; } =
            new[] { new Option<AccountKind>(AccountKind.Bank, "Banque"), new Option<AccountKind>(AccountKind.Cash, "Caisse") };

        public static IReadOnlyList<Option<AccountPurpose>> PurposeOptions { get; } =
            Enum.GetValues<AccountPurpose>().Select(p => new Option<AccountPurpose>(p, TreasuryLabels.Purpose(p))).ToList();

        public static IReadOnlyList<Option<AllocationMode>> AllocationModeOptions { get; } = new[]
        {
            new Option<AllocationMode>(AllocationMode.None, "Sans clé"),
            new Option<AllocationMode>(AllocationMode.Percentage, "Pourcentage"),
            new Option<AllocationMode>(AllocationMode.FixedAmount, "Montant"),
        };

        [ObservableProperty] private string _statusMessage = string.Empty;
        [ObservableProperty] private string _errorMessage = string.Empty;
        [ObservableProperty] private string _consolidatedText = string.Empty;

        public ObservableCollection<AccountRow> Accounts { get; } = new();
        public ObservableCollection<Option<int?>> ProjectOptions { get; } = new();
        public ObservableCollection<Option<int>> AccountOptions { get; } = new();

        [ObservableProperty] private AccountRow? _selectedAccount;

        // Formulaire compte
        [ObservableProperty] private bool _isEditingAccount;
        [ObservableProperty] private int _editAccountId;
        [ObservableProperty] private string _editTitle = string.Empty;
        [ObservableProperty] private Option<AccountKind>? _editKind;
        [ObservableProperty] private Option<AccountPurpose>? _editPurpose;
        [ObservableProperty] private string _editBankName = string.Empty;
        [ObservableProperty] private string _editBranch = string.Empty;
        [ObservableProperty] private string _editRib = string.Empty;
        [ObservableProperty] private string _editCurrency = "MAD";
        [ObservableProperty] private string _editOpeningBalance = "0";
        [ObservableProperty] private DateTime? _editOpeningDate = DateTime.Today;
        [ObservableProperty] private string _editThreshold = string.Empty;
        [ObservableProperty] private string _editNotes = string.Empty;
        [ObservableProperty] private DateTime? _closingDate = DateTime.Today;

        // Liaisons compte ↔ projets
        public ObservableCollection<LinkRow> Links { get; } = new();
        [ObservableProperty] private LinkRow? _selectedLink;
        [ObservableProperty] private Option<int?>? _linkProject;
        [ObservableProperty] private DateTime? _linkFrom = new DateTime(DateTime.Today.Year, 1, 1);
        [ObservableProperty] private DateTime? _linkTo;
        [ObservableProperty] private Option<AllocationMode>? _linkMode;
        [ObservableProperty] private string _linkValue = string.Empty;

        public TreasuryViewModel()
        {
            _editKind = KindOptions[0];
            _editPurpose = PurposeOptions[0];
            _linkMode = AllocationModeOptions[0];
            InitOperationDefaults();
        }

        private static DateOnly Today => DateOnly.FromDateTime(DateTime.Today);
        private static string User => AuditContext.CurrentUser;

        /// <summary>Exécute une action en affichant le refus d'une règle métier au lieu de planter.</summary>
        private void Run(Action action, string? success = null)
        {
            ErrorMessage = string.Empty;
            StatusMessage = string.Empty;
            try
            {
                action();
                if (success != null) StatusMessage = success;
            }
            catch (Exception ex) when (ex is FinanceRuleException or OperationValidationException or MissingExchangeRateException
                                           or ArgumentException or InvalidOperationException or DbUpdateException or IOException)
            {
                ErrorMessage = ex is DbUpdateException ? "Enregistrement refusé par la base : " + ex.GetBaseException().Message : ex.Message;
            }
        }

        private static long ParseAmount(string text, string field)
        {
            if (!Money.TryParse(text, out long minor)) throw new FinanceRuleException($"{field} : montant illisible « {text} ».");
            return minor;
        }

        private static DateOnly RequireDate(DateTime? value, string field) =>
            value is { } d ? DateOnly.FromDateTime(d) : throw new FinanceRuleException($"{field} : date obligatoire.");

        [RelayCommand]
        public void Refresh()
        {
            Run(() =>
            {
                int? selectedId = SelectedAccount?.Account.Id;
                using var db = new AppDbContext();
                var finance = new FinanceService(db);

                ProjectOptions.Clear();
                ProjectOptions.Add(new Option<int?>(null, "— Fonctionnement général —"));
                foreach (var p in db.Projects.AsNoTracking().OrderBy(p => p.Code))
                    ProjectOptions.Add(new Option<int?>(p.Id, $"{p.Code} — {p.Name}"));

                Accounts.Clear();
                AccountOptions.Clear();
                foreach (var a in db.BankAccounts.AsNoTracking().OrderBy(a => a.Status).ThenBy(a => a.Title).ToList())
                {
                    Accounts.Add(new AccountRow(a, finance.GetBalanceMinor(a.Id, Today)));
                    if (a.Status == AccountStatus.Active) AccountOptions.Add(new Option<int>(a.Id, $"{a.Title} ({a.Currency})"));
                }
                try { ConsolidatedText = "Solde consolidé : " + Money.Format(finance.GetConsolidatedBalanceMadMinor(Today)); }
                catch (MissingExchangeRateException ex) { ConsolidatedText = "Solde consolidé indisponible : " + ex.Message; }

                SelectedAccount = Accounts.FirstOrDefault(r => r.Account.Id == selectedId) ?? Accounts.FirstOrDefault();
                LoadReferenceData(db);
            });
            RefreshForecast();
        }

        partial void OnSelectedAccountChanged(AccountRow? value)
        {
            LoadLinks();
            LoadOperations();
            LoadStatements();
        }

        [RelayCommand]
        private void NewAccount()
        {
            EditAccountId = 0;
            EditTitle = EditBankName = EditBranch = EditRib = EditNotes = EditThreshold = string.Empty;
            EditCurrency = Money.DefaultCurrency;
            EditOpeningBalance = "0";
            EditOpeningDate = DateTime.Today;
            EditKind = KindOptions[0];
            EditPurpose = PurposeOptions[0];
            IsEditingAccount = true;
        }

        [RelayCommand]
        private void EditSelectedAccount()
        {
            if (SelectedAccount == null) return;
            var a = SelectedAccount.Account;
            EditAccountId = a.Id;
            EditTitle = a.Title;
            EditKind = KindOptions.First(o => o.Value == a.Kind);
            EditPurpose = PurposeOptions.First(o => o.Value == a.Purpose);
            EditBankName = a.BankName;
            EditBranch = a.Branch;
            EditRib = Rib.Format(a.Rib);
            EditCurrency = a.Currency;
            EditOpeningBalance = Money.FromMinor(a.OpeningBalanceMinor).ToString("0.00");
            EditOpeningDate = a.OpeningDate.ToDateTime(TimeOnly.MinValue);
            EditThreshold = a.LowBalanceThresholdMinor is { } t ? Money.FromMinor(t).ToString("0.00") : string.Empty;
            EditNotes = a.Notes;
            IsEditingAccount = true;
        }

        [RelayCommand]
        private void CancelAccount() => IsEditingAccount = false;

        [RelayCommand]
        private void SaveAccount()
        {
            Run(() =>
            {
                using var db = new AppDbContext();
                var account = EditAccountId == 0 ? new BankAccount() : db.BankAccounts.Single(a => a.Id == EditAccountId);
                account.Title = EditTitle.Trim();
                account.Kind = EditKind?.Value ?? AccountKind.Bank;
                account.Purpose = EditPurpose?.Value ?? AccountPurpose.Operating;
                account.BankName = EditBankName.Trim();
                account.Branch = EditBranch.Trim();
                account.Rib = EditRib;
                account.Currency = EditCurrency;
                account.OpeningBalanceMinor = ParseAmount(EditOpeningBalance, "Solde d'ouverture");
                account.OpeningDate = RequireDate(EditOpeningDate, "Date d'ouverture");
                account.LowBalanceThresholdMinor = string.IsNullOrWhiteSpace(EditThreshold) ? null : ParseAmount(EditThreshold, "Seuil d'alerte");
                account.Notes = EditNotes;
                var warnings = new AccountService(db).Save(account);
                IsEditingAccount = false;
                StatusMessage = warnings.Count == 0 ? "Compte enregistré." : "Compte enregistré. " + string.Join(" ", warnings);
            });
            Refresh();
        }

        [RelayCommand]
        private void CloseSelectedAccount()
        {
            if (SelectedAccount == null) return;
            Run(() =>
            {
                using var db = new AppDbContext();
                new AccountService(db).Close(SelectedAccount.Account.Id, RequireDate(ClosingDate, "Date de clôture"));
            }, "Compte clôturé.");
            Refresh();
        }

        private void LoadLinks()
        {
            Links.Clear();
            if (SelectedAccount == null) return;
            using var db = new AppDbContext();
            foreach (var l in db.AccountProjectLinks.Include(l => l.Project).AsNoTracking()
                         .Where(l => l.BankAccountId == SelectedAccount.Account.Id).OrderBy(l => l.ValidFrom))
                Links.Add(new LinkRow(l, l.Project == null ? "?" : $"{l.Project.Code} — {l.Project.Name}"));
        }

        [RelayCommand]
        private void AddLink()
        {
            if (SelectedAccount == null) return;
            Run(() =>
            {
                if (LinkProject?.Value is not { } projectId) throw new FinanceRuleException("Choisissez un projet.");
                var mode = LinkMode?.Value ?? AllocationMode.None;
                var link = new AccountProjectLink
                {
                    BankAccountId = SelectedAccount.Account.Id, ProjectId = projectId,
                    ValidFrom = RequireDate(LinkFrom, "Début de validité"),
                    ValidTo = LinkTo is { } to ? DateOnly.FromDateTime(to) : null,
                    AllocationMode = mode,
                };
                if (mode == AllocationMode.Percentage)
                    link.AllocationPercent = decimal.TryParse(LinkValue.Replace(',', '.').Trim('%', ' '), System.Globalization.NumberStyles.Number,
                        System.Globalization.CultureInfo.InvariantCulture, out var pct) ? pct : throw new FinanceRuleException("Pourcentage illisible.");
                if (mode == AllocationMode.FixedAmount) link.AllocationAmountMinor = ParseAmount(LinkValue, "Montant de la clé");
                using var db = new AppDbContext();
                new AccountService(db).SaveLink(link);
            }, "Liaison enregistrée.");
            LoadLinks();
        }

        [RelayCommand]
        private void DeleteLink()
        {
            if (SelectedLink == null) return;
            Run(() =>
            {
                using var db = new AppDbContext();
                db.AccountProjectLinks.Remove(db.AccountProjectLinks.Single(l => l.Id == SelectedLink.Link.Id));
                db.SaveChanges();
            }, "Liaison supprimée.");
            LoadLinks();
        }

        /// <summary>Reprise des transactions de Smart Office 1.x en brouillons sur le compte sélectionné.</summary>
        [RelayCommand]
        private void ImportLegacySmartOffice()
        {
            if (SelectedAccount == null) { ErrorMessage = "Sélectionnez d'abord le compte qui recevra les transactions reprises."; return; }
            string? path = new[]
            {
                Path.Combine(Services.SmartOfficeHostService.InstalledDataDir, "afmi_smartoffice.db"),
                Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "SmartOffice", "backend", "data", "afmi_smartoffice.db"),
            }.Select(Path.GetFullPath).FirstOrDefault(File.Exists);
            if (path == null)
            {
                var dialog = new Microsoft.Win32.OpenFileDialog { Filter = "Base Smart Office (afmi_smartoffice.db)|*.db", Title = "Base Smart Office 1.x" };
                if (dialog.ShowDialog() != true) return;
                path = dialog.FileName;
            }
            var confirm = System.Windows.MessageBox.Show(
                $"Reprendre les transactions de Smart Office en brouillons sur « {SelectedAccount.Title} » ?\n\n{path}\n\n" +
                "Elles devront être ventilées puis validées. Une transaction déjà reprise n'est jamais dupliquée.",
                "Reprise Smart Office 1.x", System.Windows.MessageBoxButton.YesNo, System.Windows.MessageBoxImage.Question);
            if (confirm != System.Windows.MessageBoxResult.Yes) return;
            Run(() =>
            {
                using var db = new AppDbContext();
                var r = new LegacySmartOfficeImporter(db).Import(path, SelectedAccount.Account.Id);
                StatusMessage = $"{r.OperationsCreated} transaction(s) reprise(s) en brouillon, {r.ProjectsCreated} projet(s) créé(s), {r.Skipped} ignorée(s)."
                                + (r.Messages.Count > 0 ? " " + string.Join(" ", r.Messages.Take(5)) : "");
            });
            Refresh();
        }
    }
}
