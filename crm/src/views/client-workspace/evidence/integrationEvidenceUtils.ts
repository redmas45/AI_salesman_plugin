export function stringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.map((item) => String(item || '').trim()).filter(Boolean) : [];
}

export function recordArray(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? value.map(safeRecord).filter((item) => Object.keys(item).length > 0) : [];
}

export function safeRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};
}
