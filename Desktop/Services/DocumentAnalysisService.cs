using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using AFMI_Gestion_projet.Models;
using UglyToad.PdfPig;
using UglyToad.PdfPig.Content;

namespace AFMI_Gestion_projet.Services
{
    public class BaselineDiagnosticResult
    {
        public double ComplianceScore { get; set; } = 100;
        public double TotalGrantCommitted { get; set; }
        public double GrantConsumedAmount { get; set; }
        public double GrantRemainingAmount { get; set; }
        public double GrantConsumptionRate { get; set; }
        public DateTime? NextReportDueDate { get; set; }
        public bool IsReportDueSoon { get; set; }
        public bool IsReportOverdue { get; set; }
        public List<string> ComplianceAlerts { get; set; } = new();
        public List<string> StrategicRecommendations { get; set; } = new();
        public string ExecutiveSummary { get; set; } = string.Empty;

        // Extended: per-phase document coverage
        public Dictionary<string, int> DocumentsPerPhase { get; set; } = new();
        public List<string> MissingPhases { get; set; } = new();

        // Extracted insights from all reference documents combined
        public List<string> ExtractedObjectives { get; set; } = new();
        public List<string> ExtractedIndicators { get; set; } = new();
        public string KnowledgeBaseSummary { get; set; } = string.Empty;

        /// <summary>Alias for GrantConsumedAmount — total actual expenditures charged to the grant</summary>
        public double TotalSpent
        {
            get => GrantConsumedAmount;
            set => GrantConsumedAmount = value;
        }
    }

    /// <summary>
    /// Represents key data extracted from a single document
    /// </summary>
    public class DocumentInsights
    {
        public string DocumentTitle { get; set; } = string.Empty;
        public string Category { get; set; } = string.Empty;
        public string Phase { get; set; } = string.Empty;
        public List<string> Objectives { get; set; } = new();
        public List<string> Indicators { get; set; } = new();
        public List<string> Amounts { get; set; } = new();
        public List<string> Dates { get; set; } = new();
        public List<string> KeyTerms { get; set; } = new();
        public string Summary { get; set; } = string.Empty;
    }

    public class DocumentAnalysisService
    {
        // Patterns for extracting key information from document text
        private static readonly string[] _objectiveKeywords = { "objectif", "but ", "finalité", "résultat attendu", "outcome", "output", "هدف", "غرض" };
        private static readonly string[] _indicatorKeywords = { "indicateur", "indicator", "mesure", "taux", "pourcentage", "nombre de", "ratio" };
        private static readonly string[] _amountPatterns = { @"\b\d[\d\s]*(?:000|[KMk])\s*(?:€|DH|MAD|EUR|$)", @"\b\d+[\.,]\d+\s*(?:€|DH|MAD|EUR)" };
        private static readonly string[] _projectPhases = { "Diagnostic", "Montage", "Rédaction", "Exécution", "Évaluation", "Clôture" };

        // ─── File Storage ────────────────────────────────────────────────────────

        /// <summary>
        /// Stores an uploaded document securely in the project's dedicated storage directory
        /// </summary>
        public (string savedPath, long fileSize, string extension) StoreDocumentFile(int projectId, string sourceFilePath)
        {
            if (!File.Exists(sourceFilePath))
            {
                throw new FileNotFoundException("Le fichier source spécifié est introuvable.", sourceFilePath);
            }

            string baseFolder = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "AFMIGestionProjet", "Projects", projectId.ToString(), "FoundationDocuments");

            if (!Directory.Exists(baseFolder))
            {
                Directory.CreateDirectory(baseFolder);
            }

            var fileInfo = new FileInfo(sourceFilePath);
            string ext = fileInfo.Extension.ToLower();
            string safeName = Path.GetFileNameWithoutExtension(sourceFilePath);

            // Remove invalid characters
            foreach (char c in Path.GetInvalidFileNameChars())
            {
                safeName = safeName.Replace(c, '_');
            }

            string targetFileName = $"{DateTime.Now:yyyyMMdd_HHmmss}_{Guid.NewGuid().ToString().Substring(0, 6)}_{safeName}{ext}";
            string destPath = Path.Combine(baseFolder, targetFileName);

            File.Copy(sourceFilePath, destPath, true);

            return (destPath, fileInfo.Length, ext);
        }

        // ─── Text Extraction ──────────────────────────────────────────────────────

        /// <summary>
        /// Extracts readable plain text from supported document formats (.pdf, .docx, .txt, .csv, .json, .xml)
        /// </summary>
        public string ExtractTextFromDocument(string filePath)
        {
            if (!File.Exists(filePath)) return string.Empty;

            try
            {
                string ext = Path.GetExtension(filePath).ToLower();

                if (ext == ".txt" || ext == ".csv" || ext == ".json" || ext == ".xml")
                {
                    return File.ReadAllText(filePath, Encoding.UTF8);
                }
                else if (ext == ".docx")
                {
                    return ExtractTextFromDocx(filePath);
                }
                else if (ext == ".doc")
                {
                    // Basic .doc reading — extract printable ASCII sequences
                    return ExtractTextFromLegacyDoc(filePath);
                }
                else if (ext == ".pdf")
                {
                    return ExtractTextFromPdf(filePath);
                }
                else if (ext == ".xlsx" || ext == ".xls")
                {
                    return ExtractTextFromExcel(filePath);
                }
                else
                {
                    var fi = new FileInfo(filePath);
                    return $"[Fichier {ext.ToUpper()} : {fi.Name} — Taille : {fi.Length / 1024} Ko — Extraction textuelle non supportée pour ce format]";
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Error extracting text: {ex.Message}");
                return string.Empty;
            }
        }

        /// <summary>Extract text from PDF using PdfPig</summary>
        private string ExtractTextFromPdf(string pdfPath)
        {
            var sb = new StringBuilder();
            try
            {
                using var document = PdfDocument.Open(pdfPath);
                foreach (Page page in document.GetPages())
                {
                    sb.Append(page.Text);
                    sb.AppendLine();
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"PDF parse error: {ex.Message}");
                sb.Append($"[Erreur extraction PDF : {ex.Message}]");
            }
            return sb.ToString();
        }

        /// <summary>Extract text from Word .docx (Open XML)</summary>
        private string ExtractTextFromDocx(string docxPath)
        {
            var sb = new StringBuilder();
            try
            {
                using (var zip = ZipFile.OpenRead(docxPath))
                {
                    var entry = zip.GetEntry("word/document.xml");
                    if (entry != null)
                    {
                        using (var stream = entry.Open())
                        using (var reader = new StreamReader(stream, Encoding.UTF8))
                        {
                            string xml = reader.ReadToEnd();
                            // Match all <w:t>...</w:t> tags
                            var matches = Regex.Matches(xml, @"<w:t[^>]*>(.*?)</w:t>");
                            foreach (Match m in matches)
                            {
                                sb.Append(m.Groups[1].Value).Append(" ");
                            }
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Docx parse error: {ex.Message}");
            }
            return sb.ToString();
        }

        /// <summary>Extract readable text from old binary .doc files (best-effort)</summary>
        private string ExtractTextFromLegacyDoc(string docPath)
        {
            try
            {
                byte[] bytes = File.ReadAllBytes(docPath);
                // Extract printable ASCII/Unicode sequences of length >= 4
                var sb = new StringBuilder();
                int i = 0;
                while (i < bytes.Length - 1)
                {
                    if (bytes[i] >= 32 && bytes[i] < 127)
                    {
                        int start = i;
                        while (i < bytes.Length && bytes[i] >= 32 && bytes[i] < 127) i++;
                        if (i - start >= 4)
                        {
                            sb.Append(Encoding.ASCII.GetString(bytes, start, i - start));
                            sb.Append(' ');
                        }
                    }
                    else i++;
                }
                return sb.ToString();
            }
            catch
            {
                return $"[Fichier .doc binaire — extraction partielle non disponible]";
            }
        }

        /// <summary>Extract cell values from .xlsx using Open XML ZIP structure</summary>
        private string ExtractTextFromExcel(string xlsxPath)
        {
            if (!xlsxPath.EndsWith(".xlsx", StringComparison.OrdinalIgnoreCase))
                return $"[Fichier Excel ancien .xls — veuillez convertir en .xlsx pour extraction]";

            var sb = new StringBuilder();
            try
            {
                using var zip = ZipFile.OpenRead(xlsxPath);

                // Read shared strings table
                var sharedStrings = new List<string>();
                var ssEntry = zip.GetEntry("xl/sharedStrings.xml");
                if (ssEntry != null)
                {
                    using var stream = ssEntry.Open();
                    using var reader = new StreamReader(stream, Encoding.UTF8);
                    string xml = reader.ReadToEnd();
                    var matches = Regex.Matches(xml, @"<t[^>]*>(.*?)</t>");
                    foreach (Match m in matches)
                    {
                        sharedStrings.Add(m.Groups[1].Value);
                    }
                }

                // Read Sheet1
                var sheetEntry = zip.GetEntry("xl/worksheets/sheet1.xml");
                if (sheetEntry != null)
                {
                    using var stream = sheetEntry.Open();
                    using var reader = new StreamReader(stream, Encoding.UTF8);
                    string xml = reader.ReadToEnd();
                    var cells = Regex.Matches(xml, @"<c r=""[^""]*""(?:[^>]* t=""([^""]*)"")?>.*?<v>(.*?)</v>.*?</c>", RegexOptions.Singleline);
                    foreach (Match cell in cells)
                    {
                        string type = cell.Groups[1].Value;
                        string val = cell.Groups[2].Value;
                        if (type == "s" && int.TryParse(val, out int idx) && idx < sharedStrings.Count)
                            sb.Append(sharedStrings[idx]).Append(" | ");
                        else
                            sb.Append(val).Append(" | ");
                    }
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Excel parse error: {ex.Message}");
            }
            return sb.ToString();
        }

        // ─── Deep Document Insight Analysis ──────────────────────────────────────

        /// <summary>
        /// Analyzes a single document's extracted text and returns structured insights:
        /// objectives, indicators, financial amounts, dates, and key terms.
        /// </summary>
        public DocumentInsights AnalyzeDocumentInsights(ProjectDocument doc)
        {
            var insights = new DocumentInsights
            {
                DocumentTitle = doc.Title,
                Category = doc.Category,
                Phase = doc.DocumentPhase
            };

            string text = !string.IsNullOrEmpty(doc.FullExtractedText)
                ? doc.FullExtractedText
                : doc.ExtractedSummary;

            if (string.IsNullOrWhiteSpace(text)) return insights;

            // Split into sentences for targeted analysis
            var sentences = text.Split(new[] { '.', '\n', ';' }, StringSplitOptions.RemoveEmptyEntries);

            foreach (var sentence in sentences)
            {
                string s = sentence.Trim();
                if (s.Length < 10) continue;

                // Detect objectives
                if (_objectiveKeywords.Any(kw => s.IndexOf(kw, StringComparison.OrdinalIgnoreCase) >= 0))
                {
                    var clean = s.Length > 160 ? s.Substring(0, 160) + "…" : s;
                    if (!insights.Objectives.Contains(clean) && insights.Objectives.Count < 8)
                        insights.Objectives.Add(clean);
                }

                // Detect indicators
                if (_indicatorKeywords.Any(kw => s.IndexOf(kw, StringComparison.OrdinalIgnoreCase) >= 0))
                {
                    var clean = s.Length > 160 ? s.Substring(0, 160) + "…" : s;
                    if (!insights.Indicators.Contains(clean) && insights.Indicators.Count < 8)
                        insights.Indicators.Add(clean);
                }
            }

            // Detect financial amounts
            foreach (var pattern in _amountPatterns)
            {
                var matches = Regex.Matches(text, pattern);
                foreach (Match m in matches)
                {
                    if (!insights.Amounts.Contains(m.Value) && insights.Amounts.Count < 10)
                        insights.Amounts.Add(m.Value.Trim());
                }
            }

            // Detect dates (dd/mm/yyyy, dd-mm-yyyy, year ranges)
            var dateMatches = Regex.Matches(text, @"\b(\d{1,2}[/\-]\d{1,2}[/\-]\d{4}|\d{4}[-/]\d{4})\b");
            foreach (Match m in dateMatches)
            {
                if (!insights.Dates.Contains(m.Value) && insights.Dates.Count < 10)
                    insights.Dates.Add(m.Value);
            }

            // Build concise structured summary
            var sb = new StringBuilder();
            if (insights.Objectives.Count > 0)
                sb.AppendLine($"■ Objectifs identifiés : {string.Join(" / ", insights.Objectives.Take(3))}");
            if (insights.Amounts.Count > 0)
                sb.AppendLine($"■ Montants relevés : {string.Join(", ", insights.Amounts.Take(5))}");
            if (insights.Dates.Count > 0)
                sb.AppendLine($"■ Dates clés : {string.Join(", ", insights.Dates.Take(5))}");
            if (insights.Indicators.Count > 0)
                sb.AppendLine($"■ Indicateurs : {string.Join(" / ", insights.Indicators.Take(3))}");

            insights.Summary = sb.ToString();

            return insights;
        }

        /// <summary>
        /// Serializes insights from a document into the semicolon-delimited KeyInsights field.
        /// </summary>
        public string SerializeInsights(DocumentInsights insights)
        {
            var parts = new List<string>();

            foreach (var obj in insights.Objectives.Take(4))
                parts.Add($"Objectif: {obj}");
            foreach (var ind in insights.Indicators.Take(3))
                parts.Add($"Indicateur: {ind}");
            foreach (var amt in insights.Amounts.Take(4))
                parts.Add($"Montant: {amt}");
            foreach (var dt in insights.Dates.Take(3))
                parts.Add($"Date: {dt}");

            return string.Join(";", parts);
        }

        /// <summary>
        /// Builds a consolidated knowledge base summary from all project reference documents.
        /// This is used as contextual input for report generation.
        /// </summary>
        public string BuildProjectKnowledgeBase(Project project)
        {
            var refDocs = project.Documents
                .Where(d => d.IsKeyReference || d.Category.Contains("Convention") || d.Category.Contains("Budget") || d.Category.Contains("Diagnostic"))
                .OrderBy(d => d.DocumentPhase)
                .ToList();

            if (!refDocs.Any()) return string.Empty;

            var sb = new StringBuilder();
            sb.AppendLine("=== BASE DE CONNAISSANCES DOCUMENTAIRE DU PROJET ===");
            sb.AppendLine($"Générée le : {DateTime.Now:dd/MM/yyyy HH:mm}");
            sb.AppendLine($"Nombre de documents de référence : {refDocs.Count}");
            sb.AppendLine();

            foreach (var doc in refDocs)
            {
                sb.AppendLine($"--- [{doc.DocumentPhase}] {doc.Title} ({doc.Category}) ---");
                if (!string.IsNullOrEmpty(doc.DonorName))
                    sb.AppendLine($"  Bailleur : {doc.DonorName}");
                if (!string.IsNullOrEmpty(doc.DocumentReference))
                    sb.AppendLine($"  Référence : {doc.DocumentReference}");
                if (doc.SignatureDate.HasValue)
                    sb.AppendLine($"  Date signature : {doc.SignatureDate:dd/MM/yyyy}");
                if (doc.ApprovedGrantAmount > 0)
                    sb.AppendLine($"  Montant approuvé : {doc.ApprovedGrantAmount:N0} €");

                // Add key insights
                if (!string.IsNullOrEmpty(doc.KeyInsights))
                {
                    var insightLines = doc.KeyInsights.Split(';', StringSplitOptions.RemoveEmptyEntries);
                    foreach (var line in insightLines.Take(6))
                        sb.AppendLine($"  • {line.Trim()}");
                }
                else if (!string.IsNullOrEmpty(doc.ExtractedSummary))
                {
                    var summary = doc.ExtractedSummary.Length > 300
                        ? doc.ExtractedSummary.Substring(0, 300) + "…"
                        : doc.ExtractedSummary;
                    sb.AppendLine($"  Résumé : {summary}");
                }

                sb.AppendLine();
            }

            return sb.ToString();
        }

        /// <summary>
        /// Returns contextual insights relevant to a specific report type.
        /// Used to enrich generated PDF reports with document references.
        /// </summary>
        public string GetContextualInsightsForReport(Project project, string reportType)
        {
            var docs = project.Documents.ToList();
            if (!docs.Any()) return string.Empty;

            var sb = new StringBuilder();
            sb.AppendLine("RÉFÉRENTIEL DOCUMENTAIRE DU PROJET");
            sb.AppendLine(new string('─', 50));

            if (reportType.Contains("Avancement") || reportType.Contains("Progress"))
            {
                // For progress reports: reference the project dossier and logical framework
                var relevant = docs.Where(d =>
                    d.Category.Contains("Dossier") ||
                    d.Category.Contains("Cadre Logique") ||
                    d.DocumentPhase == "Montage" ||
                    d.DocumentPhase == "Rédaction" ||
                    d.IsKeyReference).Take(4).ToList();

                foreach (var d in relevant)
                {
                    sb.AppendLine($"• [{d.Category}] {d.Title}");
                    if (!string.IsNullOrEmpty(d.ExtractedSummary))
                    {
                        var s = d.ExtractedSummary.Length > 200 ? d.ExtractedSummary.Substring(0, 200) + "…" : d.ExtractedSummary;
                        sb.AppendLine($"  → {s}");
                    }
                }
            }
            else if (reportType.Contains("Financier") || reportType.Contains("Financial"))
            {
                // For financial reports: reference budget docs and conventions
                var relevant = docs.Where(d =>
                    d.Category.Contains("Budget") ||
                    d.Category.Contains("Convention") ||
                    d.ApprovedGrantAmount > 0).Take(4).ToList();

                foreach (var d in relevant)
                {
                    sb.AppendLine($"• [{d.Category}] {d.Title}");
                    if (d.ApprovedGrantAmount > 0)
                        sb.AppendLine($"  → Montant conventionné : {d.ApprovedGrantAmount:N0} €");
                    if (!string.IsNullOrEmpty(d.DocumentReference))
                        sb.AppendLine($"  → Réf. : {d.DocumentReference}");
                }
            }
            else if (reportType.Contains("Clôture") || reportType.Contains("Final"))
            {
                // For closeout reports: reference all key documents, compare with diagnostic
                var diagnostic = docs.FirstOrDefault(d => d.DocumentPhase == "Diagnostic" || d.Category.Contains("Diagnostic"));
                if (diagnostic != null)
                {
                    sb.AppendLine($"• DIAGNOSTIC INITIAL : {diagnostic.Title}");
                    if (!string.IsNullOrEmpty(diagnostic.ExtractedSummary))
                    {
                        var s = diagnostic.ExtractedSummary.Length > 250 ? diagnostic.ExtractedSummary.Substring(0, 250) + "…" : diagnostic.ExtractedSummary;
                        sb.AppendLine($"  → {s}");
                    }
                }
                var keyRefs = docs.Where(d => d.IsKeyReference).Take(3).ToList();
                foreach (var d in keyRefs)
                {
                    sb.AppendLine($"• [Référence Clé] {d.Title} ({d.Category})");
                }
            }
            else
            {
                // Generic: list key reference documents
                var keyRefs = docs.Where(d => d.IsKeyReference).Take(5).ToList();
                if (!keyRefs.Any()) keyRefs = docs.Take(3).ToList();
                foreach (var d in keyRefs)
                {
                    sb.AppendLine($"• {d.Title} — {d.Category}");
                }
            }

            return sb.ToString();
        }

        // ─── Deep Project Diagnostic ──────────────────────────────────────────────

        /// <summary>
        /// Conducts in-depth baseline analysis against conventions, initial dossiers, and actual execution
        /// </summary>
        public BaselineDiagnosticResult PerformDeepDiagnostic(Project project)
        {
            var result = new BaselineDiagnosticResult();
            var today = DateTime.Today;

            // 1. Calculate committed grant amount from documents
            var conventions = project.Documents
                .Where(d => d.Category.Contains("Convention") || d.Category.Contains("Accord") || d.ApprovedGrantAmount > 0)
                .ToList();

            double totalGrant = conventions.Sum(d => d.ApprovedGrantAmount);
            if (totalGrant == 0)
            {
                // Fallback to project budget if no specific convention amounts recorded
                totalGrant = project.BudgetGlobal;
            }
            result.TotalGrantCommitted = totalGrant;

            // 2. Financial Consumption
            double actualCostTotal = 0;
            if (project.CostEntries.Any())
            {
                actualCostTotal = project.CostEntries.Sum(c => c.ActualCost);
            }
            else if (project.Tasks.Any())
            {
                actualCostTotal = project.Tasks.Where(t => t.ParentTaskId == null).Sum(t => t.Cost);
            }

            result.GrantConsumedAmount = actualCostTotal;
            result.GrantRemainingAmount = Math.Max(0, totalGrant - actualCostTotal);
            result.GrantConsumptionRate = totalGrant > 0 ? (actualCostTotal / totalGrant) * 100 : 0;

            // 3. Contractual Dates & Deadlines Analysis
            var deadlineDoc = conventions.FirstOrDefault(c => c.ContractualEndDate.HasValue);
            DateTime? eligibilityEnd = deadlineDoc?.ContractualEndDate ?? project.TargetEndDate;

            // Calculate next donor reporting date
            DateTime startDate = project.ActualStartDate ?? project.TargetStartDate ?? today.AddMonths(-3);
            int reportingMonths = (project.Baseline?.ReportingFrequency == "Trimestriel") ? 3 : 6;

            DateTime nextReport = startDate.AddMonths(reportingMonths);
            while (nextReport < today && eligibilityEnd.HasValue && nextReport < eligibilityEnd.Value)
            {
                nextReport = nextReport.AddMonths(reportingMonths);
            }
            result.NextReportDueDate = nextReport;

            if (nextReport <= today)
            {
                result.IsReportOverdue = true;
                result.ComplianceAlerts.Add($"Échéance de rapport au bailleur DÉPASSÉE depuis le {nextReport:dd/MM/yyyy}. Une justification d'étape est requise.");
            }
            else if ((nextReport - today).TotalDays <= 30)
            {
                result.IsReportDueSoon = true;
                result.ComplianceAlerts.Add($"Échéance contractuelle de rapport bailleur imminente : prévue le {nextReport:dd/MM/yyyy} (dans {(int)(nextReport - today).TotalDays} jours).");
            }

            // 4. Budget Overrun vs Grant Convention
            if (actualCostTotal > totalGrant && totalGrant > 0)
            {
                double over = actualCostTotal - totalGrant;
                result.ComplianceAlerts.Add($"Dépassement de l'enveloppe conventionnée : les dépenses engagées excèdent la subvention de {over:N0} €.");
            }
            else if (eligibilityEnd.HasValue && (eligibilityEnd.Value - today).TotalDays < 60 && result.GrantConsumptionRate < 60)
            {
                result.ComplianceAlerts.Add($"Risque de sous-consommation critique : la fin de convention approche ({eligibilityEnd:dd/MM/yyyy}) alors que seulement {result.GrantConsumptionRate:F1}% des fonds sont justifiés.");
            }

            // 5. Scope & WBS Alignment Check
            int totalTasks = project.Tasks.Count;
            int completedTasks = project.Tasks.Count(t => t.Status == "Terminé");
            int blockedTasks = project.Tasks.Count(t => t.Status == "Bloqué");

            if (blockedTasks > 0)
            {
                result.ComplianceAlerts.Add($"{blockedTasks} tâche(s) du plan de travail sont bloquées, menaçant la livraison des jalons de la convention.");
            }

            if (!project.Documents.Any())
            {
                result.ComplianceAlerts.Add("Aucun document fondateur ou convention n'a encore été rattaché au dossier projet.");
            }

            // 6. Phase Coverage Analysis
            foreach (var phase in _projectPhases)
            {
                int count = project.Documents.Count(d => d.DocumentPhase == phase);
                result.DocumentsPerPhase[phase] = count;
                if (count == 0)
                    result.MissingPhases.Add(phase);
            }

            if (result.MissingPhases.Count > 3)
            {
                result.ComplianceAlerts.Add($"Couverture documentaire incomplète : {result.MissingPhases.Count} phase(s) sans documents ({string.Join(", ", result.MissingPhases)}).");
            }

            // 7. Aggregate key insights from all reference documents
            var keyRefDocs = project.Documents.Where(d => d.IsKeyReference || d.ApprovedGrantAmount > 0).ToList();
            foreach (var doc in keyRefDocs)
            {
                if (!string.IsNullOrEmpty(doc.KeyInsights))
                {
                    var insights = doc.KeyInsights.Split(';', StringSplitOptions.RemoveEmptyEntries);
                    foreach (var ins in insights)
                    {
                        if (ins.StartsWith("Objectif:", StringComparison.OrdinalIgnoreCase))
                            result.ExtractedObjectives.Add(ins.Substring(9).Trim());
                        else if (ins.StartsWith("Indicateur:", StringComparison.OrdinalIgnoreCase))
                            result.ExtractedIndicators.Add(ins.Substring(11).Trim());
                    }
                }
            }

            // 8. Calculate Compliance Score (0 to 100)
            double score = 100;
            if (actualCostTotal > totalGrant && totalGrant > 0) score -= 30;
            if (result.IsReportOverdue) score -= 25;
            if (result.IsReportDueSoon) score -= 10;
            if (blockedTasks > 0) score -= (blockedTasks * 5);
            if (!project.Documents.Any()) score -= 20;
            if (result.MissingPhases.Count > 3) score -= 10;

            result.ComplianceScore = Math.Max(10, Math.Min(100, score));

            // 9. Recommendations
            if (result.IsReportOverdue || result.IsReportDueSoon)
            {
                result.StrategicRecommendations.Add("Préparer et éditer le rapport d'avancement et l'état financier intermédiaire pour transmission officielle au bailleur.");
            }
            if (actualCostTotal > totalGrant && totalGrant > 0)
            {
                result.StrategicRecommendations.Add("Soumettre une demande d'avenant budgétaire ou mobiliser l'apport en cofinancement / fonds propres.");
            }
            if (blockedTasks > 0)
            {
                result.StrategicRecommendations.Add("Convoquer une réunion de crise pour débloquer les tâches critiques conditionnant les livrables contractuels.");
            }
            if (result.MissingPhases.Any())
            {
                result.StrategicRecommendations.Add($"Compléter le référentiel documentaire — phases manquantes : {string.Join(", ", result.MissingPhases)}.");
            }
            if (result.StrategicRecommendations.Count == 0)
            {
                result.StrategicRecommendations.Add("Le projet respecte scrupuleusement les clauses de la convention. Maintenir le rythme d'exécution nominal.");
            }

            // 10. Build knowledge base summary
            result.KnowledgeBaseSummary = BuildProjectKnowledgeBase(project);

            // 11. Executive Narrative Summary
            string donorTitle = !string.IsNullOrEmpty(deadlineDoc?.DonorName) ? deadlineDoc.DonorName : "Bailleur de fonds institutionnel";
            string refCode = !string.IsNullOrEmpty(deadlineDoc?.DocumentReference) ? $" (Réf : {deadlineDoc.DocumentReference})" : "";

            var sb = new StringBuilder();
            sb.Append($"L'analyse approfondie des documents fondateurs et conventions pour le projet \"{project.Name}\" ");
            sb.Append($"atteste d'un engagement conventionné total de **{totalGrant:N0} €** avec **{donorTitle}**{refCode}. ");
            sb.Append($"À la date du {today:dd/MM/yyyy}, le taux de consommation de la subvention s'établit à **{result.GrantConsumptionRate:F1}%** ");
            sb.Append($"(soit {actualCostTotal:N0} € engagés sur un reliquat disponible de {result.GrantRemainingAmount:N0} €). ");
            sb.Append($"L'indice global de conformité contractuelle est évalué à **{result.ComplianceScore:F0}/100**. ");
            sb.Append($"La base documentaire du projet compte **{project.Documents.Count} document(s)** couvrant {_projectPhases.Length - result.MissingPhases.Count} sur {_projectPhases.Length} phases du cycle de vie.");

            result.ExecutiveSummary = sb.ToString();

            return result;
        }


        // ─── Automatic Work Program & Proposal Synthesis Engine ──────────────────

        /// <summary>
        /// Automatically synthesizes an executive Work Program, Objectives, Activities breakdown,
        /// and Expected Budget based on project documents knowledge base and baseline data.
        /// </summary>
        public GeneratedWorkProgram GenerateWorkProgramFromKnowledgeBase(Project project)
        {
            var program = new GeneratedWorkProgram
            {
                ProjectName = project.Name,
                ProjectCode = project.Code,
                DonorName = project.Documents.FirstOrDefault(d => !string.IsNullOrEmpty(d.DonorName))?.DonorName ?? project.Client,
                TotalBudget = project.BudgetGlobal > 0 ? project.BudgetGlobal : project.Documents.Sum(d => d.ApprovedGrantAmount),
                TargetStartDate = project.TargetStartDate ?? DateTime.Today,
                TargetEndDate = project.TargetEndDate ?? DateTime.Today.AddMonths(12)
            };

            var diagnostic = PerformDeepDiagnostic(project);

            // 1. Objectives & Results Extraction
            if (diagnostic.ExtractedObjectives.Any())
            {
                program.GeneralObjectives.AddRange(diagnostic.ExtractedObjectives.Take(3));
                program.SpecificObjectives.AddRange(diagnostic.ExtractedObjectives.Skip(3).Take(4));
            }
            else
            {
                program.GeneralObjectives.Add($"Réalisation globale et déploiement stratégique du projet : {project.Name}");
                program.GeneralObjectives.Add($"Atteinte des indicateurs de performance et conformité aux exigences contractuelles du bailleur ({program.DonorName})");
                
                program.SpecificObjectives.Add($"Exécution des livrables techniques dans le respect du calendrier (Échéance : {program.TargetEndDate:dd/MM/yyyy})");
                program.SpecificObjectives.Add($"Optimisation de la consommation budgétaire et maîtrise de l'enveloppe allouée ({program.TotalBudget:N0} €)");
                program.SpecificObjectives.Add("Garantie de la qualité, de la traçabilité des dépenses et de la pérennité des résultats");
            }

            // Expected Results & Indicators
            if (diagnostic.ExtractedIndicators.Any())
            {
                program.KeyIndicators.AddRange(diagnostic.ExtractedIndicators.Take(5));
            }
            else
            {
                program.KeyIndicators.Add("Taux d'avancement physique des tâches >= 100%");
                program.KeyIndicators.Add("Indice de performance coût CPI >= 1.0 (respect du budget)");
                program.KeyIndicators.Add("Taux de justification auprès du bailleur = 100%");
                program.KeyIndicators.Add("Livrables contractuels validés dans les délais (SPI >= 1.0)");
            }

            program.ExpectedResults.Add("Dossier de cadrage et convention de financement dûment homologués");
            program.ExpectedResults.Add("Ensemble des composantes techniques réalisées conformément au cahier des charges");
            program.ExpectedResults.Add("Rapports d'avancement physiques et financiers transmis et approuvés par le bailleur");
            program.ExpectedResults.Add("Audit final et clôture administrative apurés sans réserve");

            // 2. Structured Activities Generation
            double budget = program.TotalBudget > 0 ? program.TotalBudget : 100000;
            int actIdx = 1;

            var defaultActivities = new List<(string Name, string Desc, string Phase, string Category, int Duration, double Share, string Deliverable, string Role)>
            {
                ("A1. Diagnostic initial & Cadrage institutionnel", "Étude de faisabilité, validation des termes de référence et réunion de lancement", "Diagnostic", "Étude & Diagnostic", 3, 0.08, "Rapport de cadrage validé", "Chef de Projet"),
                ("A2. Mobilisation des ressources & Montage opérationnel", "Contractualisation des experts, acquisition des équipements et mise en place de l'équipe", "Montage", "Ingénierie & Montage", 4, 0.12, "Équipe mobilisée & Plan de travail", "Responsable Opérationnel"),
                ("A3. Rédaction du plan d'exécution & Matrice des indicateurs", "Élaboration détaillée du cadre logique, plan de suivi-évaluation et fiches de tâches", "Rédaction", "Planification", 3, 0.05, "Manuel d'exécution approuvé", "Expert Suivi-Évaluation"),
                ("A4. Déploiement des activités techniques & Composante principale", "Exécution des travaux de terrain, ateliers, formations et réalisations physiques", "Exécution", "Réalisation Technique", 16, 0.45, "Livrables techniques d'étape", "Équipe Technique & Experts"),
                ("A5. Suivi-évaluation, contrôle qualité & Reporting intermédiaire", "Missions de contrôle de terrain, calcul des KPI et édition des rapports d'étape", "Exécution", "Contrôle & Suivi", 8, 0.10, "Rapports d'avancement semestriels", "Auditeur Interne"),
                ("A6. Évaluation à mi-parcours & Revue des résultats", "Analyse des écarts, ajustements stratégiques et avenants éventuels", "Évaluation", "Évaluation", 4, 0.08, "Rapport d'évaluation mi-parcours", "Consultant Externe"),
                ("A7. Clôture administrative, Audit financier & Restitution finale", "Audit comptable externe, rapport final d'évaluation et atelier de clôture", "Clôture", "Clôture & Audit", 4, 0.12, "Rapport final & Certificat d'audit", "Directeur du Projet & Auditeur")
            };

            foreach (var act in defaultActivities)
            {
                program.Activities.Add(new GeneratedActivityItem
                {
                    Index = actIdx++,
                    Name = act.Name,
                    Description = act.Desc,
                    Phase = act.Phase,
                    Category = act.Category,
                    DurationWeeks = act.Duration,
                    EstimatedBudget = Math.Round(budget * act.Share, 0),
                    ExpectedDeliverable = act.Deliverable,
                    ResponsibleRole = act.Role
                });
            }

            // 3. Expected Budget Ledger Generation
            program.BudgetLedger = new List<GeneratedBudgetItem>
            {
                new GeneratedBudgetItem { Category = "Ressources Humaines & Expertise", Description = "Honoraires de l'équipe projet, experts techniques et consultants", EstimatedCost = Math.Round(budget * 0.40, 0), FundingSource = "Subvention Bailleur" },
                new GeneratedBudgetItem { Category = "Équipements & Matériel", Description = "Acquisitions d'outils, équipements informatiques et matériels roulants", EstimatedCost = Math.Round(budget * 0.25, 0), FundingSource = "Subvention Bailleur" },
                new GeneratedBudgetItem { Category = "Activités de Terrain & Ateliers", Description = "Frais d'organisation d'ateliers, séminaires, formations et déplacements", EstimatedCost = Math.Round(budget * 0.20, 0), FundingSource = "Subvention / Co-financement" },
                new GeneratedBudgetItem { Category = "Audit, Communication & Imprévus", Description = "Audit externe obligatoire, édition de rapports, visibilité et réserve d'aléas", EstimatedCost = Math.Round(budget * 0.15, 0), FundingSource = "Subvention Bailleur" }
            };

            // 4. Risks & Mitigation
            program.ImplementationRisks.Add("Glissement calendaire lié aux délais d'approbation ou de passation des marchés");
            program.ImplementationRisks.Add("Risque de dépassement budgétaire suite à l'inflation des coûts d'intrants");
            program.ImplementationRisks.Add("Insuffisance de justification documentaire pour les tranches de subvention");

            program.MitigationMeasures.Add("Mise en place d'un comité de pilotage mensuel et suivi serré du chemin critique SPI");
            program.MitigationMeasures.Add("Contrôle rigoureux des coûts (CPI) et négociation de contrats à prix fermes");
            program.MitigationMeasures.Add("Archivage et numérisation continue de toutes les pièces justificatives comptables");

            // 5. Full Proposal Narrative Formatting
            var sb = new StringBuilder();
            sb.AppendLine($"# PROGRAMME DE TRAVAIL & PROPOSITION D'EXÉCUTION DU PROJET");
            sb.AppendLine($"**Projet :** {program.ProjectName} ({program.ProjectCode})");
            sb.AppendLine($"**Bailleur / Partenaire :** {program.DonorName}");
            sb.AppendLine($"**Enveloppe Budgétaire globale :** {program.TotalBudget:N0} €");
            sb.AppendLine($"**Période d'exécution :** du {program.TargetStartDate:dd/MM/yyyy} au {program.TargetEndDate:dd/MM/yyyy}");
            sb.AppendLine();
            sb.AppendLine("## 1. OBJECTIFS DU PROGRAMME DE TRAVAIL");
            sb.AppendLine("### 1.1 Objectifs Généraux");
            foreach (var og in program.GeneralObjectives) sb.AppendLine($"* {og}");
            sb.AppendLine("### 1.2 Objectifs Spécifiques");
            foreach (var os in program.SpecificObjectives) sb.AppendLine($"* {os}");
            sb.AppendLine();
            sb.AppendLine("## 2. RÉSULTATS ATTENDUS ET INDICATEURS");
            foreach (var res in program.ExpectedResults) sb.AppendLine($"* **Résultat :** {res}");
            sb.AppendLine("### Indicateurs de Performance (KPI) :");
            foreach (var ind in program.KeyIndicators) sb.AppendLine($"  - {ind}");
            sb.AppendLine();
            sb.AppendLine("## 3. PROGRAMME DES ACTIVITÉS & PLAN D'ACTION DETAILÉ");
            foreach (var act in program.Activities)
            {
                sb.AppendLine($"### {act.Name} [{act.Phase}]");
                sb.AppendLine($"  * **Description :** {act.Description}");
                sb.AppendLine($"  * **Responsable :** {act.ResponsibleRole} | **Durée :** {act.DurationWeeks} semaines");
                sb.AppendLine($"  * **Budget estimé :** {act.EstimatedBudget:N0} € | **Livrable :** {act.ExpectedDeliverable}");
                sb.AppendLine();
            }
            sb.AppendLine("## 4. BUDGET ET ESTIMATION DES DÉPENSES PAR POSTE");
            foreach (var b in program.BudgetLedger)
            {
                sb.AppendLine($"* **{b.Category}** : {b.EstimatedCost:N0} € ({b.Description}) — *Source : {b.FundingSource}*");
            }
            sb.AppendLine();
            sb.AppendLine("## 5. GESTION DES RISQUES ET MESURES ATTÉNUANTES");
            for (int i = 0; i < program.ImplementationRisks.Count; i++)
            {
                sb.AppendLine($"* **Risque :** {program.ImplementationRisks[i]}");
                if (i < program.MitigationMeasures.Count)
                    sb.AppendLine($"  → **Mesure :** {program.MitigationMeasures[i]}");
            }

            program.FullProposalMarkdown = sb.ToString();

            return program;
        }
    }

    // ─── Data Models for Work Program Auto-Synthesis ───────────────────────────

    public class GeneratedActivityItem
    {
        public int Index { get; set; }
        public string Name { get; set; } = string.Empty;
        public string Description { get; set; } = string.Empty;
        public string Phase { get; set; } = "Exécution";
        public string Category { get; set; } = "Activité Technique";
        public int DurationWeeks { get; set; } = 4;
        public double EstimatedBudget { get; set; }
        public string ExpectedDeliverable { get; set; } = string.Empty;
        public string ResponsibleRole { get; set; } = "Chef de Projet";
    }

    public class GeneratedBudgetItem
    {
        public string Category { get; set; } = string.Empty;
        public string Description { get; set; } = string.Empty;
        public double EstimatedCost { get; set; }
        public string FundingSource { get; set; } = "Subvention Bailleur";
    }

    public class GeneratedWorkProgram
    {
        public string ProjectName { get; set; } = string.Empty;
        public string ProjectCode { get; set; } = string.Empty;
        public string DonorName { get; set; } = string.Empty;
        public double TotalBudget { get; set; }
        public DateTime TargetStartDate { get; set; } = DateTime.Today;
        public DateTime TargetEndDate { get; set; } = DateTime.Today.AddMonths(12);

        public string ExecutiveSummary { get; set; } = string.Empty;
        public List<string> GeneralObjectives { get; set; } = new();
        public List<string> SpecificObjectives { get; set; } = new();
        public List<string> ExpectedResults { get; set; } = new();
        public List<string> KeyIndicators { get; set; } = new();

        public List<GeneratedActivityItem> Activities { get; set; } = new();
        public List<GeneratedBudgetItem> BudgetLedger { get; set; } = new();

        public List<string> ImplementationRisks { get; set; } = new();
        public List<string> MitigationMeasures { get; set; } = new();

        public string FullProposalMarkdown { get; set; } = string.Empty;
    }
}

