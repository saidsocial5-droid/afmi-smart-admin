namespace AFMI_Gestion_projet.Models
{
    /// <summary>
    /// Entité supprimée logiquement : un <c>Remove()</c> est converti en mise à jour par <c>AppDbContext.SaveChanges</c>
    /// et un filtre global masque la ligne. Les données financières ne sont jamais effacées physiquement.
    /// </summary>
    public interface ISoftDeletable
    {
        bool IsDeleted { get; set; }
        DateTime? DeletedAtUtc { get; set; }
    }
}
