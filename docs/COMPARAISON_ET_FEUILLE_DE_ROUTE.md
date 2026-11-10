# AFMI Smart Admin — Comparaison avec les solutions du marché et feuille de route

*Novembre 2026. Les informations sur les produits tiers proviennent surtout de comparatifs publiés par les éditeurs ;
à vérifier auprès d'eux avant toute décision d'achat ou de positionnement.*

## 1. Solutions comparables

| Catégorie | Produits de référence | Points forts | Limites pour l'AFMI |
|---|---|---|---|
| Suivi-évaluation / GAR | TolaData, ActivityInfo, DevResults | Cadre de résultats configurable, plans d'indicateurs, suivi cible/réalisé multi-projets | Pas de rédaction IA, pas de comptabilité marocaine, abonnement en ligne |
| Recherche et rédaction de subventions | Grantable, Instrumentl, Granted AI | Veille des bailleurs, rédaction IA à partir de la mémoire de l'organisation, pipeline | Orientés États-Unis, pas d'arabe, pas de cadre logique ni de budget détaillé |
| Gestion de subventions | Fluxx, AmpliFund, Submittable | Workflows configurables, suivi budgétaire et conformité, reporting | Conçus pour les bailleurs ou les administrations, coûteux, pas d'IA locale |
| Gestion de projet générique | Monday, ProofHub, MS Project | Tâches, Gantt, charge | Pas d'indicateurs GAR ni de logique bailleur |

## 2. Positionnement d'AFMI Smart Admin

| Capacité | AFMI Smart Admin | TolaData | Grantable | AmpliFund |
|---|---|---|---|---|
| Portefeuille, WBS, EVM, rapports PDF | ✅ | ◐ | ❌ | ◐ |
| Cadre logique / indicateurs | ✅ (agents + module projets) | ✅ | ❌ | ◐ |
| Rédaction IA des propositions | ✅ | ❌ | ✅ | ❌ |
| **Chaînes d'agents connectés** (éligibilité → cadre logique → budget → note → communication → revue) | ✅ nouveau | ❌ | ◐ (assistant unique) | ❌ |
| OCR relevés/factures + contrôles ICE, TVA, seuils marchés publics marocains | ✅ | ❌ | ❌ | ❌ |
| Arabe / français / anglais, RTL | ✅ | ◐ | ❌ | ❌ |
| Fonctionne hors ligne (Ollama ou moteur heuristique) | ✅ | ❌ | ❌ | ❌ |
| Données stockées localement | ✅ | ❌ (cloud) | ❌ (cloud) | ❌ (cloud) |
| Collaboration multi-utilisateurs en temps réel | ❌ | ✅ | ✅ | ✅ |
| Portail partenaires / bénéficiaires | ❌ | ◐ | ❌ | ✅ |

**Différenciation :** contexte marocain (ICE, TVA, Décret 2-22-431, bailleurs nationaux), bilinguisme arabe/français,
fonctionnement hors ligne et chaîne complète de la veille au rapport final dans un seul logiciel.

## 3. Ce qui a été réalisé dans cette version (1.1.0)

1. **Installateur Windows** (`build_installer.bat` → `build\installer\AFMI_Smart_Admin_Setup_1.1.0.exe`) :
   .NET autonome, backend Python compilé (Python non requis), installation sans droits administrateur,
   raccourcis, désinstallation propre, données conservées dans `%LocalAppData%`.
2. **Orchestrateur multi-agents** (`SmartOffice/backend/core/orchestrator.py`), patron orchestrateur-travailleurs :
   - 4 chaînes : *Montage complet d'une proposition*, *Rapport d'avancement bailleur*, *Audit des dépenses & plan correctif*,
     *Veille & priorisation des opportunités* ;
   - transmission explicite des productions entre agents, isolées dans `<<<UNTRUSTED_DOCUMENT_DATA>>>` ;
   - données vérifiées injectées depuis la base (portefeuille, trésorerie, projet, contrôles d'audit déterministes) ;
   - superviseur qualité final (cohérence des chiffres, éléments GAR manquants, verdict) ;
   - nouvelle tentative par étape, étapes dépendantes ignorées si une étape amont échoue, statut partiel,
     reprise propre après fermeture (`interrupted`), suivi en direct et export Word du dossier complet.
3. **Fiabilité** : affichage du moteur réellement utilisé (gemini / ollama / heuristic) au lieu du moteur demandé ;
   correction du repli vers Ollama (le nom de modèle Gemini lui était envoyé) ; démarrage sur une base neuve ;
   profil institutionnel relu à chaque requête ; 13 tests backend (pytest) et 15 tests bureau (xUnit).

## 4. Feuille de route recommandée

| Priorité | Évolution | Inspiration | Effort |
|---|---|---|---|
| 1 | Unifier les deux bases (projets, bailleurs, indicateurs) : le module Smart Office lit le portefeuille WPF | TolaData | Moyen |
| 1 | Clé `EncryptionService` protégée par DPAPI avec migration et export chiffré par mot de passe | — | Moyen |
| 1 | Minimiser les données envoyées au cloud (masquer RIB/ICE/IF dans les prompts Gemini) | AFMI Montage Projet (`MinimiseData`) | Faible |
| 2 | Bibliothèque de contenus réutilisables (paragraphes validés, CV, références) injectée dans les agents | Grantable | Moyen |
| 2 | Calendrier des échéances bailleurs avec alertes (notifications Windows) | Instrumentl | Faible |
| 2 | Chaînes d'agents personnalisables depuis le Studio (ajout/ordre des étapes) | Fluxx (workflows configurables) | Moyen |
| 3 | Validation humaine entre étapes (« approuver puis continuer ») | Bonnes pratiques multi-agents | Faible |
| 3 | Mise à jour automatique de l'application | — | Moyen |
| 3 | Synchronisation multi-postes / collaboration | Fluxx, Submittable | Élevé |

## Sources

- [Best M&E software for UK charities 2026 — Plinth](https://www.plinth.org.uk/complete-guide/monitoring-evaluation-software-charities)
- [Best M&E software — SourceForge](https://sourceforge.net/software/monitoring-and-evaluation-m-e/)
- [Granted AI vs Grantable, Instrumentl, Candid (2026)](https://grantedai.com/blog/granted-ai-vs-grantable-comparison)
- [Best grant writing software for nonprofits — Grantable](https://grantable.co/best-grant-writing-software-for-nonprofits)
- [Instrumentl — Software Advice](https://www.softwareadvice.com/nonprofit/instrumentl-profile/)
- [Grant management systems compared — Plinth](https://www.plinth.org.uk/complete-guide/grant-management-systems-compared)
- [Fluxx vs Submittable — G2](https://www.g2.com/compare/fluxx-io-fluxx-grantmaker-vs-submittable)
- [AmpliFund vs Fluxx — TrustRadius](https://www.trustradius.com/compare-products/amplifund-vs-fluxx-grantseeker)
- [AI agent orchestration patterns — Kore.ai](https://kore.ai/blog/choosing-the-right-orchestration-pattern-for-multi-agent-systems)
- [Multi-agent orchestration patterns (2026) — Developers Digest](https://www.developersdigest.tech/blog/multi-agent-orchestration-patterns)
