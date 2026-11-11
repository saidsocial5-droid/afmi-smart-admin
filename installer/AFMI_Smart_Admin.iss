; Installateur Windows d'AFMI Smart Admin (Inno Setup 6+)
; Construit par build_installer.bat, qui prépare build\app (WPF publié + backend Smart Office compilé).

#define AppName "AFMI Smart Admin"
#ifndef AppVersion
  #define AppVersion "2.0.0"
#endif
#define AppPublisher "Association Forêt Modèle d'Ifrane (AFMI)"
#define AppExe "AFMI Smart Admin.exe"

[Setup]
AppId={{6F1B7C2E-3A9D-4E8B-9C21-AF41D0E5B7A3}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
; Installation possible sans droits administrateur (dans le profil utilisateur), ou pour tous avec élévation
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\build\installer
OutputBaseFilename=AFMI_Smart_Admin_Setup_{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#AppExe}
CloseApplications=yes
RestartApplications=no
MinVersion=10.0.17763

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\build\app\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Police arabe Amiri (SIL OFL 1.1) pour les rapports en arabe ; installée pour l'utilisateur (ou pour tous si élévation)
Source: "..\third_party\fonts\Amiri-Regular.ttf"; DestDir: "{autofonts}"; FontInstall: "Amiri"; Flags: onlyifdoesntexist uninsneveruninstall
Source: "..\third_party\fonts\Amiri-Bold.ttf"; DestDir: "{autofonts}"; FontInstall: "Amiri Bold"; Flags: onlyifdoesntexist uninsneveruninstall
Source: "..\third_party\fonts\OFL.txt"; DestDir: "{app}\licences"; DestName: "Amiri-OFL.txt"

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\Guide utilisateur"; Filename: "{app}\docs\GUIDE_UTILISATEUR.html"; Check: FileExists(ExpandConstant('{app}\docs\GUIDE_UTILISATEUR.html'))
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Arrête un backend Smart Office resté actif avant la suppression des fichiers
Filename: "{sys}\taskkill.exe"; Parameters: "/F /T /IM smartoffice-backend.exe"; Flags: runhidden; RunOnceId: "KillBackend"

; Les données (%LocalAppData%\AFMIGestionProjet et %LocalAppData%\AFMI Smart Admin) sont conservées à la désinstallation.

[Code]
function WebView2Installed(): Boolean;
var
  Version: String;
begin
  Result :=
    RegQueryStringValue(HKLM, 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version) or
    RegQueryStringValue(HKCU, 'Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version);
  Result := Result and (Version <> '') and (Version <> '0.0.0.0');
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
  if not WebView2Installed() then
    MsgBox('Le composant Microsoft Edge WebView2 Runtime n''a pas été détecté.' + #13#10 +
           'Le module Smart Office en a besoin. Il est installé par défaut sur Windows 11 ; sinon, ' +
           'téléchargez-le gratuitement sur https://developer.microsoft.com/microsoft-edge/webview2/.',
           mbInformation, MB_OK);
end;
