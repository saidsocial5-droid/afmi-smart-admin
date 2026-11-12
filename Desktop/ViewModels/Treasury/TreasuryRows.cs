using AFMI_Gestion_projet.Finance;
using AFMI_Gestion_projet.Models.Finance;

namespace AFMI_Gestion_projet.ViewModels.Treasury
{
    /// <summary>Élément de liste déroulante : valeur + libellé français.</summary>
    public sealed record Option<T>(T Value, string Label)
    {
        public override string ToString() => Label;
    }

    public sealed record AccountRow(BankAccount Account, long BalanceMinor)
    {
        public string Title => Account.Title;
        public string KindText => Account.Kind == AccountKind.Cash ? "Caisse" : "Banque";
        public string PurposeText => TreasuryLabels.Purpose(Account.Purpose);
        public string Bank => Account.BankName;
        public string RibText => Rib.Format(Account.Rib);
        public string BalanceText => Money.Format(BalanceMinor, Account.Currency);
        public string StatusText => Account.Status == AccountStatus.Active ? "Actif" : $"Clôturé le {Account.ClosedDate:dd/MM/yyyy}";
        public bool IsLow => Account.LowBalanceThresholdMinor is { } t && BalanceMinor < t || BalanceMinor < 0;
    }

    public sealed record LinkRow(AccountProjectLink Link, string ProjectName)
    {
        public string Period => $"{Link.ValidFrom:dd/MM/yyyy} → {(Link.ValidTo is { } to ? to.ToString("dd/MM/yyyy") : "…")}";
        public string KeyText => Link.AllocationMode switch
        {
            AllocationMode.Percentage => $"{Link.AllocationPercent:0.##} %",
            AllocationMode.FixedAmount => Money.Format(Link.AllocationAmountMinor ?? 0),
            _ => "—",
        };
    }

    public sealed record OperationRow(Operation Operation, string AllocationText)
    {
        public int Id => Operation.Id;
        public string Date => Operation.OperationDate.ToString("dd/MM/yyyy");
        public string Label => Operation.Label;
        public string NatureText => TreasuryLabels.Nature(Operation);
        public string DebitText => Operation.Direction == OperationDirection.Debit ? Money.Format(Operation.AmountMinor, Operation.Currency) : "";
        public string CreditText => Operation.Direction == OperationDirection.Credit ? Money.Format(Operation.AmountMinor, Operation.Currency) : "";
        public string StatusText => Operation.Status == OperationStatus.Validated ? "Validée" : "Brouillon";
        public bool IsDraft => Operation.Status == OperationStatus.Draft;
    }

    public sealed record BudgetLineRow(BudgetLine Line, long RealizedMadMinor)
    {
        public string Code => Line.Code;
        public string Label => Line.Label;
        public string CategoryText => Line.Category?.Label ?? "";
        public string PlannedText => Money.Format(Line.PlannedMinor, Line.Currency);
        public string RealizedText => Money.Format(RealizedMadMinor);
        public string RateText => Line.Currency == Money.DefaultCurrency && Line.PlannedMinor > 0
            ? $"{100m * RealizedMadMinor / Line.PlannedMinor:0.#} %" : "—";
    }

    public sealed record TrancheRow(FundingTranche Tranche)
    {
        public string Label => Tranche.Label;
        public string Expected => Tranche.ExpectedDate.ToString("dd/MM/yyyy");
        public string AmountText => Money.Format(Tranche.AmountMinor, Tranche.FundingAgreement?.Currency ?? Money.DefaultCurrency);
        public string StatusText => Tranche.ReceivedOperationId is { } id ? $"Encaissée (opération {id})" : "À recevoir";
    }

    public sealed record StatementRow(BankStatement Statement)
    {
        public string Period => $"{Statement.PeriodStart:dd/MM/yyyy} → {Statement.PeriodEnd:dd/MM/yyyy}";
        public string SourceText => Statement.Source switch { StatementSource.Csv => "CSV", StatementSource.Ocr => "Scan", _ => "Saisie" };
        public string ClosingText => Money.Format(Statement.ClosingBalanceMinor);
        public string StatusText => Statement.Status == StatementStatus.Validated ? "Validé" : "Brouillon";
    }

    public sealed record StatementLineRow(StatementLine Line, string MatchText)
    {
        public int Id => Line.Id;
        public string Date => Line.OperationDate.ToString("dd/MM/yyyy");
        public string Label => Line.Label;
        public string DebitText => Line.DebitMinor > 0 ? Money.Format(Line.DebitMinor) : "";
        public string CreditText => Line.CreditMinor > 0 ? Money.Format(Line.CreditMinor) : "";
        public bool IsMatched => Line.Match != null;
    }

    public sealed record ForecastRow(ForecastMonth Month)
    {
        public string Label => Month.Label;
        public string Opening => Money.Format(Month.OpeningMadMinor);
        public string Inflow => Money.Format(Month.InflowMadMinor);
        public string Outflow => Money.Format(Month.OutflowMadMinor);
        public string Closing => Money.Format(Month.ClosingMadMinor);
        public bool IsNegative => Month.ClosingMadMinor < 0;
    }

    public sealed record AlertRow(TreasuryAlert Alert)
    {
        public string Icon => Alert.Severity switch { AlertSeverity.Critical => "⛔", AlertSeverity.Warning => "⚠️", _ => "ℹ️" };
        public string Message => Alert.Message;
    }

    public static class TreasuryLabels
    {
        public static string Purpose(AccountPurpose p) => p switch
        {
            AccountPurpose.Operating => "Fonctionnement",
            AccountPurpose.Project => "Dédié projet",
            AccountPurpose.Deposit => "Dépôt / épargne",
            _ => "Autre",
        };

        public static string Nature(Operation o) => o.Nature switch
        {
            OperationNature.InternalTransfer => "Virement interne",
            OperationNature.Income => o.Direction == OperationDirection.Credit ? "Recette" : "Restitution de recette",
            _ => o.Direction == OperationDirection.Debit ? "Dépense" : "Avoir sur dépense",
        };
    }
}
