using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;

namespace AFMI_Gestion_projet.Data
{
    /// <summary>Utilisé uniquement par « dotnet ef » pour générer les migrations (aucune base réelle n'est touchée).</summary>
    internal sealed class DesignTimeDbContextFactory : IDesignTimeDbContextFactory<AppDbContext>
    {
        public AppDbContext CreateDbContext(string[] args) =>
            AppDbContext.WithoutMigration(new DbContextOptionsBuilder<AppDbContext>()
                .UseSqlite("Data Source=design_time.db").Options);
    }
}
