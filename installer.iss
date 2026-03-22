[Setup]
AppName=OCE
AppVersion=1.1.0
AppPublisher=paperface0128
DefaultDirName={userappdata}\OCE
DefaultGroupName=OCE
OutputDir=Output
OutputBaseFilename=OCE_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=icon.ico
PrivilegesRequired=lowest
UsedUserAreasWarning=no

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "바탕화면 바로가기"; GroupDescription: "추가 작업:"

[Files]
Source: "dist\OCE.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\OCE_updater.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "version.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "CREDITS.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\OCE"; Filename: "{app}\OCE.exe"
Name: "{group}\OCE 제거"; Filename: "{uninstallexe}"
Name: "{userdesktop}\OCE"; Filename: "{app}\OCE.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\OCE.exe"; Description: "OCE 실행"; Flags: nowait postinstall skipifsilent
