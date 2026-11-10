using System;
using System.IO;
using System.Net;
using System.Net.Mail;
using System.Windows;
using AFMI_Gestion_projet.Models;

namespace AFMI_Gestion_projet.Services
{
    public class MailService
    {
        /// <summary>
        /// Attempts to send the generated PDF report via SMTP. Shows a warning dialog and returns false if SMTP is unconfigured or fails.
        /// </summary>
        public bool SendReport(SmtpSettings? smtp, string pdfPath, string reportType)
        {
            if (smtp == null || string.IsNullOrEmpty(smtp.Server) || string.IsNullOrEmpty(smtp.RecipientEmail))
            {
                ShowSimulationDialog(smtp, pdfPath, reportType, "Configuration SMTP incomplète.");
                return false; // Not sent: LastSentSuccess must reflect it
            }

            try
            {
                using (var mail = new MailMessage())
                {
                    mail.From = new MailAddress(smtp.Username.Contains("@") ? smtp.Username : "diffusion@afmi-gestion.local");
                    mail.To.Add(smtp.RecipientEmail);
                    mail.Subject = $"[AFMI GESTION] Diffusion Automatique - {reportType} - {DateTime.Now:dd/MM/yyyy}";
                    mail.Body = $"Bonjour,\n\nVeuillez trouver ci-joint le rapport de performance '{reportType}' généré automatiquement par l'application AFMI Gestion le {DateTime.Now:dd/MM/yyyy HH:mm}.\n\nCordialement,\nL'Assistant Automatique AFMI";
                    
                    if (File.Exists(pdfPath))
                    {
                        mail.Attachments.Add(new Attachment(pdfPath));
                    }

                    using (var client = new SmtpClient(smtp.Server, smtp.Port))
                    {
                        client.Credentials = new NetworkCredential(smtp.Username, smtp.Password);
                        client.EnableSsl = true;
                        client.Send(mail);
                    }
                }
                return true;
            }
            catch (Exception ex)
            {
                ShowSimulationDialog(smtp, pdfPath, reportType, $"Échec d'envoi SMTP ({ex.Message}).");
                return false;
            }
        }

        private void ShowSimulationDialog(SmtpSettings? smtp, string pdfPath, string reportType, string reason)
        {
            string recipient = smtp?.RecipientEmail ?? "(Non configuré)";
            string server = smtp?.Server ?? "(Non configuré)";
            string filename = Path.GetFileName(pdfPath);

            Application.Current.Dispatcher.Invoke(() =>
            {
                MessageBox.Show(
                    $"=== DIFFUSION AUTOMATIQUE RAPPORTS (ÉMULATION) ===\n\n" +
                    $"Cause : {reason}\n" +
                    $"Type de Rapport : {reportType}\n" +
                    $"Destinataire : {recipient}\n" +
                    $"Serveur SMTP : {server}\n" +
                    $"Pièce jointe PDF : {filename}\n\n" +
                    $"⚠ Aucun e-mail n'a été envoyé. Vérifiez la configuration SMTP puis relancez la diffusion.",
                    "Diffusion de Rapport - Non envoyé",
                    MessageBoxButton.OK,
                    MessageBoxImage.Warning
                );
            });
        }
    }
}
