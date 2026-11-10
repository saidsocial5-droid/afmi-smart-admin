using System.Windows;
using System.Windows.Controls;
using AFMI_Gestion_projet.Models;
using AFMI_Gestion_projet.ViewModels;

namespace AFMI_Gestion_projet.Views
{
    public partial class PortfolioView : UserControl
    {
        public PortfolioView()
        {
            InitializeComponent();
        }

        private void OnCompareChecked(object sender, RoutedEventArgs e)
        {
            if (sender is CheckBox cb && cb.Tag is Project p && DataContext is PortfolioViewModel vm)
            {
                if (!vm.SelectedProjectsForAction.Contains(p))
                {
                    vm.SelectedProjectsForAction.Add(p);
                }
            }
        }

        private void OnCompareUnchecked(object sender, RoutedEventArgs e)
        {
            if (sender is CheckBox cb && cb.Tag is Project p && DataContext is PortfolioViewModel vm)
            {
                vm.SelectedProjectsForAction.Remove(p);
            }
        }

        private void OnCompareClick(object sender, RoutedEventArgs e)
        {
            if (DataContext is PortfolioViewModel vm)
            {
                vm.CompareSelectedCommand.Execute(null);
            }
        }

        private void OnCancelEditClick(object sender, RoutedEventArgs e)
        {
            if (DataContext is PortfolioViewModel vm)
            {
                vm.IsEditDialogVisible = false;
            }
        }

        private void OnCancelCreateFromTemplateClick(object sender, RoutedEventArgs e)
        {
            if (DataContext is TemplateViewModel vm)
            {
                vm.IsCreateFromTemplateVisible = false;
            }
        }
    }
}
