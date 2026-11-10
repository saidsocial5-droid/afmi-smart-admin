# Journal des modifications

## [2.0.0 — Lot 1 : Fondations] — 10/11/2026

Base de la version 2.0 : socle de données financières, migrations, journal d'audit et sécurité.
Aucun écran financier n'est encore livré (Lot 2). Plan complet : [docs/v2/ANALYSE.md](docs/v2/ANALYSE.md).

### Ajouté
- **Bibliothèque `Core/`** (net9.0, sans WPF) : entités, `AppDbContext`, migrations et règles de calcul,
  testable sur tout système. Projet de tests **`Core.Tests`** (52 tests xUnit).
- **Migrations EF Core** à la place de `EnsureCreated` et des `ALTER TABLE` ignorés en cas d'erreur :
  - `Baseline_1_3_0` : schéma 1.3.0. Une base existante est complétée puis marquée comme déjà à ce niveau ;
  - `LegacyAmountsInClear` puis `DecryptLegacyAmounts` : montants hérités remis en clair (voir *Modifié*) ;
  - `FinanceFoundation` : nouvelles tables financières et journal d'audit.
- **Sauvegarde automatique avant migration** : copie cohérente (API de sauvegarde SQLite) dans
  `%LocalAppData%\AFMIGestionProjet\backups\`, 30 dernières conservées. Un échec de migration arrête
  l'application avec un message, sans travailler sur une base incohérente.
- **Modèle financier** (montants en centimes, jamais en `double`) :
  - comptes bancaires et caisse, avec typologie et statut ;
  - liaisons comptes ↔ projets, avec période et clé de répartition ;
  - opérations et ventilations (projet ou fonctionnement, ligne budgétaire, catégorie) ;
  - catégories et plan de comptes paramétrables ;
  - conventions de financement et tranches ;
  - lignes budgétaires, exercices, taux de change datés ;
  - fichiers archivés (SHA-256), justificatifs, règles de catégorisation, paramètres.
- **Règles financières** (`Core/Finance`) :
  - solde à une date (ouverture + crédits − débits) et solde consolidé en MAD ;
  - virements internes appariés, exclus des recettes et des dépenses ;
  - validation d'une opération : ventilation exacte, ligne budgétaire du bon projet, devise du compte, dates du compte ;
  - conversion de devises au taux daté. Un taux manquant bloque l'opération ; il n'est jamais deviné ;
  - répartition au plus fort reste, sans centime perdu ;
  - contrôle de la clé du RIB marocain.
- **Contraintes en base** : montants positifs, cohérence des virements, unicité RIB / exercice / taux.
- **Journal d'audit** (`AuditEntries`) :
  - toute création, modification ou suppression est tracée (qui, quand, quoi, ancienne et nouvelle valeur),
    dans la même transaction que la donnée ;
  - le journal est en ajout seul, protégé par des déclencheurs SQLite ;
  - chaque entrée est chaînée par une empreinte SHA-256, ce qui rend toute falsification détectable ;
  - les secrets n'y apparaissent jamais.
- **Suppression logique** : projets, dépenses, comptes, opérations, conventions, tranches et lignes budgétaires.
  Supprimer un projet ne supprime plus ses tâches, ses dépenses ni son historique.
- **Paramètres partagés** Desktop/backend (table `AppSettings`, `SettingsService`). Les secrets y sont chiffrés
  par DPAPI.
- **Backend → base unique** (`backend/core/unified_db.py`) : lecture et écriture sans toucher au schéma.
  Chaque écriture est journalisée avec la même chaîne d'empreintes que le Desktop.
- **Confidentialité de l'IA** :
  - l'IA externe est **désactivée par défaut** ;
  - le masquage du RIB, de l'IBAN, de l'ICE, de l'IF, de la CIN, du n° CNSS et des salaires avant envoi est
    **activé par défaut** ;
  - une image scannée n'est jamais envoyée à l'extérieur quand le masquage est actif ;
  - réglage dans Smart Office → Mémoire institutionnelle → paramètres IA.
- **Jeton de session de l'API locale** : généré par le Desktop à chaque démarrage. Les autres programmes du poste ne
  peuvent plus appeler le backend.
- **Clé Gemini conservée chiffrée** (DPAPI) dans la base unique ; elle était perdue à chaque redémarrage.
- **Vecteurs de tests partagés** .NET/Python (`SharedTestCases/` : RIB, empreinte d'audit, répartition) et script
  de schéma pour les tests Python (`SmartOffice/tests/fixtures/unified_schema.sql`, dont l'actualité est vérifiée).
- **Intégration continue** GitHub Actions sous Windows : build, tests .NET et Python, migrations à jour, frontend.

### Modifié
- **Montants hérités en clair.** L'ancien chiffrement AES utilisait une clé écrite dans le code : il ne protégeait
  rien et empêchait tout calcul en base. La migration les déchiffre après sauvegarde, et une valeur illisible
  arrête la migration. Les champs hérités (budgets et coûts de projets) restent en `double` pour ne pas toucher
  aux écrans existants ; les flux réels passent désormais par les opérations, en centimes.
- **Base surchargeable** par la variable `AFMI_DESKTOP_DB`. Les tests Desktop et Python n'utilisent plus jamais la
  base réelle de l'utilisateur, alors qu'auparavant `Desktop.Tests` l'ouvrait.
- **Import d'une base** (menu Desktop) : la base importée est migrée immédiatement. En cas d'échec, l'ancienne base
  est restaurée.
- Le backend reçoit du Desktop le chemin de la base unique et l'utilisateur à inscrire dans le journal d'audit.

### Sécurité
- Corrigé : S1 (clé AES en dur), S2 (RIB, ICE et IF envoyés à Gemini), S3 (API sans authentification),
  S4 (clé Gemini non persistée de façon sûre), S5 (journal d'audit effaçable), S6 (suppressions physiques).
- Reste à traiter :
  - S7 : le RIB et l'ICE de `ngo_profile.json` sont-ils réels ?
  - chiffrement complet de la base (option SQLCipher, décision D2-b).

### Points à valider
1. **Sens des opérations :** une recette est toujours un crédit et une dépense toujours un débit. Comment
   enregistrer un remboursement à un bailleur, ou un avoir fournisseur ? Je propose une nature « Correction »
   au Lot 2.
2. **Arrondi des conversions de devises :** au centime, arrondi commercial (0,5 → au-dessus). Est-ce conforme à la
   pratique de votre comptable et de vos bailleurs ?
3. **Contrôle de la clé RIB :** il est implémenté, mais n'est encore vérifié que sur des vecteurs générés par la
   règle. Pouvez-vous confirmer sur 2 ou 3 RIB réels de l'AFMI ? Tant que ce n'est pas fait, une clé invalide reste
   un avertissement.
4. **Catégories préchargées :** seules les 5 catégories de recettes du cahier des charges (subventions,
   cotisations, dons, prestations, produits financiers) sont créées. Les natures de dépenses et le plan de comptes
   attendent le référentiel de votre expert-comptable (Q3).
5. **IA externe désactivée par défaut :** si vous utilisiez Gemini en 1.3.0, il faut cocher « Autoriser l'IA
   externe » dans les paramètres IA.
6. **Fusion des tables `projects` et `financial_transactions` de Smart Office :** elle est reportée au Lot 2,
   avec choix du compte de rattachement par l'utilisateur. Rattacher automatiquement d'anciennes transactions à
   un compte reviendrait à inventer une affectation.
7. **Mode WAL non activé :** les copies de base du Desktop (export, sauvegarde) copient un seul fichier, ce qui est
   incompatible avec le WAL. Les accès concurrents Desktop/backend s'appuient sur le verrouillage SQLite standard.
