using System.Collections.ObjectModel;
using AFMI_Gestion_projet.Models.Finance;
using CommunityToolkit.Mvvm.ComponentModel;

namespace AFMI_Gestion_projet.ViewModels.Treasury
{
    /// <summary>Une ligne de ventilation de l'opération en saisie : projet (ou fonctionnement), ligne budgétaire, catégorie, montant.</summary>
    public partial class AllocationRowViewModel : ObservableObject
    {
        private readonly Func<IReadOnlyList<BudgetLine>> _lines;

        public AllocationRowViewModel(Func<IReadOnlyList<BudgetLine>> lines, Option<int?>? project)
        {
            _lines = lines;
            _project = project;
            RefreshLines();
        }

        [ObservableProperty] private Option<int?>? _project;
        [ObservableProperty] private Option<int>? _budgetLine;
        [ObservableProperty] private Option<int>? _category;
        /// <summary>Vide sur une ligne unique = montant total de l'opération.</summary>
        [ObservableProperty] private string _amount = string.Empty;

        public ObservableCollection<Option<int>> BudgetLineOptions { get; } = new();

        partial void OnProjectChanged(Option<int?>? value) => RefreshLines();

        public void RefreshLines(int? preferredCategoryId = null)
        {
            int? keep = BudgetLine?.Value;
            BudgetLineOptions.Clear();
            var lines = _lines().Where(l => l.ProjectId == Project?.Value).ToList();
            foreach (var l in lines) BudgetLineOptions.Add(new Option<int>(l.Id, $"{l.Code} — {l.Label}"));
            var byCategory = preferredCategoryId is { } c ? lines.Where(l => l.CategoryId == c).ToList() : new List<BudgetLine>();
            BudgetLine = BudgetLineOptions.FirstOrDefault(o => o.Value == keep)
                         ?? (byCategory.Count == 1 ? BudgetLineOptions.First(o => o.Value == byCategory[0].Id) : BudgetLineOptions.FirstOrDefault());
        }
    }
}
