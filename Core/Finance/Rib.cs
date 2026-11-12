using System.Text;

namespace AFMI_Gestion_projet.Finance
{
    public sealed record RibCheck(bool IsWellFormed, bool IsKeyValid, string Normalized, string BankCode, string CityCode,
        string AccountNumber, string Key, int? ExpectedKey)
    {
        public bool IsValid => IsWellFormed && IsKeyValid;
    }

    /// <summary>
    /// RIB marocain : 24 chiffres = code banque (3) + code localité (3) + numéro de compte (16) + clé (2).
    /// Clé = 97 − ((banque‖localité‖compte × 100) mod 97).
    /// À confirmer sur des RIB réels de l'AFMI : tant que ce n'est pas fait, une clé invalide est un avertissement.
    /// </summary>
    public static class Rib
    {
        public static string Normalize(string? input)
        {
            if (string.IsNullOrWhiteSpace(input)) return string.Empty;
            var sb = new StringBuilder(24);
            foreach (char c in input)
            {
                if (char.IsDigit(c)) sb.Append(c);
                else if (c is not (' ' or '-' or '.' or ' ')) return input.Trim(); // caractère inattendu : laissé tel quel
            }
            return sb.ToString();
        }

        public static int ComputeKey(string first22Digits)
        {
            if (first22Digits.Length != 22 || !first22Digits.All(char.IsAsciiDigit))
                throw new ArgumentException("22 chiffres attendus (banque, localité, compte).", nameof(first22Digits));
            int remainder = 0;
            foreach (char c in first22Digits + "00")
            {
                remainder = (remainder * 10 + (c - '0')) % 97;
            }
            return 97 - remainder;
        }

        public static RibCheck Check(string? input)
        {
            string rib = Normalize(input);
            if (rib.Length != 24 || !rib.All(char.IsAsciiDigit))
                return new RibCheck(false, false, rib, "", "", "", "", null);
            int expected = ComputeKey(rib[..22]);
            int actual = int.Parse(rib[22..]);
            return new RibCheck(true, expected == actual, rib, rib[..3], rib[3..6], rib[6..22], rib[22..], expected);
        }

        /// <summary>Format d'affichage « 000 000 0000000000000000 00 ».</summary>
        public static string Format(string? input)
        {
            string rib = Normalize(input);
            return rib.Length == 24 && rib.All(char.IsAsciiDigit) ? $"{rib[..3]} {rib[3..6]} {rib[6..22]} {rib[22..]}" : rib;
        }

        /// <summary>Masque pour l'affichage et les envois externes : seuls les 4 derniers chiffres restent visibles.</summary>
        public static string Mask(string? input)
        {
            string rib = Normalize(input);
            return rib.Length <= 4 ? new string('•', rib.Length) : new string('•', rib.Length - 4) + rib[^4..];
        }
    }
}
