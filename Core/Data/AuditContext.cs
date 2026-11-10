namespace AFMI_Gestion_projet.Data
{
    /// <summary>Identité inscrite dans le journal d'audit (compte Windows par défaut ; remplaçable par l'utilisateur connecté).</summary>
    public static class AuditContext
    {
        private static Func<string> _userProvider = () => Environment.UserName;

        public static string CurrentUser => _userProvider();

        public static void SetUserProvider(Func<string> provider) => _userProvider = provider ?? throw new ArgumentNullException(nameof(provider));
    }
}
