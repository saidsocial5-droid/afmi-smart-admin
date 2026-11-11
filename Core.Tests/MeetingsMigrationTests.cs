using AFMI_Gestion_projet.Models;
using Microsoft.EntityFrameworkCore;

namespace AFMI_Gestion_projet.Core.Tests;

public class MeetingsMigrationTests
{
    [Fact]
    public void Meeting_WithParticipantsResolutionsAndActions_IsStored_AndDocumentsKeepTheirData()
    {
        using var db = new TestDatabase();
        int docId;
        using (var ctx = db.Open())
        {
            var p = new Project { Name = "Projet", Code = "P1" };
            ctx.Projects.Add(p);
            ctx.SaveChanges();
            var folder = new DocumentFolder { Name = "Correspondances bailleur", ProjectId = p.Id, Year = 2026 };
            ctx.DocumentFolders.Add(folder);
            var doc = new ProjectDocument { ProjectId = p.Id, Title = "PV COPIL", Category = "PV", Folder = folder };
            ctx.Documents.Add(doc);
            ctx.Meetings.Add(new Meeting
            {
                Kind = "COPIL", Title = "Comité de pilotage n° 1", Date = new DateOnly(2026, 3, 12), ProjectId = p.Id,
                Participants = { new MeetingParticipant { Name = "A", Sex = "F" }, new MeetingParticipant { Name = "B", Sex = "M", Present = false } },
                Decisions = { new MeetingResolution { Number = 1, Text = "Valider le diagnostic." } },
                Actions = { new MeetingAction { Text = "Commander le matériel", DueDate = new DateOnly(2026, 4, 1) } },
            });
            ctx.SaveChanges();
            docId = doc.Id;
        }
        using (var ctx = db.Open())
        {
            var m = ctx.Meetings.Include(x => x.Participants).Include(x => x.Decisions).Include(x => x.Actions).Single();
            Assert.Equal((2, 1, 1), (m.Participants.Count, m.Decisions.Count, m.Actions.Count));
            Assert.Equal("À faire", m.Actions.Single().Status);
            Assert.Equal("Correspondances bailleur", ctx.Documents.Include(d => d.Folder).Single(d => d.Id == docId).Folder!.Name);
            ctx.Meetings.Remove(m);                          // suppression logique : décisions et actions conservées
            ctx.SaveChanges();
        }
        Assert.Equal(1L, (long)db.Scalar("SELECT COUNT(*) FROM MeetingActions")!);
        Assert.Equal(1L, (long)db.Scalar("SELECT IsDeleted FROM Meetings")!);
        Assert.ThrowsAny<Exception>(() => db.Execute("INSERT INTO Meetings (Kind, Title, Date, StartTime, Location, Organizer, Secretary, Agenda, Summary, " +
            "Status, CreatedBy, CreatedAtUtc, UpdatedAtUtc, IsDeleted) VALUES ('Inconnu', 't', '2026-01-01', '', '', '', '', '', '', 'Brouillon', '', '', '', 0)"));
    }
}
