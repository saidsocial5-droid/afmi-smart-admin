using System.Security.Cryptography;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace AFMI_Gestion_projet.Services
{
    /// <summary>Manifeste d'une version publiée (latest.json), signé par la clé de publication de l'AFMI.</summary>
    public sealed class UpdateManifest
    {
        [JsonPropertyName("product")] public string Product { get; set; } = "";
        [JsonPropertyName("version")] public string Version { get; set; } = "";
        [JsonPropertyName("published")] public string Published { get; set; } = "";
        [JsonPropertyName("url")] public string Url { get; set; } = "";
        [JsonPropertyName("sha256")] public string Sha256 { get; set; } = "";
        [JsonPropertyName("size")] public long Size { get; set; }
        [JsonPropertyName("notes")] public string Notes { get; set; } = "";
    }

    /// <summary>
    /// Règles de sécurité de la mise à jour automatique (sans réseau, testables) :
    /// 1. le manifeste n'est accepté que si sa signature ECDSA P-256 / SHA-256 est valide pour la clé publique intégrée
    ///    à l'application (la clé privée n'existe que dans les secrets GitHub du dépôt) ;
    /// 2. l'installateur doit venir du dépôt de publication officiel, en HTTPS ;
    /// 3. le fichier téléchargé doit avoir exactement la taille et l'empreinte SHA-256 annoncées ;
    /// 4. seule une version strictement plus récente est proposée (jamais de retour en arrière).
    /// </summary>
    public static class UpdateVerifier
    {
        public const string ReleasesRepository = "saidsocial5-droid/afmi-smart-admin-releases";
        public const string ManifestUrl = "https://github.com/" + ReleasesRepository + "/releases/latest/download/latest.json";
        public const string SignatureUrl = ManifestUrl + ".sig";
        public const string AllowedDownloadPrefix = "https://github.com/" + ReleasesRepository + "/releases/download/";

        /// <summary>Clé publique de vérification. La clé privée correspondante est le secret GitHub UPDATE_SIGNING_KEY.</summary>
        public const string PublicKeyPem = """
            -----BEGIN PUBLIC KEY-----
            MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEl/N4ZQZZlReiqS0T50QTGguwau6R
            ZNp8hP1xr6vSCuT6rRSTZ5+cI7WGO2peYUjflL6bMyG5gTP6f8jnpjf2Iw==
            -----END PUBLIC KEY-----
            """;

        /// <summary>Vérifie la signature (DER, produite par « openssl dgst -sha256 -sign ») puis lit le manifeste.</summary>
        public static UpdateManifest ParseSigned(byte[] manifestBytes, byte[] signature, string? publicKeyPem = null)
        {
            using var key = ECDsa.Create();
            key.ImportFromPem(publicKeyPem ?? PublicKeyPem);
            if (!key.VerifyData(manifestBytes, signature, HashAlgorithmName.SHA256, DSASignatureFormat.Rfc3279DerSequence))
                throw new UpdateException("Signature du manifeste invalide : la mise à jour est refusée.");
            UpdateManifest m;
            try { m = JsonSerializer.Deserialize<UpdateManifest>(manifestBytes) ?? throw new UpdateException("Manifeste vide."); }
            catch (JsonException e) { throw new UpdateException("Manifeste illisible : " + e.Message); }
            if (m.Product != "AFMI Smart Admin") throw new UpdateException("Le manifeste ne concerne pas AFMI Smart Admin.");
            if (ParseVersion(m.Version) is null) throw new UpdateException($"Numéro de version invalide : « {m.Version} ».");
            if (!m.Url.StartsWith(AllowedDownloadPrefix, StringComparison.Ordinal) || m.Url.Contains("..") || !m.Url.EndsWith(".exe", StringComparison.OrdinalIgnoreCase))
                throw new UpdateException("Adresse de téléchargement non autorisée.");
            if (m.Sha256.Length != 64 || !m.Sha256.All(Uri.IsHexDigit)) throw new UpdateException("Empreinte SHA-256 invalide.");
            if (m.Size <= 0) throw new UpdateException("Taille de l'installateur invalide.");
            return m;
        }

        public static Version? ParseVersion(string? text)
        {
            text = (text ?? "").Trim().TrimStart('v', 'V');
            int plus = text.IndexOfAny(['+', '-']);
            if (plus >= 0) text = text[..plus];
            return System.Version.TryParse(text, out var v) && v.Major >= 0 ? Normalize(v) : null;
        }

        private static Version Normalize(Version v) => new(v.Major, v.Minor, Math.Max(v.Build, 0));

        /// <summary>Vrai seulement si la version publiée est strictement plus récente que la version installée.</summary>
        public static bool IsNewer(string published, string installed)
        {
            var p = ParseVersion(published);
            var i = ParseVersion(installed);
            return p != null && i != null && p > i;
        }

        /// <summary>Contrôle du fichier téléchargé : taille puis empreinte SHA-256.</summary>
        public static void VerifyFile(string path, UpdateManifest manifest)
        {
            var info = new FileInfo(path);
            if (!info.Exists || info.Length != manifest.Size)
                throw new UpdateException($"Taille inattendue du fichier téléchargé ({(info.Exists ? info.Length : 0)} octets au lieu de {manifest.Size}).");
            using var stream = File.OpenRead(path);
            string hash = Convert.ToHexString(SHA256.HashData(stream));
            if (!hash.Equals(manifest.Sha256, StringComparison.OrdinalIgnoreCase))
                throw new UpdateException("Empreinte SHA-256 différente : fichier altéré ou incomplet, il ne sera pas exécuté.");
        }
    }

    public sealed class UpdateException(string message) : Exception(message);
}
