using System;
using AFMI_Gestion_projet.Data;
using AFMI_Gestion_projet.Models;

namespace AFMI_Gestion_projet.Services
{
    public class AuditService
    {
        public void LogChange(AppDbContext context, int projectId, string entityType, int entityId, 
            string changeType, string fieldName, string oldValue, string newValue, string user = "Utilisateur local")
        {
            try
            {
                var log = new AuditLog
                {
                    ProjectId = projectId,
                    EntityType = entityType,
                    EntityId = entityId,
                    ChangeType = changeType,
                    FieldName = fieldName,
                    OldValue = oldValue ?? string.Empty,
                    NewValue = newValue ?? string.Empty,
                    Timestamp = DateTime.Now,
                    User = user
                };

                context.AuditLogs.Add(log);
                context.SaveChanges();
            }
            catch (Exception ex)
            {
                // Silent fail to avoid crashing the app on logging issues
                System.Diagnostics.Debug.WriteLine($"Failed to write audit log: {ex.Message}");
            }
        }
    }
}
