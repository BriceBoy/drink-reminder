# drink-reminder

**Water Reminder** est un utilitaire Windows 10/11, en français, qui rappelle de
boire de l'eau. Il fonctionne hors ligne, sans console ni fenêtre permanente.
L'icône en forme de goutte reste dans la zone de notification.

## Installation rapide

1. Exécutez `dist\WaterReminderSetup.exe`.
2. Conservez le démarrage automatique si vous le souhaitez.
3. Lancez Water Reminder à la fin de l'installation.
4. L'assistant demande votre prénom et l'intervalle en minutes (45 par défaut).
   Cliquez sur **Commencer**. Aucun droit administrateur n'est nécessaire.

Les fichiers compilés sont également inclus dans `bin` dans l'archive
`dist\WaterReminder-project.zip`. L'exécutable seul peut être lancé sans installer
Python ; l'installateur est recommandé pour la désinstallation et les raccourcis.
Les exécutables ne sont pas signés : Windows SmartScreen peut demander une
confirmation. Ne contournez pas une politique de sécurité de votre organisation.

## Utilisation

Clic droit sur la goutte (éventuellement sous la flèche des icônes masquées) :

- **Paramètres** : prénom, intervalle et démarrage avec Windows.
- **Modifier mon prénom / Modifier l'intervalle des rappels** : ouvre les paramètres
  avec le champ correspondant sélectionné.
- **Mettre en pause / Reprendre** : suspend et restaure le temps restant.
- **Afficher le prochain rappel** : indique le temps restant.
- **Tester une notification** : envoie immédiatement un vrai rappel et relance le
  délai normal ; ses boutons fonctionnent comme ceux d'un rappel automatique.
- **Modifier les messages** : ouvre votre fichier JSON avec son application associée.
- **Quitter l'application** : retire les notifications et arrête les rappels.

Le clic principal sur la goutte ouvre aussi les paramètres.

### Règles des rappels

| Événement | Comportement |
|---|---|
| « J'ai bu ! » | Ferme le rappel et repart pour l'intervalle configuré, depuis le clic traité. |
| « Rappeler dans 10 min » | Ferme le rappel et repart pour **600 secondes**, sans changer l'intervalle habituel. |
| Rappel ignoré ou fermé | Un nouveau rappel est envoyé après l'intervalle habituel. La disparition du bandeau n'est pas un acquittement. |
| Nouvel intervalle validé | Annule l'ancien rappel/report et repart du moment de validation. En pause, le nouveau délai attend la reprise. |
| Nouveau prénom validé | Retire l'ancien rappel, conserve le délai et personnalise les prochaines notifications. |
| Pause | Retire le rappel et fige le temps restant. |
| Redémarrage de l'application | Repart pour un intervalle complet ; pause, report et compte à rebours ne persistent pas. |
| Retour de veille | Un seul rappel si le délai est dépassé, jamais une rafale de rappels manqués. |

Une action périmée ou déjà traitée ne peut pas modifier un nouveau compte à
rebours. Les actions passent par la même boucle d'événements que les paramètres.
La précision à l'écran dépend de Windows ; la boucle vérifie le délai toutes
les 250 ms et peut être retardée par une boîte de dialogue ou une machine occupée.

## Messages personnalisables

Paramètres et messages sont dans **`%APPDATA%\WaterReminder`**, jamais dans le
dossier d'installation :

- `settings.json` : prénom, intervalle (entier de 1 à 1440), démarrage et état de
  l'assistant.
- `messages.json` : liste éditable, relue à **chaque notification**, même après report.
- `water-reminder.log` : diagnostic, avec rotation limitée à trois fichiers.
- `water.ico` : icône persistante pour l'identité Windows.

Exemple de `messages.json` :

```json
{
  "messages": [
    "Bonjour {name}, une petite pause pour boire ?",
    "{name}, quelques gorgées d'eau et on repart !"
  ]
}
```

`{name}` est le seul marqueur accepté ; `{{` et `}}` permettent d'afficher des
accolades. Le choix est aléatoire,
sans répétition immédiate lorsque plusieurs textes distincts existent. Les
messages doivent contenir de 1 à 500 caractères ; la liste de 1 à 1000 entrées.

En cas de fichier absent, illisible, vide ou invalide, un avertissement et une
entrée de journal expliquent le retour aux messages intégrés. Un même problème
n'affiche pas un avertissement à chaque rappel. Les paramètres corrompus sont
conservés dans `settings.corrupt-<identifiant>.json` et l'assistant est réouvert.
Une erreur d'accès aux paramètres n'est pas masquée par une configuration fictive.
Les sauvegardes utilisent un fichier temporaire puis un remplacement atomique.

## Choix techniques et limites

- **Python 3.12 x64**, **Tkinter/ttk** fourni avec Python : interface légère.
- **pystray 0.19.5** : zone de notification Win32, dans un thread dédié. Tkinter
  reste sur le thread principal ; une file transfère les événements Windows.
  Le backend Windows est utilisable hors du thread principal selon sa documentation.
- **Windows-Toasts 1.3.1** avec **PyWinRT 3.2.1** : vrais toasts Windows avec image
  locale, deux boutons et événements d'activation. La documentation et les
  métadonnées annoncent Windows 10/11 et Python 3.12. Une identité AUMID
  `BriceBoy.WaterReminder` est enregistrée dans HKCU afin de prendre en charge
  notamment les actions depuis le centre de notifications. L'objet SDK est
  conservé pour fermer explicitement le bandeau, en plus du nettoyage de l'historique.
- **Pillow 11.3.0** : images originales générées localement, pas d'image téléchargée.
- **PyInstaller 6.16.0** : exécutable unique, sans console. Les ressources et
  modules WinRT sont explicitement collectés.
- **Inno Setup 6** : installation x64 par utilisateur, identité stable pour les
  mises à jour, raccourcis, démarrage et désinstallation.

Il n'y a **aucune fausse notification constituée d'une fenêtre personnalisée**.
Le bandeau et le centre de notifications sont ceux de Windows.

**Limites importantes :**

- L'application doit rester active pour recevoir les boutons. Elle ne constitue
  ni un service Windows ni un serveur COM capable de redémarrer le programme
  depuis une notification après sa fermeture. Les rappels sont retirés au départ
  et à l'arrêt ; les anciens identifiants sont invalidés.
- Windows décide de l'affichage, de la durée du bandeau et de l'expansion des
  boutons. Ne pas déranger, l'assistant de concentration et les stratégies
  d'entreprise peuvent bloquer ou masquer les rappels. Le statut désactivé de
  l'application est vérifié après l'envoi (Windows initialise ce statut à la
  première notification). Les erreurs mettent les rappels en pause et sont signalées.
- Aucun rappel garanti PC éteint, en veille profonde, avant ouverture de session
  ou si les notifications sont bloquées. Aucun accès réseau en fonctionnement normal.
- Une instance par session Windows, protégée par un mutex Win32 (pas un fichier
  verrou susceptible de rester après un crash).
- Le démarrage automatique en développement référence votre environnement virtuel :
  ne déplacez pas le projet ou désactivez cette option avant de supprimer `.venv`.
- Le packaging fourni cible Windows x64. Une version ARM64 native demanderait un
  build et une validation séparés.

Sources techniques consultées :
[Windows-Toasts](https://windows-toasts.readthedocs.io/en/stable/),
[boutons](https://windows-toasts.readthedocs.io/en/stable/interactable.html),
[AUMID](https://windows-toasts.readthedocs.io/en/stable/custom_aumid.html),
[pystray](https://pystray.readthedocs.io/en/latest/usage.html),
[Inno Setup](https://jrsoftware.org/isinfo.php).
Inno Setup exige une licence pour certains usages commerciaux : consultez ses
conditions avant une distribution commerciale.

## Développement : commandes PowerShell

Prérequis : **Windows 10/11 x64**, Python **3.12 x64** avec Tcl/Tk (option de
l'installateur Python). La compilation doit être exécutée **sur Windows**.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe scripts\generate_assets.py
.\.venv\Scripts\python.exe -m water_reminder
```

Pour lancer sans console en développement :

```powershell
Start-Process .\.venv\Scripts\pythonw.exe -ArgumentList ".\run.pyw"
```

Pour reproduire les versions exactes de la compilation de livraison, remplacez
l'installation des dépendances par :

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
```

Tests et contrôle du code :

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
```

Après compilation, le test optionnel ci-dessous ouvre réellement l'assistant
de l'exécutable dans un profil temporaire, puis le ferme sans enregistrer :

```powershell
$env:WATER_REMINDER_EXE = (Resolve-Path .\dist\WaterReminder.exe).Path
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
Remove-Item Env:WATER_REMINDER_EXE
```

Les tests couvrent les onze points du prompt, avec horloge simulée (aucune
attente de 45 minutes), vrai mutex entre processus Windows, interface Tkinter
et XML natif. Les tests de notifications unitaires simulent la livraison :
**ils ne prouvent pas le fonctionnement des vrais boutons Windows**.

Pour tester les boutons sur votre bureau interactif :

```powershell
.\.venv\Scripts\python.exe scripts\test_native.py
```

Cliquez sur **J'ai bu !**, puis **Rappeler dans 10 min** (120 secondes maximum
pour chaque action). Le script vérifie le callback Windows et le délai réel du
moteur, sans attendre son expiration. Il utilise une identité de test distincte,
sans toucher au démarrage automatique ni à vos paramètres. Les erreurs
d'intégration font échouer le script ; il n'annonce pas un succès fictif.
Testez également les boutons après disparition du bandeau, depuis le centre.

## Compilation et archive

Installez [Inno Setup 6](https://jrsoftware.org/isdl.php), puis :

```powershell
# Exécutable seul :
powershell -ExecutionPolicy Bypass -File .\scripts\build.ps1

# Exécutable et installateur :
powershell -ExecutionPolicy Bypass -File .\scripts\build.ps1 -Installer

# Archive sources + exécutables disponibles :
powershell -ExecutionPolicy Bypass -File .\scripts\package.ps1
```

Le script recherche `ISCC.exe` dans le PATH, puis dans
`C:\Program Files (x86)\Inno Setup 6`. Si Inno Setup est ailleurs, ajoutez son
dossier au PATH de la session. Il exécute les tests et Ruff avant la compilation.
Ne contournez pas les restrictions PowerShell de votre organisation.

Commandes élémentaires équivalentes :

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm WaterReminder.spec
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\WaterReminder.iss
```

Sorties : `dist\WaterReminder.exe`, `dist\WaterReminderSetup.exe` et
`dist\WaterReminder-project.zip`. Aucun Python requis sur le poste destinataire.
Le premier démarrage d'un exécutable unique peut prendre quelques secondes.

## Arborescence

```text
drink-reminder\
  README.md
  prompt.txt
  prompt-notification-messages.txt
  pyproject.toml
  requirements.txt
  requirements-dev.txt
  requirements-lock.txt
  WaterReminder.spec
  run.pyw
  water_reminder\
    __init__.py
    __main__.py
    app.py              # orchestration, événements, journal
    config.py           # validation et sauvegarde atomique
    messages.py         # lecture et sélection des messages
    reminders.py        # moteur avec horloge injectable
    notifications.py    # notifications natives et actions
    paths.py
    ui.py               # assistant et paramètres
    windows.py          # mutex, AUMID, démarrage utilisateur
    assets\
      water.ico
      water.png
      hydration.png
      messages.json
  installer\
    WaterReminder.iss
  scripts\
    build.ps1
    generate_assets.py
    package.ps1
    test_native.py
  tests\
    test_core.py
    test_frozen.py
    test_windows.py
  docs\
    INSTALLATION.md
    VALIDATION.md
  dist\                 # résultats générés, non versionnés
```

Guides : [installation, configuration et désinstallation](docs/INSTALLATION.md),
[checklist et état des vérifications](docs/VALIDATION.md).
