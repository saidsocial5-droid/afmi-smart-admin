using System.Text;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Navigation;
using System.Windows.Shapes;

namespace AFMI_Gestion_projet;

/// <summary>
/// Interaction logic for MainWindow.xaml
/// </summary>
public partial class MainWindow : Window
{
    public MainWindow()
    {
        InitializeComponent();
        DataContext = new ViewModels.MainViewModel();
    }

    private void OnSmtpOverlayVisibleChanged(object sender, DependencyPropertyChangedEventArgs e)
    {
        if (sender is Grid grid && grid.Visibility == Visibility.Visible && DataContext is ViewModels.MainViewModel vm && vm.SmtpConfig != null)
        {
            SmtpPasswordBox.Password = vm.SmtpConfig.Password;
        }
    }

    private void OnSaveSmtpClick(object sender, RoutedEventArgs e)
    {
        if (DataContext is ViewModels.MainViewModel vm)
        {
            vm.SmtpConfig.Password = SmtpPasswordBox.Password;
            if (vm.SaveSmtpSettingsCommand.CanExecute(null))
            {
                vm.SaveSmtpSettingsCommand.Execute(null);
            }
        }
    }

    private void OnCancelSmtpClick(object sender, RoutedEventArgs e)
    {
        if (DataContext is ViewModels.MainViewModel vm)
        {
            vm.IsSmtpConfigVisible = false;
        }
    }
}