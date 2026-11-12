using AFMI_Gestion_projet.Data;
using AFMI_Gestion_projet.Models.Finance;
using Microsoft.EntityFrameworkCore;

namespace AFMI_Gestion_projet.Finance
{
    public enum AlertSeverity { Info, Warning, Critical }

    public sealed record TreasuryAlert(AlertSeverity Severity, string Code, string Message, int? AccountId = null);

    /// <summary>Alertes de trésorerie : solde bas ou négatif, compte projet inactif, écart de rapprochement, anomalies.</summary>
    public sealed class TreasuryAlertService(AppDbContext db)
    {
        public const int DefaultInactivityDays = 90;

        public IReadOnlyList<TreasuryAlert> GetAlerts(DateOnly today, int inactivityDays = DefaultInactivityDays)
        {
            var alerts = new List<TreasuryAlert>();
            var finance = new FinanceService(db);
            var reconciliation = new ReconciliationService(db);

            foreach (var account in db.BankAccounts.AsNoTracking().Where(a => a.Status == AccountStatus.Active && a.OpeningDate <= today).ToList())
            {
                long balance = finance.GetBalanceMinor(account.Id, today);
                if (balance < 0)
                    alerts.Add(new(AlertSeverity.Critical, "NEGATIVE_BALANCE", $"{account.Title} : solde négatif ({Money.Format(balance, account.Currency)}).", account.Id));
                else if (account.LowBalanceThresholdMinor is { } threshold && balance < threshold)
                    alerts.Add(new(AlertSeverity.Warning, "LOW_BALANCE",
                        $"{account.Title} : solde {Money.Format(balance, account.Currency)} sous le seuil de {Money.Format(threshold, account.Currency)}.", account.Id));

                if (account.Purpose == AccountPurpose.Project)
                {
                    var last = db.Operations.Where(o => o.BankAccountId == account.Id && o.Status == OperationStatus.Validated)
                        .OrderByDescending(o => o.OperationDate).Select(o => (DateOnly?)o.OperationDate).FirstOrDefault() ?? account.OpeningDate;
                    int idle = today.DayNumber - last.DayNumber;
                    if (idle > inactivityDays)
                        alerts.Add(new(AlertSeverity.Info, "INACTIVE_PROJECT_ACCOUNT", $"{account.Title} : aucun mouvement depuis {idle} jours.", account.Id));
                }

                var lastStatement = db.BankStatements.Where(s => s.BankAccountId == account.Id).OrderByDescending(s => s.PeriodEnd).FirstOrDefault();
                if (lastStatement != null)
                {
                    var report = reconciliation.GetReport(lastStatement.Id);
                    if (report.UnexplainedDifferenceMinor != 0)
                        alerts.Add(new(AlertSeverity.Warning, "RECONCILIATION_GAP",
                            $"{account.Title} : écart de rapprochement inexpliqué de {Money.Format(report.UnexplainedDifferenceMinor, account.Currency)} au {lastStatement.PeriodEnd:dd/MM/yyyy}.", account.Id));
                    else if (report.UnmatchedLines.Count + report.UnmatchedOperations.Count > 0)
                        alerts.Add(new(AlertSeverity.Info, "UNRECONCILED_ITEMS",
                            $"{account.Title} : {report.UnmatchedLines.Count} ligne(s) de relevé et {report.UnmatchedOperations.Count} opération(s) non rapprochées.", account.Id));
                }
            }

            foreach (var group in finance.FindUnpairedTransfers())
                alerts.Add(new(AlertSeverity.Critical, "TRANSFER_UNPAIRED", $"Virement interne incomplet (une seule jambe) : {group}."));

            foreach (var t in db.FundingTranches.Include(t => t.FundingAgreement)
                         .Where(t => t.ReceivedOperationId == null && t.ExpectedDate < today).ToList()
                         .Where(t => t.FundingAgreement is { IsDeleted: false }))
                alerts.Add(new(AlertSeverity.Warning, "TRANCHE_OVERDUE",
                    $"Tranche « {t.Label} » ({t.FundingAgreement!.Reference}) attendue le {t.ExpectedDate:dd/MM/yyyy}, non encaissée."));

            int drafts = db.Operations.Count(o => o.Status == OperationStatus.Draft);
            if (drafts > 0) alerts.Add(new(AlertSeverity.Info, "DRAFT_OPERATIONS", $"{drafts} opération(s) en brouillon à compléter et valider."));

            return alerts.OrderByDescending(a => a.Severity).ToList();
        }
    }
}
