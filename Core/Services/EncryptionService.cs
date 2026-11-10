using System;
using System.IO;
using System.Security.Cryptography;
using System.Text;

namespace AFMI_Gestion_projet.Services
{
    public static class EncryptionService
    {
        // 256-bit encryption key and 128-bit initialization vector (obfuscated static keys)
        private static readonly byte[] Key = Encoding.UTF8.GetBytes("AFMI_SecureKey_2026_ProjectPM2!!"); // 32 bytes
        private static readonly byte[] Iv = Encoding.UTF8.GetBytes("AFMI_InitVector!");                 // 16 bytes

        /// <summary>
        /// Encrypts a string value using AES-256
        /// </summary>
        public static string Encrypt(string plainText)
        {
            if (string.IsNullOrEmpty(plainText)) return string.Empty;

            try
            {
                using (var aes = Aes.Create())
                {
                    aes.Key = Key;
                    aes.IV = Iv;

                    var encryptor = aes.CreateEncryptor(aes.Key, aes.IV);
                    using (var ms = new MemoryStream())
                    {
                        using (var cs = new CryptoStream(ms, encryptor, CryptoStreamMode.Write))
                        {
                            using (var sw = new StreamWriter(cs))
                            {
                                sw.Write(plainText);
                            }
                        }
                        return Convert.ToBase64String(ms.ToArray());
                    }
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Encryption error: {ex.Message}");
                return plainText; // Fallback to plain text on error to prevent data loss
            }
        }

        /// <summary>
        /// Decrypts a base64 encoded AES-256 ciphertext
        /// </summary>
        public static string Decrypt(string cipherText)
        {
            if (string.IsNullOrEmpty(cipherText)) return string.Empty;

            try
            {
                var cipherBytes = Convert.FromBase64String(cipherText);
                using (var aes = Aes.Create())
                {
                    aes.Key = Key;
                    aes.IV = Iv;

                    var decryptor = aes.CreateDecryptor(aes.Key, aes.IV);
                    using (var ms = new MemoryStream(cipherBytes))
                    {
                        using (var cs = new CryptoStream(ms, decryptor, CryptoStreamMode.Read))
                        {
                            using (var sr = new StreamReader(cs))
                            {
                                return sr.ReadToEnd();
                            }
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Decryption error: {ex.Message}");
                return cipherText; // Return original on error (e.g. if database is not encrypted yet)
            }
        }
    }
}
