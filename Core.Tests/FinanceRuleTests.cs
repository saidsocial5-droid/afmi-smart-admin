using AFMI_Gestion_projet.Finance;
using AFMI_Gestion_projet.Models.Finance;

namespace AFMI_Gestion_projet.Core.Tests;

public class FinanceRuleTests
{
    [Fact]
    public void Rib_FormatAndMask()
    {
        string rib = "007330000123456789012300";
        rib = rib[..22] + Rib.ComputeKey(rib[..22]).ToString("00");
        Assert.Equal($"007 330 0001234567890123 {rib[22..]}", Rib.Format(rib));
        Assert.Equal(new string('•', 20) + rib[^4..], Rib.Mask(rib));
        Assert.Equal("007", Rib.Check(rib).BankCode);
    }

    [Theory]
    [InlineData(12.345, 1235)]
    [InlineData(12.344, 1234)]
    [InlineData(-0.005, -1)]
    [InlineData(0, 0)]
    public void Money_ToMinor_RoundsHalfAwayFromZero(decimal amount, long expected) => Assert.Equal(expected, Money.ToMinor(amount));

    [Theory]
    [InlineData("dh", "MAD")]
    [InlineData(" eur ", "EUR")]
    public void Money_NormalizesCurrency(string input, string expected) => Assert.Equal(expected, Money.NormalizeCurrency(input));

    [Fact]
    public void Money_RejectsInvalidCurrency() => Assert.Throws<ArgumentException>(() => Money.NormalizeCurrency("EURO"));

    [Fact]
    public void Converter_UsesLatestRateOnOrBeforeDate()
    {
        var rates = new[]
        {
            new CurrencyRate { Currency = "EUR", Date = new(2026, 1, 1), RateToMad = 10.80m },
            new CurrencyRate { Currency = "EUR", Date = new(2026, 3, 1), RateToMad = 10.95m },
            new CurrencyRate { Currency = "USD", Date = new(2026, 2, 1), RateToMad = 9.90m },
        };
        Assert.Equal(10.80m, CurrencyConverter.FindRate(rates, "EUR", new(2026, 2, 28)));
        Assert.Equal(10.95m, CurrencyConverter.FindRate(rates, "EUR", new(2026, 3, 1)));
        Assert.Equal(1m, CurrencyConverter.FindRate(rates, "MAD", new(2000, 1, 1)));
        Assert.Throws<MissingExchangeRateException>(() => CurrencyConverter.FindRate(rates, "EUR", new(2025, 12, 31)));
        Assert.Throws<MissingExchangeRateException>(() => CurrencyConverter.FindRate(rates, "GBP", new(2026, 6, 1)));
        Assert.Equal(1_095_00, CurrencyConverter.ToMadMinor(100_00, 10.95m));
        Assert.Equal(1, CurrencyConverter.ToMadMinor(1, 0.5m)); // 0,5 centime → arrondi à 1
    }

    [Fact]
    public void Splitter_RejectsInvalidKeys()
    {
        Assert.Throws<ArgumentException>(() => AllocationSplitter.Split(100, Array.Empty<decimal>()));
        Assert.Throws<ArgumentException>(() => AllocationSplitter.Split(100, new[] { 0m, 0m }));
        Assert.Throws<ArgumentException>(() => AllocationSplitter.Split(100, new[] { 1m, -1m }));
    }

    private static BankAccount Account() => new() { Id = 1, Currency = "MAD", OpeningDate = new(2026, 1, 1) };

    private static Operation Expense(long amount, params OperationAllocation[] allocations)
    {
        var op = new Operation
        {
            BankAccountId = 1, OperationDate = new(2026, 2, 1), Currency = "MAD", AmountMinor = amount,
            Direction = OperationDirection.Debit, Nature = OperationNature.Expense,
        };
        foreach (var a in allocations) op.Allocations.Add(a);
        return op;
    }

    private static readonly Dictionary<int, BudgetLine> Lines = new()
    {
        [10] = new BudgetLine { Id = 10, ProjectId = 7, Code = "1.1", Label = "Plants" },
        [20] = new BudgetLine { Id = 20, ProjectId = null, Code = "F1", Label = "Loyer" },
    };

    private static IEnumerable<string> Codes(Operation op, bool forValidation = true, BankAccount? account = null) =>
        OperationValidator.Validate(op, account ?? Account(), Lines, forValidation).Select(i => i.Code);

    [Fact]
    public void Validator_AcceptsFullyAllocatedOperation()
    {
        var op = Expense(1000,
            new OperationAllocation { ProjectId = 7, BudgetLineId = 10, AmountMinor = 600 },
            new OperationAllocation { ProjectId = null, BudgetLineId = 20, AmountMinor = 400 });
        Assert.Empty(Codes(op));
    }

    [Fact]
    public void Validator_RequiresExactAllocationOnBudgetLinesOfTheSameProject()
    {
        Assert.Contains("NOT_ALLOCATED", Codes(Expense(1000)));
        Assert.Contains("ALLOCATION_SUM", Codes(Expense(1000, new OperationAllocation { ProjectId = 7, BudgetLineId = 10, AmountMinor = 999 })));
        Assert.Contains("NO_BUDGET_LINE", Codes(Expense(1000, new OperationAllocation { ProjectId = 7, AmountMinor = 1000 })));
        Assert.Contains("BUDGET_LINE_PROJECT", Codes(Expense(1000, new OperationAllocation { ProjectId = 7, BudgetLineId = 20, AmountMinor = 1000 })));
        Assert.Contains("UNKNOWN_BUDGET_LINE", Codes(Expense(1000, new OperationAllocation { ProjectId = 7, BudgetLineId = 99, AmountMinor = 1000 })));
        // Un brouillon peut être incomplet, mais pas sur-ventilé.
        Assert.Empty(Codes(Expense(1000), forValidation: false));
        Assert.Contains("ALLOCATION_SUM", Codes(Expense(1000, new OperationAllocation { BudgetLineId = 20, AmountMinor = 1001 }), forValidation: false));
    }

    [Fact]
    public void Validator_ChecksAccountDatesCurrencyAndDirection()
    {
        var op = Expense(1000, new OperationAllocation { BudgetLineId = 20, AmountMinor = 1000 });
        op.OperationDate = new(2025, 12, 31);
        Assert.Contains("BEFORE_OPENING", Codes(op));

        op = Expense(1000, new OperationAllocation { BudgetLineId = 20, AmountMinor = 1000 });
        var closed = Account(); closed.Status = AccountStatus.Closed; closed.ClosedDate = new(2026, 1, 15);
        Assert.Contains("ACCOUNT_CLOSED", Codes(op, account: closed));

        op.Currency = "EUR";
        Assert.Contains("CURRENCY", Codes(op));

        op = Expense(1000, new OperationAllocation { BudgetLineId = 20, AmountMinor = 1000 });
        op.Direction = OperationDirection.Credit;
        Assert.Contains("NATURE_DIRECTION", Codes(op));

        op = Expense(0);
        Assert.Contains("AMOUNT", Codes(op, forValidation: false));
    }

    [Fact]
    public void Validator_TransfersAreNeverAllocated()
    {
        var op = Expense(500, new OperationAllocation { BudgetLineId = 20, AmountMinor = 500 });
        op.Nature = OperationNature.InternalTransfer;
        var codes = Codes(op).ToList();
        Assert.Contains("TRANSFER_GROUP", codes);
        Assert.Contains("TRANSFER_ALLOCATION", codes);

        var income = Expense(500);
        income.Nature = OperationNature.Income; income.Direction = OperationDirection.Credit; income.TransferGroupId = Guid.NewGuid();
        Assert.Contains("TRANSFER_GROUP", Codes(income, forValidation: false));
    }
}
