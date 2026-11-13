using System.Windows;
using System.Windows.Input;

namespace AFMI_Gestion_projet.Behaviors
{
    /// <summary>
    /// Lot 11 — glisser-déposer de fichiers depuis l'explorateur Windows :
    /// <c>behaviors:FileDrop.Command="{Binding DropFilesCommand}"</c> sur une zone ; la commande reçoit les chemins (string[]).
    /// </summary>
    public static class FileDrop
    {
        public static readonly DependencyProperty CommandProperty = DependencyProperty.RegisterAttached(
            "Command", typeof(ICommand), typeof(FileDrop), new PropertyMetadata(null, OnChanged));

        public static ICommand? GetCommand(DependencyObject d) => (ICommand?)d.GetValue(CommandProperty);
        public static void SetCommand(DependencyObject d, ICommand? value) => d.SetValue(CommandProperty, value);

        private static void OnChanged(DependencyObject d, DependencyPropertyChangedEventArgs e)
        {
            if (d is not UIElement el) return;
            el.AllowDrop = e.NewValue != null;
            el.PreviewDragOver -= OnDragOver;
            el.PreviewDrop -= OnDrop;
            if (e.NewValue != null)
            {
                el.PreviewDragOver += OnDragOver;
                el.PreviewDrop += OnDrop;
            }
        }

        private static void OnDragOver(object sender, DragEventArgs e)
        {
            e.Effects = e.Data.GetDataPresent(DataFormats.FileDrop) ? DragDropEffects.Copy : DragDropEffects.None;
            e.Handled = true;
        }

        private static void OnDrop(object sender, DragEventArgs e)
        {
            if (sender is not DependencyObject d || !e.Data.GetDataPresent(DataFormats.FileDrop)) return;
            var files = (string[])e.Data.GetData(DataFormats.FileDrop);
            var cmd = GetCommand(d);
            if (files.Length > 0 && cmd?.CanExecute(files) == true) cmd.Execute(files);
            e.Handled = true;
        }
    }
}
