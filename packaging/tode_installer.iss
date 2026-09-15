; Inno Setup script for tode — a customized, branded Windows setup wizard.
;
; Prerequisite: run PyInstaller first so dist\tode\ exists:
;     pyinstaller packaging/tode.spec
; Then compile this script with Inno Setup (GUI: Build > Compile, or CLI):
;     iscc packaging\tode_installer.iss
; Output: packaging\Output\tode-setup.exe

#define AppName        "tode"
#define AppVersion     "1.0.1"
#define AppPublisher   "welldropp"
#define AppExeName     "tode.exe"
#define AppUrl         "https://github.com/welldropp/tode"

[Setup]
AppId={{E6D2F0A1-7C3B-4E5A-9B21-TODE00000001}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppUrl}
AppSupportURL={#AppUrl}/issues
AppUpdatesURL={#AppUrl}/releases
VersionInfoVersion={#AppVersion}.0
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} — AI auto-annotation tool
VersionInfoProductName={#AppName}

; ── install location & privileges ─────────────────────────────────────────────
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
AllowNoIcons=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog commandline
MinVersion=10.0
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible

; ── output ────────────────────────────────────────────────────────────────────
OutputDir=Output
OutputBaseFilename=tode-setup
Compression=lzma2/max
SolidCompression=yes

; ── branding ──────────────────────────────────────────────────────────────────
WizardStyle=modern
SetupIconFile=tode.ico
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName} {#AppVersion}
WizardImageFile=wizard-large.bmp
WizardSmallImageFile=wizard-small.bmp
DisableWelcomePage=no
LicenseFile=..\LICENSE

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";     Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1

[Files]
; The entire PyInstaller one-dir bundle.
Source: "..\dist\tode\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
; Ship the icon so shortcuts and Add/Remove Programs use branded art.
Source: "tode.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}";            Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\tode.ico"
Name: "{group}\{#AppName} on GitHub";  Filename: "{#AppUrl}"
Name: "{group}\Uninstall {#AppName}";  Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}";      Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\tode.ico"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: quicklaunchicon

[Registry]
; Record the install location (handy for updaters / uninstall detection).
Root: HKCU; Subkey: "Software\{#AppPublisher}\{#AppName}"; ValueType: string; ValueName: "InstallDir"; ValueData: "{app}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\{#AppPublisher}\{#AppName}"; ValueType: string; ValueName: "Version";    ValueData: "{#AppVersion}"

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove any caches tode wrote next to the app (leave user datasets alone).
Type: filesandordirs; Name: "{app}\logs"
