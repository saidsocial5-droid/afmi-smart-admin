using System;
using System.Linq;
using System.Net.Http;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;

namespace AFMI_Gestion_projet.Services
{
    /// <summary>
    /// Lot 11 — assistant de rédaction et dictée sur TOUTES les zones de texte de l'application de bureau, sans modifier
    /// chaque écran : un menu contextuel (clic droit) est ajouté à chaque TextBox modifiable.
    /// • ✨ Assistant IA : corriger, reformuler, enrichir, générer, résumer, traduire (sélection ou tout le texte) — même
    ///   service que Smart Office (/api/assist/text), donc même IA, mêmes règles de confidentialité ; Ctrl+Z annule.
    /// • 🎤 Dicter : ouvre la dictée vocale de Windows (Windows + H), qui écrit dans la zone où se trouve le curseur.
    /// Raccourcis : Ctrl+Maj+D (dictée), Ctrl+Maj+Espace (menu).
    /// </summary>
    public static class TextAssist
    {
        private static readonly HttpClient Http = new() { Timeout = TimeSpan.FromMinutes(3) };
        private static readonly (string Key, string Label)[] Actions =
        {
            ("corriger", "Corriger (orthographe, grammaire)"), ("reformuler", "Reformuler (style institutionnel)"),
            ("enrichir", "Enrichir / développer"), ("generer", "Générer le contenu du champ"), ("resumer", "Résumer"),
            ("traduire:ar", "Traduire en arabe"), ("traduire:fr", "Traduire en français"), ("traduire:en", "Traduire en anglais"),
        };

        public static void Register()
        {
            EventManager.RegisterClassHandler(typeof(TextBox), FrameworkElement.LoadedEvent, new RoutedEventHandler(OnLoaded));
            EventManager.RegisterClassHandler(typeof(TextBox), UIElement.PreviewKeyDownEvent, new KeyEventHandler(OnKeyDown));
        }

        private static bool Eligible(TextBox tb) =>
            !tb.IsReadOnly && tb.IsEnabled && !"no-assist".Equals(tb.Tag as string, StringComparison.Ordinal);

        private static void OnLoaded(object sender, RoutedEventArgs e)
        {
            if (sender is TextBox tb && tb.ContextMenu == null && Eligible(tb))
                tb.ContextMenu = BuildMenu(tb);
        }

        private static void OnKeyDown(object sender, KeyEventArgs e)
        {
            if (sender is not TextBox tb || !Eligible(tb) || Keyboard.Modifiers != (ModifierKeys.Control | ModifierKeys.Shift)) return;
            if (e.Key == Key.D) { Dictation.Start(tb); e.Handled = true; }
            else if (e.Key == Key.Space && tb.ContextMenu != null) { tb.ContextMenu.PlacementTarget = tb; tb.ContextMenu.IsOpen = true; e.Handled = true; }
        }

        private static ContextMenu BuildMenu(TextBox tb)
        {
            var menu = new ContextMenu();
            menu.Items.Add(new MenuItem { Header = "Couper", Command = ApplicationCommands.Cut, CommandTarget = tb });
            menu.Items.Add(new MenuItem { Header = "Copier", Command = ApplicationCommands.Copy, CommandTarget = tb });
            menu.Items.Add(new MenuItem { Header = "Coller", Command = ApplicationCommands.Paste, CommandTarget = tb });
            menu.Items.Add(new Separator());
            var ai = new MenuItem { Header = "✨ Assistant IA" };
            foreach (var (key, label) in Actions)
            {
                var item = new MenuItem { Header = label };
                item.Click += async (_, _) => await RunAsync(tb, key);
                ai.Items.Add(item);
            }
            menu.Items.Add(ai);
            var dictate = new MenuItem { Header = "🎤 Dicter au micro (Windows + H)", InputGestureText = "Ctrl+Maj+D" };
            dictate.Click += (_, _) => Dictation.Start(tb);
            menu.Items.Add(dictate);
            return menu;
        }

        /// <summary>Libellé du champ (pour « Générer ») : info-bulle, nom d'accessibilité, ou texte placé juste avant.</summary>
        private static string FieldLabel(TextBox tb)
        {
            if (tb.ToolTip is string tip && tip.Length > 0) return tip;
            string name = System.Windows.Automation.AutomationProperties.GetName(tb);
            if (!string.IsNullOrWhiteSpace(name)) return name;
            if (VisualTreeHelper.GetParent(tb) is Panel panel)
            {
                int i = panel.Children.IndexOf(tb);
                for (int k = i - 1; k >= 0; k--)
                    if (panel.Children[k] is TextBlock t && !string.IsNullOrWhiteSpace(t.Text)) return t.Text.Trim(' ', ':', '*');
            }
            return "texte";
        }

        private static async Task RunAsync(TextBox tb, string key)
        {
            string[] parts = key.Split(':');
            bool hasSelection = tb.SelectionLength > 0;
            string text = hasSelection ? tb.SelectedText : tb.Text;
            Mouse.OverrideCursor = Cursors.Wait;
            try
            {
                string url = await SmartOfficeHostService.Instance.EnsureStartedAsync();
                string payload = JsonSerializer.Serialize(new
                {
                    action = parts[0], text, field = FieldLabel(tb), target = parts.Length > 1 ? parts[1] : "",
                    context = Window.GetWindow(tb)?.Title ?? "",
                });
                using var request = new HttpRequestMessage(HttpMethod.Post, $"{url}/api/assist/text")
                {
                    Content = new StringContent(payload, Encoding.UTF8, "application/json"),
                };
                request.Headers.Add("X-AFMI-Token", SmartOfficeHostService.Instance.SessionToken ?? string.Empty);
                using var response = await Http.SendAsync(request);
                using var json = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
                if (!response.IsSuccessStatusCode)
                    throw new InvalidOperationException(json.RootElement.TryGetProperty("detail", out var d) ? d.ToString() : $"erreur {(int)response.StatusCode}");
                string result = json.RootElement.GetProperty("text").GetString() ?? string.Empty;
                tb.Focus();
                if (!hasSelection)
                {
                    if (parts[0] == "generer" && tb.Text.Trim().Length > 0) { tb.CaretIndex = tb.Text.Length; result = Environment.NewLine + result; }
                    else tb.SelectAll();
                }
                tb.SelectedText = result;                        // modification annulable par Ctrl+Z
                tb.CaretIndex = tb.SelectionStart + tb.SelectionLength;
            }
            catch (Exception ex)
            {
                MessageBox.Show(ex.Message, "Assistant IA", MessageBoxButton.OK, MessageBoxImage.Information);
            }
            finally
            {
                Mouse.OverrideCursor = null;
            }
        }
    }

    /// <summary>Dictée vocale de Windows (Windows + H) dans le champ qui a le focus ; aussi déclenchée par les pages Smart Office.</summary>
    public static class Dictation
    {
        [DllImport("user32.dll")]
        private static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);
        private const byte VkLeftWin = 0x5B, VkH = 0x48;
        private const uint KeyUp = 0x0002;

        public static void Start(UIElement? target = null)
        {
            target?.Focus();
            // Petite attente : le focus doit être dans le champ quand la dictée s'ouvre.
            Application.Current.Dispatcher.BeginInvoke(new Action(() =>
            {
                keybd_event(VkLeftWin, 0, 0, UIntPtr.Zero);
                keybd_event(VkH, 0, 0, UIntPtr.Zero);
                keybd_event(VkH, 0, KeyUp, UIntPtr.Zero);
                keybd_event(VkLeftWin, 0, KeyUp, UIntPtr.Zero);
            }), System.Windows.Threading.DispatcherPriority.Input);
        }
    }

    /// <summary>Messages des pages Smart Office affichées dans l'application (WebView2) : « dictate » → dictée Windows.</summary>
    public static class WebViewBridge
    {
        public static void Attach(Microsoft.Web.WebView2.Wpf.WebView2 view)
        {
            if (view.CoreWebView2 == null) return;
            view.CoreWebView2.WebMessageReceived += (_, e) =>
            {
                try
                {
                    using var json = JsonDocument.Parse(e.TryGetWebMessageAsString());
                    if (json.RootElement.TryGetProperty("type", out var t) && t.GetString() == "dictate")
                        Dictation.Start();      // le focus reste dans le champ de la page
                }
                catch (Exception) { /* message inconnu : ignoré */ }
            };
        }
    }
}
