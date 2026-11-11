# Mises à jour automatiques (depuis la version 2.2.0)

## Fonctionnement

1. **Publication.** Le workflow GitHub « Installateur Windows » construit l'installateur, calcule son empreinte
   SHA-256 et écrit `latest.json` (`installer/make_manifest.py`). Il signe ce manifeste avec la clé privée
   `UPDATE_SIGNING_KEY`, puis crée la version `vX.Y.Z` dans le dépôt **public** `saidsocial5-droid/afmi-smart-admin-releases`.
   La publication a lieu :
   - à chaque fusion dans `main` ;
   - avec l'étiquette `publier` sur une pull request.

   Une version déjà publiée n'est jamais remplacée. Pour publier, augmentez `VERSION` dans `build_installer.bat` et
   ajoutez sa section au `CHANGELOG.md` (un test le vérifie).
2. **Recherche.** Au démarrage, l'application lit `releases/latest/download/latest.json` et sa signature
   (`Desktop/Services/UpdateService.cs`). Elle ne fait rien en mode démonstration ni si Paramètres › Mises à jour
   le désactive.
3. **Vérifications** (`Core/Services/UpdateVerifier.cs`, testées) :
   - la signature est valide pour la clé publique intégrée ;
   - le produit est « AFMI Smart Admin » ;
   - l'adresse de téléchargement est celle du dépôt de publication, en HTTPS, et désigne un `.exe` ;
   - la version est strictement plus récente ;
   - la taille et le SHA-256 du fichier téléchargé correspondent.
4. **Installation.** L'application fait d'abord une sauvegarde de la base (`Backups\afmi_backup_…_avant_mise_a_jour_X.db`).
   Elle lance ensuite `Setup.exe /SILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS` et se ferme.
   L'installateur remplace les fichiers et relance l'application (`[Run] … Check: WizardSilent`). Au redémarrage,
   les migrations s'appliquent avec leur sauvegarde automatique habituelle.

Les données (`%LocalAppData%`) ne sont jamais touchées par l'installateur.

## Mise en place (une seule fois, par le propriétaire du dépôt)

1. **Dépôt de publication.** Sur GitHub : *New repository* → nom `afmi-smart-admin-releases`, **Public**, cochez
   *Add a README file*. Il ne contiendra que les installateurs ; le code reste dans le dépôt privé.
2. **Jeton `RELEASES_TOKEN`.**
   - Ouvrez Settings (de votre compte) › Developer settings › Personal access tokens › *Fine-grained tokens* ›
     *Generate new token*.
   - *Repository access* : **Only select repositories** → `afmi-smart-admin-releases`.
   - *Permissions* › Repository › **Contents : Read and write**.
   - Choisissez une expiration (par exemple un an) et notez-la : il faudra renouveler le jeton.
   - Copiez le jeton, puis, dans le dépôt privé `afmi-smart-admin` : Settings › Secrets and variables › Actions ›
     *New repository secret* → nom `RELEASES_TOKEN`, valeur = le jeton.
3. **Clé `UPDATE_SIGNING_KEY`.** Même écran : *New repository secret*, nom `UPDATE_SIGNING_KEY`. La valeur est le
   contenu complet du fichier `update_signing_key.pem` fourni, lignes `-----BEGIN…` et `-----END…` comprises.
   - Supprimez ensuite le fichier de votre ordinateur, ou gardez-en une copie hors ligne (clé USB au coffre).
   - Ne la mettez jamais dans le dépôt.
   - Le workflow vérifie que cette clé correspond bien à la clé publique de l'application avant toute publication.
4. **Première publication.** Ajoutez l'étiquette `publier` à la pull request (ou fusionnez-la dans `main`).
   Vérifiez ensuite que la version apparaît dans l'onglet *Releases* du dépôt de publication.
5. **Installez la 2.2.0 à la main**, une seule fois. Les versions suivantes seront proposées automatiquement.

## Sécurité et confidentialité

| Risque | Mesure |
|---|---|
| Fausse version déposée dans le dépôt de publication (jeton volé) | Refusée : sans la clé privée, la signature du manifeste est invalide. |
| Installateur remplacé ou altéré pendant le téléchargement | Refusé : taille et SHA-256 vérifiés juste après le téléchargement et juste avant l'exécution. |
| Redirection vers un autre site | Refusée : seule l'adresse `https://github.com/saidsocial5-droid/afmi-smart-admin-releases/releases/download/…` est acceptée. |
| Retour à une ancienne version vulnérable | Refusé : seule une version strictement plus récente est proposée. |
| Perte de données | Sauvegarde de la base avant l'installation, puis sauvegarde avant migration au redémarrage. |
| Fuite d'information | La recherche est une simple lecture d'un fichier public : aucune donnée, aucun identifiant envoyés. |
| Clé privée compromise | Créer une nouvelle paire de clés, mettre la nouvelle clé publique dans `UpdateVerifier.PublicKeyPem` et publier une version installée à la main. |

**Limite connue.** L'installateur n'est pas signé Authenticode, ce qui demande un certificat de signature de code
payant. Windows SmartScreen peut donc l'avertir lors d'une installation manuelle. La mise à jour automatique n'est pas
concernée, car elle vérifie sa propre signature.
