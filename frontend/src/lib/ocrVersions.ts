/**
 * PP-OCR release / language compatibility, mirrored from the backend.
 *
 * Not every PP-OCR release ships a model for every language — PP-OCRv6 in
 * particular covers Chinese, English, Japanese and Latin-script languages only,
 * so pairing it with Thai produces an engine that cannot load. The backend
 * rejects those pairs; this module lets the UI grey them out first.
 */

/**
 * `version_languages` from `GET /api/config`.
 *
 * A version **absent** from the map has no documented restriction and supports
 * every language. Treating a missing key as an empty list would wrongly
 * disable every option.
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
