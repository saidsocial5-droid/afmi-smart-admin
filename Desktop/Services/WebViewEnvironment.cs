using System.IO;
using System.Threading.Tasks;
using Microsoft.Web.WebView2.Core;

namespace AFMI_Gestion_projet.Services
{
    /// <summary>
    /// Environnement WebView2 partagé (profil dans LocalAppData : le dossier d'installation est en lecture seule).
    /// Utilisé par Smart Office et par l'éditeur intégré à l'onglet Projet › Rapports.
    /// </summary>
    public static class WebViewEnvironment
    {
        private static Task<CoreWebView2Environment>? _environment;

        public static Task<CoreWebView2Environment> GetAsync()
        {
            string userData = Path.Combine(
                System.Environment.GetFolderPath(System.Environment.SpecialFolder.LocalApplicationData), "AFMIGestionProjet", "WebView2");
            return _environment ??= CoreWebView2Environment.CreateAsync(null, userData);
        }
    }
}
