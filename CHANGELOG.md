# Journal des modifications

## [2.0.0 — Lot 3 : Lecture intelligente des relevés] — 11/11/2026

Nouveau menu **Smart Office → Relevés bancaires**. La lecture se fait **sur le poste** (OCR Tesseract) ; l'IA n'est
qu'un recours facultatif, soumis aux paramètres de confidentialité du Lot 1.

### Ajouté
- **Import** à l'unité ou par lot : PDF natif, PDF scanné, JPG, PNG, TIFF, CSV, Excel. Les photos de plusieurs pages
  d'un même relevé peuvent être regroupées (« les pages d'un même relevé »).
- **Pipeline** (`SmartOffice/backend/tools/statements/`) :
  1. prétraitement (OpenCV) : redressement par profil de projection, débruitage, contraste local, mise à
     300 dpi ;
  2. OCR Tesseract (français), avec position et confiance de chaque mot. Les PDF natifs sont lus directement, sans
     OCR ;
  3. détection de la banque par gabarits configurables (`config/bank_templates.json` : Banque Populaire,
     Attijariwafa bank, Bank of Africa, CIH, Crédit Agricole du Maroc, Société Générale, générique) ;
  4. extraction structurée :
     - colonnes repérées sur l'en-tête, lignes commençant par une date, libellés sur plusieurs lignes ;
     - montants à milliers séparés recollés, confusions O/0 et l/1 corrigées ;
     - soldes initial et final, période, RIB (clé contrôlée) ;
     - pages multiples, en-tête répété ignoré ;
  5. **seconde lecture** si l'équilibre des soldes échoue. Un montant n'est corrigé que si une seule correction
     rétablit l'équilibre ; il est alors surligné pour vérification ;
  6. **IA en option**, seulement si la lecture OCR ne s'équilibre pas et que l'utilisateur l'a cochée. Le résultat
     n'est retenu que s'il équilibre les soldes.
- **Contrôles bloquants** : solde initial + mouvements = solde final, relevé déjà importé (même fichier, ou même
  période et même solde), continuité avec le relevé précédent. Relevé manquant signalé.
- **Écran de validation** :
  - image du relevé à côté du tableau extrait ;
  - champs à faible confiance surlignés ;
  - un clic sur une ligne la repère sur l'image ;
  - correction des dates, libellés, montants et soldes, ajout ou suppression de lignes ;
  - écart de soldes recalculé en direct. La validation reste impossible tant qu'un écart subsiste.
- **Catégorisation** :
  - règles saisies, règles apprises des corrections de l'utilisateur (la correction d'une catégorie ou d'une
    imputation est mémorisée et reproposée), puis règles de base prudentes (frais bancaires, salaires et CNSS,
    loyer, déplacements, subventions, dons, cotisations, intérêts, prestations) ;
  - projet proposé d'après les liaisons du compte ;
  - ligne budgétaire proposée si elle est unique pour ce projet et cette catégorie.
- **Anomalies** : frais bancaires inhabituels (au-delà de 3 fois la médiane de l'historique, ou de 500 MAD sans
  historique), dépassement d'une ligne budgétaire (en cumul), dépense de 1 000 MAD ou plus sans justificatif, ligne
  en double, champs peu sûrs.
- **Intégration** (après validation explicite) : une opération en **brouillon** par ligne, avec l'imputation
  proposée. Elle est à ventiler et valider dans la Trésorerie, qui applique toutes les règles de `Core/Finance`.
  - une ligne déjà comptabilisée (même montant, à ± 3 jours) n'est pas dupliquée ;
  - relancer l'intégration ne crée aucun doublon.
- **Archivage** : le fichier source est conservé, identifié par son SHA-256 et lié au relevé ; les images des pages
  sont conservées pour la relecture. Toutes les écritures sont journalisées dans `AuditEntries`.
- **Mesure de précision** :
  - générateur déterministe de relevés de test (`SmartOffice/tests/tools/statement_fixtures.py`) : 3 mises en page,
    chacune en PDF natif, en scan (inclinaison ±2°, bruit, flou, JPEG) et en photo difficile (3 à 4,5°,
    150 dpi, éclairage inégal) ;
  - banc de mesure (`tests/tools/statement_accuracy.py`) et dossier `backend/tests/fixtures/releves/` pour les vrais
    relevés, évalués automatiquement dès qu'ils sont déposés.
- 27 tests pytest (98 au total), dont un parcours complet vérifié dans un navigateur (Playwright) : import d'un scan,
  correction, contrôle de l'écart, validation, intégration.

### Résultats mesurés
| Jeu | Lignes correctes | Soldes corrects |
|---|---|---|
| Relevés **synthétiques** (6 PDF natifs, 6 scans, 3 photos difficiles) | **270/270 (100 %)** | 15/15 |
| **Vrais relevés de l'AFMI** | **non mesuré : aucun relevé fourni** | — |

Le critère d'acceptation (≥ 95 % sur `fixtures/releves/`) est automatisé, mais il ne vaut que pour des relevés que
j'ai moi-même générés. Les mises en page réelles des banques marocaines, les tampons, le papier froissé ou les
colonnes alignées différemment ne sont pas encore éprouvés.

### Points à valider
1. **Relevés réels anonymisés** : 2 à 3 par banque utilisée, à déposer dans `SmartOffice/backend/tests/fixtures/releves/`
   avec leur vérité terrain (le format est décrit dans le README du dossier). C'est la seule façon de mesurer
   réellement les 95 %.
2. **Seuils d'anomalies** : frais inhabituels (3 × la médiane, ou 500 MAD) et justificatif attendu dès 1 000 MAD.
   Ils seront paramétrables au Lot 7.
3. **Tesseract dans l'installateur Windows** : à intégrer au Lot 8, avec les langues fra et ara (environ +70 Mo).
   D'ici là, il faut l'installer à part ou renseigner `AFMI_TESSERACT`. Sans lui, seuls les PDF natifs, CSV et Excel
   sont lus.
4. **Arabe** : la reconnaissance est réglée sur le français, la langue des relevés bancaires marocains courants.
   Un relevé entièrement en arabe nécessitera un réglage du gabarit.

## [2.0.0 — Lot 2 : Banque et trésorerie] — 10/11/2026

Nouveau menu **🏦 Trésorerie** dans l'application de bureau. Toutes les règles de calcul sont dans `Core/Finance`
et testées (76 tests .NET) ; l'écran ne fait qu'appeler ces services.

### Décisions prises (points à valider du Lot 1, tranchés par délégation)
| Point | Décision |
|---|---|
| Remboursements et avoirs | Pas de nouvelle nature : une **recette au débit** (restitution à un bailleur) et une **dépense au crédit** (avoir, remboursement fournisseur) sont admises et viennent **en diminution** des recettes ou des dépenses. Case « Contre-passation » dans la saisie. |
| Arrondi des conversions | Conservé : au centime, arrondi commercial (0,5 au-dessus), sur la contre-valeur de chaque opération. |
| Clé RIB | Reste un avertissement tant qu'elle n'est pas confirmée sur de vrais RIB. |
| Natures de dépenses | 9 catégories génériques, modifiables, sans rattachement comptable imposé : personnel, achats, prestations et honoraires, déplacements, loyers, communication, frais bancaires, équipements, autres. |
| Reprise de Smart Office 1.x | Bouton dédié : transactions reprises en **brouillons** sur un compte choisi, projets manquants recréés, aucune duplication en cas de relance. |

### Ajouté
- **Comptes :**
  - création et modification, avec contrôle du RIB ;
  - typologie : fonctionnement, dédié projet, dépôt ;
  - seuil d'alerte « solde bas » ;
  - clôture, refusée si le solde n'est pas nul ;
  - solde du jour et solde consolidé en MAD.
- **Liaisons comptes ↔ projets :**
  - période de validité ;
  - clé de répartition en % ou en montant, refusée au-delà de 100 % et pour un même projet sur une période qui
    chevauche ;
  - proposition automatique du projet à la saisie d'une opération.
- **Opérations :** recette, dépense ou contre-passation, avec imputation (projet ou fonctionnement, ligne budgétaire,
  catégorie). Une opération est soit un brouillon, soit validée, et sa suppression est logique. Une opération
  rapprochée ne peut pas être supprimée.
- **Virements internes :** même devise, ou devises différentes avec le montant reçu. Ils sont exclus des recettes et
  des dépenses.
- **Budget et conventions :**
  - lignes budgétaires par projet ou pour le fonctionnement, avec le réalisé en MAD et le taux d'exécution ;
  - conventions par bailleur (taux contractuel facultatif) et échéanciers de tranches ;
  - rattachement d'une tranche à la recette qui l'encaisse ;
  - saisie des taux de change datés.
- **Rapprochement bancaire :**
  - import d'un relevé CSV de la banque : séparateur et colonnes détectés, formats français et ISO, débit/crédit ou
    montant signé, encodages UTF-8 et Windows-1252 ;
  - contrôles : solde initial + mouvements = solde final, relevé déjà importé, continuité avec le relevé précédent,
    relevé manquant ;
  - rapprochement automatique (même montant, date à ± N jours, libellé approchant). Un cas ambigu n'est **jamais**
    rapproché automatiquement ;
  - rapprochement manuel, et son annulation ;
  - **état de rapprochement** : solde bancaire rectifié, solde comptable, écart inexpliqué. Export PDF et CSV
    (Excel), nom de fichier `AFMI_EtatRapprochement_<compte>_<date>`.
- **Prévision de trésorerie** sur 3, 6 ou 12 mois, mois par mois, en MAD :
  - encaissements : tranches non reçues (une tranche en retard est comptée le premier mois) ;
  - décaissements : reste à consommer des lignes budgétaires, réparti uniformément jusqu'à la fin du projet ou de
    l'exercice ;
  - point bas et hypothèses affichés.
- **Alertes :** solde négatif ou bas, compte projet sans mouvement depuis 90 jours, écart de rapprochement, lignes non
  rapprochées, virement orphelin, tranche en retard, brouillons à valider.
- **Migration `BankingAndReconciliation` :** relevés, lignes, rapprochements, seuil d'alerte et catégories de
  dépenses. Elle est sauvegardée et réversible comme les précédentes.

### Points à valider
1. **Ventilation multiple à l'écran.** Le moteur sait répartir une opération sur plusieurs projets (clés de
   répartition), mais la saisie à l'écran ne propose qu'une imputation par opération. Pour l'instant, il faut
   saisir une opération par projet. Je propose la saisie multi-lignes au Lot 5, avec la répartition des frais de
   fonctionnement.
2. **Hypothèse de prévision :** reste à consommer étalé uniformément jusqu'à la fin du projet. Si vos plans de
   décaissement sont plus précis (par trimestre, par activité), on pourra les saisir plus tard.
3. **Rapprochement un pour un :** une remise de plusieurs chèques en une seule ligne bancaire n'est pas encore gérée.
4. **Paramètres par défaut :** tolérance de date de 3 jours, compte projet « inactif » après 90 jours. Ils seront
   modifiables au Lot 7.
5. **Import CSV :** les soldes initial et final sont à saisir, car les exports bancaires ne les contiennent souvent
   pas. Au Lot 3, ils seront lus sur le relevé PDF ou scanné.
6. **Écran non vérifié visuellement.** Il compile, et toutes ses liaisons de données correspondent à une propriété
   existante (vérifié par un script), mais je ne peux pas lancer WPF dans mon environnement. **Merci de l'essayer
   sous Windows** et de me signaler tout problème d'affichage ou de saisie.

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
