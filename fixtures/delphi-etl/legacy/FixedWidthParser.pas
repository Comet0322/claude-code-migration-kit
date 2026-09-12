unit FixedWidthParser;

interface

type
  TSalesRecord = record
    CustomerId: string;
    SaleDate: string;    // kept as 'YYYY-MM-DD' string, not TDateTime
    AmountCents: Integer; // raw integer cents, e.g. 123456 means 1234.56
    CurrencyCode: string; // raw 2-char legacy region code, e.g. 'US'
  end;

function ParseSalesLine(const Line: string): TSalesRecord;

implementation

function ParseSalesLine(const Line: string): TSalesRecord;
var
  Y, M, D: string;
begin
  // Fixed-width mainframe extract layout (1-based columns — Delphi's Copy
  // is 1-indexed, unlike most target languages):
  //   1-10  CustomerId (space-padded)
  //  11-18  Date as YYYYMMDD
  //  19-28  Amount as zero-padded integer cents (implied 2 decimals)
  //  29-30  Currency code
  Result.CustomerId := Trim(Copy(Line, 1, 10));

  Y := Copy(Line, 11, 4);
  M := Copy(Line, 15, 2);
  D := Copy(Line, 17, 2);
  Result.SaleDate := Y + '-' + M + '-' + D;

  Result.AmountCents := StrToInt(Copy(Line, 19, 10));
  Result.CurrencyCode := Copy(Line, 29, 2);
end;

end.
