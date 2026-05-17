import type { Lang } from './types';
import en from '../i18n/en.json';
import af from '../i18n/af.json';

type Dict = typeof en;
const dicts: Record<Lang, Dict> = { en, af: af as Dict };

export function getDict(lang: Lang): Dict {
  return dicts[lang];
}

/** Lookup with `nav.timeline` style dot-paths. Falls back to the key itself. */
export function t(lang: Lang, key: string): string {
  const dict = dicts[lang] as Record<string, unknown>;
  const parts = key.split('.');
  let cur: unknown = dict;
  for (const p of parts) {
    if (cur && typeof cur === 'object' && p in (cur as object)) {
      cur = (cur as Record<string, unknown>)[p];
    } else {
      return key;
    }
  }
  return typeof cur === 'string' ? cur : key;
}

/** Interpolate `{name}` placeholders. */
export function tFormat(lang: Lang, key: string, vars: Record<string, string | number>): string {
  const tpl = t(lang, key);
  return tpl.replace(/\{(\w+)\}/g, (_, k) => (k in vars ? String(vars[k]) : `{${k}}`));
}

export function otherLang(lang: Lang): Lang {
  return lang === 'en' ? 'af' : 'en';
}
