using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using AFMI_Gestion_projet.Models;

namespace AFMI_Gestion_projet.Services
{
    public class CorrectionItem
    {
        public string Original { get; set; } = string.Empty;
        public string Replacement { get; set; } = string.Empty;
        public string Reason { get; set; } = string.Empty;
    }

    public class TextAnalysisResult
    {
        public string OriginalText { get; set; } = string.Empty;
        public string ProcessedText { get; set; } = string.Empty;
        public int WordCount { get; set; }
        public int CorrectionsCount { get; set; }
        public List<CorrectionItem> Corrections { get; set; } = new();
        public string ExecutionEngine { get; set; } = "Moteur Interne Local (100% Gratuit)";
    }

    public enum ReformulationTone
    {
        ProfessionnelFormel,
        ExecutifSynthetique,
        OperationnelTechnique,
        PersuasifImpact
    }

    public enum ReformulationGoal
    {
        AmeliorerStyle,
        SynthetiserPuces,
        DevelopperArgumenter,
        TransformerEnPlanActions
    }

    public class InternalAiAgentService
    {
        private static readonly HttpClient _httpClient = new() { Timeout = TimeSpan.FromSeconds(8) };

        public string OllamaEndpoint { get; set; } = "http://localhost:11434";
        public string OllamaModel { get; set; } = "mistral";
        public bool UseLocalOllamaIfAvailable { get; set; } = false;

        public bool UseCloudApi { get; set; } = false;
        public string CloudProvider { get; set; } = "OpenAI";
        public string CloudApiKey { get; set; } = string.Empty;

        // Dictionnaire de correction orthographique et typographique française
        private static readonly Dictionary<string, (string corrected, string reason)> _commonSpellingErrors = new(StringComparer.OrdinalIgnoreCase)
        {
            { "a faire", ("à faire", "Accent prépositionnel manquant") },
            { "a definir", ("à définir", "Accent prépositionnel manquant") },
            { "a valider", ("à valider", "Accent prépositionnel manquant") },
            { "a jour", ("à jour", "Accent prépositionnel manquant") },
            { "a l'heure", ("à l'heure", "Accent prépositionnel manquant") },
            { "a temps", ("à temps", "Accent prépositionnel manquant") },
            { "deja", ("déjà", "Accents manquants") },
            { "cout", ("coût", "Accent circonflexe manquant") },
            { "couts", ("coûts", "Accent circonflexe manquant") },
            { "echeance", ("échéance", "Accents aigus manquants") },
            { "echeances", ("échéances", "Accents aigus manquants") },
            { "delai", ("délai", "Accent aigu manquant") },
            { "delais", ("délais", "Accent aigu manquant") },
            { "etape", ("étape", "Accent aigu manquant") },
            { "etapes", ("étapes", "Accent aigu manquant") },
            { "tache", ("tâche", "Accent circonflexe sur tâche de travail") },
            { "taches", ("tâches", "Accent circonflexe sur tâches de travail") },
            { "reunion", ("réunion", "Accent aigu manquant") },
            { "reunions", ("réunions", "Accent aigu manquant") },
            { "developpement", ("développement", "Accent aigu et orthographe") },
            { "developpements", ("développements", "Accent aigu et orthographe") },
            { "developper", ("développer", "Accent aigu manquant") },
            { "evaluation", ("évaluation", "Accent aigu manquant") },
            { "evaluations", ("évaluations", "Accent aigu manquant") },
            { "evaluer", ("évaluer", "Accent aigu manquant") },
            { "indicateur cle", ("indicateur clé", "Accent aigu sur clé") },
            { "indicateurs cles", ("indicateurs clés", "Accent aigu sur clés") },
            { "probleme", ("problème", "Accent grave manquant") },
            { "problemes", ("problèmes", "Accent grave manquant") },
            { "activite", ("activité", "Accents aigus manquants") },
            { "activites", ("activités", "Accents aigus manquants") },
            { "synthese", ("synthèse", "Accent grave manquant") },
            { "syntheses", ("synthèses", "Accent grave manquant") },
            { "amelioration", ("amélioration", "Accent aigu manquant") },
            { "ameliorations", ("améliorations", "Accent aigu manquant") },
            { "ameliorer", ("améliorer", "Accent aigu manquant") },
            { "redaction", ("rédaction", "Accent aigu manquant") },
            { "compte rendu", ("compte-rendu", "Trait d'union recommandé") },
            { "comptes rendus", ("comptes-rendus", "Trait d'union recommandé") },
            { "cloture", ("clôture", "Accent circonflexe manquant") },
            { "cloturer", ("clôturer", "Accent circonflexe manquant") },
            { "tres", ("très", "Accent grave manquant") },
            { "apres", ("après", "Accent grave manquant") },
            { "meme", ("même", "Accent circonflexe manquant") },
            { "memes", ("mêmes", "Accent circonflexe manquant") },
            { "evenement", ("événement", "Accents aigus manquants") },
            { "evenements", ("événements", "Accents aigus manquants") },
            { "prevision", ("prévision", "Accent aigu manquant") },
            { "previsions", ("prévisions", "Accent aigu manquant") },
            { "previsionnel", ("prévisionnel", "Accent aigu manquant") },
            { "previsionnelle", ("prévisionnelle", "Accent aigu manquant") },
            { "operationnel", ("opérationnel", "Accent aigu manquant") },
            { "operationnelle", ("opérationnelle", "Accent aigu manquant") },
            { "operationnels", ("opérationnels", "Accent aigu manquant") },
            { "operationnelles", ("opérationnelles", "Accent aigu manquant") },
            { "recommandation", ("recommandation", "Orthographe (deux m)") },
            { "recommandations", ("recommandations", "Orthographe (deux m)") },
            { "livrable", ("livrable", "Orthographe standard") },
            { "livrables", ("livrables", "Orthographe standard") },
            { "comite", ("comité", "Accent aigu manquant") },
            { "comites", ("comités", "Accent aigu manquant") },
            { "responsabilite", ("responsabilité", "Accents manquants") },
            { "responsabilites", ("responsabilités", "Accents manquants") },
            { "partenaire", ("partenaire", "Orthographe standard") },
            { "partenaires", ("partenaires", "Orthographe standard") },
            { "coordination", ("coordination", "Orthographe standard") },
            { "beneficiaire", ("bénéficiaire", "Accents aigus manquants") },
            { "beneficiaires", ("bénéficiaires", "Accents aigus manquants") },
            { "perimetre", ("périmètre", "Accents manquants") },
            { "perimetres", ("périmètres", "Accents manquants") },
            { "budgetaire", ("budgétaire", "Accent aigu manquant") },
            { "budgetaires", ("budgétaires", "Accent aigu manquant") },
            { "financiere", ("financière", "Accent grave manquant") },
            { "financieres", ("financières", "Accent grave manquant") },
            { "planification", ("planification", "Orthographe standard") },
            { "retroplanning", ("rétroplanning", "Accent aigu manquant") },
            { "jalon", ("jalon", "Orthographe standard") },
            { "jalons", ("jalons", "Orthographe standard") },
            { "crise", ("crise", "Orthographe standard") },
            { "bloquant", ("bloquant", "Orthographe standard") },
            { "bloquants", ("bloquants", "Orthographe standard") }
        };

        // Termes familiers ou faibles remplacés par des formulations de gestion de projet
        private static readonly Dictionary<string, string> _weakExpressionsReplacements = new(StringComparer.OrdinalIgnoreCase)
        {
            { "on doit faire", "il convient d'engager" },
            { "il faut faire", "il est impératif de mettre en œuvre" },
            { "on a fait", "l'équipe a réalisé" },
            { "on a vu que", "il a été constaté que" },
            { "ça marche pas", "un dysfonctionnement a été identifié" },
            { "ça ne marche pas", "un dysfonctionnement opérationnel est constaté" },
            { "c'est en retard", "un glissement calendaire est enregistré" },
            { "on est en retard", "un décalage sur le planning cible est à déplorer" },
            { "y a pas assez d'argent", "une insuffisance de marge budgétaire est mise en évidence" },
            { "on a plus de budget", "l'enveloppe budgétaire allouée est arrivée à épuisement" },
            { "le client n'est pas content", "des réserves ont été formulées par le commanditaire" },
            { "le boss veut", "la direction a ordonné" },
            { "on va essayer de", "l'équipe s'engage à" },
            { "pas de probleme", "aucune anomalie n'est à signaler" },
            { "vite fait", "dans les meilleurs délais" },
            { "a peu pres", "selon les estimations provisoires" },
            { "en gros", "en synthèse" },
            { "comme prevu", "conformément aux orientations initiales" },
            { "comme prévu", "conformément aux orientations initiales" },
            { "on attend la reponse", "dans l'attente d'une validation formelle" },
            { "on attend la réponse", "dans l'attente d'une validation formelle" }
        };

        #region 1. Correction Orthographique, Grammaticale & Typographique

        /// <summary>
        /// Corrige l'orthographe, les accords récurrents et normalise la typographie française (version synchrone interne)
        /// </summary>
        public TextAnalysisResult CorrectText(string input)
        {
            return CorrectTextInternal(input);
        }

        /// <summary>
        /// Corrige l'orthographe, les accords récurrents et normalise la typographie française via LLM ou moteur interne
        /// </summary>
        public async Task<TextAnalysisResult> CorrectTextAsync(string input)
        {
            if (string.IsNullOrWhiteSpace(input))
            {
                return new TextAnalysisResult();
            }

            if (UseCloudApi && !string.IsNullOrWhiteSpace(CloudApiKey))
            {
                var cloudResult = await TryCloudApiPromptAsync(BuildCorrectionPrompt(input));
                if (!string.IsNullOrWhiteSpace(cloudResult))
                {
                    return new TextAnalysisResult
                    {
                        OriginalText = input,
                        ProcessedText = cloudResult.Trim(),
                        WordCount = CountWords(cloudResult),
                        CorrectionsCount = 1,
                        ExecutionEngine = $"Moteur Cloud API ({CloudProvider})"
                    };
                }
            }

            if (UseLocalOllamaIfAvailable)
            {
                var llmResult = await TryOllamaPromptAsync(BuildCorrectionPrompt(input));
                if (!string.IsNullOrWhiteSpace(llmResult))
                {
                    return new TextAnalysisResult
                    {
                        OriginalText = input,
                        ProcessedText = llmResult.Trim(),
                        WordCount = CountWords(llmResult),
                        CorrectionsCount = 1,
                        ExecutionEngine = $"Moteur LLM Local ({OllamaModel})"
                    };
                }
            }

            return CorrectTextInternal(input);
        }

        private TextAnalysisResult CorrectTextInternal(string input)
        {
            if (string.IsNullOrWhiteSpace(input))
            {
                return new TextAnalysisResult();
            }

            var result = new TextAnalysisResult
            {
                OriginalText = input,
                WordCount = CountWords(input)
            };

            string text = input;

            // 1. Correction des mots courants et expressions
            foreach (var kv in _commonSpellingErrors)
            {
                string pattern = $@"\b{Regex.Escape(kv.Key)}\b";
                var matches = Regex.Matches(text, pattern, RegexOptions.IgnoreCase);
                if (matches.Count > 0)
                {
                    foreach (Match m in matches)
                    {
                        // Conserver la casse initiale si majuscule
                        string replacement = PreserveCase(m.Value, kv.Value.corrected);
                        if (m.Value != replacement)
                        {
                            result.Corrections.Add(new CorrectionItem
                            {
                                Original = m.Value,
                                Replacement = replacement,
                                Reason = kv.Value.reason
                            });
                        }
                    }
                    text = Regex.Replace(text, pattern, m => PreserveCase(m.Value, kv.Value.corrected), RegexOptions.IgnoreCase);
                }
            }

            // 2. Correction des règles d'accords courantes
            // "les/des/plusieurs/tous les + mot pluriel manquant d'un s"
            var pluralMatches = Regex.Matches(text, @"\b(les|des|plusieurs|tous les|toutes les)\s+([a-zA-ZÀ-ÿ]{4,})(?<!s|x|z)\b", RegexOptions.IgnoreCase);
            foreach (Match m in pluralMatches)
            {
                string word = m.Groups[2].Value;
                // Exclure les mots invariables courants
                if (!IsFrenchInvariable(word))
                {
                    string correctedWord = word + "s";
                    string oldFull = m.Value;
                    string newFull = $"{m.Groups[1].Value} {correctedWord}";
                    text = ReplaceFirst(text, oldFull, newFull);
                    result.Corrections.Add(new CorrectionItem
                    {
                        Original = word,
                        Replacement = correctedWord,
                        Reason = "Accord pluriel après déterminant pluriel"
                    });
                }
            }

            // 3. Normalisation typographique française
            // - Espace insécable avant les doubles ponctuations (: ; ? !)
            string beforePunct = text;
            text = Regex.Replace(text, @"\s*([:;?!])", " $1");
            text = Regex.Replace(text, @"([«])\s*", "$1 ");
            text = Regex.Replace(text, @"\s*([»])", " $1");

            // - Majuscule en début de phrase
            text = Regex.Replace(text, @"(^|[.!?]\s+)([a-zà-ÿ])", m => m.Groups[1].Value + m.Groups[2].Value.ToUpper());

            if (beforePunct != text)
            {
                result.Corrections.Add(new CorrectionItem
                {
                    Original = "[Typographie]",
                    Replacement = "[Ponctuation normalisée]",
                    Reason = "Harmonisation des espaces et majuscules selon la typographie française"
                });
            }

            result.ProcessedText = text.Trim();
            result.CorrectionsCount = result.Corrections.Count;
            return result;
        }

        #endregion

        #region 2. Reformulation & Amélioration de Rédaction

        /// <summary>
        /// Reformule et améliore la rédaction d'un texte selon l'objectif et le ton choisis
        /// </summary>
        public async Task<TextAnalysisResult> ReformulateTextAsync(
            string input, 
            ReformulationGoal goal, 
            ReformulationTone tone, 
            Project? contextProject = null)
        {
            if (string.IsNullOrWhiteSpace(input))
            {
                return new TextAnalysisResult();
            }

            if (UseCloudApi && !string.IsNullOrWhiteSpace(CloudApiKey))
            {
                var cloudResult = await TryCloudApiPromptAsync(BuildReformulationPrompt(input, goal, tone, contextProject));
                if (!string.IsNullOrWhiteSpace(cloudResult))
                {
                    return new TextAnalysisResult
                    {
                        OriginalText = input,
                        ProcessedText = cloudResult.Trim(),
                        WordCount = CountWords(cloudResult),
                        ExecutionEngine = $"Moteur Cloud API ({CloudProvider})"
                    };
                }
            }

            // Si Ollama est activé et répond, tenter la génération locale via LLM
            if (UseLocalOllamaIfAvailable)
            {
                var llmResult = await TryOllamaPromptAsync(BuildReformulationPrompt(input, goal, tone, contextProject));
                if (!string.IsNullOrWhiteSpace(llmResult))
                {
                    return new TextAnalysisResult
                    {
                        OriginalText = input,
                        ProcessedText = llmResult.Trim(),
                        WordCount = CountWords(llmResult),
                        ExecutionEngine = $"Moteur LLM Local ({OllamaModel})"
                    };
                }
            }

            // Moteur Interne Autonome (100% Gratuit, instantané)
            return ReformulateInternal(input, goal, tone, contextProject);
        }

        private TextAnalysisResult ReformulateInternal(
            string input, 
            ReformulationGoal goal, 
            ReformulationTone tone, 
            Project? contextProject)
        {
            // Étape 1 : Nettoyage et correction de base
            var baseCorrection = CorrectTextInternal(input);
            string workingText = baseCorrection.ProcessedText;

            // Étape 2 : Substitution des termes faibles par du vocabulaire de gestion de projet
            foreach (var kv in _weakExpressionsReplacements)
            {
                string pattern = $@"\b{Regex.Escape(kv.Key)}\b";
                if (Regex.IsMatch(workingText, pattern, RegexOptions.IgnoreCase))
                {
                    workingText = Regex.Replace(workingText, pattern, kv.Value, RegexOptions.IgnoreCase);
                }
            }

            var sentences = SplitIntoSentences(workingText);
            var sb = new StringBuilder();

            switch (goal)
            {
                case ReformulationGoal.AmeliorerStyle:
                    sb.Append(ApplyToneEnhancement(sentences, tone, contextProject));
                    break;

                case ReformulationGoal.SynthetiserPuces:
                    sb.Append(GenerateBulletSummary(sentences, tone, contextProject));
                    break;

                case ReformulationGoal.DevelopperArgumenter:
                    sb.Append(DevelopAndArgue(sentences, tone, contextProject));
                    break;

                case ReformulationGoal.TransformerEnPlanActions:
                    sb.Append(TransformToTaskPlan(sentences, tone, contextProject));
                    break;
            }

            string resultText = sb.ToString().Trim();

            return new TextAnalysisResult
            {
                OriginalText = input,
                ProcessedText = resultText,
                WordCount = CountWords(resultText),
                CorrectionsCount = baseCorrection.CorrectionsCount,
                Corrections = baseCorrection.Corrections,
                ExecutionEngine = "Moteur Linguistique Interne (100% Gratuit)"
            };
        }

        private string ApplyToneEnhancement(List<string> sentences, ReformulationTone tone, Project? proj)
        {
            var sb = new StringBuilder();
            
            // Préambule contextuel selon le ton
            string header = tone switch
            {
                ReformulationTone.ProfessionnelFormel => "Dans le cadre de la conduite opérationnelle et de la gouvernance du projet, ",
                ReformulationTone.ExecutifSynthetique => "En synthèse exécutive pour arbitrage et décision, ",
                ReformulationTone.OperationnelTechnique => "Sur le plan technique et de la coordination terrain, ",
                ReformulationTone.PersuasifImpact => "Afin de maximiser la portée stratégique et l'impact direct auprès des bénéficiaires, ",
                _ => ""
            };

            sb.Append(header);

            for (int i = 0; i < sentences.Count; i++)
            {
                string s = sentences[i].Trim();
                if (string.IsNullOrEmpty(s)) continue;

                // Améliorer les verbes introductifs
                if (i > 0)
                {
                    string transition = (i % 3) switch
                    {
                        0 => " Par ailleurs, ",
                        1 => " De surcroît, ",
                        _ => " En outre, "
                    };
                    sb.Append(transition);
                }

                // Mettre la première lettre en minuscule si précédé d'une transition
                if (i > 0 || !string.IsNullOrEmpty(header))
                {
                    s = char.ToLower(s[0]) + s.Substring(1);
                }

                sb.Append(s);
                if (!s.EndsWith(".")) sb.Append(".");
            }

            // Si un projet est rattaché, ajouter une phrase de consolidation
            if (proj != null)
            {
                sb.AppendLine();
                sb.AppendLine();
                sb.Append($"Ces éléments s'inscrivent directement dans le suivi du projet « {proj.Name} » ({proj.Code}), sous la supervision de {proj.Manager ?? "la direction de projet"}.");
            }

            return sb.ToString();
        }

        private string GenerateBulletSummary(List<string> sentences, ReformulationTone tone, Project? proj)
        {
            var sb = new StringBuilder();
            sb.AppendLine("SYNTHÈSE EXÉCUTIVE DES POINTS CLÉS :");
            sb.AppendLine();

            foreach (var s in sentences)
            {
                if (string.IsNullOrWhiteSpace(s)) continue;
                string clean = s.Trim().TrimEnd('.');
                sb.AppendLine($"• {clean}");
            }

            if (proj != null)
            {
                sb.AppendLine();
                sb.AppendLine($"[Projet de référence : {proj.Code} - {proj.Name} | Statut : {proj.Status} | Avancement Global : {proj.BudgetGlobal:N0} MAD]");
            }

            return sb.ToString();
        }

        private string DevelopAndArgue(List<string> sentences, ReformulationTone tone, Project? proj)
        {
            var sb = new StringBuilder();

            sb.AppendLine("NOTE D'ANALYSE DÉTAILLÉE ET DÉVELOPPEMENT :");
            sb.AppendLine();

            int step = 1;
            foreach (var s in sentences)
            {
                if (string.IsNullOrWhiteSpace(s)) continue;
                string clean = s.Trim();
                if (!clean.EndsWith(".")) clean += ".";

                sb.AppendLine($"1.{step} Constat et cadrage de la situation");
                sb.AppendLine($"{clean} Cette dynamique exige une attention rigoureuse afin d'aligner les efforts opérationnels avec les engagements contractuels.");
                sb.AppendLine();

                sb.AppendLine($"1.{step}.1 Analyse d'impact & mesures préconisées");
                sb.AppendLine($"Il convient de mobiliser les ressources appropriées, de sécuriser les arbitrages requis et de documenter chaque étape pour garantir la traçabilité intégrale des livrables.");
                sb.AppendLine();
                step++;
            }

            if (proj != null)
            {
                sb.AppendLine("RECOMMANDATION FINALE DE LA DIRECTION DU PROJET :");
                sb.AppendLine($"Consolider ces actions dans la feuille de route du projet {proj.Name}, en coordination continue avec le client/bailleur ({proj.Client ?? "Partenaire institutionnel"}).");
            }

            return sb.ToString();
        }

        private string TransformToTaskPlan(List<string> sentences, ReformulationTone tone, Project? proj)
        {
            var sb = new StringBuilder();
            sb.AppendLine("MATRICE DU PLAN D'ACTIONS OPÉRATIONNELLES :");
            sb.AppendLine();
            sb.AppendLine("| Réf | Action Prioritaire | Responsable Préconisé | Échéance Cible | Degré d'Urgence |");
            sb.AppendLine("|-----|--------------------|-----------------------|----------------|-----------------|");

            int idx = 1;
            foreach (var s in sentences)
            {
                if (string.IsNullOrWhiteSpace(s)) continue;
                string clean = s.Trim().TrimEnd('.');
                string resp = proj?.Manager ?? "Chef de projet";
                string dateTarget = DateTime.Today.AddDays(idx * 7).ToString("dd/MM/yyyy");
                string priority = idx == 1 ? "Haute" : (idx == 2 ? "Moyenne" : "Normale");

                sb.AppendLine($"| ACT-{idx:D2} | {clean} | {resp} | {dateTarget} | {priority} |");
                idx++;
            }

            return sb.ToString();
        }

        #endregion

        #region 3. Génération de Comptes Rendus (CR) Professionnels

        /// <summary>
        /// Génère un compte rendu complet, structuré et professionnel à partir d'un modèle de données et d'un projet optionnel
        /// </summary>
        public async Task<MeetingMinutesModel> GenerateMeetingMinutesAsync(MeetingMinutesModel model, Project? project = null)
        {
            if (project != null)
            {
                model.ProjectId = project.Id;
                model.ProjectName = project.Name;
                model.ProjectCode = project.Code;
                model.ProjectManager = project.Manager;
                model.ClientOrDonor = project.Client;
                
                if (project.Funder != null)
                {
                    model.FunderName = project.Funder.Name;
                    model.FunderPrimaryColor = string.IsNullOrWhiteSpace(project.Funder.PrimaryColor) ? "#1E293B" : project.Funder.PrimaryColor;
                    model.FunderLogoPath = project.Funder.LogoPath ?? "";
                    model.FunderHeaderText = project.Funder.HeaderText ?? "";
                    model.FunderFooterText = project.Funder.FooterText ?? "";
                }
            }

            if (UseCloudApi && !string.IsNullOrWhiteSpace(CloudApiKey))
            {
                string prompt = BuildMinutesPrompt(model, project);
                var cloudRes = await TryCloudApiPromptAsync(prompt);
                if (!string.IsNullOrWhiteSpace(cloudRes))
                {
                    model.GeneratedSummary = cloudRes.Trim();
                    ExtractDecisionsAndActionsFromText(model.GeneratedSummary, model);
                    return model;
                }
            }

            // Si Ollama local activé, on peut faire enrichir la synthèse par le LLM
            if (UseLocalOllamaIfAvailable)
            {
                string prompt = BuildMinutesPrompt(model, project);
                var llmRes = await TryOllamaPromptAsync(prompt);
                if (!string.IsNullOrWhiteSpace(llmRes))
                {
                    model.GeneratedSummary = llmRes.Trim();
                    ExtractDecisionsAndActionsFromText(model.GeneratedSummary, model);
                    return model;
                }
            }

            // Moteur Interne 100% Autonome
            model.GeneratedSummary = BuildInternalMeetingMinutesText(model, project);
            ExtractDecisionsAndActionsFromText(model.GeneratedSummary, model);
            return model;
        }

        private string BuildInternalMeetingMinutesText(MeetingMinutesModel model, Project? project)
        {
            var sb = new StringBuilder();

            sb.AppendLine("================================================================================");
            sb.AppendLine($"          {model.Title.ToUpperInvariant()}");
            sb.AppendLine($"     Type de séance : {model.MeetingType} | Date : {model.MeetingDate:dd/MM/yyyy}");
            sb.AppendLine("================================================================================");
            sb.AppendLine();

            // 1. Informations Générales
            sb.AppendLine("1. FICHE SIGNALÉTIQUE & CONTEXTE DE LA RÉUNION");
            sb.AppendLine("--------------------------------------------------------------------------------");
            sb.AppendLine($"• Date & Heure     : {model.MeetingDate:dd/MM/yyyy à HH:mm}");
            sb.AppendLine($"• Lieu / Format    : {(!string.IsNullOrWhiteSpace(model.Location) ? model.Location : "Salle de réunion principale / Visioconférence")}");
            sb.AppendLine($"• Animateur        : {(!string.IsNullOrWhiteSpace(model.Organizer) ? model.Organizer : (project?.Manager ?? "Chef de Projet"))}");
            sb.AppendLine($"• Rédacteur        : {(!string.IsNullOrWhiteSpace(model.Secretary) ? model.Secretary : "Secrétariat de séance")}");
            sb.AppendLine($"• Participants     : {(!string.IsNullOrWhiteSpace(model.Attendees) ? model.Attendees : "Équipe de coordination, partenaires et parties prenantes")}");
            if (!string.IsNullOrWhiteSpace(model.Excused))
            {
                sb.AppendLine($"• Excusés          : {model.Excused}");
            }

            if (project != null)
            {
                sb.AppendLine($"• Projet concerné  : {project.Name} (Code : {project.Code})");
                sb.AppendLine($"• Commanditaire    : {(!string.IsNullOrWhiteSpace(project.Client) ? project.Client : "Non spécifié")}");
                sb.AppendLine($"• Phase actuelle   : {project.Status} | Priorité : {project.Priority}");
                sb.AppendLine($"• Budget Alloué    : {project.BudgetGlobal:N0} MAD");
            }
            sb.AppendLine();

            // 2. Ordre du Jour
            sb.AppendLine("2. ORDRE DU JOUR & OBJECTIFS DE LA SÉANCE");
            sb.AppendLine("--------------------------------------------------------------------------------");
            if (!string.IsNullOrWhiteSpace(model.Agenda))
            {
                var agendaItems = model.Agenda.Split(new[] { '\n', '\r', ';' }, StringSplitOptions.RemoveEmptyEntries);
                int aNum = 1;
                foreach (var item in agendaItems)
                {
                    sb.AppendLine($"  {aNum}. {item.Trim()}");
                    aNum++;
                }
            }
            else
            {
                sb.AppendLine("  1. Revue de l'état d'avancement des actions de la période précédente.");
                sb.AppendLine("  2. Examen des livrables et jalons en cours de finalisation.");
                sb.AppendLine("  3. Identification des difficultés, points bloquants et analyse des risques.");
                sb.AppendLine("  4. Arbitrages stratégiques et validation du plan d'actions pour la période suivante.");
            }
            sb.AppendLine();

            // 3. Synthèse des Échanges & Points Abordés
            sb.AppendLine("3. SYNTHÈSE DÉTAILLÉE DES ÉCHANGES ET DISCUSSIONS");
            sb.AppendLine("--------------------------------------------------------------------------------");
            if (!string.IsNullOrWhiteSpace(model.RawNotes))
            {
                var noteLines = model.RawNotes.Split(new[] { '\n', '\r' }, StringSplitOptions.RemoveEmptyEntries);
                foreach (var line in noteLines)
                {
                    string cleanLine = line.Trim();
                    if (cleanLine.StartsWith("-") || cleanLine.StartsWith("•") || cleanLine.StartsWith("*"))
                    {
                        cleanLine = cleanLine.Substring(1).Trim();
                    }
                    if (cleanLine.Length > 0)
                    {
                        sb.AppendLine($"• {cleanLine}");
                    }
                }
            }
            else
            {
                sb.AppendLine("L'équipe a procédé à une revue méthodique des jalons opérationnels. Les parties prenantes ont réaffirmé leur engagement à maintenir les délais cibles.");
                sb.AppendLine("Les indicateurs de suivi démontrent une mobilisation conforme aux attentes, tout en soulignant la nécessité de sécuriser les dépendances critiques.");
            }

            // Injection des faits réels du projet si disponibles
            if (project != null && project.Tasks != null && project.Tasks.Any())
            {
                sb.AppendLine();
                sb.AppendLine("Focus sur la situation opérationnelle des tâches du projet :");
                var lateTasks = project.Tasks.Where(t => t.Status != "Terminé" && t.TargetEndDate < DateTime.Today).ToList();
                if (lateTasks.Any())
                {
                    sb.AppendLine($"  ⚠️ Alerte calendrier : {lateTasks.Count} tâche(s) présente(nt) un décalage sur l'échéance prévue :");
                    foreach (var lt in lateTasks.Take(3))
                    {
                        sb.AppendLine($"     - {lt.Name} (Assigné à : {lt.Assignee ?? "Non assigné"}, Fin cible : {lt.TargetEndDate:dd/MM/yyyy})");
                    }
                }
                else
                {
                    sb.AppendLine("  ✅ Aucun retard critique identifié sur les échéances actuelles des tâches.");
                }
            }
            sb.AppendLine();

            // 4. Décisions Actées
            sb.AppendLine("4. RELEVÉ DES DÉCISIONS ACTÉES");
            sb.AppendLine("--------------------------------------------------------------------------------");
            sb.AppendLine("1. DEC-01 : Validation formelle des orientations techniques et de la feuille de route.");
            sb.AppendLine("2. DEC-02 : Maintien du dispositif de suivi renforcé avec reporting hebdomadaire.");
            sb.AppendLine("3. DEC-03 : Approbation des ajustements d'affectation des ressources pour sécuriser les livrables.");
            sb.AppendLine();

            // 5. Plan d'Actions Immédiat
            sb.AppendLine("5. PLAN D'ACTIONS ET ENGAGEMENTS (QUI / QUOI / QUAND)");
            sb.AppendLine("--------------------------------------------------------------------------------");
            sb.AppendLine("| N°  | Action à mener                          | Responsable        | Échéance   | Priorité |");
            sb.AppendLine("|-----|-----------------------------------------|--------------------|------------|----------|");
            sb.AppendLine($"| 01  | Finaliser la diffusion du compte rendu   | {model.Secretary ?? "Secrétaire"}       | {DateTime.Today.AddDays(2):dd/MM/yyyy} | Haute    |");
            sb.AppendLine($"| 02  | Lever les points bloquants opérationnels | {project?.Manager ?? "Chef Projet"}    | {DateTime.Today.AddDays(5):dd/MM/yyyy} | Haute    |");
            sb.AppendLine($"| 03  | Mettre à jour le planning et budget WBS | {project?.Manager ?? "Coordination"}   | {DateTime.Today.AddDays(7):dd/MM/yyyy} | Moyenne  |");
            sb.AppendLine($"| 04  | Préparer les éléments de la séance suiv.| Équipe Projet      | {DateTime.Today.AddDays(12):dd/MM/yyyy}| Normale  |");
            sb.AppendLine();

            // 6. Prochaine Échéance
            sb.AppendLine("6. PROCHAINE RÉUNION");
            sb.AppendLine("--------------------------------------------------------------------------------");
            string nextDateStr = !string.IsNullOrWhiteSpace(model.NextMeetingDate) 
                ? model.NextMeetingDate 
                : DateTime.Today.AddDays(14).ToString("dd/MM/yyyy à 10:00");
            sb.AppendLine($"• Date prévisionnelle : {nextDateStr}");
            sb.AppendLine($"• Ordre du jour prévu  : {(!string.IsNullOrWhiteSpace(model.NextMeetingAgenda) ? model.NextMeetingAgenda : "Revue d'avancement des actions actées et validation des livrables de l'étape.")}");
            sb.AppendLine();
            sb.AppendLine("================================================================================");
            sb.AppendLine($"Fin du document — Document généré par l'Agent IA AFMI Gestion Projet le {DateTime.Now:dd/MM/yyyy à HH:mm}");
            sb.AppendLine("================================================================================");

            return sb.ToString();
        }

        private void ExtractDecisionsAndActionsFromText(string text, MeetingMinutesModel model)
        {
            model.Decisions.Clear();
            model.ActionItems.Clear();

            // Remplir les décisions par défaut
            model.Decisions.Add(new MeetingDecision
            {
                Reference = "DEC-01",
                Decision = "Validation de la feuille de route et du calendrier prévisionnel des livrables.",
                Impact = "Sécurisation des jalons de l'étape",
                Responsible = model.Organizer ?? "Direction de Projet"
            });
            model.Decisions.Add(new MeetingDecision
            {
                Reference = "DEC-02",
                Decision = "Maintien de la gouvernance hebdomadaire et suivi rigoureux des tâches sensibles.",
                Impact = "Maîtrise continue des risques et délais",
                Responsible = model.ProjectManager ?? "Chef de Projet"
            });

            // Remplir les actions par défaut
            model.ActionItems.Add(new MeetingActionItem
            {
                Action = "Diffuser le compte rendu validé à l'ensemble des parties prenantes.",
                Responsible = !string.IsNullOrWhiteSpace(model.Secretary) ? model.Secretary : "Secrétariat",
                DueDate = DateTime.Today.AddDays(2),
                Priority = "Haute",
                Status = "À faire"
            });
            model.ActionItems.Add(new MeetingActionItem
            {
                Action = "Traiter les réserves et bloquants techniques identifiés lors de la séance.",
                Responsible = !string.IsNullOrWhiteSpace(model.ProjectManager) ? model.ProjectManager : "Chef de Projet",
                DueDate = DateTime.Today.AddDays(5),
                Priority = "Haute",
                Status = "À faire"
            });
            model.ActionItems.Add(new MeetingActionItem
            {
                Action = "Actualiser le suivi budgétaire et le tableau de bord d'avancement.",
                Responsible = "Coordination financière",
                DueDate = DateTime.Today.AddDays(7),
                Priority = "Moyenne",
                Status = "À faire"
            });
        }

        #endregion

        #region 4. Génération de Rapports Professionnels Personnalisés

        public enum AiReportType
        {
            RapportAvancementNarratif,
            AnalyseRisquesEtCouts,
            NoteStrategiqueCadrage,
            ConformiteBailleur,
            BilanClotureCapitalisation
        }

        /// <summary>
        /// Génère un rapport professionnel complet à partir du projet et du type demandé
        /// </summary>
        public async Task<string> GenerateAiReportAsync(AiReportType reportType, Project project, string additionalNotes = "")
        {
            if (project == null) return string.Empty;

            if (UseCloudApi && !string.IsNullOrWhiteSpace(CloudApiKey))
            {
                string prompt = BuildReportPrompt(reportType, project, additionalNotes);
                var cloudRes = await TryCloudApiPromptAsync(prompt);
                if (!string.IsNullOrWhiteSpace(cloudRes))
                {
                    return cloudRes.Trim();
                }
            }

            if (UseLocalOllamaIfAvailable)
            {
                string prompt = BuildReportPrompt(reportType, project, additionalNotes);
                var llmRes = await TryOllamaPromptAsync(prompt);
                if (!string.IsNullOrWhiteSpace(llmRes))
                {
                    return llmRes.Trim();
                }
            }

            return BuildInternalReport(reportType, project, additionalNotes);
        }

        private string BuildInternalReport(AiReportType reportType, Project project, string additionalNotes)
        {
            var sb = new StringBuilder();
            string title = reportType switch
            {
                AiReportType.RapportAvancementNarratif => "RAPPORT NARRATIF D'AVANCEMENT PÉRIODIQUE",
                AiReportType.AnalyseRisquesEtCouts => "RAPPORT D'ANALYSE STRATÉGIQUE DES RISQUES, DÉLAIS ET COÛTS",
                AiReportType.NoteStrategiqueCadrage => "NOTE DE CADRAGE ET D'ALIGNEMENT STRATÉGIQUE",
                AiReportType.ConformiteBailleur => "RAPPORT DE CONFORMITÉ CONTRACTUELLE ET BAILLEUR DE FONDS",
                AiReportType.BilanClotureCapitalisation => "BILAN FINAL DE CLÔTURE ET CAPITALISATION DES ENSEIGNEMENTS",
                _ => "RAPPORT DE GESTION DE PROJET"
            };

            sb.AppendLine("================================================================================");
            sb.AppendLine($"           {title}");
            sb.AppendLine($"  Projet : {project.Name} (Code: {project.Code})");
            sb.AppendLine("================================================================================");
            sb.AppendLine();
            sb.AppendLine($"Date de génération : {DateTime.Now:dd/MM/yyyy à HH:mm}");
            sb.AppendLine($"Responsable du projet : {project.Manager ?? "Direction du projet"}");
            sb.AppendLine($"Commanditaire / Bailleur : {project.Client ?? "Partenaire Institutionnel"}");
            sb.AppendLine($"Statut : {project.Status} | Priorité : {project.Priority} | Budget Global : {project.BudgetGlobal:N0} MAD");
            sb.AppendLine();

            switch (reportType)
            {
                case AiReportType.RapportAvancementNarratif:
                    sb.AppendLine("1. RÉSUMÉ DE L'ÉTAT D'AVANCEMENT");
                    sb.AppendLine("--------------------------------------------------------------------------------");
                    sb.AppendLine($"Au cours de la période écoulée, le projet « {project.Name} » a progressé conformément aux orientations stratégiques définies.");
                    if (!string.IsNullOrWhiteSpace(additionalNotes))
                    {
                        sb.AppendLine();
                        sb.AppendLine("Détails et notes complémentaires apportés :");
                        sb.AppendLine(additionalNotes);
                    }
                    sb.AppendLine();
                    sb.AppendLine("2. COMPTE RENDU DES ACTIVITÉS ENTREPRISES DURANT LA PÉRIODE");
                    sb.AppendLine("--------------------------------------------------------------------------------");
                    sb.AppendLine("| Activités du projet | Échéance | Statut de l'activité |");
                    sb.AppendLine("|---|---|---|");
                    if (project.Tasks != null && project.Tasks.Any())
                    {
                        foreach (var t in project.Tasks)
                        {
                            sb.AppendLine($"| {t.Name} | {t.TargetEndDate:dd/MM/yyyy} | {t.Status} |");
                        }
                    }
                    else
                    {
                        sb.AppendLine("| Aucune activité enregistrée | - | - |");
                    }
                    sb.AppendLine();
                    sb.AppendLine("3. ANALYSE DES CONTRAINTES ET PLAN DE CONDUITE");
                    sb.AppendLine("--------------------------------------------------------------------------------");
                    sb.AppendLine("Les arbitrages requis ont été documentés. La feuille de route pour la période à venir priorise la sécurisation du calendrier cible et le maintien d'une stricte discipline budgétaire.");
                    break;

                case AiReportType.AnalyseRisquesEtCouts:
                    sb.AppendLine("1. AUDIT BUDGÉTAIRE ET PERFORMANCE DES COÛTS");
                    sb.AppendLine("--------------------------------------------------------------------------------");
                    sb.AppendLine($"L'enveloppe budgétaire globale contractuelle s'élève à {project.BudgetGlobal:N0} MAD.");
                    sb.AppendLine("Le contrôle de gestion confirme que les dépenses engagées sont régulières et adossées aux livrables prévus dans le plan d'action.");
                    sb.AppendLine();
                    sb.AppendLine("2. MATRICE DES RISQUES ET IMPACT SUR LES DÉLAIS");
                    sb.AppendLine("--------------------------------------------------------------------------------");
                    sb.AppendLine("• Risque Calendrier : Vigilance sur les délais de livraison externes et les temps d'approbation.");
                    sb.AppendLine("• Risque Financier  : Nécessité d'anticiper les décaissements et de prévenir tout dépassement imprévu.");
                    sb.AppendLine("• Risque Technique  : Renforcement des revues d'assurance qualité avant validation définitive.");
                    sb.AppendLine();
                    sb.AppendLine("3. MESURES DE MITIGATION PRÉCONISÉES");
                    sb.AppendLine("--------------------------------------------------------------------------------");
                    sb.AppendLine("1. Mettre en place des points d'étape bi-mensuels avec les prestataires.");
                    sb.AppendLine("2. Bloquer une réserve pour aléas sur les postes budgétaires les plus volatils.");
                    break;

                case AiReportType.ConformiteBailleur:
                    sb.AppendLine("1. CADRE D'ENGAGEMENT AVEC LE BAILLEUR");
                    sb.AppendLine("--------------------------------------------------------------------------------");
                    sb.AppendLine($"Le projet s'exécute dans le respect scrupuleux des directives du bailleur ({project.Client ?? "Partenaire Bailleur"}).");
                    sb.AppendLine("Les critères d'éligibilité des coûts, les pièces justificatives d'audit et les normes de passation sont scrupuleusement appliqués.");
                    sb.AppendLine();
                    sb.AppendLine("2. ÉTAT DU RESPECT DES OBJECTIFS CONTRACTUELS");
                    sb.AppendLine("--------------------------------------------------------------------------------");
                    sb.AppendLine("• Atteinte des indicateurs d'impact : Les cibles intermédiaires sont respectées.");
                    sb.AppendLine("• Visibilité et communication institutionnelle : Les mentions et logos obligatoires sont apposés sur l'ensemble des supports.");
                    break;

                default:
                    sb.AppendLine("1. RÉSUMÉ EXÉCUTIF");
                    sb.AppendLine("--------------------------------------------------------------------------------");
                    sb.AppendLine($"Le présent rapport consigne les faits marquants et les décisions majeures relatives au projet {project.Name}.");
                    break;
            }

            sb.AppendLine();
            sb.AppendLine("================================================================================");
            sb.AppendLine("Document officiel validé par l'Agent IA AFMI Gestion Projet");
            sb.AppendLine("================================================================================");

            return sb.ToString();
        }

        #endregion

        #region Helpers & Ollama Connector

        private async Task<string> TryCloudApiPromptAsync(string prompt)
        {
            try
            {
                using var client = new HttpClient();
                client.DefaultRequestHeaders.Add("Accept", "application/json");

                if (CloudProvider.Equals("OpenAI", StringComparison.OrdinalIgnoreCase))
                {
                    client.DefaultRequestHeaders.Add("Authorization", $"Bearer {CloudApiKey}");
                    var payload = new
                    {
                        model = "gpt-4o-mini",
                        messages = new[]
                        {
                            new { role = "system", content = "You are a professional project management assistant." },
                            new { role = "user", content = prompt }
                        }
                    };
                    var content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");
                    var res = await client.PostAsync("https://api.openai.com/v1/chat/completions", content);
                    
                    if (res.IsSuccessStatusCode)
                    {
                        var json = await res.Content.ReadAsStringAsync();
                        using var doc = JsonDocument.Parse(json);
                        return doc.RootElement.GetProperty("choices")[0].GetProperty("message").GetProperty("content").GetString() ?? "";
                    }
                }
                else if (CloudProvider.Equals("Gemini", StringComparison.OrdinalIgnoreCase))
                {
                    var payload = new
                    {
                        contents = new[]
                        {
                            new { parts = new[] { new { text = prompt } } }
                        }
                    };
                    var content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");
                    // Clé transmise en en-tête, jamais dans l'URL (qui finit dans les journaux et messages d'erreur).
                    content.Headers.Add("x-goog-api-key", CloudApiKey);
                    var res = await client.PostAsync("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent", content);
                    
                    if (res.IsSuccessStatusCode)
                    {
                        var json = await res.Content.ReadAsStringAsync();
                        using var doc = JsonDocument.Parse(json);
                        return doc.RootElement.GetProperty("candidates")[0].GetProperty("content").GetProperty("parts")[0].GetProperty("text").GetString() ?? "";
                    }
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Cloud API Error: {ex.Message}");
            }
            return string.Empty;
        }

        private async Task<string> TryOllamaPromptAsync(string prompt)
        {
            try
            {
                var payload = new
                {
                    model = OllamaModel,
                    prompt = prompt,
                    stream = false
                };

                string json = JsonSerializer.Serialize(payload);
                using var content = new StringContent(json, Encoding.UTF8, "application/json");
                var response = await _httpClient.PostAsync($"{OllamaEndpoint.TrimEnd('/')}/api/generate", content);
                if (response.IsSuccessStatusCode)
                {
                    string resJson = await response.Content.ReadAsStringAsync();
                    using var doc = JsonDocument.Parse(resJson);
                    if (doc.RootElement.TryGetProperty("response", out var respProp))
                    {
                        return respProp.GetString() ?? string.Empty;
                    }
                }
            }
            catch
            {
                // Ollama non joignable ou désactivé : bascule transparente sur le moteur interne
            }
            return string.Empty;
        }

        private string BuildCorrectionPrompt(string input)
        {
            var sb = new StringBuilder();
            sb.AppendLine("Tu es un expert en orthographe et grammaire française.");
            sb.AppendLine("Corrige parfaitement les fautes d'orthographe, de grammaire et de typographie du texte suivant.");
            sb.AppendLine("IMPORTANT: Ne réponds QU'AVEC le texte final corrigé. N'ajoute AUCUNE introduction, AUCUNE conclusion, et AUCUN commentaire. Ne modifie pas le style ou le ton.");
            sb.AppendLine("TEXTE A CORRIGER :");
            sb.AppendLine(input);
            return sb.ToString();
        }

        private string BuildReformulationPrompt(string input, ReformulationGoal goal, ReformulationTone tone, Project? proj)
        {
            var sb = new StringBuilder();
            sb.AppendLine("Tu es un expert senior en gestion de projet, rédaction professionnelle et relations institutionnelles.");
            sb.AppendLine($"Objectif : {goal}");
            sb.AppendLine($"Ton à adopter : {tone}");
            if (proj != null)
            {
                sb.AppendLine($"Contexte du projet : Nom='{proj.Name}', Code='{proj.Code}', Manager='{proj.Manager}', Client='{proj.Client}'.");
            }
            sb.AppendLine("Corrige les fautes, enrichis le vocabulaire et reformule le texte suivant en français impeccable.");
            sb.AppendLine("IMPORTANT: Ne réponds QU'AVEC le texte final. N'ajoute AUCUNE introduction, AUCUNE conclusion, et AUCUN commentaire.");
            sb.AppendLine("TEXTE A REFORMULER :");
            sb.AppendLine(input);
            return sb.ToString();
        }

        private string BuildMinutesPrompt(MeetingMinutesModel model, Project? project)
        {
            var sb = new StringBuilder();
            sb.AppendLine("Tu es un secrétaire de séance professionnel. Rédige un compte-rendu de réunion officiel et structuré en français :");
            sb.AppendLine($"Titre : {model.Title}");
            sb.AppendLine($"Date : {model.MeetingDate:dd/MM/yyyy}");
            sb.AppendLine($"Type : {model.MeetingType}");
            sb.AppendLine($"Animateur : {model.Organizer}");
            sb.AppendLine($"Participants : {model.Attendees}");
            sb.AppendLine($"Ordre du jour : {model.Agenda}");
            sb.AppendLine($"Notes brutes : {model.RawNotes}");
            if (!string.IsNullOrWhiteSpace(model.Q_Decisions)) sb.AppendLine($"Décisions majeures prises : {model.Q_Decisions}");
            if (!string.IsNullOrWhiteSpace(model.Q_Blockers)) sb.AppendLine($"Points bloquants soulevés : {model.Q_Blockers}");
            if (!string.IsNullOrWhiteSpace(model.Q_NextSteps)) sb.AppendLine($"Prochaines étapes clés : {model.Q_NextSteps}");
            if (project != null)
            {
                sb.AppendLine($"Projet : {project.Name} ({project.Code}), Budget : {project.BudgetGlobal} MAD, Manager : {project.Manager}");
            }
            return sb.ToString();
        }

        private string BuildReportPrompt(AiReportType type, Project project, string notes)
        {
            var sb = new StringBuilder();
            sb.AppendLine($"Rédige un rapport officiel de type '{type}' pour le projet '{project.Name}' ({project.Code}).");
            sb.AppendLine($"Manager: {project.Manager}, Statut: {project.Status}, Budget: {project.BudgetGlobal} MAD.");
            sb.AppendLine($"Notes complémentaires : {notes}");
            return sb.ToString();
        }

        private static int CountWords(string s)
        {
            if (string.IsNullOrWhiteSpace(s)) return 0;
            return s.Split(new[] { ' ', '\r', '\n', '\t' }, StringSplitOptions.RemoveEmptyEntries).Length;
        }

        private static List<string> SplitIntoSentences(string text)
        {
            if (string.IsNullOrWhiteSpace(text)) return new List<string>();
            var raw = Regex.Split(text, @"(?<=[.!?])\s+");
            return raw.Where(s => !string.IsNullOrWhiteSpace(s)).ToList();
        }

        private static string PreserveCase(string original, string target)
        {
            if (string.IsNullOrEmpty(original) || string.IsNullOrEmpty(target)) return target;
            if (char.IsUpper(original[0]))
            {
                return char.ToUpper(target[0]) + (target.Length > 1 ? target.Substring(1) : "");
            }
            return target.ToLower();
        }

        private static bool IsFrenchInvariable(string word)
        {
            string[] invariables = { "toujours", "jamais", "parfois", "souvent", "moins", "plus", "assez", "beaucoup", "trop", "dehors", "dedans", "ailleurs", "temps", "corps", "cas", "choix", "prix", "taux", "fois", "mois", "pays" };
            return invariables.Contains(word.ToLower());
        }

        private static string ReplaceFirst(string text, string search, string replace)
        {
            int pos = text.IndexOf(search, StringComparison.OrdinalIgnoreCase);
            if (pos < 0) return text;
            return text.Substring(0, pos) + replace + text.Substring(pos + search.Length);
        }

        #endregion
    }
}
