[Setup]
AppId={{550D5562-DAE5-4B1A-AAF1-9BB713AEAC22}
AppName=Plume
AppVersion=0.1.0
AppPublisher=Plume
DefaultDirName={localappdata}\Programs\Plume
DefaultGroupName=Plume
PrivilegesRequired=lowest
OutputDir=output
OutputBaseFilename=Plume-Installation-Windows
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\Plume.exe
WizardStyle=modern

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le Bureau"; GroupDescription: "Raccourcis :"; Flags: unchecked

[Files]
Source: "dist\Plume\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "NOTICE.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Plume"; Filename: "{app}\Plume.exe"
Name: "{userdesktop}\Plume"; Filename: "{app}\Plume.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Plume.exe"; Description: "Ouvrir Plume"; Flags: nowait postinstall skipifsilent
