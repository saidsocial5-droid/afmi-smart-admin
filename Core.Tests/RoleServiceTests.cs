using AFMI_Gestion_projet.Services;

namespace AFMI_Gestion_projet.Core.Tests;

public class RoleServiceTests : IDisposable
{
    private readonly TestDatabase _db = new();
    public void Dispose() => _db.Dispose();

    [Fact]
    public void NoUsers_MeansAllRights()
    {
        using var ctx = _db.Open();
        Assert.Null(RoleService.CurrentRole(ctx, "quiconque"));
        Assert.True(RoleService.CanEditFinance(null));
    }

    [Fact]
    public void Roles_FollowTheSettingsList_LikeThePythonBackend()
    {
        using (var ctx = _db.Open())
        {
            new SettingsService(ctx).Set(RoleService.UsersKey, new object[]
            {
                new { login = "admin.afmi", role = "Administrateur", active = true },
                new { login = "Compta", role = "Comptable", active = true },
                new { login = "projet", role = "Chargé de projet", active = true },
                new { login = "ancien", role = "Comptable", active = false },
            });
        }
        using var db = _db.Open();
        Assert.Equal("Comptable", RoleService.CurrentRole(db, "compta"));          // insensible à la casse
        Assert.True(RoleService.CanEditFinance(RoleService.CurrentRole(db, "compta")));
        Assert.False(RoleService.CanEditFinance(RoleService.CurrentRole(db, "projet")));
        Assert.True(RoleService.CanEditProjects(RoleService.CurrentRole(db, "projet")));
        Assert.Equal("Lecteur", RoleService.CurrentRole(db, "ancien"));             // inactif
        Assert.Equal("Lecteur", RoleService.CurrentRole(db, "inconnu"));
        Assert.False(RoleService.CanEditProjects("Lecteur"));
    }

    [Fact]
    public void SaveChanges_EnforcesTheRole_ForEveryScreen()
    {
        string role = "Chargé de projet";
        using (var ctx = _db.Open())
        {
            ctx.WritePermission = area => RoleService.CanWrite(role, area);
            ctx.Projects.Add(new Models.Project { Name = "Projet", Code = "P1" });
            ctx.SaveChanges();                                                          // projets : permis
            ctx.BankAccounts.Add(new Models.Finance.BankAccount { Title = "Compte", BankName = "B", Currency = "MAD" });
            Assert.Throws<UnauthorizedAccessException>(() => ctx.SaveChanges());        // trésorerie : refusée
        }
        role = "Lecteur";
        using (var ctx = _db.Open())
        {
            ctx.WritePermission = area => RoleService.CanWrite(role, area);
            ctx.Projects.Add(new Models.Project { Name = "Autre", Code = "P2" });
            Assert.Throws<UnauthorizedAccessException>(() => ctx.SaveChanges());
        }
        using (var ctx = _db.Open())
        {
            ctx.WritePermission = area => RoleService.CanWrite("Lecteur", area);
            new SettingsService(ctx).Set(SettingKeys.BackupLastError, "erreur");       // écriture système : permise
            Assert.Throws<UnauthorizedAccessException>(() => new SettingsService(ctx).Set(SettingKeys.AssociationName, "X"));
        }
        using var check = _db.Open();
        Assert.Equal(1, check.Projects.Count());
        Assert.Empty(check.BankAccounts);
    }
}
