using System.IO;
using System.Globalization;
using System.Text;
using AFMI_Gestion_projet.Finance;
using QuestPDF.Fluent;
using QuestPDF.Helpers;
using QuestPDF.Infrastructure;

namespace AFMI_Gestion_projet.Services
{
    /// <summary>État de rapprochement bancaire : PDF (impression, archivage) et CSV (tableur).</summary>
    public static class ReconciliationExportService
    {
        public static void ExportPdf(ReconciliationReport r, string path)
        {
            QuestPDF.Settings.License = LicenseType.Community;
            var st = r.Statement;
            var account = st.BankAccount!;
            Document.Create(doc => doc.Page(page =>
            {
                page.Size(PageSizes.A4);
                page.Margin(36);
                page.DefaultTextStyle(t => t.FontSize(9.5f));
                page.Header().Column(c =>
                {
                    c.Item().Text("État de rapprochement bancaire").FontSize(16).Bold();
                    c.Item().Text($"{account.Title} — {account.BankName} — RIB {Rib.Format(account.Rib)}");
                    c.Item().Text($"Relevé du {st.PeriodStart:dd/MM/yyyy} au {st.PeriodEnd:dd/MM/yyyy} — édité le {DateTime.Now:dd/MM/yyyy HH:mm}");
                });
                page.Content().PaddingVertical(10).Column(c =>
                {
                    c.Spacing(8);
                    c.Item().Table(t =>
                    {
                        t.ColumnsDefinition(cd => { cd.RelativeColumn(3); cd.RelativeColumn(1); });
                        void Row(string label, long amount, bool bold = false)
                        {
                            t.Cell().BorderBottom(0.5f).BorderColor(Colors.Grey.Lighten2).Padding(3).Text(label).Bold();
                            var cell = t.Cell().BorderBottom(0.5f).BorderColor(Colors.Grey.Lighten2).Padding(3).AlignRight().Text(Money.Format(amount, account.Currency));
                            if (bold) cell.Bold();
                        }
                        Row("Solde du relevé bancaire", r.BankClosingMinor);
                        Row("+ Opérations comptabilisées non encore passées en banque", r.UnmatchedOperations.Sum(o => o.SignedAmountMinor));
                        Row("− Mouvements bancaires non comptabilisés", r.UnmatchedLines.Sum(l => l.SignedAmountMinor));
                        Row("= Solde bancaire rectifié", r.AdjustedBankMinor, true);
                        Row("Solde comptable à la même date", r.BookBalanceMinor, true);
                        Row("Écart inexpliqué", r.UnexplainedDifferenceMinor, true);
                    });
                    Section(c, "Opérations comptabilisées non passées en banque",
                        r.UnmatchedOperations.Select(o => (o.OperationDate.ToString("dd/MM/yyyy"), o.Label, o.SignedAmountMinor)), account.Currency);
                    Section(c, "Mouvements bancaires non comptabilisés",
                        r.UnmatchedLines.Select(l => (l.OperationDate.ToString("dd/MM/yyyy"), l.Label, l.SignedAmountMinor)), account.Currency);
                });
                page.Footer().AlignCenter().Text(x => { x.Span("Page "); x.CurrentPageNumber(); x.Span(" / "); x.TotalPages(); });
            })).GeneratePdf(path);
        }

        private static void Section(ColumnDescriptor c, string title, IEnumerable<(string Date, string Label, long Signed)> rows, string currency)
        {
            var list = rows.ToList();
            c.Item().PaddingTop(6).Text($"{title} ({list.Count})").FontSize(11).Bold();
            if (list.Count == 0) { c.Item().Text("Aucun.").Italic(); return; }
            c.Item().Table(t =>
            {
                t.ColumnsDefinition(cd => { cd.ConstantColumn(70); cd.RelativeColumn(); cd.ConstantColumn(100); });
                t.Header(h =>
                {
                    h.Cell().Background(Colors.Grey.Lighten3).Padding(3).Text("Date").Bold();
                    h.Cell().Background(Colors.Grey.Lighten3).Padding(3).Text("Libellé").Bold();
                    h.Cell().Background(Colors.Grey.Lighten3).Padding(3).AlignRight().Text("Montant").Bold();
                });
                foreach (var (date, label, signed) in list)
                {
                    t.Cell().Padding(3).Text(date);
                    t.Cell().Padding(3).Text(label);
                    t.Cell().Padding(3).AlignRight().Text(Money.Format(signed, currency));
                }
            });
        }

        public static void ExportCsv(ReconciliationReport r, string path)
        {
            var fr = CultureInfo.GetCultureInfo("fr-FR");
            string Amount(long minor) => Money.FromMinor(minor).ToString("0.00", fr);
            static string Esc(string s) => "\"" + s.Replace("\"", "\"\"") + "\"";
            var sb = new StringBuilder();
            sb.AppendLine("Rubrique;Date;Libellé;Montant");
            sb.AppendLine($"Solde du relevé;{r.Statement.PeriodEnd:dd/MM/yyyy};;{Amount(r.BankClosingMinor)}");
            foreach (var o in r.UnmatchedOperations) sb.AppendLine($"Opération non passée en banque;{o.OperationDate:dd/MM/yyyy};{Esc(o.Label)};{Amount(o.SignedAmountMinor)}");
            foreach (var l in r.UnmatchedLines) sb.AppendLine($"Mouvement bancaire non comptabilisé;{l.OperationDate:dd/MM/yyyy};{Esc(l.Label)};{Amount(l.SignedAmountMinor)}");
            sb.AppendLine($"Solde bancaire rectifié;;;{Amount(r.AdjustedBankMinor)}");
            sb.AppendLine($"Solde comptable;;;{Amount(r.BookBalanceMinor)}");
            sb.AppendLine($"Écart inexpliqué;;;{Amount(r.UnexplainedDifferenceMinor)}");
            File.WriteAllText(path, sb.ToString(), new UTF8Encoding(true)); // BOM : Excel lit les accents
        }
    }
}
