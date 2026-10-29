import * as fs from 'node:fs';
import * as path from 'node:path';

/** Is anything under `dir` owned by someone other than `uid`? (Left behind by a container that ran as root.) */
export function hasForeignOwner(dir: string, uid: number): boolean {
  if (!fs.existsSync(dir)) {
    return false;
  }
  if (fs.lstatSync(dir).uid !== uid) {
    return true;
  }
  for (const item of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, item.name);
    if (item.isDirectory() ? hasForeignOwner(full, uid) : fs.lstatSync(full).uid !== uid) {
      return true;
    }
  }
  return false;
}
