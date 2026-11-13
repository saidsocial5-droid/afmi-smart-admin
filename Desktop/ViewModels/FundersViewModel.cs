using System;
using System.Collections.ObjectModel;
using System.Linq;
using System.Windows;
using System.Windows.Input;
using AFMI_Gestion_projet.Data;
using AFMI_Gestion_projet.Models;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Microsoft.Win32;

namespace AFMI_Gestion_projet.ViewModels
{
    public partial class FundersViewModel : ObservableObject
    {
        private readonly MainViewModel _mainViewModel;

        [ObservableProperty]
        private ObservableCollection<Funder> _funders = new();

        [ObservableProperty]
        private Funder? _selectedFunder;

        [ObservableProperty]
        private bool _isEditing;

        public ICommand AddFunderCommand { get; }
        public ICommand SaveFunderCommand { get; }
        public ICommand DeleteFunderCommand { get; }
        public ICommand CancelEditCommand { get; }
        public ICommand BrowseLogoCommand { get; }

        public FundersViewModel(MainViewModel mainViewModel)
        {
            _mainViewModel = mainViewModel;

            AddFunderCommand = new RelayCommand(AddFunder);
            SaveFunderCommand = new RelayCommand(SaveFunder, CanSaveFunder);
            DeleteFunderCommand = new RelayCommand<Funder>(DeleteFunder);
            CancelEditCommand = new RelayCommand(CancelEdit);
            BrowseLogoCommand = new RelayCommand(BrowseLogo);

            LoadFunders();
        }

        public void LoadFunders()
        {
            using var db = new AppDbContext();
            var list = db.Funders.ToList();
            Funders = new ObservableCollection<Funder>(list);
        }

        private void AddFunder()
        {
            SelectedFunder = new Funder { PrimaryColor = "#000000" };
            IsEditing = true;
        }

        private bool CanSaveFunder()
        {
            return SelectedFunder != null && !string.IsNullOrWhiteSpace(SelectedFunder.Name);
        }

        private void SaveFunder()
        {
            if (SelectedFunder == null) return;

            try
            {
                using var db = new AppDbContext();
                if (SelectedFunder.Id == 0)
                {
                    db.Funders.Add(SelectedFunder);
                }
                else
                {
                    db.Funders.Update(SelectedFunder);
                }
                db.SaveChanges();
                
                IsEditing = false;
                LoadFunders();
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Erreur lors de la sauvegarde: {ex.Message}", "Erreur", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void DeleteFunder(Funder? funder)
        {
            if (funder == null) return;

            var result = MessageBox.Show($"Voulez-vous vraiment supprimer le bailleur {funder.Name} ?", "Confirmation", MessageBoxButton.YesNo, MessageBoxImage.Warning);
            if (result == MessageBoxResult.Yes)
            {
                try
                {
                    using var db = new AppDbContext();
                    db.Funders.Remove(funder);
                    db.SaveChanges();
                    
                    if (SelectedFunder?.Id == funder.Id)
                    {
                        SelectedFunder = null;
                        IsEditing = false;
                    }
                    LoadFunders();
                }
                catch (Exception ex)
                {
                    MessageBox.Show($"Erreur lors de la suppression: {ex.Message}", "Erreur", MessageBoxButton.OK, MessageBoxImage.Error);
                }
            }
        }

        private void CancelEdit()
        {
            SelectedFunder = null;
            IsEditing = false;
        }

        private void BrowseLogo()
        {
            if (SelectedFunder == null) return;

            var ofd = new OpenFileDialog
            {
                Filter = "Images (*.png;*.jpg;*.jpeg)|*.png;*.jpg;*.jpeg",
                Title = "Sélectionner un logo"
            };

            if (ofd.ShowDialog() == true) SetLogo(ofd.FileName);
        }

        public ICommand DropLogoCommand => _dropLogoCommand ??= new RelayCommand<string[]>(f =>
        {
            var img = f?.FirstOrDefault(x => new[] { ".png", ".jpg", ".jpeg" }.Contains(System.IO.Path.GetExtension(x).ToLowerInvariant()));
            if (img != null && SelectedFunder != null) SetLogo(img);
        });
        private ICommand? _dropLogoCommand;

        private void SetLogo(string path)
        {
            if (SelectedFunder == null) return;
            SelectedFunder.LogoPath = path;
            OnPropertyChanged(nameof(SelectedFunder));
            ((RelayCommand)SaveFunderCommand).NotifyCanExecuteChanged();
        }

        partial void OnSelectedFunderChanged(Funder? value)
        {
            if (value != null && !IsEditing)
            {
                IsEditing = true;
            }
            ((RelayCommand)SaveFunderCommand).NotifyCanExecuteChanged();
        }
    }
}
