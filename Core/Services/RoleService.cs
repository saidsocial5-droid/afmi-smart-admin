using System.Text.Json;
using AFMI_Gestion_projet.Data;

namespace AFMI_Gestion_projet.Services
{
    /// <summary>
    /// Rôles des utilisateurs (Paramètres › Utilisateurs, clé « security.users »), mêmes règles que backend/core/roles.py :
    /// liste vide = poste mono-utilisateur, tous les droits ; compte Windows absent ou inactif = lecture seule.
    /// </summary>
    public static class RoleService
    {
        public const string UsersKey = "security.users";
        public const string Administrator = "Administrateur";
        public const string Accountant = "Comptable";
        public const string ProjectOfficer = "Chargé de projet";
        public const string Reader = "Lecteur";

        /// <summary>Rôle de <paramref name="user"/> ; null si aucun utilisateur n'est déclaré.</summary>
        public static string? CurrentRole(AppDbContext db, string user)
        {
            var row = db.AppSettings.Find(UsersKey);
            if (row == null) return null;
            List<JsonElement>? users;
            try { users = JsonSerializer.Deserialize<List<JsonElement>>(row.ValueJson); }
            catch (JsonException) { return Reader; }              // liste illisible : prudence
            if (users == null || users.Count == 0) return null;
            foreach (var u in users)
            {
                string login = u.TryGetProperty("login", out var l) ? l.GetString() ?? "" : "";
                bool active = !u.TryGetProperty("active", out var a) || a.ValueKind != JsonValueKind.False;
                if (active && string.Equals(login, user, StringComparison.OrdinalIgnoreCase))
                    return u.TryGetProperty("role", out var r) ? r.GetString() ?? Reader : Reader;
            }
            return Reader;
        }

        /// <summary>Trésorerie, relevés, rapprochement : administrateur ou comptable.</summary>
        public static bool CanEditFinance(string? role) => role is null or Administrator or Accountant;

        /// <summary>Projets, documents, rapports : tous sauf lecteur.</summary>
        public static bool CanEditProjects(string? role) => role is null or Administrator or Accountant or ProjectOfficer;

        public static string Describe(string? role) => role ?? "poste mono-utilisateur";
    }
}
