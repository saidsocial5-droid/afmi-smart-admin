using AFMI_Gestion_projet.Services;

namespace AFMI_Gestion_projet.Core.Tests;

public class SettingsServiceTests : IDisposable
{
    private readonly TestDatabase _db = new();
    public void Dispose() => _db.Dispose();

    [Fact]
    public void Defaults_AreLocalFirst_AndOverridesPersist()
    {
        using (var ctx = _db.Open())
        {
            var settings = new SettingsService(ctx);
            Assert.True(settings.Get<bool>(SettingKeys.AiOfflineMode));
            Assert.True(settings.Get<bool>(SettingKeys.AiMaskSensitiveData));
            Assert.Equal("MAD", settings.Get<string>(SettingKeys.DefaultCurrency));
            settings.Set(SettingKeys.FiscalYearStartMonth, 7);
        }
        using (var ctx = _db.Open())
        {
            var settings = new SettingsService(ctx);
            Assert.Equal(7, settings.Get<int>(SettingKeys.FiscalYearStartMonth));
            settings.ResetToDefault(SettingKeys.FiscalYearStartMonth);
            Assert.Equal(1, settings.Get<int>(SettingKeys.FiscalYearStartMonth));
        }
    }

    [Fact]
    public void Secret_IsEncryptedAtRest_OnWindows()
    {
        if (!OperatingSystem.IsWindows()) return; // DPAPI : Windows uniquement (vérifié par l'intégration continue Windows)
        using var ctx = _db.Open();
        var settings = new SettingsService(ctx);
        settings.SetSecret("ai.anthropic.api_key", "sk-test-123");
        Assert.Equal("sk-test-123", settings.Get<string>("ai.anthropic.api_key"));
        Assert.DoesNotContain("sk-test-123", (string)_db.Scalar("SELECT ValueJson FROM AppSettings WHERE Key = 'ai.anthropic.api_key'")!);
    }
}
