using AFMI_Gestion_projet.Data;
using AFMI_Gestion_projet.Models.Finance;
using Microsoft.EntityFrameworkCore;

namespace AFMI_Gestion_projet.Finance
{
    public sealed record IncomeExpenseTotals(long IncomeMadMinor, long ExpenseMadMinor)
    {
        public long ResultMadMinor => IncomeMadMinor - ExpenseMadMinor;
    }

    public sealed record AccountBalance(int AccountId, string Title, string Currency, long BalanceMinor, long BalanceMadMinor);

    /// <summary>Opérations et calculs de trésorerie sur la base. Seules les opérations validées et non supprimées comptent.</summary>
    public sealed class FinanceService(AppDbContext db)
    {
        /// <summary>Solde à la fin de la journée <paramref name="date"/> : ouverture + crédits − débits. 0 avant l'ouverture.</summary>
        public long GetBalanceMinor(int accountId, DateOnly date)
        {
            var account = db.BankAccounts.AsNoTracking().Single(a => a.Id == accountId);
            if (date < account.OpeningDate) return 0;
            long movements = db.Operations
                .Where(o => o.BankAccountId == accountId && o.Status == OperationStatus.Validated && o.OperationDate <= date)
                .Sum(o => o.Direction == OperationDirection.Credit ? o.AmountMinor : -o.AmountMinor);
            return account.OpeningBalanceMinor + movements;
        }

        /// <summary>Soldes de tous les comptes actifs à la date, avec la contre-valeur en MAD au taux du jour.</summary>
        public IReadOnlyList<AccountBalance> GetBalances(DateOnly date)
        {
            var rates = db.CurrencyRates.AsNoTracking().ToList();
            return db.BankAccounts.AsNoTracking().Where(a => a.OpeningDate <= date).OrderBy(a => a.Title).ToList()
                .Select(a =>
                {
                    long balance = GetBalanceMinor(a.Id, date);
                    long mad = CurrencyConverter.ToMadMinor(balance, CurrencyConverter.FindRate(rates, a.Currency, date));
                    return new AccountBalance(a.Id, a.Title, a.Currency, balance, mad);
                }).ToList();
        }

        public long GetConsolidatedBalanceMadMinor(DateOnly date) => GetBalances(date).Sum(b => b.BalanceMadMinor);

        /// <summary>
        /// Recettes et dépenses validées de la période, en MAD, nettes des contre-passations
        /// (restitutions de recettes, avoirs sur dépenses). Les virements internes en sont exclus.
        /// </summary>
        public IncomeExpenseTotals GetIncomeAndExpenses(DateOnly from, DateOnly to)
        {
            var period = db.Operations.Where(o => o.Status == OperationStatus.Validated && o.OperationDate >= from && o.OperationDate <= to);
            long income = period.Where(o => o.Nature == OperationNature.Income)
                .Sum(o => o.Direction == OperationDirection.Credit ? o.AmountMadMinor : -o.AmountMadMinor);
            long expense = period.Where(o => o.Nature == OperationNature.Expense)
                .Sum(o => o.Direction == OperationDirection.Debit ? o.AmountMadMinor : -o.AmountMadMinor);
            return new IncomeExpenseTotals(income, expense);
        }

        /// <summary>Enregistre un brouillon : contrôles de base, taux et contre-valeur MAD figés.</summary>
        public Operation AddDraft(Operation op)
        {
            op.Status = OperationStatus.Draft;
            Check(op, forValidation: false);
            db.Operations.Add(op);
            db.SaveChanges();
            return op;
        }

        /// <summary>Valide une opération : elle doit être entièrement ventilée sur des lignes budgétaires cohérentes.</summary>
        public Operation Validate(int operationId, string user)
        {
            var op = db.Operations.Include(o => o.Allocations).Single(o => o.Id == operationId);
            Check(op, forValidation: true);
            op.Status = OperationStatus.Validated;
            op.ValidatedAtUtc = DateTime.UtcNow;
            op.ValidatedBy = user;
            db.SaveChanges();
            return op;
        }

        /// <summary>
        /// Virement interne : deux opérations validées liées (débit de la source, crédit de la destination).
        /// Entre devises différentes, le montant reçu doit être indiqué (pas de conversion devinée).
        /// </summary>
        public Guid CreateInternalTransfer(int fromAccountId, int toAccountId, DateOnly date, long amountMinor,
            string label, string user, long? receivedAmountMinor = null)
        {
            if (fromAccountId == toAccountId) throw new ArgumentException("Les comptes source et destination doivent être différents.");
            var from = db.BankAccounts.Single(a => a.Id == fromAccountId);
            var to = db.BankAccounts.Single(a => a.Id == toAccountId);
            long received = receivedAmountMinor
                ?? (from.Currency == to.Currency ? amountMinor
                    : throw new ArgumentException($"Virement {from.Currency} → {to.Currency} : indiquez le montant reçu."));

            var group = Guid.NewGuid();
            var now = DateTime.UtcNow;
            Operation Leg(BankAccount account, OperationDirection direction, long amount) => new()
            {
                BankAccountId = account.Id, BankAccount = account, OperationDate = date, Label = label,
                Direction = direction, Nature = OperationNature.InternalTransfer, AmountMinor = amount,
                Currency = account.Currency, TransferGroupId = group,
                Status = OperationStatus.Validated, ValidatedAtUtc = now, ValidatedBy = user,
            };
            var debit = Leg(from, OperationDirection.Debit, amountMinor);
            var credit = Leg(to, OperationDirection.Credit, received);
            Check(debit, forValidation: true);
            Check(credit, forValidation: true);

            using var tx = db.Database.BeginTransaction();
            db.Operations.AddRange(debit, credit);
            db.SaveChanges();
            tx.Commit();
            return group;
        }

        /// <summary>Virements dont il manque une jambe (anomalie bloquante pour les rapports).</summary>
        public IReadOnlyList<Guid> FindUnpairedTransfers() =>
            db.Operations.Where(o => o.Nature == OperationNature.InternalTransfer && o.TransferGroupId != null)
                .GroupBy(o => o.TransferGroupId!.Value)
                .Where(g => g.Count(o => o.Direction == OperationDirection.Debit) != 1 || g.Count(o => o.Direction == OperationDirection.Credit) != 1)
                .Select(g => g.Key).ToList();

        private void Check(Operation op, bool forValidation)
        {
            var account = op.BankAccount ?? db.BankAccounts.IgnoreQueryFilters().Single(a => a.Id == op.BankAccountId);
            op.Currency = Money.NormalizeCurrency(op.Currency);
            var lineIds = op.Allocations.Where(a => a.BudgetLineId != null).Select(a => a.BudgetLineId!.Value).Distinct().ToList();
            var lines = db.BudgetLines.Where(l => lineIds.Contains(l.Id)).ToDictionary(l => l.Id);

            var issues = OperationValidator.Validate(op, account, lines, forValidation);
            if (issues.Count > 0) throw new OperationValidationException(issues);

            decimal rate = CurrencyConverter.FindRate(db.CurrencyRates.AsNoTracking().ToList(), op.Currency, op.OperationDate);
            op.RateToMad = op.Currency == Money.DefaultCurrency ? null : rate;
            op.AmountMadMinor = CurrencyConverter.ToMadMinor(op.AmountMinor, rate);
        }
    }
}
