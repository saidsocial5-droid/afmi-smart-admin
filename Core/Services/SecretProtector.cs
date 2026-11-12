using System;
using System.Security.Cryptography;
using System.Text;

namespace AFMI_Gestion_projet.Services
{
    /// <summary>
    /// Protège les secrets stockés en base (mot de passe SMTP, clé API) avec DPAPI (compte Windows courant).
    /// Les anciennes valeurs en clair restent lisibles et sont chiffrées à la prochaine sauvegarde.
    /// </summary>
    public static class SecretProtector
    {
        private const string Prefix = "dpapi:";
        private static readonly byte[] Entropy = Encoding.UTF8.GetBytes("AFMI-SmartAdmin-Secrets");

        public static string Protect(string plainText)
        {
            if (string.IsNullOrEmpty(plainText)) return string.Empty;
            byte[] cipher = ProtectedData.Protect(Encoding.UTF8.GetBytes(plainText), Entropy, DataProtectionScope.CurrentUser);
            return Prefix + Convert.ToBase64String(cipher);
        }

        public static string Unprotect(string stored)
        {
            if (string.IsNullOrEmpty(stored)) return string.Empty;
            if (!stored.StartsWith(Prefix, StringComparison.Ordinal)) return stored; // valeur héritée en clair

            try
            {
                byte[] plain = ProtectedData.Unprotect(Convert.FromBase64String(stored[Prefix.Length..]), Entropy, DataProtectionScope.CurrentUser);
                return Encoding.UTF8.GetString(plain);
            }
            catch (Exception ex) when (ex is CryptographicException or FormatException)
            {
                // Base importée depuis un autre compte/poste : le secret doit être ressaisi.
                return string.Empty;
            }
        }
    }
}
