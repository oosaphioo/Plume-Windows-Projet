# Plume — votre traitement de texte

Première version pour Windows 10/11 64 bits : courriers, textes, histoires et RP.
Interface française, fonctionnement local sans compte et sans abonnement.
Nom provisoire : Plume. Version 0.2 — interface modernisée.

## Mettre à jour depuis la version 0.1

Remplacez les fichiers de votre dossier de projet par ceux de cette archive,
validez les modifications dans Visual Studio Code et synchronisez avec GitHub.
Téléchargez le nouvel installateur dans Actions après la coche verte.
Fermez Plume avant de réinstaller au même endroit. Vos fichiers .plume
restent compatibles et sont conservés.

La version 0.2 apporte une feuille centrée, une barre d’outils avec icônes,
un panneau de chapitres plus léger, des boutons thème/concentration directs
et des menus déroulants dont le contraste est corrigé.

## Ce qui fonctionne

- Polices, tailles, gras, italique, souligné, couleurs et titres.
- Alignement, listes à puces et numérotées.
- Insertion d’images intégrées au document, tableaux simples et liens.
- Chapitres : ajouter, renommer, réordonner et supprimer.
- Compteur de mots par chapitre et pour le document entier.
- Recherche/remplacement dans le chapitre ouvert ; annuler/rétablir.
- Thèmes clair/sombre, zoom et concentration avec F11.
- Documents .plume : texte mis en forme, images et chapitres.
- Import de texte UTF-8 et import/export Word .docx simplifiés.
- Export texte, PDF, aperçu et impression A4 avec marges de 20 mm.
- Copie de secours locale toutes les 15 secondes en cas de modifications.

## Obtenir l’installateur avec GitHub (sans installer Python sur votre PC)

1. Décompressez l’archive et ouvrez le dossier **Plume** dans Visual Studio Code.
2. Publiez **le contenu de ce dossier** dans un nouveau dépôt GitHub. `main.py`,
   `requirements.txt` et `.github` doivent être à la racine du dépôt.
   Vous pouvez utiliser un dépôt privé. Aucune clé ni variable secrète nécessaire.
3. Ouvrez l’onglet **Actions** du dépôt. La compilation démarre après l’envoi
   sur la branche main ou master. Vous pouvez aussi choisir
   **Construire Plume pour Windows → Run workflow**.
4. Lorsque la compilation a une coche verte, ouvrez son résultat et descendez
   jusqu’à **Artifacts**. Téléchargez **Plume-Installation-Windows**.
5. Décompressez ce téléchargement et lancez **Plume-Installation-Windows.exe**.
6. Suivez les étapes en français ; ouvrez Plume depuis le menu Démarrer.

Le workflow est préparé ; l’installateur Windows n’a pas été compilé dans
l’environnement Linux où cette première version a été créée. Les tests du
moteur, des formats et de l’interface ont été exécutés sous Linux avec Qt.
Les mêmes tests s’exécutent sous Windows avant la compilation GitHub.
L’installateur n’est pas signé par un certificat d’éditeur.

Une version portable est aussi fournie comme artifact. Décompressez-la puis
ouvrez Plume.exe en conservant tous les fichiers voisins et le dossier _internal.

## Premier document

Écrivez, puis utilisez **Fichier → Enregistrer** (Ctrl+S). Choisissez un fichier
`.plume`, le format qui conserve tout votre projet. Pour une histoire, ajoutez
vos chapitres dans la colonne de gauche. Pour un courrier, gardez un seul chapitre.

Utilisez **Fichier → Aperçu avant impression** pour contrôler les pages A4.
Chaque chapitre commence sur une nouvelle page dans le PDF et à l’impression.
Les titres de chapitres servent à la navigation ; ils ne sont pas ajoutés
au texte exporté. Écrivez les titres souhaités directement dans le contenu.
Le thème sombre modifie l’interface ; la feuille reste blanche pour respecter
les couleurs destinées à l’impression.

## Sauvegarde de secours

Ctrl+S enregistre votre fichier. La copie automatique est distincte : elle se
trouve dans les données locales de l’application et sert à reprendre après
une interruption. Au prochain lancement, Plume propose de la restaurer.
Après restauration, enregistrez-la dans un fichier .plume.
La copie peut perdre les 15 dernières secondes et ne remplace pas une sauvegarde
sur un autre support. Une seule instance de Plume peut être ouverte à la fois.

## Limites de cette version

- L’éditeur est continu : pas de feuilles A4 séparées pendant la saisie.
- Pas encore de correction orthographique, suivi des modifications,
  commentaires, modèles de CV, en-têtes, pieds de page ou numéros de page.
- Word : styles usuels, paragraphes, images et tableaux simples. Ne sont pas
  garantis : listes lors de l’import, cellules fusionnées, liens, sauts de page,
  sections, sommaires, objets flottants, commentaires et disposition complexe.
  Le fichier Word d’origine n’est jamais remplacé à l’import ; gardez-le.
- Les images de fichiers et du presse-papiers sont intégrées. Les images dans
  du HTML collé sont retirées : utilisez **Image…** pour les ajouter.
- Changer de chapitre réinitialise l’historique annuler/rétablir de l’éditeur.
- Recherche/remplacement : dans le chapitre ouvert, sensible à la casse pour
  le bouton Remplacer ; rechercher et tout remplacer suivent les règles Qt.

## Lancer directement depuis les sources

Installez Python 3.12 sur Windows avec le lanceur `py`, puis double-cliquez
sur `Lancer-Plume.cmd`. La première installation des dépendances nécessite
une connexion ; le logiciel fonctionne ensuite hors connexion.

Pour construire localement : `Construire-Windows.cmd` (Python 3.12 requis ;
Inno Setup 6 facultatif pour générer l’installateur).

Sur Linux/macOS, pour développer :

```sh
python -m venv .venv
# Activez votre environnement virtuel, puis :
python -m pip install -r requirements.txt
python main.py
```

## Tests

```sh
python -m unittest discover -s tests -v
```

Tests : sauvegarde/relecture avec chapitres et image intégrée, récupération,
fichier invalide, export PDF, export/import Word avec styles/tableau/image,
et lancement de l’interface. Les tests génèrent `apercu.png`.
