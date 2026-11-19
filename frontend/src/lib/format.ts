export function money(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const number = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(number)) return String(value);
  return `₹${number.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
}
