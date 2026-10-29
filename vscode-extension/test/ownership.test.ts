import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import { describe, expect, it } from 'vitest';
import { hasForeignOwner } from '../src/core/ownership';

describe('hasForeignOwner', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 's2t-own-'));
  fs.mkdirSync(path.join(dir, 'a', 'b'), { recursive: true });
  fs.writeFileSync(path.join(dir, 'a', 'b', 'file'), 'x');
  const me = fs.lstatSync(dir).uid;

  it('is false when everything belongs to the given user', () => {
    expect(hasForeignOwner(dir, me)).toBe(false);
  });

  it('finds a file or folder owned by someone else, however deep', () => {
    expect(hasForeignOwner(dir, me + 1)).toBe(true);
  });

  it('has nothing to complain about for a missing folder', () => {
    expect(hasForeignOwner(path.join(dir, 'missing'), me)).toBe(false);
  });
});
