using System;
using System.Linq;
using System.Threading;
using AFMI_Gestion_projet.Data;
using AFMI_Gestion_projet.ViewModels;
using Xunit;

namespace AFMI_Gestion_projet.Tests;

public class UnitTest1
{
    [Fact]
    public void TestOpenAllProjectsFromDb()
    {
        using var db = new AppDbContext();
        var projects = db.Projects.ToList();
        var mainVM = new MainViewModel();

        foreach (var p in projects)
        {
            Console.WriteLine($"Testing project {p.Id}: {p.Code} - {p.Name}");
            mainVM.NavigateToProjectDetail(p.Id);
            Assert.NotNull(mainVM.CurrentViewModel);
        }
    }

    [Fact]
    public void TestCreateProjectDetailViewInSta()
    {
        Exception? exception = null;
        var thread = new Thread(() =>
        {
            try
            {
                if (System.Windows.Application.Current == null)
                {
                    var app = new System.Windows.Application();
                    var dict = new System.Windows.ResourceDictionary();
                    dict.Source = new Uri("pack://application:,,,/AFMI Smart Admin;component/Themes/ModernStyles.xaml");
                    app.Resources.MergedDictionaries.Add(dict);
                }

                using var db = new AppDbContext();
                var projects = db.Projects.ToList();
                foreach (var p in projects)
                {
                    Console.WriteLine($"Testing STA View for project {p.Id}: {p.Code} - {p.Name}");
                    var mainVM = new MainViewModel();
                    mainVM.NavigateToProjectDetail(p.Id);
                    var detailView = new AFMI_Gestion_projet.Views.ProjectDetailView();
                    detailView.DataContext = mainVM.CurrentViewModel;
                }

                // Also test other views
                var dashView = new AFMI_Gestion_projet.Views.DashboardView();
                var portView = new AFMI_Gestion_projet.Views.PortfolioView();
                var templView = new AFMI_Gestion_projet.Views.TemplateView();
                var mainWin = new AFMI_Gestion_projet.MainWindow();
                Assert.NotNull(dashView);
                Assert.NotNull(portView);
                Assert.NotNull(templView);
                Assert.NotNull(mainWin);
            }
            catch (Exception ex)
            {
                exception = ex;
            }
        });
        thread.SetApartmentState(ApartmentState.STA);
        thread.Start();
        thread.Join();

        if (exception != null)
        {
            throw exception;
        }
    }
}
