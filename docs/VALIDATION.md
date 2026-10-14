# Vérification et recette Windows

## Vérifications automatisées

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe scripts\test_native.py
```

Après compilation, activez aussi la vérification du binaire :

```powershell
$env:WATER_REMINDER_EXE = (Resolve-Path .\dist\WaterReminder.exe).Path
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
Remove-Item Env:WATER_REMINDER_EXE
```

Sans cette variable, le test du binaire est explicitement ignoré. Ce test ouvre
le vrai assistant compilé, puis l'annule, avec un dossier APPDATA temporaire.
Il restaure l'identité Windows précédente et n'active pas le démarrage automatique.

La suite standard utilise une horloge simulée et ne déclenche pas de notifications
sur le bureau. Elle teste :

- création des valeurs par défaut, sauvegarde, rechargement et redémarrage ;
- validations, configuration corrompue préservée, refus d'accès non masqué ;
- remplacement atomique et nettoyage d'un fichier temporaire après erreur ;
- messages avec prénom, relecture, hasard injecté, non-répétition et secours ;
- seuil exact de l'intervalle, report de **600 secondes**, reports successifs ;
- actions périmées/doubles, rappel ignoré, pause/reprise, changement de paramètres ;
- retour de veille sans rafale, arrêt puis redémarrage pour un délai complet ;
- mutex **réel entre deux processus Windows**, puis libération ;
- interface Tkinter : validation, sauvegarde, annulation ;
- resources graphiques décodables, XML natif avec image et deux boutons ;
- erreurs explicites si Windows désactive les notifications.

Le script `test_native.py` est une recette interactive séparée. Les boutons doivent
être **cliqués dans Windows**, pas appelés par un mock Python. Il affiche des
résultats `PASS` uniquement si Windows délivre les callbacks et si les délais
mesurés correspondent à 2700 et 600 secondes. Un délai sans clic est un échec.

## Checklist à effectuer sur Windows 10 ET Windows 11

### Installation et démarrage

- [ ] Installer sans élévation ni Python installé.
- [ ] Vérifier les raccourcis et la présence dans Applications installées.
- [ ] Configurer prénom et intervalle via le premier assistant.
- [ ] Annuler une première configuration : aucun rappel, assistant au relancement.
- [ ] Vérifier absence de console et présence de l'icône, même sans notification.
- [ ] Lancer une deuxième fois : pas de deuxième processus applicatif actif.
- [ ] Redémarrer Windows : une instance démarre et utilise les paramètres enregistrés.
- [ ] Désactiver le démarrage depuis l'interface, fermer puis rouvrir la session.

### Notifications natives

- [ ] Utiliser **Tester une notification** et contrôler prénom, illustration,
  titre et les deux boutons (développer la notification si nécessaire).
- [ ] Exécuter `scripts\test_native.py` : cliquer « J'ai bu ! », puis « Rappeler
  dans 10 min » ; les deux lignes PASS doivent être présentes.
- [ ] Refaire la recette en laissant le bandeau disparaître, puis cliquer les
  boutons depuis le centre de notifications (Win+N sous Windows 11).
- [ ] Vérifier disparition du rappel après chaque action.
- [ ] Régler 1 minute pour vérifier un déclenchement automatique sans clic.
- [ ] Reporter, puis vérifier le temps restant proche de **10 minutes**, quelle
  que soit la durée normale ; tester un second report.
- [ ] Fermer un rappel avec X : le délai habituel continue, pas de boucle immédiate.
- [ ] Ignorer plusieurs rappels : un seul rappel applicatif dans le centre.
- [ ] Changer l'intervalle pendant un report : le nouveau délai remplace le report.
- [ ] Changer le prénom : le rappel ancien est retiré ; le prochain utilise le nouveau.
- [ ] Pause : aucun rappel ; reprise : le temps figé reprend.
- [ ] Mettre le PC en veille, revenir après échéance : au plus un rappel immédiat.
- [ ] Désactiver les notifications Windows : erreur signalée, rappels en pause.
- [ ] Activer Ne pas déranger : documenter le comportement Windows (bandeau non garanti).

### Messages, mises à jour et arrêt

- [ ] Ajouter deux messages différents dans `%APPDATA%\WaterReminder\messages.json`
  avec `{name}`, puis tester plusieurs rappels sans recompiler.
- [ ] Vérifier absence de répétition consécutive et prise en compte des modifications.
- [ ] Tester un JSON invalide, vide ou supprimé : avertissement puis messages intégrés.
- [ ] Fermer, relancer : prénom et intervalle conservés, délai complet redémarré.
- [ ] Réinstaller par-dessus : configuration et messages inchangés.
- [ ] Désinstaller après avoir quitté : fichiers, raccourcis et Run retirés ;
  données utilisateur conservées avec avertissement.
- [ ] Réinstaller, lancer à la fin : configuration conservée, préférence de
  démarrage réappliquée.
- [ ] Tester le binaire compilé sur un autre poste sans Python.

## État de la validation de livraison

La livraison est construite sur **Windows 11 x64 (build 26200), Python 3.12.9**.

- **36 tests automatisés exécutés : succès**, dont l'ouverture et la fermeture
  du vrai assistant de l'exécutable PyInstaller, la vraie icône de zone de
  notification et le routage des événements de son menu.
- **Ruff (analyse et formatage) : succès.**
- **PyInstaller : compilation de l'exécutable autonome réussie.**
- **Inno Setup 6.7.3 : compilation de l'installateur réussie.**
- L'envoi d'un vrai toast avec une identité distincte a été accepté par WinRT ;
  le statut Windows a retourné `ENABLED` après l'envoi. Un contrôle supplémentaire
  a trouvé exactement un rappel avec deux boutons dans l'historique Windows,
  puis zéro après fermeture explicite du bandeau et nettoyage de l'historique.
- **Les vrais clics des deux boutons ne sont pas validés dans cette session** :
  la recette interactive a expiré sans activation. L'envoi accepté n'est pas
  présenté comme une preuve d'affichage ou de callbacks fonctionnels.
- Windows 10, le redémarrage de session, la veille, l'installation/désinstallation
  sur un autre ordinateur et la vérification visuelle restent à effectuer.

Une compilation réussie ne remplace pas la recette d'installation.
