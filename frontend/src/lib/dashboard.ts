export const activityRanges = [1, 6, 24, 72, 168] as const;

export function activityRangeLabel(hours: number): string {
  if (hours === 1) return "last hour";
  if (hours === 168) return "last 7 days";
  return `last ${hours} hours`;
}
