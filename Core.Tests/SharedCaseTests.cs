using System.Text.Json;
using AFMI_Gestion_projet.Finance;

namespace AFMI_Gestion_projet.Core.Tests;

/// <summary>Mêmes vecteurs que les tests Python (SharedTestCases/) : les deux implémentations doivent concorder.</summary>
public class SharedCaseTests
{
    private static JsonElement Load(string name) =>
        JsonDocument.Parse(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "SharedTestCases", name))).RootElement;

    public static IEnumerable<object[]> RibCases() =>
        Load("rib.json").GetProperty("cases").EnumerateArray()
            .Select(c => new object[] { c.GetProperty("input").GetString()!, c.GetProperty("wellFormed").GetBoolean(), c.GetProperty("keyValid").GetBoolean() });

    [Theory, MemberData(nameof(RibCases))]
    public void Rib_MatchesSharedVectors(string input, bool wellFormed, bool keyValid)
    {
        var check = Rib.Check(input);
        Assert.Equal(wellFormed, check.IsWellFormed);
        Assert.Equal(keyValid, check.IsKeyValid);
    }

    [Fact]
    public void AuditHash_MatchesSharedVectors()
    {
        foreach (var c in Load("audit_hash.json").GetProperty("cases").EnumerateArray())
        {
            var entry = new AFMI_Gestion_projet.Models.AuditEntry
            {
                PreviousHash = c.GetProperty("previousHash").GetString()!,
                TimestampUtc = DateTime.Parse(c.GetProperty("timestampUtc").GetString()!, System.Globalization.CultureInfo.InvariantCulture),
                User = c.GetProperty("user").GetString()!,
                Machine = c.GetProperty("machine").GetString()!,
                EntityType = c.GetProperty("entityType").GetString()!,
                EntityId = c.GetProperty("entityId").GetString()!,
                Action = c.GetProperty("action").GetString()!,
                ChangesJson = c.GetProperty("changesJson").GetString()!,
            };
            Assert.Equal(c.GetProperty("expectedHash").GetString(), AFMI_Gestion_projet.Data.AppDbContext.ComputeAuditHash(entry));
        }
    }

    /// <summary>
    /// Le backend Python teste sur une base créée par ce script : il doit suivre les migrations.
    /// Pour le régénérer : dotnet ef migrations script --project Core -o SmartOffice/tests/fixtures/unified_schema.sql
    /// </summary>
    [Fact]
    public void PythonSchemaFixture_IsUpToDate()
    {
        using var db = new TestDatabase();
        using var ctx = db.OpenWithoutMigration();
        string generated = Microsoft.EntityFrameworkCore.Infrastructure.AccessorExtensions
            .GetService<Microsoft.EntityFrameworkCore.Migrations.IMigrator>(ctx).GenerateScript();
        static string Normalize(string s) => s.Replace("\uFEFF", "").Replace("\r\n", "\n").Trim();
        string fixture = File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "unified_schema.sql"));
        Assert.True(Normalize(generated) == Normalize(fixture),
            "SmartOffice/tests/fixtures/unified_schema.sql est périmé : régénérez-le avec dotnet ef migrations script.");
    }

    [Fact]
    public void AllocationSplit_MatchesSharedVectors()
    {
        foreach (var c in Load("allocation_split.json").GetProperty("cases").EnumerateArray())
        {
            long total = c.GetProperty("total").GetInt64();
            var weights = c.GetProperty("weights").EnumerateArray().Select(w => w.GetDecimal()).ToList();
            var expected = c.GetProperty("expected").EnumerateArray().Select(e => e.GetInt64()).ToArray();
            var parts = AllocationSplitter.Split(total, weights);
            Assert.Equal(expected, parts);
            Assert.Equal(total, parts.Sum());
        }
    }
}
