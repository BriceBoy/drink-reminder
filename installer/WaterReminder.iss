#define AppVersion "1.0.0"

[Setup]
AppId={{7E8F5C46-64A8-4CD7-9523-7C2F3C1B65D0}
AppName=Water Reminder
AppVersion={#AppVersion}
AppPublisher=BriceBoy
DefaultDirName={localappdata}\Programs\WaterReminder
DefaultGroupName=Water Reminder
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist
OutputBaseFilename=WaterReminderSetup
SetupIconFile=..\water_reminder\assets\water.ico
UninstallDisplayIcon={app}\WaterReminder.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
AppMutex=Local\BriceBoy.WaterReminder
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "autostart"; Description: "Démarrer Water Reminder à l'ouverture de session"; Flags: checkedonce
Name: "desktopicon"; Description: "Créer un raccourci sur le Bureau"; Flags: unchecked

[Files]
Source: "..\dist\WaterReminder.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\water_reminder\assets\water.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Water Reminder"; Filename: "{app}\WaterReminder.exe"
Name: "{autodesktop}\Water Reminder"; Filename: "{app}\WaterReminder.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Classes\AppUserModelId\BriceBoy.WaterReminder"; ValueType: string; ValueName: "DisplayName"; ValueData: "Water Reminder"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\AppUserModelId\BriceBoy.WaterReminder"; ValueType: string; ValueName: "IconUri"; ValueData: "{app}\water.ico"
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "WaterReminder"; ValueData: """{app}\WaterReminder.exe"""; Tasks: autostart; Check: NeedsInitialConfig; Flags: uninsdeletevalue

[Run]
Filename: "{app}\WaterReminder.exe"; Description: "Lancer Water Reminder et configurer les rappels"; Flags: nowait postinstall skipifsilent

[Code]
function NeedsInitialConfig: Boolean;
begin
  Result := not FileExists(ExpandConstant('{userappdata}\WaterReminder\settings.json'));
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigPath, InitialConfig: String;
begin
  if CurStep = ssPostInstall then
  begin
    ConfigPath := ExpandConstant('{userappdata}\WaterReminder\settings.json');
    if not FileExists(ConfigPath) then
    begin
      if WizardIsTaskSelected('autostart') then
        InitialConfig := '{"name":"Vous","interval_minutes":45,"autostart":true,"setup_complete":false}'
      else
        InitialConfig := '{"name":"Vous","interval_minutes":45,"autostart":false,"setup_complete":false}';
      if not ForceDirectories(ExtractFileDir(ConfigPath)) then
        RaiseException('Impossible de créer le dossier des paramètres.');
      if not SaveStringToFile(ConfigPath, InitialConfig, False) then
        RaiseException('Impossible d''enregistrer les paramètres initiaux.');
    end;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
    if not UninstallSilent then
      MsgBox('Les paramètres et messages personnels ont été conservés dans ' +
        ExpandConstant('{userappdata}\WaterReminder') +
        '. Vous pouvez supprimer ce dossier manuellement si vous ne souhaitez plus les garder.',
        mbInformation, MB_OK);
end;
