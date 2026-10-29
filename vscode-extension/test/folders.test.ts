import * as path from 'node:path';
import { describe, expect, it } from 'vitest';
import { dataFolderNotes, isNested, isWithin } from '../src/core/folders';

describe('isWithin', () => {
  it('is true for the folder itself and for anything below it', () => {
    const root = path.join(path.sep, 'data', 'features');
    expect(isWithin(root, root)).toBe(true);
    expect(isWithin(path.join(root, 'login.feature'), root)).toBe(true);
    expect(isWithin(path.join(root, 'deep', 'x.feature'), root)).toBe(true);
  });

  it('is false for siblings that only share a name prefix, and for parents', () => {
    const root = path.join(path.sep, 'data', 'features');
    expect(isWithin(path.join(path.sep, 'data', 'features-other', 'x.feature'), root)).toBe(false);
    expect(isWithin(path.join(path.sep, 'data'), root)).toBe(false);
  });
});

describe('isNested', () => {
  it('is true when one folder lies inside the other, in either direction', () => {
    const outer = path.join(path.sep, 'data');
    const inner = path.join(outer, 'spec2test');
    expect(isNested(inner, outer)).toBe(true);
    expect(isNested(outer, inner)).toBe(true);
  });

  it('is false for equal folders and for unrelated ones that share a prefix', () => {
    const a = path.join(path.sep, 'data', 'spec2test');
    expect(isNested(a, a)).toBe(false);
    expect(isNested(path.join(path.sep, 'data', 'spec2test-2'), a)).toBe(false);
  });
});

describe('dataFolderNotes', () => {
  it('is empty when the folder is empty and the current one holds no projects', () => {
    expect(dataFolderNotes(true, false)).toBe('');
  });

  it('explains a non-empty folder', () => {
    expect(dataFolderNotes(false, false)).toBe('The folder is not empty: Spec2Test will add its files inside it.');
  });

  it('explains the copy when the current folder holds projects', () => {
    expect(dataFolderNotes(true, true)).toBe(
      'Copy brings projects.json and the work areas along. Your input folders and their results are not touched, and the old folder is left in place for you to delete.',
    );
  });

  it('separates the two notes with a blank line', () => {
    expect(dataFolderNotes(false, true)).toBe(
      'The folder is not empty: Spec2Test will add its files inside it.\n\nCopy brings projects.json and the work areas along. Your input folders and their results are not touched, and the old folder is left in place for you to delete.',
    );
  });
});
