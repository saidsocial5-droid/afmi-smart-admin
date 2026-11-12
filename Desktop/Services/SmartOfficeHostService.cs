using System;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Net.Http;
using System.Net.Sockets;
using System.Threading;
using System.Threading.Tasks;

namespace AFMI_Gestion_projet.Services
{
    /// <summary>
    /// Démarre et supervise le backend Python « Smart Office » (FastAPI) intégré à l'application.
    /// Le backend sert aussi l'interface React compilée (SmartOffice/frontend/dist), affichée dans un WebView2.
    /// </summary>
    public sealed class SmartOfficeHostService
    {
        public static SmartOfficeHostService Instance { get; } = new();

        private static readonly HttpClient _httpClient = new() { Timeout = TimeSpan.FromSeconds(2) };
        private readonly SemaphoreSlim _startLock = new(1, 1);
        private Process? _process;

        public string? BaseUrl { get; private set; }

        /// <summary>Jeton de la session en cours (à passer à la page via ?afmi_token=…, ou en en-tête X-AFMI-Token).</summary>
        public string? SessionToken { get; private set; }

        public string LogFilePath { get; } = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "AFMIGestionProjet", "smartoffice.log");

        public bool IsRunning => _process != null && !_process.HasExited && BaseUrl != null;

        /// <summary>
        /// Démarre le backend s'il ne tourne pas déjà, puis attend qu'il réponde. Retourne l'URL de base.
        /// </summary>
        public async Task<string> EnsureStartedAsync(CancellationToken cancellationToken = default)
        {
            await _startLock.WaitAsync(cancellationToken);
            try
            {
                if (IsRunning) return BaseUrl!;

                int port = GetFreeLoopbackPort();
                string url = $"http://127.0.0.1:{port}";

                var psi = new ProcessStartInfo
                {
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                };

                // 1) Version installée : backend compilé (PyInstaller) livré avec l'application, sans Python requis.
                //    Le dossier d'installation est en lecture seule : les données vont dans %LocalAppData%.
                // 2) Développement : sources Python du dossier SmartOffice.
                string? bundledExe = LocateBundledBackend();
                string? root = null;
                if (bundledExe != null)
                {
                    psi.FileName = bundledExe;
                    psi.WorkingDirectory = Path.GetDirectoryName(bundledExe)!;
                    // AFMI_DATA_DIR déjà fixé (fenêtre de démonstration) : conservé
                    psi.Environment["AFMI_DATA_DIR"] = Environment.GetEnvironmentVariable("AFMI_DATA_DIR") ?? InstalledDataDir;
                    foreach (var arg in new[] { "--host", "127.0.0.1", "--port", port.ToString() }) psi.ArgumentList.Add(arg);
                }
                else
                {
                    root = LocateSmartOfficeRoot()
                        ?? throw new InvalidOperationException(
                            "Moteur Smart Office introuvable : ni backend installé, ni dossier « SmartOffice » à côté de « Desktop ». " +
                            "Réinstallez l'application ou définissez AFMI_SMARTOFFICE_DIR.");
                    psi.FileName = Environment.GetEnvironmentVariable("AFMI_PYTHON") ?? "python";
                    psi.WorkingDirectory = root;
                    foreach (var arg in new[] { "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", port.ToString() })
                    {
                        psi.ArgumentList.Add(arg);
                    }
                }
                // Jeton de session : seule cette application (et sa fenêtre Smart Office) peut appeler l'API locale.
                string token = Convert.ToHexString(System.Security.Cryptography.RandomNumberGenerator.GetBytes(32));
                psi.Environment["AFMI_API_TOKEN"] = token;
                // Base unique du poste, partagée avec le backend (schéma géré par les migrations EF Core).
                psi.Environment["AFMI_DESKTOP_DB"] = AFMI_Gestion_projet.Data.DatabasePaths.GetDatabasePath();
                psi.Environment["AFMI_AUDIT_USER"] = AFMI_Gestion_projet.Data.AuditContext.CurrentUser;

                // Le backend affiche de l'arabe et des emojis : sans UTF-8 la console Windows (cp1252) fait planter print().
                psi.Environment["PYTHONIOENCODING"] = "utf-8";
                psi.Environment["PYTHONUTF8"] = "1";

                Directory.CreateDirectory(Path.GetDirectoryName(LogFilePath)!);
                var log = new StreamWriter(LogFilePath, append: false) { AutoFlush = true };

                Process process;
                try
                {
                    process = Process.Start(psi) ?? throw new InvalidOperationException("Le processus Python n'a pas démarré.");
                }
                catch (System.ComponentModel.Win32Exception)
                {
                    log.Dispose();
                    throw new InvalidOperationException(
                        "Python est introuvable. Installez Python 3.11+ puis exécutez SmartOffice\\install_backend.bat " +
                        "(ou définissez AFMI_PYTHON avec le chemin de python.exe).");
                }

                void WriteLog(string? line)
                {
                    if (line == null) return;
                    lock (log)
                    {
                        try { log.WriteLine(line); } catch (ObjectDisposedException) { }
                    }
                }
                process.OutputDataReceived += (_, e) => WriteLog(e.Data);
                process.ErrorDataReceived += (_, e) => WriteLog(e.Data);
                process.EnableRaisingEvents = true;
                process.Exited += (_, _) => { lock (log) log.Dispose(); };
                process.BeginOutputReadLine();
                process.BeginErrorReadLine();

                // Port publié pour les autres clients éventuels en développement (Electron, navigateur).
                if (root != null)
                {
                    try { File.WriteAllText(Path.Combine(root, "backend", "data", ".backend_port"), port.ToString()); } catch { }
                }

                _process = process;

                var deadline = DateTime.UtcNow.AddSeconds(45);
                while (DateTime.UtcNow < deadline)
                {
                    cancellationToken.ThrowIfCancellationRequested();
                    if (process.HasExited)
                    {
                        _process = null;
                        throw new InvalidOperationException(
                            $"Le backend Smart Office s'est arrêté (code {process.ExitCode}). " +
                            $"Vérifiez les dépendances Python (SmartOffice\\install_backend.bat). Journal : {LogFilePath}");
                    }
                    try
                    {
                        using var request = new HttpRequestMessage(HttpMethod.Get, $"{url}/api/agents");
                        request.Headers.Add("X-AFMI-Token", token);
                        using var response = await _httpClient.SendAsync(request, cancellationToken);
                        if (response.IsSuccessStatusCode)
                        {
                            BaseUrl = url;
                            SessionToken = token;
                            return url;
                        }
                    }
                    catch (HttpRequestException) { }
                    catch (TaskCanceledException) when (!cancellationToken.IsCancellationRequested) { }

                    await Task.Delay(400, cancellationToken);
                }

                Stop();
                throw new TimeoutException($"Le backend Smart Office ne répond pas après 45 s. Journal : {LogFilePath}");
            }
            finally
            {
                _startLock.Release();
            }
        }

        /// <summary>
        /// Arrête le backend et ses processus enfants. Appelé à la fermeture de l'application.
        /// </summary>
        public void Stop()
        {
            var process = _process;
            _process = null;
            BaseUrl = null;
            if (process == null) return;

            try
            {
                if (!process.HasExited) process.Kill(entireProcessTree: true);
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[SmartOffice] Arrêt impossible : {ex.Message}");
            }
            finally
            {
                process.Dispose();
            }
        }

        /// <summary>Données du backend en version installée (base, exports, profil institutionnel).</summary>
        public static string InstalledDataDir { get; } = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "AFMI Smart Admin", "SmartOffice");

        private static string? LocateBundledBackend()
        {
            string candidate = Path.Combine(AppContext.BaseDirectory, "SmartOffice", "smartoffice-backend", "smartoffice-backend.exe");
            return File.Exists(candidate) ? candidate : null;
        }

        private static string? LocateSmartOfficeRoot()
        {
            string? fromEnv = Environment.GetEnvironmentVariable("AFMI_SMARTOFFICE_DIR");
            if (!string.IsNullOrWhiteSpace(fromEnv) && IsSmartOfficeRoot(fromEnv)) return fromEnv;

            // Remonte depuis le dossier de l'exécutable (bin\Debug\net9.0-windows en dev, dossier publish en prod).
            var dir = new DirectoryInfo(AppContext.BaseDirectory);
            while (dir != null)
            {
                string candidate = Path.Combine(dir.FullName, "SmartOffice");
                if (IsSmartOfficeRoot(candidate)) return candidate;
                dir = dir.Parent;
            }
            return null;
        }

        private static bool IsSmartOfficeRoot(string path) =>
            File.Exists(Path.Combine(path, "backend", "main.py"));

        private static int GetFreeLoopbackPort()
        {
            var listener = new TcpListener(IPAddress.Loopback, 0);
            listener.Start();
            int port = ((IPEndPoint)listener.LocalEndpoint).Port;
            listener.Stop();
            return port;
        }
    }
}
