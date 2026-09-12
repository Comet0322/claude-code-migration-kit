unit CurrencyRules;

interface

// Internal business rule (not a generic library): the mainframe extract's
// 2-letter region codes do not match ISO 4217 currency codes. This mapping
// is company-specific data, not a normalization algorithm — see the domain
// skill's replacement rule for how it must be carried into the new language.
function NormalizeCurrencyCode(const LegacyCode: string): string;

implementation

function NormalizeCurrencyCode(const LegacyCode: string): string;
begin
  if LegacyCode = 'US' then
    Result := 'USD'
  else if LegacyCode = 'EU' then
    Result := 'EUR'
  else if LegacyCode = 'JP' then
    Result := 'JPY'
  else
    Result := 'XXX'; // unknown/unmapped legacy code
end;

end.
