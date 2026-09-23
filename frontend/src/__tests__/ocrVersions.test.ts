import { describe, expect, it } from 'vitest';
import {
  buildVersionOptions,
  versionSupportsLang,
  versionsForLang,
} from '../lib/ocrVersions';

// What GET /api/config returns without paddleocr installed: every release is
// listed, from the table measured on PaddleOCR 3.7.0.
const VERSIONS = ['PP-OCRv6', 'PP-OCRv5', 'PP-OCRv4', 'PP-OCRv3'];
const VERSION_LANGUAGES = {
  'PP-OCRv6': ['en', 'ch', 'chinese_cht', 'japan'],
  'PP-OCRv5': ['th', 'en', 'ch', 'chinese_cht', 'japan', 'korean'],
  'PP-OCRv4': ['en', 'ch'],
  'PP-OCRv3': ['en', 'ch', 'chinese_cht', 'japan', 'korean'],
};

const describeUnsupported = (v: string, l: string) => `${v} has no model for ${l}`;

describe('versionSupportsLang', () => {
  it('rejects PP-OCRv6 for Thai', () => {
    expect(versionSupportsLang(VERSION_LANGUAGES, 'PP-OCRv6', 'th')).toBe(false);
  });

  it('rejects PP-OCRv4 for Thai', () => {
    // The backend's earlier table left v4 unrestricted and so offered this.
    expect(versionSupportsLang(VERSION_LANGUAGES, 'PP-OCRv4', 'th')).toBe(false);
  });

  it('accepts PP-OCRv6 for a language it ships', () => {
    expect(versionSupportsLang(VERSION_LANGUAGES, 'PP-OCRv6', 'en')).toBe(true);
  });

  it('treats a release an older backend left out as unrestricted', () => {
    // Absent means "no information", not "supports nothing".
    const partial = { 'PP-OCRv6': VERSION_LANGUAGES['PP-OCRv6'] };
    expect(versionSupportsLang(partial, 'PP-OCRv5', 'th')).toBe(true);
  });

  it('stays permissive when the map is missing entirely', () => {
    expect(versionSupportsLang(undefined, 'PP-OCRv6', 'th')).toBe(true);
  });
});

describe('versionsForLang', () => {
  it('leaves only PP-OCRv5 for Thai', () => {
    expect(versionsForLang(VERSION_LANGUAGES, VERSIONS, 'th')).toEqual(['PP-OCRv5']);
  });

  it('keeps backend order for a language several releases share', () => {
    expect(versionsForLang(VERSION_LANGUAGES, VERSIONS, 'korean')).toEqual([
      'PP-OCRv5',
      'PP-OCRv3',
    ]);
  });

  it('keeps every version for English', () => {
    expect(versionsForLang(VERSION_LANGUAGES, VERSIONS, 'en')).toEqual(VERSIONS);
  });
});

describe('buildVersionOptions', () => {
  it('disables and explains every release without a Thai model', () => {
    const opts = buildVersionOptions(
      VERSION_LANGUAGES,
      VERSIONS,
      'th',
      describeUnsupported,
    );
    const disabled = opts.filter((o) => o.disabled).map((o) => o.value);
    expect(disabled).toEqual(['PP-OCRv6', 'PP-OCRv4', 'PP-OCRv3']);
    expect(opts[0].label).toContain('has no model for th');

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
