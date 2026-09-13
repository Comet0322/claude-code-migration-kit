unit Dept200Log;

interface

type
  TLogLevel = (llInfo, llError);

procedure LogMessage(Level: TLogLevel; const Msg: string; const KeyValues: array of string);

implementation

uses
  SysUtils, Classes;

procedure LogMessage(Level: TLogLevel; const Msg: string; const KeyValues: array of string);
var
  LevelName, LogPath, Line: string;
  I: Integer;
  F: TextFile;
begin
  if Level = llInfo then LevelName := 'INFO' else LevelName := 'ERROR';
  LogPath := ExtractFilePath(ParamStr(0)) + 'logs\' + FormatDateTime('yyyymmdd', Now) + '.log';
  Line := '[' + FormatDateTime('yyyy-mm-dd hh:nn:ss', Now) + '] [' + LevelName + '] ' + Msg;
  for I := Low(KeyValues) to High(KeyValues) do
    Line := Line + ' ' + KeyValues[I];

  AssignFile(F, LogPath);
  if FileExists(LogPath) then Append(F) else Rewrite(F);
  WriteLn(F, Line);
  CloseFile(F);
end;

end.
