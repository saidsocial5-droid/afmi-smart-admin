using AFMI_Gestion_projet.Data;
using AFMI_Gestion_projet.Models.Finance;
using Microsoft.EntityFrameworkCore;

namespace AFMI_Gestion_projet.Finance
{
    public sealed record ForecastMonth(int Year, int Month, long OpeningMadMinor, long InflowMadMinor, long OutflowMadMinor)
    {
        public long ClosingMadMinor => OpeningMadMinor + InflowMadMinor - OutflowMadMinor;
        public string Label => new DateTime(Year, Month, 1).ToString("MMMM yyyy", System.Globalization.CultureInfo.GetCultureInfo("fr-FR"));
    }

    public sealed record TreasuryForecast(DateOnly AsOf, long StartingMadMinor, IReadOnlyList<ForecastMonth> Months, IReadOnlyList<string> Notes)
    {
        public long LowestClosingMadMinor => Months.Count == 0 ? StartingMadMinor : Months.Min(m => m.ClosingMadMinor);
    }

    /// <summary>
    /// Prévision de trésorerie consolidée (MAD), mois par mois.
    /// Encaissements : tranches de conventions non encore reçues (une tranche en retard est comptée le premier mois).
    /// Décaissements : reste à consommer de chaque ligne budgétaire (prévu − réalisé), réparti uniformément jusqu'à la fin
    /// du projet (ou de l'exercice pour le fonctionnement, sinon sur tout l'horizon). Hypothèses rappelées dans Notes.
    /// </summary>
    public sealed class TreasuryForecastService(AppDbContext db)
    {
        private static readonly string[] FinishedStatuses = { "Clôture", "Archivé" };

        public TreasuryForecast Forecast(DateOnly asOf, int months)
        {
            if (months is < 1 or > 36) throw new ArgumentOutOfRangeException(nameof(months), "Horizon de 1 à 36 mois.");
            var notes = new List<string>();
            var rates = db.CurrencyRates.AsNoTracking().ToList();
            var finance = new FinanceService(db);
            long start = finance.GetConsolidatedBalanceMadMinor(asOf);

            var firstMonth = new DateOnly(asOf.Year, asOf.Month, 1).AddMonths(1);
            var horizonEnd = firstMonth.AddMonths(months).AddDays(-1);
            var inflow = new long[months];
            var outflow = new long[months];
            int Index(DateOnly d) => Math.Clamp((d.Year - firstMonth.Year) * 12 + d.Month - firstMonth.Month, 0, months - 1);

            long? ToMad(long amount, string currency, decimal? contractualRate, string what)
            {
                if (currency == Money.DefaultCurrency) return amount;
                if (contractualRate is { } r) return CurrencyConverter.ToMadMinor(amount, r);
                try { return CurrencyConverter.ToMadMinor(amount, CurrencyConverter.FindRate(rates, currency, asOf)); }
                catch (MissingExchangeRateException) { notes.Add($"{what} ignoré : aucun taux {currency}/MAD connu."); return null; }
            }

            // Encaissements attendus
            var tranches = db.FundingTranches.Include(t => t.FundingAgreement).ThenInclude(a => a!.Project)
                .Where(t => t.ReceivedOperationId == null && t.ExpectedDate <= horizonEnd).ToList()
                .Where(t => t.FundingAgreement is { IsDeleted: false }).ToList();
            foreach (var t in tranches)
            {
                var agreement = t.FundingAgreement!;
                var mad = ToMad(t.AmountMinor, agreement.Currency, agreement.ContractualRateToMad, $"Tranche « {t.Label} »");
                if (mad == null) continue;
                if (t.ExpectedDate <= asOf) notes.Add($"Tranche en retard comptée en {firstMonth:MM/yyyy} : « {t.Label} » ({agreement.Reference}), attendue le {t.ExpectedDate:dd/MM/yyyy}.");
                inflow[t.ExpectedDate <= asOf ? 0 : Index(t.ExpectedDate)] += mad.Value;
            }

            // Décaissements : reste à consommer des lignes budgétaires
            var lines = db.BudgetLines.Include(l => l.Project).Include(l => l.FiscalYear).Include(l => l.FundingAgreement).ToList()
                .Where(l => l.Project == null || !FinishedStatuses.Contains(l.Project.Status)).ToList();
            var realized = RealizedMadByBudgetLine(lines.Select(l => l.Id).ToList());
            foreach (var line in lines)
            {
                var planned = ToMad(line.PlannedMinor, line.Currency, line.FundingAgreement?.ContractualRateToMad, $"Ligne « {line.Code} {line.Label} »");
                if (planned == null) continue;
                long remaining = planned.Value - realized.GetValueOrDefault(line.Id);
                if (remaining <= 0) continue;

                DateOnly? end = line.Project?.TargetEndDate is { } pe ? DateOnly.FromDateTime(pe) : line.FiscalYear?.EndDate;
                int lastIndex;
                if (end == null) lastIndex = months - 1;
                else if (end.Value < firstMonth)
                {
                    lastIndex = 0;
                    notes.Add($"Ligne « {line.Code} {line.Label} » : reste à consommer après la date de fin ({end:dd/MM/yyyy}), compté le premier mois.");
                }
                else lastIndex = Index(end.Value);

                // Seule la part de la période restante qui tombe dans l'horizon est prise en compte.
                int totalMonths = end == null ? months : Math.Max(1, (end.Value.Year - firstMonth.Year) * 12 + end.Value.Month - firstMonth.Month + 1);
                var parts = AllocationSplitter.Split(remaining, Enumerable.Repeat(1m, totalMonths).ToList());
                for (int i = 0; i <= lastIndex && i < parts.Length; i++) outflow[i] += parts[i];
            }

            var result = new List<ForecastMonth>();
            long opening = start;
            for (int i = 0; i < months; i++)
            {
                var m = firstMonth.AddMonths(i);
                var month = new ForecastMonth(m.Year, m.Month, opening, inflow[i], outflow[i]);
                result.Add(month);
                opening = month.ClosingMadMinor;
            }
            notes.Insert(0, "Hypothèses : tranches non reçues aux dates prévues ; reste à consommer des lignes budgétaires réparti uniformément jusqu'à la fin du projet ou de l'exercice.");
            return new TreasuryForecast(asOf, start, result, notes);
        }

        /// <summary>Réalisé par ligne budgétaire, en MAD : dépenses validées nettes des avoirs (quote-part de chaque ventilation).</summary>
        public Dictionary<int, long> RealizedMadByBudgetLine(IReadOnlyCollection<int> lineIds)
        {
            var allocations = db.OperationAllocations.Include(a => a.Operation)
                .Where(a => a.BudgetLineId != null && lineIds.Contains(a.BudgetLineId.Value)
                            && a.Operation!.Status == OperationStatus.Validated && a.Operation.Nature == OperationNature.Expense)
                .ToList()
                .Where(a => a.Operation is { IsDeleted: false });
            return allocations.GroupBy(a => a.BudgetLineId!.Value).ToDictionary(g => g.Key, g => g.Sum(a =>
            {
                var op = a.Operation!;
                long mad = op.AmountMinor == 0 ? 0 : (long)Math.Round((decimal)a.AmountMinor * op.AmountMadMinor / op.AmountMinor, MidpointRounding.AwayFromZero);
                return op.Direction == OperationDirection.Debit ? mad : -mad;
            }));
        }
    }
}
