; Inno Setup Script for HAPAG Form 5A Comparator
#ifndef AppVersion
  #define AppVersion "1.3.0"
#endif

[Setup]
AppName=HAPAG Form 5A Comparator
AppVersion={#AppVersion}
AppPublisher=HAPAG
DefaultDirName={autopf}\HAPAG Form 5A Comparator
DefaultGroupName=HAPAG Form 5A Comparator
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=hapag_comparator_windows_setup_{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\hapag_comparator.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\hapag_comparator\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\HAPAG Form 5A Comparator"; Filename: "{app}\hapag_comparator.exe"
Name: "{autodesktop}\HAPAG Form 5A Comparator"; Filename: "{app}\hapag_comparator.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\hapag_comparator.exe"; Description: "{cm:LaunchProgram,HAPAG Form 5A Comparator}"; Flags: nowait postinstall skipifsilent
