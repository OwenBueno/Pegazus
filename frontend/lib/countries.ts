/** ISO 3166-1 alpha-2 — MX first (primary market), then common LatAm + others. */
export type CountryOption = { code: string; nameEn: string; nameEs: string };

export const COUNTRIES: CountryOption[] = [
  { code: "MX", nameEn: "Mexico", nameEs: "México" },
  { code: "AR", nameEn: "Argentina", nameEs: "Argentina" },
  { code: "BO", nameEn: "Bolivia", nameEs: "Bolivia" },
  { code: "BR", nameEn: "Brazil", nameEs: "Brasil" },
  { code: "CA", nameEn: "Canada", nameEs: "Canadá" },
  { code: "CL", nameEn: "Chile", nameEs: "Chile" },
  { code: "CO", nameEn: "Colombia", nameEs: "Colombia" },
  { code: "CR", nameEn: "Costa Rica", nameEs: "Costa Rica" },
  { code: "CU", nameEn: "Cuba", nameEs: "Cuba" },
  { code: "DO", nameEn: "Dominican Republic", nameEs: "República Dominicana" },
  { code: "EC", nameEn: "Ecuador", nameEs: "Ecuador" },
  { code: "ES", nameEn: "Spain", nameEs: "España" },
  { code: "GT", nameEn: "Guatemala", nameEs: "Guatemala" },
  { code: "HN", nameEn: "Honduras", nameEs: "Honduras" },
  { code: "NI", nameEn: "Nicaragua", nameEs: "Nicaragua" },
  { code: "PA", nameEn: "Panama", nameEs: "Panamá" },
  { code: "PE", nameEn: "Peru", nameEs: "Perú" },
  { code: "PR", nameEn: "Puerto Rico", nameEs: "Puerto Rico" },
  { code: "PY", nameEn: "Paraguay", nameEs: "Paraguay" },
  { code: "SV", nameEn: "El Salvador", nameEs: "El Salvador" },
  { code: "US", nameEn: "United States", nameEs: "Estados Unidos" },
  { code: "UY", nameEn: "Uruguay", nameEs: "Uruguay" },
  { code: "VE", nameEn: "Venezuela", nameEs: "Venezuela" },
  { code: "XX", nameEn: "Other / elsewhere", nameEs: "Otro / otro país" },
];

export function countryLabel(code: string, locale: string): string {
  const c = COUNTRIES.find((x) => x.code === code);
  if (!c) return code;
  return locale.startsWith("es") ? c.nameEs : c.nameEn;
}
