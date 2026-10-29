import * as path from 'node:path';

/** True when `child` is `parent` itself or lies somewhere below it. */
export function isWithin(child: string, parent: string): boolean {
  return child === parent || child.startsWith(parent + path.sep);
}

/** True when one folder lies inside the other, in either direction (equal folders are not nested). */
export function isNested(a: string, b: string): boolean {
  return a.startsWith(b + path.sep) || b.startsWith(a + path.sep);
}

/** The explanatory notes shown under the data-folder confirmation (empty when there is nothing to say). */
export function dataFolderNotes(isEmpty: boolean, hasCurrent: boolean): string {
  return [
    isEmpty ? '' : `The folder is not empty: Spec2Test will add its files inside it.`,
    hasCurrent ? 'Copy brings projects.json and the work areas along. Your input folders and their results are not touched, and the old folder is left in place for you to delete.' : '',
  ]
    .filter(Boolean)
    .join('\n\n');
}
