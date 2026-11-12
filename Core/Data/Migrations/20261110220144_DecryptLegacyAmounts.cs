using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace AFMI_Gestion_projet.Data.Migrations
{
    /// <summary>
    /// Migration de données uniquement (aucun changement de schéma), écrite à la main.
    /// Après LegacyAmountsInClear (colonnes REAL), les valeurs héritées sont encore chiffrées (texte base64) :
    /// la fonction afmi_legacy_amount, enregistrée par DatabaseMigrator, les déchiffre dans une seule transaction.
    /// Une valeur illisible fait échouer la migration ; la base reste dans l'état précédent (sauvegarde déjà faite).
    /// Le modèle cible (fichier .Designer.cs) est identique à celui de LegacyAmountsInClear.
    /// </summary>
    public partial class DecryptLegacyAmounts : Migration
    {
        internal static readonly (string Table, string Column)[] Amounts =
        {
            ("Projects", "BudgetGlobal"), ("Tasks", "Budget"), ("Tasks", "Cost"),
            ("CostEntries", "EstimatedCost"), ("CostEntries", "ActualCost"),
            ("Documents", "ApprovedGrantAmount"),
            ("Baselines", "TotalGrantCommitted"), ("Baselines", "CoFinancingShare"),
        };

        protected override void Up(MigrationBuilder migrationBuilder)
        {
            foreach (var (table, column) in Amounts)
            {
                migrationBuilder.Sql(
                    $"UPDATE \"{table}\" SET \"{column}\" = {DatabaseMigrator.LegacyAmountFunction}(\"{column}\") WHERE typeof(\"{column}\") <> 'real';");
            }
        }

        protected override void Down(MigrationBuilder migrationBuilder)
        {
            // Rien à défaire : les montants restent en clair, lisibles par toutes les versions (voir LegacyAmountsInClear).
        }
    }
}
