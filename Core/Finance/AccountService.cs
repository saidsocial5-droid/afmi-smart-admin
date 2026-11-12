using AFMI_Gestion_projet.Data;
using AFMI_Gestion_projet.Models.Finance;
using Microsoft.EntityFrameworkCore;

namespace AFMI_Gestion_projet.Finance
{
    public sealed class FinanceRuleException(string message) : InvalidOperationException(message);

    /// <summary>Comptes bancaires, caisse et liaisons comptes ↔ projets.</summary>
    public sealed class AccountService(AppDbContext db)
    {
        /// <summary>Enregistre un compte. Retourne les avertissements non bloquants (clé RIB à vérifier…).</summary>
        public IReadOnlyList<string> Save(BankAccount account)
        {
            var warnings = new List<string>();
            if (string.IsNullOrWhiteSpace(account.Title)) throw new FinanceRuleException("L'intitulé du compte est obligatoire.");
            account.Currency = Money.NormalizeCurrency(account.Currency);

            if (account.Kind == AccountKind.Cash)
            {
                account.Rib = null;
            }
            else if (!string.IsNullOrWhiteSpace(account.Rib))
            {
                var rib = Rib.Check(account.Rib);
                if (!rib.IsWellFormed) throw new FinanceRuleException("Le RIB doit comporter 24 chiffres.");
                account.Rib = rib.Normalized;
                if (!rib.IsKeyValid)
                    warnings.Add($"Clé RIB {rib.Key} différente de la clé calculée ({rib.ExpectedKey:00}) : vérifiez le RIB auprès de la banque.");
            }
            else
            {
                account.Rib = null;
            }

            if (account.Id != 0 && db.Operations.Any(o => o.BankAccountId == account.Id && o.OperationDate < account.OpeningDate))
                throw new FinanceRuleException("Des opérations sont antérieures à cette date d'ouverture.");

            if (account.Id == 0) db.BankAccounts.Add(account);
            db.SaveChanges();
            return warnings;
        }

        /// <summary>Clôture : refusée tant que le solde n'est pas nul (transférez-le d'abord).</summary>
        public void Close(int accountId, DateOnly closingDate)
        {
            var account = db.BankAccounts.Single(a => a.Id == accountId);
            long balance = new FinanceService(db).GetBalanceMinor(accountId, closingDate);
            if (balance != 0)
                throw new FinanceRuleException($"Solde au {closingDate:dd/MM/yyyy} : {Money.Format(balance, account.Currency)}. Virez-le avant de clôturer.");
            if (db.Operations.Any(o => o.BankAccountId == accountId && o.OperationDate > closingDate))
                throw new FinanceRuleException("Des opérations sont postérieures à la date de clôture.");
            account.Status = AccountStatus.Closed;
            account.ClosedDate = closingDate;
            db.SaveChanges();
        }

        public void SaveLink(AccountProjectLink link)
        {
            if (link.ValidTo is { } to && to < link.ValidFrom) throw new FinanceRuleException("La fin de validité précède le début.");
            switch (link.AllocationMode)
            {
                case AllocationMode.Percentage when link.AllocationPercent is not (> 0 and <= 100):
                    throw new FinanceRuleException("Le pourcentage doit être compris entre 0 et 100.");
                case AllocationMode.FixedAmount when link.AllocationAmountMinor is not > 0:
                    throw new FinanceRuleException("Le montant de la clé de répartition doit être positif.");
                case AllocationMode.None:
                    link.AllocationPercent = null;
                    link.AllocationAmountMinor = null;
                    break;
            }

            var overlapping = db.AccountProjectLinks
                .Where(l => l.BankAccountId == link.BankAccountId && l.Id != link.Id).ToList()
                .Where(l => Overlaps(l, link.ValidFrom, link.ValidTo)).ToList();
            if (overlapping.Any(l => l.ProjectId == link.ProjectId))
                throw new FinanceRuleException("Ce compte est déjà lié à ce projet sur une période qui chevauche celle-ci.");
            if (link.AllocationMode == AllocationMode.Percentage)
            {
                decimal total = overlapping.Where(l => l.AllocationMode == AllocationMode.Percentage).Sum(l => l.AllocationPercent ?? 0) + link.AllocationPercent!.Value;
                if (total > 100) throw new FinanceRuleException($"Les clés de répartition de ce compte dépasseraient 100 % ({total} %).");
            }

            if (link.Id == 0) db.AccountProjectLinks.Add(link);
            db.SaveChanges();
        }

        public IReadOnlyList<AccountProjectLink> GetActiveLinks(int accountId, DateOnly date) =>
            db.AccountProjectLinks.Include(l => l.Project).Where(l => l.BankAccountId == accountId).ToList()
                .Where(l => Overlaps(l, date, date)).ToList();

        /// <summary>
        /// Ventilation proposée pour un mouvement : projet unique lié au compte, ou répartition selon les pourcentages,
        /// ou fonctionnement pour un compte de fonctionnement. Les lignes budgétaires restent à choisir.
        /// </summary>
        public IReadOnlyList<OperationAllocation> SuggestAllocations(int accountId, DateOnly date, long amountMinor)
        {
            var account = db.BankAccounts.Single(a => a.Id == accountId);
            var links = GetActiveLinks(accountId, date);
            var percent = links.Where(l => l.AllocationMode == AllocationMode.Percentage).ToList();
            if (percent.Count > 0 && percent.Sum(l => l.AllocationPercent!.Value) == 100)
            {
                var parts = AllocationSplitter.Split(amountMinor, percent.Select(l => l.AllocationPercent!.Value).ToList());
                return percent.Select((l, i) => new OperationAllocation { ProjectId = l.ProjectId, AmountMinor = parts[i] })
                    .Where(a => a.AmountMinor > 0).ToList();
            }
            if (links.Count == 1)
                return new[] { new OperationAllocation { ProjectId = links[0].ProjectId, AmountMinor = amountMinor } };
            if (links.Count == 0 && account.Purpose == AccountPurpose.Operating)
                return new[] { new OperationAllocation { ProjectId = null, AmountMinor = amountMinor } };
            return Array.Empty<OperationAllocation>();
        }

        private static bool Overlaps(AccountProjectLink l, DateOnly from, DateOnly? to) =>
            l.ValidFrom <= (to ?? DateOnly.MaxValue) && (l.ValidTo ?? DateOnly.MaxValue) >= from;
    }
}
