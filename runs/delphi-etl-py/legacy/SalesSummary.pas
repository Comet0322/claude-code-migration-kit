unit SalesSummary;

interface

uses
  FixedWidthParser, CurrencyRules;

function SummarizeLine(const Line: string): string;

implementation

uses
  SysUtils;

function SummarizeLine(const Line: string): string;
var
  Rec: TSalesRecord;
  Amount: Double;
  Iso: string;
begin
  Rec := ParseSalesLine(Line);
  Amount := Rec.AmountCents / 100.0;
  Iso := NormalizeCurrencyCode(Rec.CurrencyCode);
  // NOTE: FormatFloat's decimal separator follows the system locale
  // (DecimalSeparator) — on a comma-locale machine this would emit
  // '1234,56' instead of '1234.56'. This is a latent portability hazard,
  // not intended behavior — see the domain skill's rule on this.
  Result := Rec.CustomerId + '|' + Rec.SaleDate + '|' +
            FormatFloat('0.00', Amount) + '|' + Iso;
end;

end.
