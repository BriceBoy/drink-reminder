# Installation et configuration

## Première installation

1. Lancez `WaterReminderSetup.exe` depuis l'archive (`bin`) ou le dossier `dist`.
2. L'installation se fait dans `%LOCALAPPDATA%\Programs\WaterReminder`, pour le
   compte Windows courant, sans élévation.
3. L'option de démarrage automatique est cochée par défaut ; le raccourci Bureau
   est facultatif.
4. Laissez le lancement final sélectionné. L'assistant intégré demande le prénom
   (1 à 80 caractères) et l'intervalle (entier de 1 à 1440 minutes).
5. Cliquez sur **Commencer**. L'icône apparaît dans la zone de notification.
   La fenêtre de configuration disparaît ; aucun écran principal ne reste ouvert.

Si vous annulez l'assistant, l'application quitte, sans commencer les rappels.
L'assistant réapparaît au prochain lancement. Si vous désélectionnez le lancement
final, ouvrez le raccourci du menu Démarrer pour compléter la configuration.

Les paramètres sont créés dans `%APPDATA%\WaterReminder`. L'installateur écrit
uniquement les valeurs initiales et le choix de démarrage si la configuration
n'existe pas. Le prénom et l'intervalle sont saisis au premier lancement plutôt
que dans des pages d'installateur : l'interface de validation est ainsi la même
à la première utilisation et lors des modifications.

## Démarrage automatique

La valeur `WaterReminder` dans
`HKCU\Software\Microsoft\Windows\CurrentVersion\Run` référence l'exécutable
installé. Les chemins avec espaces sont correctement entre guillemets.
Modifiez l'option dans **Paramètres** ; elle est appliquée et sauvegardée à la
validation. Une mise à jour ne remplace pas votre fichier de configuration.

Le gestionnaire des tâches Windows peut désactiver une entrée de démarrage
indépendamment du programme. Si l'application ne part pas à la connexion,
vérifiez également **Paramètres Windows > Applications > Démarrage**.

## Mise à jour / réinstallation

1. Quittez Water Reminder depuis son menu avant d'exécuter le nouvel installateur.
2. Réutilisez le même dossier. L'identifiant de l'installateur est stable.
3. Les fichiers de programme sont remplacés, les paramètres et messages ne sont
   pas écrasés.
4. Lancez l'application à la fin : elle réapplique votre préférence de démarrage,
   particulièrement après une désinstallation suivie d'une réinstallation.

L'installateur vérifie le mutex pour éviter de remplacer un programme actif.
Le raccourci du menu Démarrer conserve le même nom, sans créer plusieurs éditions.

## Désinstallation

Quittez l'application puis utilisez **Applications installées > Water Reminder >
Désinstaller**. L'exécutable, les raccourcis installés, l'identité AUMID et la clé
de démarrage sont retirés.

Les paramètres, messages et journaux dans `%APPDATA%\WaterReminder` sont
**conservés**, avec un message d'information. Si vous voulez les effacer
définitivement, supprimez explicitement ce seul dossier après désinstallation.
En désinstallation silencieuse, le dossier est aussi conservé, sans dialogue.

## Dépannage

- **Déjà lancé** : cherchez la goutte dans les icônes masquées. Une seconde
  instance n'est pas créée.
- **Aucun rappel** : vérifiez la pause, le temps restant, les autorisations Windows
  pour Water Reminder et le mode Ne pas déranger/assistant de concentration.
- **Erreur de notification** : corrigez les paramètres Windows puis reprenez les
  rappels. Consultez `%APPDATA%\WaterReminder\water-reminder.log`.
- **Message JSON invalide** : corrigez le fichier indiqué par l'avertissement ;
  il sera relu au prochain rappel. Les messages de secours assurent la continuité.
- **Paramètres corrompus** : une copie nommée `settings.corrupt-...json` est
  conservée et l'assistant permet de repartir proprement.
- **Fichier inaccessible** : vérifiez les permissions du dossier utilisateur ;
  l'application ne masque pas un échec de sauvegarde.
- **SmartScreen/antivirus** : les binaires sont non signés et PyInstaller peut
  attirer des avertissements. Faites vérifier le programme selon votre politique
  informatique, ou compilez depuis les sources.

Ne modifiez pas `settings.json` pendant que le programme fonctionne ; utilisez
l'interface. En revanche `messages.json` est conçu pour être modifié à chaud.
