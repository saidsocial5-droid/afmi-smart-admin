using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using AFMI_Gestion_projet.Models;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.ChangeTracking;

namespace AFMI_Gestion_projet.Data
{
    /// <summary>
    /// Toute écriture passe par ici : suppression logique des entités <see cref="ISoftDeletable"/>, puis journal
    /// d'audit écrit dans la même transaction que les données (pas de donnée sans trace, pas de trace sans donnée).
    /// </summary>
    public partial class AppDbContext
    {
        public const string ActionCreate = "Création";
        public const string ActionUpdate = "Modification";
        public const string ActionSoftDelete = "Suppression";
        public const string ActionHardDelete = "Suppression définitive";
        private const int MaxAuditedTextLength = 2000;

        private static readonly HashSet<(Type, string)> RedactedProperties = new()
        {
            (typeof(SmtpSettings), nameof(Models.SmtpSettings.Password)),
            (typeof(AiSettings), nameof(Models.AiSettings.CloudApiKey)),
        };

        private bool _writingAudit;

        private sealed record PendingAudit(EntityEntry Entry, string Action, Dictionary<string, object?> Changes);

        public override int SaveChanges(bool acceptAllChangesOnSuccess)
        {
            if (_writingAudit) return base.SaveChanges(acceptAllChangesOnSuccess);
            var pending = PrepareChanges();
            if (pending.Count == 0) return base.SaveChanges(acceptAllChangesOnSuccess);

            var ownTransaction = Database.CurrentTransaction == null ? Database.BeginTransaction() : null;
            try
            {
                int result = base.SaveChanges(acceptAllChangesOnSuccess);
                WriteAudit(pending);
                ownTransaction?.Commit();
                return result;
            }
            finally
            {
                ownTransaction?.Dispose();
            }
        }

        public override async Task<int> SaveChangesAsync(bool acceptAllChangesOnSuccess, CancellationToken cancellationToken = default)
        {
            if (_writingAudit) return await base.SaveChangesAsync(acceptAllChangesOnSuccess, cancellationToken);
            var pending = PrepareChanges();
            if (pending.Count == 0) return await base.SaveChangesAsync(acceptAllChangesOnSuccess, cancellationToken);

            var ownTransaction = Database.CurrentTransaction == null ? await Database.BeginTransactionAsync(cancellationToken) : null;
            try
            {
                int result = await base.SaveChangesAsync(acceptAllChangesOnSuccess, cancellationToken);
                WriteAudit(pending);
                if (ownTransaction != null) await ownTransaction.CommitAsync(cancellationToken);
                return result;
            }
            finally
            {
                if (ownTransaction != null) await ownTransaction.DisposeAsync();
            }
        }

        private List<PendingAudit> PrepareChanges()
        {
            ChangeTracker.DetectChanges();
            var now = DateTime.UtcNow;
            var pending = new List<PendingAudit>();

            foreach (var entry in ChangeTracker.Entries().ToList())
            {
                if (entry.Entity is AuditEntry)
                {
                    if (entry.State is EntityState.Modified or EntityState.Deleted)
                        throw new InvalidOperationException("Le journal d'audit est en ajout seul : modification ou suppression interdite.");
                    continue;
                }
                if (entry.Entity is AuditLog) continue; // ancien journal (lecture seule en v2)

                string? action = null;
                if (entry.State == EntityState.Deleted && entry.Entity is ISoftDeletable soft)
                {
                    entry.State = EntityState.Modified;
                    foreach (var p in entry.Properties) p.IsModified = false;
                    soft.IsDeleted = true;
                    soft.DeletedAtUtc = now;
                    entry.Property(nameof(ISoftDeletable.IsDeleted)).IsModified = true;
                    entry.Property(nameof(ISoftDeletable.DeletedAtUtc)).IsModified = true;
                    action = ActionSoftDelete;
                }

                action ??= entry.State switch
                {
                    EntityState.Added => ActionCreate,
                    EntityState.Modified => ActionUpdate,
                    EntityState.Deleted => ActionHardDelete,
                    _ => null,
                };
                if (action == null) continue;

                var changes = new Dictionary<string, object?>();
                foreach (var p in entry.Properties)
                {
                    if (p.Metadata.IsPrimaryKey() && entry.State == EntityState.Added) continue;
                    bool include = entry.State switch
                    {
                        EntityState.Added or EntityState.Deleted => true,
                        _ => p.IsModified && !Equals(p.OriginalValue, p.CurrentValue),
                    };
                    if (!include) continue;
                    var type = entry.Metadata.ClrType;
                    bool redact = RedactedProperties.Contains((type, p.Metadata.Name))
                                  || (entry.Entity is AppSetting { IsSecret: true } && p.Metadata.Name == nameof(AppSetting.ValueJson));
                    changes[p.Metadata.Name] = entry.State switch
                    {
                        EntityState.Added => new { @new = Describe(p.CurrentValue, redact) },
                        EntityState.Deleted => new { old = Describe(p.OriginalValue, redact) },
                        _ => new { old = Describe(p.OriginalValue, redact), @new = Describe(p.CurrentValue, redact) },
                    };
                }
                if (action == ActionUpdate && changes.Count == 0) continue;
                pending.Add(new PendingAudit(entry, action, changes));
            }
            return pending;
        }

        private static object? Describe(object? value, bool redact)
        {
            if (value == null) return null;
            if (redact) return "***";
            return value switch
            {
                string s when s.Length > MaxAuditedTextLength => $"[texte de {s.Length} caractères]",
                DateTime d => d.ToString("O", CultureInfo.InvariantCulture),
                DateOnly d => d.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture),
                Enum e => e.ToString(),
                IFormattable f => f.ToString(null, CultureInfo.InvariantCulture),
                _ => value.ToString(),
            };
        }

        private void WriteAudit(List<PendingAudit> pending)
        {
            _writingAudit = true;
            try
            {
                string previous = AuditEntries.OrderByDescending(a => a.Id).Select(a => a.Hash).FirstOrDefault() ?? string.Empty;
                var now = DateTime.UtcNow;
                string user = AuditContext.CurrentUser;
                string machine = Environment.MachineName;
                foreach (var p in pending)
                {
                    string key = string.Join(",", p.Entry.Metadata.FindPrimaryKey()!.Properties
                        .Select(k => Convert.ToString(p.Entry.Property(k.Name).CurrentValue, CultureInfo.InvariantCulture)));
                    var audit = new AuditEntry
                    {
                        TimestampUtc = now,
                        User = user,
                        Machine = machine,
                        EntityType = p.Entry.Metadata.ClrType.Name,
                        EntityId = key,
                        Action = p.Action,
                        ChangesJson = JsonSerializer.Serialize(p.Changes),
                        PreviousHash = previous,
                    };
                    audit.Hash = ComputeAuditHash(audit);
                    previous = audit.Hash;
                    AuditEntries.Add(audit);
                }
                base.SaveChanges(acceptAllChangesOnSuccess: true);
            }
            finally
            {
                _writingAudit = false;
            }
        }

        public static string ComputeAuditHash(AuditEntry a)
        {
            string canonical = string.Join("\u001F", a.PreviousHash, a.TimestampUtc.ToString("yyyy-MM-ddTHH:mm:ss.fffffff", CultureInfo.InvariantCulture),
                a.User, a.Machine, a.EntityType, a.EntityId, a.Action, a.ChangesJson);
            return Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(canonical)));
        }

        /// <summary>Vérifie la chaîne d'empreintes. Retourne l'identifiant de la première entrée altérée, ou null.</summary>
        public long? FindFirstTamperedAuditEntry()
        {
            string previous = string.Empty;
            foreach (var a in AuditEntries.AsNoTracking().OrderBy(a => a.Id))
            {
                if (a.PreviousHash != previous || ComputeAuditHash(a) != a.Hash) return a.Id;
                previous = a.Hash;
            }
            return null;
        }
    }
}
