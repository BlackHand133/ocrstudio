import { describe, expect, it } from 'vitest';
import {
  buildVersionOptions,
  versionSupportsLang,
  versionsForLang,
} from '../lib/ocrVersions';

// Shape the backend actually returns: only restricted versions appear.
const VERSIONS = ['PP-OCRv6', 'PP-OCRv5', 'PP-OCRv4', 'PP-OCRv3'];
const VERSION_LANGUAGES = { 'PP-OCRv6': ['en', 'ch', 'japan', 'latin'] };

const describeUnsupported = (v: string, l: string) => `${v} has no model for ${l}`;

describe('versionSupportsLang', () => {
  it('rejects PP-OCRv6 for Thai', () => {
    expect(versionSupportsLang(VERSION_LANGUAGES, 'PP-OCRv6', 'th')).toBe(false);
  });

  it('accepts PP-OCRv6 for a language it ships', () => {
    expect(versionSupportsLang(VERSION_LANGUAGES, 'PP-OCRv6', 'en')).toBe(true);
  });

  it('treats an unlisted version as unrestricted', () => {
    // PP-OCRv5 is absent from the map: absent means "no known restriction",
    // not "supports nothing".
    expect(versionSupportsLang(VERSION_LANGUAGES, 'PP-OCRv5', 'th')).toBe(true);
  });

  it('stays permissive when the map is missing entirely', () => {
    expect(versionSupportsLang(undefined, 'PP-OCRv6', 'th')).toBe(true);
  });
});

describe('versionsForLang', () => {
  it('drops PP-OCRv6 for Thai but keeps the rest in order', () => {
    expect(versionsForLang(VERSION_LANGUAGES, VERSIONS, 'th')).toEqual([
      'PP-OCRv5',
      'PP-OCRv4',
      'PP-OCRv3',
    ]);
  });

  it('keeps every version for English', () => {
    expect(versionsForLang(VERSION_LANGUAGES, VERSIONS, 'en')).toEqual(VERSIONS);
  });
});

describe('buildVersionOptions', () => {
  it('disables and explains the unsupported version', () => {
    const opts = buildVersionOptions(
      VERSION_LANGUAGES,
      VERSIONS,
      'th',
      describeUnsupported,
    );
    const v6 = opts.find((o) => o.value === 'PP-OCRv6')!;
    expect(v6.disabled).toBe(true);
    expect(v6.label).toContain('has no model for th');

    const v5 = opts.find((o) => o.value === 'PP-OCRv5')!;
    expect(v5.disabled).toBe(false);
    expect(v5.label).toBe('PP-OCRv5'); // no noise on supported entries
  });

  it('offers every version unadorned for a supported language', () => {
    const opts = buildVersionOptions(
      VERSION_LANGUAGES,
      VERSIONS,
      'en',
      describeUnsupported,
    );
    expect(opts.every((o) => !o.disabled)).toBe(true);
    expect(opts.map((o) => o.label)).toEqual(VERSIONS);
  });
});
