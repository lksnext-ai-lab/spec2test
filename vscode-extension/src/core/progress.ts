/** Extract "3/8" from a server progress message such as "Analysing video segment 3/8". */
export function parseStep(message: string): { index: number; total: number } | undefined {
  const match = /(\d+)\s*\/\s*(\d+)/.exec(message);
  if (!match) {
    return undefined;
  }
  const index = Number(match[1]);
  const total = Number(match[2]);
  return total > 0 && index <= total ? { index, total } : undefined;
}
