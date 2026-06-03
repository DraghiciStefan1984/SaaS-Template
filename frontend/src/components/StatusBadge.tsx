const toneByStatus: Record<string, string> = {
  active: "success",
  available: "success",
  configured: "success",
  connected: "success",
  free: "neutral",
  succeeded: "success",
  sent: "success",
  queued: "pending",
  running: "info",
  retrying: "warning",
  trialing: "info",
  not_configured: "warning",
  failed: "danger",
  disabled: "danger",
  skipped: "neutral",
  human_review: "warning",
};

export function StatusBadge({ value }: { value: string }) {
  const tone = toneByStatus[value] ?? "neutral";
  return <span className={`status-badge ${tone}`}>{value.replaceAll("_", " ")}</span>;
}
