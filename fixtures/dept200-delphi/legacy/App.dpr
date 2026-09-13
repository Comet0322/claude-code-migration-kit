program App;

uses
  Dept200Data,
  Dept200Log,
  UserSync;

begin
  UserSync.RunNightlySync;
end.
