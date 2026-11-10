using AFMI_Gestion_projet.Services;

namespace AFMI_Gestion_projet.Tests
{
    public class SecretProtectorTests
    {
        [Fact]
        public void ProtectedSecretRoundTrips()
        {
            string stored = SecretProtector.Protect("s3cret");
            Assert.StartsWith("dpapi:", stored);
            Assert.DoesNotContain("s3cret", stored);
            Assert.Equal("s3cret", SecretProtector.Unprotect(stored));
        }

        [Fact]
        public void LegacyPlainTextIsStillReadable()
        {
            Assert.Equal("ancien-mot-de-passe", SecretProtector.Unprotect("ancien-mot-de-passe"));
        }

        [Fact]
        public void UnreadableSecretBecomesEmpty()
        {
            Assert.Equal(string.Empty, SecretProtector.Unprotect("dpapi:AAAA"));
        }
    }
}
