; ============================================================
; Claude Win Monitor — Script Inno Setup
; Version : 1.8.4
; ============================================================

#define AppName    "Claude Win Monitor"
#define AppVersion "1.8.4"
#define AppPublisher "Laurent Gérard"
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
WizardImageFile=work\INSTALL-bannière.png
WizardSmallImageFile=work\INSTALL-header.png
WizardStyle=modern

; Désinstallation
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\Claude-Win-Monitor.ico

; Infos Windows Add/Remove Programs
VersionInfoVersion={#AppVersion}
VersionInfoProductName={#AppName}
VersionInfoCompany={#AppPublisher}

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Files]
; Contenu du build Nuitka (exe + DLLs + ressources)
; Exclure PDF et MD du guide : ces fichiers sont distribués séparément dans l'archive ZIP
Source: "{#SourceDist}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs; \
  Excludes: "guide_extension\Guide d'installation.pdf,guide_extension\Guide d'installation.md"

; Icône pour les raccourcis (l'exe n'a pas d'icône intégrée — Defender bloquait --windows-icon-from-ico)
Source: "work\Claude-Win-Monitor_ICO.ico"; DestDir: "{app}"; DestName: "Claude-Win-Monitor.ico"

; NOTE : l'extension Chrome et le guide sont distribués séparément dans l'archive ZIP,
; pas inclus dans l'installateur.

[Icons]
; Menu Démarrer
Name: "{group}\{#AppName}";              Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\Claude-Win-Monitor.ico"
Name: "{group}\Désinstaller {#AppName}"; Filename: "{uninstallexe}"

; Bureau
Name: "{autodesktop}\{#AppName}";        Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\Claude-Win-Monitor.ico"

[Run]
; Proposer de lancer l'app après installation
Filename: "{app}\{#AppExeName}"; \
  Description: "Lancer {#AppName}"; \
  Flags: nowait postinstall skipifsilent

[UninstallDelete]
; IMPORTANT : %LOCALAPPDATA%\Claude-Win-Monitor\ (JSON de config) n'est PAS supprimé
; → la configuration utilisateur est préservée lors des réinstallations / mises à jour
