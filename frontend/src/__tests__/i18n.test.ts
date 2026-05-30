import { describe, it, expect } from 'vitest';
import { translate } from '../i18n';

describe('translate', () => {
  it('returns English and Thai strings', () => {
    expect(translate('en', 'exp.export')).toBe('Export');
    expect(translate('th', 'exp.export')).toBe('ส่งออก');
  });

  it('interpolates {params}', () => {
    expect(translate('en', 'hdr.annotated', { a: 3, b: 5 })).toBe('3/5 annotated');
    expect(translate('th', 'list.missing', { n: 7 })).toContain('7');
  });

  it('falls back to the key for unknown entries', () => {
    expect(translate('th', 'nope.key')).toBe('nope.key');
  });
});
