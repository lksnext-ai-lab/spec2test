/** Read and update a .env file without losing comments, order or unknown lines. */

const ASSIGNMENT = /^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$/;
const COMMENTED = /^\s*#\s*([A-Za-z_][A-Za-z0-9_]*)\s*=/;

export function parseEnv(text: string): Record<string, string> {
  const values: Record<string, string> = {};
  for (const line of text.split(/\r?\n/)) {
    const match = ASSIGNMENT.exec(line);
    if (match) {
      values[match[1]] = unquote(match[2].trim());
    }
  }
  return values;
}

function unquote(value: string): string {
  if (value.length >= 2 && value[0] === '"' && value.endsWith('"')) {
    return value.slice(1, -1).replace(/\\(["\\$])/g, '$1');
  }
  if (value.length >= 2 && value[0] === "'" && value.endsWith("'")) {
    return value.slice(1, -1);
  }
  return value.replace(/\s+#.*$/, '');
}

export function formatValue(value: string): string {
  return /[\s#"'$]/.test(value) ? `"${value.replace(/(["\\$])/g, '\\$1')}"` : value;
}

/**
 * Apply `updates`: an existing `KEY=` line is rewritten in place, a commented
 * template line (`# KEY=`) is replaced, and anything new is appended. A `null`
 * value comments an active assignment out.
 */
export function updateEnv(text: string, updates: Record<string, string | null>): string {
  const lines = text === '' ? [] : text.split(/\r?\n/);
  const pending = new Map(Object.entries(updates));

  const result = lines.map((line) => {
    const active = ASSIGNMENT.exec(line);
    if (active && pending.has(active[1])) {
      const value = pending.get(active[1]) as string | null;
      pending.delete(active[1]);
      return value === null ? `# ${active[1]}=` : `${active[1]}=${formatValue(value)}`;
    }
    const commented = COMMENTED.exec(line);
    if (commented && pending.has(commented[1]) && pending.get(commented[1]) !== null) {
      const value = pending.get(commented[1]) as string;
      pending.delete(commented[1]);
      return `${commented[1]}=${formatValue(value)}`;
    }
    return line;
  });

  while (result.length > 0 && result[result.length - 1] === '') {
    result.pop();
  }
  for (const [key, value] of pending) {
    if (value !== null) {
      result.push(`${key}=${formatValue(value)}`);
    }
  }
  return result.join('\n') + '\n';
}
