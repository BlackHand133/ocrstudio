/**
 * PP-OCR release / language compatibility, as reported by the backend.
 *
 * Not every PP-OCR release ships a model for every language. Thai, for one,
 * exists only in PP-OCRv5, so pairing it with v6, v4 or v3 produces an engine
 * that cannot load. The backend asks the installed PaddleOCR which pairs work
 * and rejects the rest on save; this module lets the UI grey them out first.
 */

/**
 * `version_languages` from `GET /api/config`.
 *
 * The backend lists every release it offers, with the languages each one can
 * recognize. A release **absent** from the map (an older backend) is treated as
 * unrestricted rather than as supporting nothing: the backend still validates
 * on save, whereas an empty list would disable every option.
 */
export type VersionLanguages = Record<string, string[]>;

export function versionSupportsLang(
  versionLanguages: VersionLanguages | undefined,
  version: string,
  lang: string,
): boolean {
  const allowed = versionLanguages?.[version];
  return !allowed || allowed.includes(lang);
}

/** Releases that can handle `lang`, in the order the backend listed them. */
export function versionsForLang(
  versionLanguages: VersionLanguages | undefined,
  versions: string[],
  lang: string,
): string[] {
  return versions.filter((v) => versionSupportsLang(versionLanguages, v, lang));
}

export interface VersionOption {
  value: string;
  label: string;
  disabled: boolean;
}

/**
 * Build the version picker's options, disabling the ones with no model for the
 * current language and saying why in the label.
 */
export function buildVersionOptions(
  versionLanguages: VersionLanguages | undefined,
  versions: string[],
  lang: string,
  describeUnsupported: (version: string, lang: string) => string,
): VersionOption[] {
  return versions.map((version) => {
    const ok = versionSupportsLang(versionLanguages, version, lang);
    return {
      value: version,
      label: ok ? version : `${version} — ${describeUnsupported(version, lang)}`,
      disabled: !ok,
    };
  });
}
