; installer.iss — Inno Setup 6 Script
; Produces RAW_Culler_Setup.exe with:
;   - Standard Windows install wizard
;   - Start Menu & Desktop shortcuts (optional)
;   - Built-in uninstaller
;   - No Python required on the target machine

[Setup]
AppName=RAW Culler
AppVersion=1.0
AppPublisher=RAW Culler
AppPublisherURL=https://github.com/
AppSupportURL=https://github.com/
AppUpdatesURL=https://github.com/
DefaultDirName={autopf}\RAW Culler
DefaultGroupName=RAW Culler
AllowNoIcons=yes
LicenseFile=
OutputDir=Output
OutputBaseFilename=RAW_Culler_Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

; Appearance
WizardSmallImageFile=
SetupIconFile=
UninstallDisplayIcon={app}\RAW_Culler.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a Desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
; Main EXE (single-file PyInstaller output)
Source: "dist\RAW_Culler.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Start Menu
Name: "{group}\RAW Culler";           Filename: "{app}\RAW_Culler.exe"
Name: "{group}\Uninstall RAW Culler"; Filename: "{uninstallexe}"
; Desktop (optional)
Name: "{autodesktop}\RAW Culler";     Filename: "{app}\RAW_Culler.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\RAW_Culler.exe"; Description: "Launch RAW Culler now"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
