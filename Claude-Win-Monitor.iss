; ============================================================
; Claude Win Monitor — Script Inno Setup
; Version : 1.8.4
; ============================================================

#define AppName    "Claude Win Monitor"
#define AppVersion "1.8.4"
#define AppPublisher "M0DR1SH"
#define AppExeName "ClaudeWinMonitor.exe"
#define SourceDist "build\claude_usage_monitor.dist"

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL=https://github.com/M0DR1SH/Claude-Win-Monitor
DefaultDirName={autopf}\Claude-Win-Monitor
DefaultGroupName={#AppName}
OutputBaseFilename=Claude-Win-Monitor-Setup
OutputDir=dist-installer
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin

; Icône de l'installateur
SetupIconFile=work\Claude-Win-Monitor_ICO.ico

; Assets graphiques
WizardImageFile=work\INSTALL-bannière.bmp
WizardSmallImageFile=work\INSTALL-header.bmp
WizardStyle=modern

; Désinstallation
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExeName}

; Infos Windows Add/Remove Programs
VersionInfoVersion={#AppVersion}
VersionInfoProductName={#AppName}
VersionInfoCompany={#AppPublisher}

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Files]
; Contenu du build Nuitka (exe + DLLs + ressources)
Source: "{#SourceDist}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

; Extension Chrome (copiée dans le dossier d'installation pour que l'utilisateur puisse la charger)
Source: "extension\*"; DestDir: "{app}\extension"; Flags: recursesubdirs createallsubdirs

; Guide d'installation HTML (inclus dans le dist via Nuitka, mais aussi disponible hors-app)
; Source: "guide_extension\*"; DestDir: "{app}\guide_extension"; Flags: recursesubdirs createallsubdirs

[Icons]
; Menu Démarrer
Name: "{group}\{#AppName}";       Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\Claude-Win-Monitor.ico"
Name: "{group}\Désinstaller {#AppName}"; Filename: "{uninstallexe}"

; Bureau
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\Claude-Win-Monitor.ico"

[Run]
; Proposer de lancer l'app après installation
Filename: "{app}\{#AppExeName}"; \
  Description: "Lancer {#AppName}"; \
  Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Nettoyer uniquement le répertoire d'installation
; IMPORTANT : %LOCALAPPDATA%\Claude-Win-Monitor\ (JSON de config) n'est PAS supprimé
; → la configuration utilisateur est préservée lors des réinstallations / mises à jour

[Code]
// Vérification : avertir si une version précédente est déjà installée
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then begin
    // Rien à faire — Inno Setup gère automatiquement l'écrasement des fichiers
  end;
end;
