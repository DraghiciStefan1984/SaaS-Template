export function formatDate(value: string | null | undefined) {
  if (!value) {
    return "n/a";
  }
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
  }).format(new Date(value));
}

export function formatNumber(value: number | string | null | undefined) {
  if (value === null || value === undefined || value === "") {
    return "0";
  }
  return new Intl.NumberFormat().format(Number(value));
}

export function formatLimit(value: unknown) {
  if (value === null || value === undefined) {
    return "unlimited";
  }
  if (typeof value === "number" || typeof value === "string") {
    return String(value);
  }
  return JSON.stringify(value);
}
