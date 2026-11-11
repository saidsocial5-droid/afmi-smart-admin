using System;
using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Reflection;
using System.Threading;
using System.Threading.Tasks;
using AFMI_Gestion_projet.Data;

namespace AFMI_Gestion_projet.Services
{
    /// <summary>
    /// Mise à jour automatique : lit le manifeste signé de la dernière version publiée, télécharge l'installateur,
    /// vérifie taille et empreinte, sauvegarde la base puis lance l'installation silencieuse (l'application redémarre seule).
    /// Les règles de sécurité sont dans Core (UpdateVerifier) et testées sans réseau.
    /// </summary>
    public static class UpdateService
    {
        private static readonly HttpClient Http = CreateClient();

        private static HttpClient CreateClient()
        {
            var client = new HttpClient { Timeout = TimeSpan.FromMinutes(30) };
            client.DefaultRequestHeaders.UserAgent.ParseAdd("AFMI-Smart-Admin-Updater");
            return client;
        }

        /// <summary>Version installée (fixée à la construction par build_installer.bat : -p:Version).</summary>
        public static string InstalledVersion
        {
            get
            {
                var asm = Assembly.GetEntryAssembly() ?? typeof(UpdateService).Assembly;
                var info = asm.GetCustomAttribute<AssemblyInformationalVersionAttribute>()?.InformationalVersion;
                var v = UpdateVerifier.ParseVersion(info) ?? UpdateVerifier.ParseVersion(asm.GetName().Version?.ToString());
                return v?.ToString(3) ?? "0.0.0";
            }
        }

        public static bool AutoCheckEnabled()
        {
            try
            {
                using var db = new AppDbContext();
                return new SettingsService(db).Get<bool>(SettingKeys.UpdatesAutoCheck);
            }
            catch { return true; }
        }

        /// <summary>Renvoie le manifeste si une version plus récente est publiée, sinon null. Lève UpdateException si le manifeste est refusé.</summary>
        public static async Task<UpdateManifest?> CheckAsync(CancellationToken ct = default)
        {
            byte[] manifest, signature;
            try
            {
                using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
                cts.CancelAfter(TimeSpan.FromSeconds(30));
                manifest = await Http.GetByteArrayAsync(UpdateVerifier.ManifestUrl, cts.Token);
                signature = await Http.GetByteArrayAsync(UpdateVerifier.SignatureUrl, cts.Token);
            }
            catch (HttpRequestException e) when (e.StatusCode == System.Net.HttpStatusCode.NotFound)
            {
                return null;                                  // aucune version publiée pour l'instant
            }
            var m = UpdateVerifier.ParseSigned(manifest, signature);
            return UpdateVerifier.IsNewer(m.Version, InstalledVersion) ? m : null;
        }

        public static string DownloadFolder =>
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "AFMI Smart Admin", "Mises à jour");

        /// <summary>Télécharge l'installateur (reprend un fichier déjà vérifié), puis contrôle taille et SHA-256.</summary>
        public static async Task<string> DownloadAsync(UpdateManifest m, IProgress<double>? progress, CancellationToken ct = default)
        {
            Directory.CreateDirectory(DownloadFolder);
            foreach (var old in Directory.GetFiles(DownloadFolder, "AFMI_Smart_Admin_Setup_*"))
                if (!Path.GetFileName(old).Contains(m.Version)) TryDelete(old);
            string target = Path.Combine(DownloadFolder, $"AFMI_Smart_Admin_Setup_{m.Version}.exe");
            if (File.Exists(target))
            {
                try { UpdateVerifier.VerifyFile(target, m); return target; }
                catch (UpdateException) { TryDelete(target); }
            }
            string partial = target + ".partial";
            using (var response = await Http.GetAsync(m.Url, HttpCompletionOption.ResponseHeadersRead, ct))
            {
                response.EnsureSuccessStatusCode();
                await using var input = await response.Content.ReadAsStreamAsync(ct);
                await using var output = File.Create(partial);
                var buffer = new byte[1 << 16];
                long done = 0;
                int read;
                while ((read = await input.ReadAsync(buffer, ct)) > 0)
                {
                    await output.WriteAsync(buffer.AsMemory(0, read), ct);
                    done += read;
                    if (done > m.Size) throw new UpdateException("Le fichier téléchargé dépasse la taille annoncée.");
                    progress?.Report((double)done / m.Size);
                }
            }
            try { UpdateVerifier.VerifyFile(partial, m); }
            catch { TryDelete(partial); throw; }
            File.Move(partial, target, overwrite: true);
            return target;
        }

        /// <summary>Sauvegarde la base, puis lance l'installateur vérifié en mode silencieux. L'appelant ferme ensuite l'application.</summary>
        public static void BackupAndLaunch(string installer, UpdateManifest m)
        {
            string db = DatabasePaths.GetDatabasePath();
            if (File.Exists(db))
            {
                using var ctx = new AppDbContext();
                var settings = new SettingsService(ctx);
                BackupService.Create(db, BackupService.ResolveFolder(db, settings.Get<string>(SettingKeys.BackupFolder)), $"avant_mise_a_jour_{m.Version}");
            }
            // Vérification juste avant l'exécution (le fichier ne doit pas avoir changé depuis le téléchargement)
            UpdateVerifier.VerifyFile(installer, m);
            Process.Start(new ProcessStartInfo(installer, "/SILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS")
            {
                UseShellExecute = true,                       // permet l'élévation si l'application est installée pour tous
            });
        }

        private static void TryDelete(string path)
        {
            try { File.Delete(path); } catch { /* fichier verrouillé : il sera remplacé plus tard */ }
        }
    }
}
