using AFMI_Gestion_projet.Finance;
using AFMI_Gestion_projet.Models.Finance;
using Microsoft.Data.Sqlite;

namespace AFMI_Gestion_projet.Core.Tests;

public class ImportTests : IDisposable
{
    private readonly TestDatabase _db = new();
    public void Dispose() => _db.Dispose();

    [Fact]
    public void Csv_FrenchBankExport_IsParsed()
    {
        const string csv = "Date opération;Date valeur;Libellé;Référence;Débit;Crédit\n" +
                           "05/03/2026;06/03/2026;\"PRLV LOYER; MARS\";R1;2 000,00;\n" +
                           "10/03/2026;10/03/2026;VIR RECU BAILLEUR;R2;;15 250,50\n" +
                           "11/03/2026;11/03/2026;SOLDE REPORTE;;;\n" +
                           "xx/03/2026;;ERREUR;;1,00;\n";
        var parsed = StatementCsvImporter.Parse(csv);
        Assert.Equal(2, parsed.Lines.Count);
        Assert.Single(parsed.Errors);
        Assert.Equal("PRLV LOYER; MARS", parsed.Lines[0].Label);
        Assert.Equal(2_000_00, parsed.Lines[0].DebitMinor);
        Assert.Equal(new DateOnly(2026, 3, 6), parsed.Lines[0].ValueDate);
        Assert.Equal(15_250_50, parsed.Lines[1].CreditMinor);
        Assert.Equal(13_250_50, parsed.NetMovementMinor);
    }

    [Fact]
    public void Csv_SignedAmountColumn_AndIsoFormats()
    {
        const string csv = "date,description,amount\n2026-03-05,Loyer,-2000.00\n2026-03-10,Don,\"1,250.75\"\n";
        var parsed = StatementCsvImporter.Parse(csv);
        Assert.Empty(parsed.Errors);
        Assert.Equal(2_000_00, parsed.Lines[0].DebitMinor);
        Assert.Equal(1_250_75, parsed.Lines[1].CreditMinor);
        Assert.NotEmpty(StatementCsvImporter.Parse("a;b\n1;2").Errors);
    }

    [Theory]
    [InlineData("1 234,56", 123456)]
    [InlineData("1.234,56", 123456)]
    [InlineData("1,234.56", 123456)]
    [InlineData("-12,5", -1250)]
    [InlineData("(10,00)", -1000)]
    [InlineData("250 MAD", 25000)]
    public void Csv_Amounts(string text, long expected)
    {
        Assert.True(StatementCsvImporter.TryAmount(text, out long minor));
        Assert.Equal(expected, minor);
    }

    [Fact]
    public void Csv_ImportCreatesDraftStatementThatChecksBalances()
    {
        using var ctx = _db.Open();
        var f = Lot2Fixture.Seed(ctx);
        var parsed = StatementCsvImporter.Parse("Date;Libellé;Débit;Crédit\n05/03/2026;Loyer;2000,00;\n");
        var st = StatementCsvImporter.Import(ctx, f.Operating, parsed, 10_000_00, 8_000_00);
        Assert.Equal(StatementSource.Csv, st.Source);
        Assert.Equal(StatementStatus.Draft, st.Status);
        Assert.True(new ReconciliationService(ctx).Check(st.Id).BalanceOk);
    }

    [Fact]
    public void LegacySmartOffice_IsImportedAsDrafts_OnlyOnce()
    {
        string legacy = Path.Combine(_db.Directory, "afmi_smartoffice.db");
        using (var c = new SqliteConnection($"Data Source={legacy};Pooling=False"))
        {
            c.Open();
            using var cmd = c.CreateCommand();
            cmd.CommandText = @"
                CREATE TABLE projects (id INTEGER PRIMARY KEY, code TEXT, title TEXT, total_budget REAL, currency TEXT, start_date TEXT, end_date TEXT, status TEXT);
                CREATE TABLE financial_transactions (id INTEGER PRIMARY KEY, tx_date TEXT, label TEXT, reference TEXT, debit REAL, credit REAL, beneficiary_or_emitter TEXT);
                INSERT INTO projects VALUES (1, 'P1', 'Déjà présent', 1, 'MAD', NULL, NULL, 'In Progress');
                INSERT INTO projects VALUES (2, 'SO-ECO', 'Écotourisme', 50000, 'MAD', '2026-01-01', '2026-12-31', 'In Progress');
                INSERT INTO financial_transactions VALUES (1, '05/03/2026', 'Achat plants', 'F12', 1200.5, 0, 'Pépinière');
                INSERT INTO financial_transactions VALUES (2, '2026-03-10', 'Don', NULL, 0, 300, 'Donateur');
                INSERT INTO financial_transactions VALUES (3, 'n/a', 'Illisible', NULL, 10, 0, NULL);
                INSERT INTO financial_transactions VALUES (4, '2026-03-11', 'Les deux', NULL, 10, 10, NULL);";
            cmd.ExecuteNonQuery();
        }

        using var ctx = _db.Open();
        var f = Lot2Fixture.Seed(ctx);
        var result = new LegacySmartOfficeImporter(ctx).Import(legacy, f.Operating);
        Assert.Equal(1, result.ProjectsCreated);
        Assert.Equal(2, result.OperationsCreated);
        Assert.Equal(2, result.Skipped);
        var ops = ctx.Operations.Where(o => o.Reference.StartsWith("SO-")).OrderBy(o => o.Reference).ToList();
        Assert.All(ops, o => Assert.Equal(OperationStatus.Draft, o.Status));
        Assert.Equal(1_200_50, ops[0].AmountMinor);
        Assert.Equal(OperationNature.Expense, ops[0].Nature);
        Assert.Equal(OperationNature.Income, ops[1].Nature);

        var again = new LegacySmartOfficeImporter(ctx).Import(legacy, f.Operating);
        Assert.Equal(0, again.OperationsCreated + again.ProjectsCreated);
        Assert.Equal(4, again.Skipped);
    }
}
