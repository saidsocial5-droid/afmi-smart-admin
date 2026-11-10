using System.Windows;
using System.Windows.Controls;
using AFMI_Gestion_projet.ViewModels;

namespace AFMI_Gestion_projet.Views
{
    public partial class TemplateView : UserControl
    {
        public TemplateView()
        {
            InitializeComponent();
        }

        private void OnCancelCreateClick(object sender, RoutedEventArgs e)
        {
            if (DataContext is TemplateViewModel vm)
            {
                vm.IsCreateFromTemplateVisible = false;
            }
        }
    }
}
