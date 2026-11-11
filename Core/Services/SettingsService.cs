using System.Text.Json;
using AFMI_Gestion_projet.Data;
using AFMI_Gestion_projet.Models;

namespace AFMI_Gestion_projet.Services
{
    /// <summary>Clés des paramètres partagés avec le backend Python (même table AppSettings).</summary>
    public static class SettingKeys
    {
        public const string AssociationName = "association.name";
        public const string AssociationAcronym = "association.acronym";
        public const string FiscalYearStartMonth = "association.fiscal_year_start_month";
        public const string DefaultCurrency = "association.default_currency";
        public const string DefaultLanguage = "association.default_language";
        public const string AiOfflineMode = "ai.offline_mode";
        public const string AiMaskSensitiveData = "ai.mask_sensitive_data";
        public const string ReconciliationToleranceDays = "bank.reconciliation_tolerance_days";
        public const string BackupFolder = "backup.folder";
        public const string BackupFrequency = "backup.frequency";
        public const string BackupRetention = "backup.retention";
        public const string BackupLastError = "backup.last_error";
    }

    /// <summary>Lecture/écriture typée des paramètres (JSON). Les secrets sont protégés par DPAPI (Windows).</summary>
    public sealed class SettingsService(AppDbContext db)
    {
        private static readonly Dictionary<string, object> Defaults = new()
        {
            [SettingKeys.AssociationName] = "Association Forêt Modèle d'Ifrane",
            [SettingKeys.AssociationAcronym] = "AFMI",
            [SettingKeys.FiscalYearStartMonth] = 1,
            [SettingKeys.DefaultCurrency] = "MAD",
            [SettingKeys.DefaultLanguage] = "fr",
            // Local-first : l'IA externe est désactivée tant que l'utilisateur ne l'a pas activée.
            [SettingKeys.AiOfflineMode] = true,
            [SettingKeys.AiMaskSensitiveData] = true,
            // Lot 7 : mêmes valeurs par défaut que le registre des paramètres (backend/core/settings_registry.py)
            [SettingKeys.ReconciliationToleranceDays] = 3,
            [SettingKeys.BackupFolder] = "",
            [SettingKeys.BackupFrequency] = "daily",
            [SettingKeys.BackupRetention] = 30,
            [SettingKeys.BackupLastError] = "",
        };

        public T Get<T>(string key)
        {
            var row = db.AppSettings.Find(key);
            if (row != null)
            {
                string json = row.IsSecret ? SecretProtector.Unprotect(JsonSerializer.Deserialize<string>(row.ValueJson) ?? "") : row.ValueJson;
                if (row.IsSecret) return (T)(object)json;
                return JsonSerializer.Deserialize<T>(json)!;
            }
            return Defaults.TryGetValue(key, out var value) ? (T)Convert.ChangeType(value, typeof(T)) : default!;
        }

        public void Set<T>(string key, T value)
        {
            Upsert(key, JsonSerializer.Serialize(value), isSecret: false);
        }

        /// <summary>Secret (clé API…) : chiffré par DPAPI, masqué dans le journal d'audit.</summary>
        public void SetSecret(string key, string secret)
        {
            Upsert(key, JsonSerializer.Serialize(SecretProtector.Protect(secret)), isSecret: true);
        }

        public void ResetToDefault(string key)
        {
            var row = db.AppSettings.Find(key);
            if (row == null) return;
            db.AppSettings.Remove(row);
            db.SaveChanges();
        }

        private void Upsert(string key, string json, bool isSecret)
        {
            var row = db.AppSettings.Find(key);
            if (row == null)
            {
                db.AppSettings.Add(new AppSetting { Key = key, ValueJson = json, IsSecret = isSecret, UpdatedAtUtc = DateTime.UtcNow });
            }
            else
            {
                row.ValueJson = json;
                row.IsSecret = isSecret;
                row.UpdatedAtUtc = DateTime.UtcNow;
            }
            db.SaveChanges();
        }
    }
}
