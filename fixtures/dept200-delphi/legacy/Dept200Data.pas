unit Dept200Data;

interface

type
  TDBConnection = class
  public
    constructor Create(const ConnString: string);
    destructor Destroy; override;
    function Query(const SQL: string; const Params: array of Variant): Variant;
    procedure Execute(const SQL: string; const Params: array of Variant);
    procedure BeginTransaction;
    procedure Commit;
    procedure Rollback;
  end;

function ReadIniConnString(const IniPath: string): string;

implementation

uses
  IniFiles;

function ReadIniConnString(const IniPath: string): string;
var
  Ini: TIniFile;
begin
  Ini := TIniFile.Create(IniPath);
  try
    Result := Ini.ReadString('DB', 'ConnString', '');
  finally
    Ini.Free;
  end;
end;

constructor TDBConnection.Create(const ConnString: string);
begin
  inherited Create;
  // 底層透過 BDE 連到 MS SQL Server，這裡只是給 fixture 用的模擬骨架，
  // 不是真的可編譯/可執行的實作。
end;

destructor TDBConnection.Destroy;
begin
  inherited;
end;

function TDBConnection.Query(const SQL: string; const Params: array of Variant): Variant;
begin
  Result := Null;
end;

procedure TDBConnection.Execute(const SQL: string; const Params: array of Variant);
begin
end;

procedure TDBConnection.BeginTransaction;
begin
end;

procedure TDBConnection.Commit;
begin
end;

procedure TDBConnection.Rollback;
begin
end;

end.
