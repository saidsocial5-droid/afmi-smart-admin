using System.Security.Cryptography;
using System.Text;
using AFMI_Gestion_projet.Services;
using Xunit;

namespace AFMI_Gestion_projet.Core.Tests
{
    public class UpdateVerifierTests
    {
        private static readonly ECDsa Key = ECDsa.Create(ECCurve.NamedCurves.nistP256);
        private static string PublicPem => Key.ExportSubjectPublicKeyInfoPem();

        private static string Manifest(string version = "2.2.0", string? url = null, string sha = "", long size = 3) =>
            $$"""
            {"product":"AFMI Smart Admin","version":"{{version}}","published":"2026-11-12","url":"{{url ?? UpdateVerifier.AllowedDownloadPrefix + "v" + version + "/AFMI_Smart_Admin_Setup_" + version + ".exe"}}",
             "sha256":"{{(sha == "" ? new string('a', 64) : sha)}}","size":{{size}},"notes":"Nouveautés"}
            """;

        private static byte[] Sign(byte[] data) => Key.SignData(data, HashAlgorithmName.SHA256, DSASignatureFormat.Rfc3279DerSequence);

        [Fact]
        public void SignedManifest_IsAccepted()
        {
            var bytes = Encoding.UTF8.GetBytes(Manifest());
            var m = UpdateVerifier.ParseSigned(bytes, Sign(bytes), PublicPem);
            Assert.Equal("2.2.0", m.Version);
            Assert.Equal(3, m.Size);
        }

        [Fact]
        public void TamperedManifest_IsRefused()
        {
            var bytes = Encoding.UTF8.GetBytes(Manifest());
            var sig = Sign(bytes);
            var tampered = Encoding.UTF8.GetBytes(Manifest(sha: new string('b', 64)));
            Assert.Throws<UpdateException>(() => UpdateVerifier.ParseSigned(tampered, sig, PublicPem));
        }

        [Fact]
        public void ManifestSignedByAnotherKey_IsRefused()
        {
            var bytes = Encoding.UTF8.GetBytes(Manifest());
            using var other = ECDsa.Create(ECCurve.NamedCurves.nistP256);
            var sig = other.SignData(bytes, HashAlgorithmName.SHA256, DSASignatureFormat.Rfc3279DerSequence);
            Assert.Throws<UpdateException>(() => UpdateVerifier.ParseSigned(bytes, sig, PublicPem));
            // Ni la clé de l'application : une signature de test n'est jamais acceptée par la clé intégrée
            Assert.Throws<UpdateException>(() => UpdateVerifier.ParseSigned(bytes, Sign(bytes)));
        }

        [Theory]
        [InlineData("https://example.com/AFMI_Smart_Admin_Setup_2.2.0.exe")]
        [InlineData("http://github.com/saidsocial5-droid/afmi-smart-admin-releases/releases/download/v2.2.0/x.exe")]
        [InlineData("https://github.com/saidsocial5-droid/afmi-smart-admin-releases/releases/download/../../other/x.exe")]
        [InlineData("https://github.com/saidsocial5-droid/afmi-smart-admin-releases/releases/download/v2.2.0/script.ps1")]
        public void ForeignDownloadUrl_IsRefused(string url)
        {
            var bytes = Encoding.UTF8.GetBytes(Manifest(url: url));
            Assert.Throws<UpdateException>(() => UpdateVerifier.ParseSigned(bytes, Sign(bytes), PublicPem));
        }

        [Theory]
        [InlineData("2.2.0", "2.1.0", true)]
        [InlineData("v2.10.0", "2.9.5", true)]
        [InlineData("2.1.0", "2.1.0", false)]
        [InlineData("2.1", "2.1.0", false)]
        [InlineData("2.0.9", "2.1.0", false)]
        [InlineData("2.2.0", "2.1.0+abc123", true)]
        [InlineData("n'importe quoi", "2.1.0", false)]
        public void OnlyStrictlyNewerVersionsAreOffered(string published, string installed, bool expected) =>
            Assert.Equal(expected, UpdateVerifier.IsNewer(published, installed));

        [Fact]
        public void DownloadedFile_MustMatchSizeAndHash()
        {
            string path = Path.GetTempFileName();
            try
            {
                File.WriteAllBytes(path, [1, 2, 3]);
                string sha = Convert.ToHexString(SHA256.HashData(new byte[] { 1, 2, 3 }));
                var ok = new UpdateManifest { Sha256 = sha, Size = 3 };
                UpdateVerifier.VerifyFile(path, ok);
                Assert.Throws<UpdateException>(() => UpdateVerifier.VerifyFile(path, new UpdateManifest { Sha256 = sha, Size = 4 }));
                Assert.Throws<UpdateException>(() => UpdateVerifier.VerifyFile(path, new UpdateManifest { Sha256 = new string('0', 64), Size = 3 }));
            }
            finally { File.Delete(path); }
        }

        [Fact]
        public void OpenSslSignature_IsUnderstood()
        {
            // Manifeste signé par « openssl dgst -sha256 -sign » (même commande que le workflow de publication), clé de test jetable
            const string pub = """
                -----BEGIN PUBLIC KEY-----
                MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE+3DV/q72/GsbK37fY/4YyLGvdFdB
                ojopt+Gr0pAdkY6dOgowR7tuSFk+/SGhpvNb9mRTE4pR5wlwPK0c1GO0Sw==
                -----END PUBLIC KEY-----
                """;
            var json = Convert.FromBase64String("eyJwcm9kdWN0IjoiQUZNSSBTbWFydCBBZG1pbiIsInZlcnNpb24iOiI5LjkuOSIsInB1Ymxpc2hlZCI6IjIwMjYtMTEtMTIiLCJ1cmwiOiJodHRwczovL2dpdGh1Yi5jb20vc2FpZHNvY2lhbDUtZHJvaWQvYWZtaS1zbWFydC1hZG1pbi1yZWxlYXNlcy9yZWxlYXNlcy9kb3dubG9hZC92OS45LjkvQUZNSV9TbWFydF9BZG1pbl9TZXR1cF85LjkuOS5leGUiLCJzaGEyNTYiOiIyZDcxMTY0MmI3MjZiMDQ0MDE2MjdjYTlmYmFjMzJmNWM4NTMwZmIxOTAzY2M0ZGIwMjI1ODcxNzkyMWE0ODgxIiwic2l6ZSI6MSwibm90ZXMiOiJ0ZXN0IG9wZW5zc2wifQ==");
            var sig = Convert.FromBase64String("MEUCIQCYpzCc3IsZkSO63nmEeFzM5+dBgZz4z7rXbCl2xoLwAgIgQDXLf2UyD5fx6TUr24tHsazq3nFig2iKs1AHpKhgF/o=");
            Assert.Equal("9.9.9", UpdateVerifier.ParseSigned(json, sig, pub).Version);
        }

        [Fact]
        public void EmbeddedPublicKey_IsAValidP256Key()
        {
            using var k = ECDsa.Create();
            k.ImportFromPem(UpdateVerifier.PublicKeyPem);
            Assert.Equal(256, k.KeySize);
        }
    }
}
