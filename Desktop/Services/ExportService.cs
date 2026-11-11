using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using AFMI_Gestion_projet.Models;

namespace AFMI_Gestion_projet.Services
{
    public class ExportService
    {
        /// <summary>
        /// Exports a list of projects to a CSV file (Excel-compatible with UTF-8 BOM)
        /// </summary>
        public void ExportProjectsToCsv(IEnumerable<Project> projects, string filePath)
        {
            var sb = new StringBuilder();
            
            // CSV Header
            sb.AppendLine("ID;Code;Nom;Directeur;Propriétaire;Client;Département;Statut;Priorité;Budget Global (MAD);Date Début Prévue;Date Fin Prévue;Date Début Réelle;Date Fin Réelle");

            foreach (var p in projects)
            {
                sb.AppendLine($"{p.Id};" +
                              $"\"{EscapeCsv(p.Code)}\";" +
                              $"\"{EscapeCsv(p.Name)}\";" +
                              $"\"{EscapeCsv(p.Manager)}\";" +
                              $"\"{EscapeCsv(p.Owner)}\";" +
                              $"\"{EscapeCsv(p.Client)}\";" +
                              $"\"{EscapeCsv(p.Department)}\";" +
                              $"\"{EscapeCsv(p.Status)}\";" +
                              $"\"{EscapeCsv(p.Priority)}\";" +
                              $"{p.BudgetGlobal:F2};" +
                              $"\"{p.TargetStartDate?.ToString("dd/MM/yyyy")}\";" +
                              $"\"{p.TargetEndDate?.ToString("dd/MM/yyyy")}\";" +
                              $"\"{p.ActualStartDate?.ToString("dd/MM/yyyy")}\";" +
                              $"\"{p.ActualEndDate?.ToString("dd/MM/yyyy")}\"");
            }

            // Write with UTF-8 BOM for Excel compatibility
            File.WriteAllText(filePath, sb.ToString(), Encoding.UTF8);
        }

        /// <summary>
        /// Exports detailed project financial budget and transactions to CSV
        /// </summary>
        public void ExportProjectBudgetToCsv(Project project, IEnumerable<CostEntry> costEntries, string filePath)
        {
            var sb = new StringBuilder();
            
            sb.AppendLine($"Export du Budget - Projet : {project.Name} ({project.Code})");
            sb.AppendLine($"Généré le : {DateTime.Now:dd/MM/yyyy HH:mm}");
            sb.AppendLine($"Budget Global Initial : {project.BudgetGlobal:F2} MAD");
            sb.AppendLine();
            
            // Section 1: Detailed Cost Ledger
            sb.AppendLine("REGISTRE DES DEPENSES");
            sb.AppendLine("Date;Catégorie;Description;Ressource/Fournisseur;Coût Estimé (MAD);Coût Réel (MAD);Écart (MAD)");
            
            double totalEst = 0;
            double totalAct = 0;

            foreach (var cost in costEntries)
            {
                double variance = cost.EstimatedCost - cost.ActualCost;
                totalEst += cost.EstimatedCost;
                totalAct += cost.ActualCost;

                var supplierText = string.IsNullOrEmpty(cost.Supplier) ? cost.ResourceName : $"{cost.ResourceName} ({cost.Supplier})";
                sb.AppendLine($"{cost.Date:dd/MM/yyyy};" +
                              $"\"{EscapeCsv(cost.Category)}\";" +
                              $"\"{EscapeCsv(cost.Description)}\";" +
                              $"\"{EscapeCsv(supplierText)}\";" +
                              $"{cost.EstimatedCost:F2};" +
                              $"{cost.ActualCost:F2};" +
                              $"{variance:F2}");
            }
            
            sb.AppendLine($";;;Total;{totalEst:F2};{totalAct:F2};{(totalEst - totalAct):F2}");
            sb.AppendLine();

            // Section 2: Task-level Budgets
            sb.AppendLine("BUDGET DES TACHES");
            sb.AppendLine("ID Tâche;Nom de la Tâche;Responsable;Statut;Avancement;Budget Alloué (MAD);Coût Engagé (MAD);Écart (MAD)");

            foreach (var task in project.Tasks)
            {
                double taskVar = task.Budget - task.Cost;
                sb.AppendLine($"{task.Id};" +
                              $"\"{EscapeCsv(task.Name)}\";" +
                              $"\"{EscapeCsv(task.Assignee)}\";" +
                              $"\"{EscapeCsv(task.Status)}\";" +
                              $"{task.ProgressPercentage}%;" +
                              $"{task.Budget:F2};" +
                              $"{task.Cost:F2};" +
                              $"{taskVar:F2}");
            }

            File.WriteAllText(filePath, sb.ToString(), Encoding.UTF8);
        }

        private string EscapeCsv(string text)
        {
            if (string.IsNullOrEmpty(text)) return string.Empty;
            return text.Replace("\"", "\"\"");
        }

        /// <summary>
        /// Exports the synthesized Work Program & Proposal to a fully formatted Microsoft Word (.docx / .doc) document
        /// </summary>
        public void ExportWorkProgramToWord(GeneratedWorkProgram program, string filePath)
        {
            var sb = new StringBuilder();

            sb.AppendLine("<!DOCTYPE html>");
            sb.AppendLine("<html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>");
            sb.AppendLine("<head>");
            sb.AppendLine("<meta charset='utf-8'/>");
            sb.AppendLine("<title>Programme de Travail</title>");
            sb.AppendLine("<style>");
            sb.AppendLine("  body { font-family: 'Segoe UI', Calibri, Arial, sans-serif; font-size: 11pt; color: #1E293B; line-height: 1.5; margin: 30px; }");
            sb.AppendLine("  .cover-box { background: #1E3A8A; color: white; padding: 25px; border-radius: 8px; margin-bottom: 25px; }");
            sb.AppendLine("  .cover-title { font-size: 22pt; font-weight: bold; margin: 0 0 10px 0; color: #FFFFFF; }");
            sb.AppendLine("  .cover-subtitle { font-size: 13pt; color: #93C5FD; margin: 0; }");
            sb.AppendLine("  .meta-table { width: 100%; border-collapse: collapse; margin-bottom: 25px; }");
            sb.AppendLine("  .meta-table td { padding: 8px 12px; border: 1px solid #CBD5E1; background: #F8FAFC; font-size: 10.5pt; }");
            sb.AppendLine("  .meta-table td.label { font-weight: bold; background: #E2E8F0; color: #1E293B; width: 25%; }");
            sb.AppendLine("  h2 { font-size: 15pt; color: #1E3A8A; border-bottom: 2px solid #2563EB; padding-bottom: 5px; margin-top: 25px; }");
            sb.AppendLine("  h3 { font-size: 12pt; color: #1D4ED8; margin-top: 15px; }");
            sb.AppendLine("  ul { margin-top: 5px; margin-bottom: 15px; }");
            sb.AppendLine("  li { margin-bottom: 4px; }");
            sb.AppendLine("  table.data-table { width: 100%; border-collapse: collapse; margin-top: 10px; margin-bottom: 20px; }");
            sb.AppendLine("  table.data-table th { background: #1E3A8A; color: white; padding: 9px; text-align: left; font-size: 10pt; font-weight: bold; }");
            sb.AppendLine("  table.data-table td { padding: 8px; border: 1px solid #CBD5E1; font-size: 9.5pt; }");
            sb.AppendLine("  table.data-table tr:nth-child(even) { background: #F8FAFC; }");
            sb.AppendLine("  .badge { display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 9pt; font-weight: bold; background: #DBEAFE; color: #1E40AF; }");
            sb.AppendLine("  .risk-box { background: #FEF2F2; border-left: 4px solid #EF4444; padding: 10px 15px; margin-bottom: 10px; }");
            sb.AppendLine("</style>");
            sb.AppendLine("</head>");
            sb.AppendLine("body>");

            // Cover Banner
            sb.AppendLine("<div class='cover-box'>");
            sb.AppendLine($"  <div class='cover-title'>PROGRAMME DE TRAVAIL & PROPOSITION D'EXÉCUTION</div>");
            sb.AppendLine($"  <div class='cover-subtitle'>Projet : {System.Net.WebUtility.HtmlEncode(program.ProjectName)} ({program.ProjectCode})</div>");
            sb.AppendLine("</div>");

            // Meta Info Table
            sb.AppendLine("<table class='meta-table'>");
            sb.AppendLine($"  <tr><td class='label'>Partenaire / Bailleur</td><td>{System.Net.WebUtility.HtmlEncode(program.DonorName)}</td><td class='label'>Enveloppe Budgétaire</td><td><b>{program.TotalBudget:N0} MAD</b></td></tr>");
            sb.AppendLine($"  <tr><td class='label'>Date de Début</td><td>{program.TargetStartDate:dd/MM/yyyy}</td><td class='label'>Date d'Échéance</td><td>{program.TargetEndDate:dd/MM/yyyy}</td></tr>");
            sb.AppendLine($"  <tr><td class='label'>Généré le</td><td colspan='3'>{DateTime.Now:dd/MM/yyyy HH:mm} par AFMI Gestion Projet</td></tr>");
            sb.AppendLine("</table>");

            // 1. Objectives
            sb.AppendLine("<h2>1. OBJECTIFS DU PROGRAMME</h2>");
            sb.AppendLine("<h3>1.1 Objectifs Généraux</h3><ul>");
            foreach (var og in program.GeneralObjectives)
                sb.AppendLine($"  <li>{System.Net.WebUtility.HtmlEncode(og)}</li>");
            sb.AppendLine("</ul>");

            sb.AppendLine("<h3>1.2 Objectifs Spécifiques</h3><ul>");
            foreach (var os in program.SpecificObjectives)
                sb.AppendLine($"  <li>{System.Net.WebUtility.HtmlEncode(os)}</li>");
            sb.AppendLine("</ul>");

            // 2. Expected Results & KPIs
            sb.AppendLine("<h2>2. RÉSULTATS ATTENDUS & INDICATEURS (KPI)</h2>");
            sb.AppendLine("<ul>");
            foreach (var res in program.ExpectedResults)
                sb.AppendLine($"  <li><b>Résultat attendu :</b> {System.Net.WebUtility.HtmlEncode(res)}</li>");
            sb.AppendLine("</ul>");

            sb.AppendLine("<h3>Indicateurs Clés de Performance :</h3><ul>");
            foreach (var ind in program.KeyIndicators)
                sb.AppendLine($"  <li>{System.Net.WebUtility.HtmlEncode(ind)}</li>");
            sb.AppendLine("</ul>");

            // 3. Activities Breakdown Table
            sb.AppendLine("<h2>3. PROGRAMME DES ACTIVITÉS & PLAN D'ACTION DETAILÉ</h2>");
            sb.AppendLine("<table class='data-table'>");
            sb.AppendLine("  <tr><th>N°</th><th>Activité & Intitulé</th><th>Phase</th><th>Responsable</th><th>Durée</th><th>Budget Est. (MAD)</th><th>Livrables Attendus</th></tr>");

            foreach (var act in program.Activities)
            {
                sb.AppendLine("  <tr>");
                sb.AppendLine($"    <td>A{act.Index}</td>");
                sb.AppendLine($"    <td><b>{System.Net.WebUtility.HtmlEncode(act.Name)}</b><br/><small>{System.Net.WebUtility.HtmlEncode(act.Description)}</small></td>");
                sb.AppendLine($"    <td><span class='badge'>{System.Net.WebUtility.HtmlEncode(act.Phase)}</span></td>");
                sb.AppendLine($"    <td>{System.Net.WebUtility.HtmlEncode(act.ResponsibleRole)}</td>");
                sb.AppendLine($"    <td>{act.DurationWeeks} sem.</td>");
                sb.AppendLine($"    <td><b>{act.EstimatedBudget:N0} MAD</b></td>");
                sb.AppendLine($"    <td>{System.Net.WebUtility.HtmlEncode(act.ExpectedDeliverable)}</td>");
                sb.AppendLine("  </tr>");
            }
            sb.AppendLine("</table>");

            // 4. Expected Budget Ledger Table
            sb.AppendLine("<h2>4. ESTIMATION DES DÉPENSES ET BUDGET PRÉVISIONNEL</h2>");
            sb.AppendLine("<table class='data-table'>");
            sb.AppendLine("  <tr><th>Poste Budgétaire</th><th>Description & Intitulé</th><th>Montant Estimé (MAD)</th><th>Source de Financement</th></tr>");

            foreach (var b in program.BudgetLedger)
            {
                sb.AppendLine("  <tr>");
                sb.AppendLine($"    <td><b>{System.Net.WebUtility.HtmlEncode(b.Category)}</b></td>");
                sb.AppendLine($"    <td>{System.Net.WebUtility.HtmlEncode(b.Description)}</td>");
                sb.AppendLine($"    <td><b>{b.EstimatedCost:N0} MAD</b></td>");
                sb.AppendLine($"    <td>{System.Net.WebUtility.HtmlEncode(b.FundingSource)}</td>");
                sb.AppendLine("  </tr>");
            }
            sb.AppendLine($"  <tr style='background:#E2E8F0;'>");
            sb.AppendLine($"    <td colspan='2'><b>TOTAL BUDGET ENVISAGÉ</b></td>");
            sb.AppendLine($"    <td><b>{program.TotalBudget:N0} MAD</b></td>");
            sb.AppendLine($"    <td>-</td>");
            sb.AppendLine("  </tr>");
            sb.AppendLine("</table>");

            // 5. Risks & Mitigation
            sb.AppendLine("<h2>5. GESTION DES RISQUES & DISPOSITIF DE SUIVI</h2>");
            for (int i = 0; i < program.ImplementationRisks.Count; i++)
            {
                sb.AppendLine("<div class='risk-box'>");
                sb.AppendLine($"  <b>Risque {i + 1} :</b> {System.Net.WebUtility.HtmlEncode(program.ImplementationRisks[i])}<br/>");
                if (i < program.MitigationMeasures.Count)
                    sb.AppendLine($"  <span style='color:#059669;'>→ <b>Mesure d'atténuation :</b> {System.Net.WebUtility.HtmlEncode(program.MitigationMeasures[i])}</span>");
                sb.AppendLine("</div>");
            }

            sb.AppendLine("</body>");
            sb.AppendLine("</html>");

            File.WriteAllText(filePath, sb.ToString(), Encoding.UTF8);
        }

        /// <summary>
        /// Exporte un compte rendu de réunion au format Word (.docx) avec en-tête officiel et tableau d'actions
        /// </summary>
        public void ExportMeetingMinutesToWord(MeetingMinutesModel minutes, string filePath)
        {
            var sb = new StringBuilder();

            sb.AppendLine("<!DOCTYPE html>");
            sb.AppendLine("<html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>");
            sb.AppendLine("<head>");
            sb.AppendLine("<meta charset='utf-8'/>");
            sb.AppendLine($"<title>{System.Net.WebUtility.HtmlEncode(minutes.Title)}</title>");
            sb.AppendLine("<style>");
            sb.AppendLine("  body { font-family: 'Segoe UI', Calibri, Arial, sans-serif; font-size: 11pt; color: #1E293B; line-height: 1.5; margin: 35px; }");
            sb.AppendLine($"  .cover-box {{ background: {minutes.FunderPrimaryColor}; color: white; padding: 25px; border-radius: 6px; margin-bottom: 25px; border-left: 8px solid #2563EB; }}");
            sb.AppendLine("  .cover-title { font-size: 20pt; font-weight: bold; margin: 0 0 8px 0; color: #FFFFFF; }");
            sb.AppendLine("  .cover-subtitle { font-size: 12pt; color: #E2E8F0; margin: 0; }");
            sb.AppendLine("  .meta-table { width: 100%; border-collapse: collapse; margin-bottom: 25px; }");
            sb.AppendLine("  .meta-table td { padding: 8px 12px; border: 1px solid #CBD5E1; background: #F8FAFC; font-size: 10.5pt; }");
            sb.AppendLine("  .meta-table td.label { font-weight: bold; background: #E2E8F0; color: #1E293B; width: 22%; }");
            sb.AppendLine($"  h2 {{ font-size: 14pt; color: {minutes.FunderPrimaryColor}; border-bottom: 2px solid {minutes.FunderPrimaryColor}; padding-bottom: 5px; margin-top: 25px; }}");
            sb.AppendLine("  .content-box { background: #F8FAFC; border: 1px solid #E2E8F0; padding: 15px; border-radius: 6px; white-space: pre-wrap; font-size: 10.5pt; margin-bottom: 20px; }");
            sb.AppendLine("  table.data-table { width: 100%; border-collapse: collapse; margin-top: 10px; margin-bottom: 20px; }");
            sb.AppendLine($"  table.data-table th {{ background: {minutes.FunderPrimaryColor}; color: white; padding: 8px 10px; text-align: left; font-size: 10pt; font-weight: bold; }}");
            sb.AppendLine("  table.data-table td { padding: 8px 10px; border: 1px solid #CBD5E1; font-size: 9.5pt; }");
            sb.AppendLine("  table.data-table tr:nth-child(even) { background: #F8FAFC; }");
            sb.AppendLine("  .badge { display: inline-block; padding: 2px 7px; border-radius: 4px; font-size: 8.5pt; font-weight: bold; }");
            sb.AppendLine("  .badge-danger { background: #FEE2E2; color: #991B1B; }");
            sb.AppendLine("  .badge-warning { background: #FEF3C7; color: #92400E; }");
            sb.AppendLine("  .badge-info { background: #DBEAFE; color: #1E40AF; }");
            sb.AppendLine("</style>");
            sb.AppendLine("</head>");
            sb.AppendLine("<body>");

            // En-tête officiel
            if (!string.IsNullOrWhiteSpace(minutes.FunderHeaderText))
            {
                sb.AppendLine($"<div style='text-align:center; font-size:9.5pt; font-style:italic; color:{minutes.FunderPrimaryColor}; margin-bottom: 10px;'>{System.Net.WebUtility.HtmlEncode(minutes.FunderHeaderText)}</div>");
            }
            sb.AppendLine("<div class='cover-box'>");
            sb.AppendLine($"  <div class='cover-title'>{System.Net.WebUtility.HtmlEncode(minutes.Title.ToUpperInvariant())}</div>");
            sb.AppendLine($"  <div class='cover-subtitle'>Séance : {System.Net.WebUtility.HtmlEncode(minutes.MeetingType)} | Date : {minutes.MeetingDate:dd/MM/yyyy}</div>");
            sb.AppendLine("</div>");

            // Métadonnées
            sb.AppendLine("<table class='meta-table'>");
            sb.AppendLine($"  <tr><td class='label'>Projet associé</td><td><b>{System.Net.WebUtility.HtmlEncode(minutes.ProjectName)}</b> ({System.Net.WebUtility.HtmlEncode(minutes.ProjectCode)})</td><td class='label'>Lieu / Format</td><td>{System.Net.WebUtility.HtmlEncode(minutes.Location)}</td></tr>");
            sb.AppendLine($"  <tr><td class='label'>Animateur</td><td>{System.Net.WebUtility.HtmlEncode(minutes.Organizer)}</td><td class='label'>Rédacteur</td><td>{System.Net.WebUtility.HtmlEncode(minutes.Secretary)}</td></tr>");
            sb.AppendLine($"  <tr><td class='label'>Participants</td><td colspan='3'>{System.Net.WebUtility.HtmlEncode(minutes.Attendees)}</td></tr>");
            if (!string.IsNullOrWhiteSpace(minutes.Excused))
            {
                sb.AppendLine($"  <tr><td class='label'>Excusés</td><td colspan='3'>{System.Net.WebUtility.HtmlEncode(minutes.Excused)}</td></tr>");
            }
            sb.AppendLine("</table>");

            // Ordre du jour
            if (!string.IsNullOrWhiteSpace(minutes.Agenda))
            {
                sb.AppendLine("<h2>1. ORDRE DU JOUR</h2>");
                sb.AppendLine("<div class='content-box'>");
                sb.AppendLine(System.Net.WebUtility.HtmlEncode(minutes.Agenda));
                sb.AppendLine("</div>");
            }

            // Synthèse rédigée par l'Agent IA
            sb.AppendLine("<h2>2. SYNTHÈSE DÉTAILLÉE DES ÉCHANGES</h2>");
            sb.AppendLine("<div class='content-box'>");
            sb.AppendLine(System.Net.WebUtility.HtmlEncode(minutes.GeneratedSummary));
            sb.AppendLine("</div>");

            // Décisions actées
            if (minutes.Decisions != null && minutes.Decisions.Any())
            {
                sb.AppendLine("<h2>3. RELEVÉ DES DÉCISIONS ACTÉES</h2>");
                sb.AppendLine("<table class='data-table'>");
                sb.AppendLine("  <tr><th style='width:12%;'>Réf</th><th>Décision Validée</th><th style='width:25%;'>Impact Opérationnel</th><th style='width:20%;'>Responsable</th></tr>");
                foreach (var d in minutes.Decisions)
                {
                    sb.AppendLine("  <tr>");
                    sb.AppendLine($"    <td><b>{System.Net.WebUtility.HtmlEncode(d.Reference)}</b></td>");
                    sb.AppendLine($"    <td>{System.Net.WebUtility.HtmlEncode(d.Decision)}</td>");
                    sb.AppendLine($"    <td>{System.Net.WebUtility.HtmlEncode(d.Impact)}</td>");
                    sb.AppendLine($"    <td>{System.Net.WebUtility.HtmlEncode(d.Responsible)}</td>");
                    sb.AppendLine("  </tr>");
                }
                sb.AppendLine("</table>");
            }

            // Plan d'actions
            if (minutes.ActionItems != null && minutes.ActionItems.Any())
            {
                sb.AppendLine("<h2>4. PLAN D'ACTIONS & ENGAGEMENTS</h2>");
                sb.AppendLine("<table class='data-table'>");
                sb.AppendLine("  <tr><th>Action Prioritaire</th><th style='width:20%;'>Responsable</th><th style='width:15%;'>Échéance</th><th style='width:12%;'>Priorité</th><th style='width:12%;'>Statut</th></tr>");
                foreach (var a in minutes.ActionItems)
                {
                    string badgeClass = a.Priority == "Haute" ? "badge-danger" : (a.Priority == "Moyenne" ? "badge-warning" : "badge-info");
                    sb.AppendLine("  <tr>");
                    sb.AppendLine($"    <td>{System.Net.WebUtility.HtmlEncode(a.Action)}</td>");
                    sb.AppendLine($"    <td>{System.Net.WebUtility.HtmlEncode(a.Responsible)}</td>");
                    sb.AppendLine($"    <td>{a.DueDate:dd/MM/yyyy}</td>");
                    sb.AppendLine($"    <td><span class='badge {badgeClass}'>{System.Net.WebUtility.HtmlEncode(a.Priority)}</span></td>");
                    sb.AppendLine($"    <td>{System.Net.WebUtility.HtmlEncode(a.Status)}</td>");
                    sb.AppendLine("  </tr>");
                }
                sb.AppendLine("</table>");
            }

            // Prochaine réunion
            if (!string.IsNullOrWhiteSpace(minutes.NextMeetingDate))
            {
                sb.AppendLine("<h2>5. PROCHAINE RÉUNION</h2>");
                sb.AppendLine($"<p><b>Date prévisionnelle :</b> {System.Net.WebUtility.HtmlEncode(minutes.NextMeetingDate)}<br/>");
                if (!string.IsNullOrWhiteSpace(minutes.NextMeetingAgenda))
                {
                    sb.AppendLine($"<b>Ordre du jour prévu :</b> {System.Net.WebUtility.HtmlEncode(minutes.NextMeetingAgenda)}</p>");
                }
            }

            // Annexes: Photos
            if (minutes.Photos != null && minutes.Photos.Count > 0)
            {
                sb.AppendLine("<h2>6. ANNEXES (PHOTOS & MÉDIAS)</h2>");
                sb.AppendLine("<div style='margin-top: 15px;'>");
                foreach (var photo in minutes.Photos)
                {
                    if (File.Exists(photo))
                    {
                        // En HTML local Word, l'URL de l'image locale peut être injectée
                        sb.AppendLine($"<div style='margin-bottom: 20px; text-align: center;'>");
                        sb.AppendLine($"  <img src='{photo.Replace("\\", "/")}' style='max-width: 600px; max-height: 400px; border: 1px solid #CBD5E1; padding: 5px; border-radius: 4px;' />");
                        sb.AppendLine($"  <p style='font-size: 9pt; color: #64748B; margin-top: 5px;'><i>{System.IO.Path.GetFileName(photo)}</i></p>");
                        sb.AppendLine($"</div>");
                    }
                }
                sb.AppendLine("</div>");
            }

            // Pied de page du bailleur
            if (!string.IsNullOrWhiteSpace(minutes.FunderFooterText))
            {
                sb.AppendLine($"<div style='margin-top: 30px; border-top: 1px solid #CBD5E1; padding-top: 10px; text-align: center; font-size: 8.5pt; color: #64748B;'>");
                sb.AppendLine(System.Net.WebUtility.HtmlEncode(minutes.FunderFooterText).Replace("\n", "<br/>"));
                sb.AppendLine("</div>");
            }

            sb.AppendLine("</body>");
            sb.AppendLine("</html>");

            File.WriteAllText(filePath, sb.ToString(), Encoding.UTF8);
        }

        /// <summary>
        /// Exporte un rapport généré par l'Agent IA au format Word (.docx)
        /// </summary>
        public void ExportAiReportToWord(string title, string content, Project? project, string filePath)
        {
            var sb = new StringBuilder();

            sb.AppendLine("<!DOCTYPE html>");
            sb.AppendLine("<html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>");
            sb.AppendLine("<head>");
            sb.AppendLine("<meta charset='utf-8'/>");
            sb.AppendLine($"<title>{System.Net.WebUtility.HtmlEncode(title)}</title>");
            sb.AppendLine("<style>");
            sb.AppendLine("  body { font-family: 'Segoe UI', Calibri, Arial, sans-serif; font-size: 11pt; color: #1E293B; line-height: 1.6; margin: 35px; }");
            sb.AppendLine("  .cover-box { background: #1E3A8A; color: white; padding: 25px; border-radius: 6px; margin-bottom: 25px; }");
            sb.AppendLine("  .cover-title { font-size: 20pt; font-weight: bold; margin: 0 0 8px 0; color: #FFFFFF; }");
            sb.AppendLine("  .cover-subtitle { font-size: 12pt; color: #93C5FD; margin: 0; }");
            sb.AppendLine("  .meta-table { width: 100%; border-collapse: collapse; margin-bottom: 25px; }");
            sb.AppendLine("  .meta-table td { padding: 8px 12px; border: 1px solid #CBD5E1; background: #F8FAFC; font-size: 10.5pt; }");
            sb.AppendLine("  .meta-table td.label { font-weight: bold; background: #E2E8F0; color: #1E293B; width: 25%; }");
            sb.AppendLine("  .report-body { background: #FFFFFF; line-height: 1.6; white-space: pre-wrap; font-size: 11pt; }");
            sb.AppendLine("</style>");
            sb.AppendLine("</head>");
            sb.AppendLine("<body>");

            sb.AppendLine("<div class='cover-box'>");
            sb.AppendLine($"  <div class='cover-title'>{System.Net.WebUtility.HtmlEncode(title)}</div>");
            if (project != null)
            {
                sb.AppendLine($"  <div class='cover-subtitle'>Projet : {System.Net.WebUtility.HtmlEncode(project.Name)} ({System.Net.WebUtility.HtmlEncode(project.Code)})</div>");
            }
            sb.AppendLine("</div>");

            if (project != null)
            {
                sb.AppendLine("<table class='meta-table'>");
                sb.AppendLine($"  <tr><td class='label'>Manager de Projet</td><td>{System.Net.WebUtility.HtmlEncode(project.Manager)}</td><td class='label'>Bailleur / Client</td><td>{System.Net.WebUtility.HtmlEncode(project.Client)}</td></tr>");
                sb.AppendLine($"  <tr><td class='label'>Phase / Statut</td><td>{System.Net.WebUtility.HtmlEncode(project.Status)}</td><td class='label'>Budget Alloué</td><td><b>{project.BudgetGlobal:N0} MAD</b></td></tr>");
                sb.AppendLine($"  <tr><td class='label'>Date du Rapport</td><td colspan='3'>{DateTime.Now:dd/MM/yyyy à HH:mm} — AFMI Gestion Projet</td></tr>");
                sb.AppendLine("</table>");
            }

            sb.AppendLine("<div class='report-body'>");
            sb.AppendLine(System.Net.WebUtility.HtmlEncode(content));
            sb.AppendLine("</div>");

            sb.AppendLine("</body>");
            sb.AppendLine("</html>");

            File.WriteAllText(filePath, sb.ToString(), Encoding.UTF8);
        }
    }
}

