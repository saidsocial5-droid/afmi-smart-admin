using System.Windows;
using System.Windows.Controls;
using AFMI_Gestion_projet.ViewModels;

namespace AFMI_Gestion_projet.Views
{
    public partial class ProjectDetailView : UserControl
    {
        public ProjectDetailView()
        {
            InitializeComponent();
        }

        private void OnCancelTaskClick(object sender, RoutedEventArgs e)
        {
            if (DataContext is ProjectDetailViewModel vm)
            {
                vm.IsTaskEditVisible = false;
            }
        }

        private void OnCancelCostClick(object sender, RoutedEventArgs e)
        {
            if (DataContext is ProjectDetailViewModel vm)
            {
                vm.IsCostEditVisible = false;
            }
        }

        private void OnCancelStepClick(object sender, RoutedEventArgs e)
        {
            if (DataContext is ProjectDetailViewModel vm)
            {
                vm.IsStepEditVisible = false;
            }
        }

        private void OnCancelDocumentUploadClick(object sender, RoutedEventArgs e)
        {
            if (DataContext is ProjectDetailViewModel vm)
            {
                vm.IsDocumentUploadVisible = false;
            }
        }

        private void OnCancelDocumentPreviewClick(object sender, RoutedEventArgs e)
        {
            if (DataContext is ProjectDetailViewModel vm)
            {
                vm.IsDocumentPreviewVisible = false;
            }
        }

        private void OnCancelWorkProgramClick(object sender, RoutedEventArgs e)
        {
            if (DataContext is ProjectDetailViewModel vm)
            {
                vm.IsWorkProgramModalVisible = false;
            }
        }
    }
}


