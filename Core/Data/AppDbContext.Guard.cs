using AFMI_Gestion_projet.Models;
using Models = AFMI_Gestion_projet.Models;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.ChangeTracking;

namespace AFMI_Gestion_projet.Data
{
    /// <summary>Zone fonctionnelle d'une écriture, pour les rôles (mêmes zones que backend/core/roles.py).</summary>
    public enum WriteArea { Settings, Finance, Projects, System }

    /// <summary>
    /// Contrôle des droits au moment de l'enregistrement (Lot 8) : tous les écrans de l'application de bureau, y compris
    /// ceux de la 1.3.0, passent par SaveChanges. Le Desktop fixe <see cref="DefaultWritePermission"/> au démarrage
    /// d'après le rôle de l'utilisateur ; sans politique (null), tout est permis.
    /// </summary>
    public partial class AppDbContext
    {
        public static Func<WriteArea, bool>? DefaultWritePermission { get; set; }

        /// <summary>Politique de ce contexte (initialisée avec la politique par défaut ; les tests la fixent par instance).</summary>
        public Func<WriteArea, bool>? WritePermission { get; set; } = DefaultWritePermission;

        private static readonly string[] SystemSettingPrefixes = ["backup.", "notifications.state", "ai.usage."];

        public static WriteArea AreaOf(EntityEntry entry)
        {
            switch (entry.Entity)
            {
                case AppSetting s:
                    return SystemSettingPrefixes.Any(p => s.Key.StartsWith(p, StringComparison.Ordinal)) ? WriteArea.System : WriteArea.Settings;
                case Models.SmtpSettings when entry.State == EntityState.Modified &&
                                       entry.Properties.Where(p => p.IsModified).All(p => p.Metadata.Name.StartsWith("LastSent", StringComparison.Ordinal)):
                    return WriteArea.System;          // suivi des envois programmés
                case Models.SmtpSettings or Models.AiSettings:
                    return WriteArea.Settings;
                case AuditEntry:
                    return WriteArea.System;
            }
            string ns = entry.Entity.GetType().Namespace ?? "";
            return ns.EndsWith(".Finance", StringComparison.Ordinal) ? WriteArea.Finance : WriteArea.Projects;
        }

        private void EnforceWritePermission()
        {
            if (WritePermission is not { } allowed) return;
            foreach (var entry in ChangeTracker.Entries())
            {
                if (entry.State is EntityState.Unchanged or EntityState.Detached) continue;
                var area = AreaOf(entry);
                if (area != WriteArea.System && !allowed(area))
                    throw new UnauthorizedAccessException(area switch
                    {
                        WriteArea.Settings => "Action réservée à l'administrateur (paramètres).",
                        WriteArea.Finance => "Votre rôle ne permet pas de modifier la trésorerie.",
                        _ => "Votre rôle ne permet que la consultation.",
                    });
            }
        }
    }
}
