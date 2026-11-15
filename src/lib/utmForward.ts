// Reenvía los utm_* con los que llegó el visitante a los links de registro
// del admin, para que el alta guarde la atribución (first-touch en el admin).
export const SIGNUP_ORIGIN = "https://app.barbersoftly.com";
const STORAGE_KEY = "bs_landing_utm";
const UTM_KEYS = ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"];

export const pickUtm = (search: string): string => {
  const params = new URLSearchParams(search);
  const utm = new URLSearchParams();
  for (const key of UTM_KEYS) {
    const value = params.get(key)?.trim();
    if (value) utm.set(key, value);
  }
  return utm.toString();
};

// Agrega la UTM a un link del admin sin pisar parámetros que ya traiga.
export const withUtm = (href: string, utm: string): string => {
  if (!utm) return href;
  let url: URL;
  try {
    url = new URL(href);
  } catch {
    return href;
  }
  if (url.origin !== SIGNUP_ORIGIN) return href;
  new URLSearchParams(utm).forEach((value, key) => {
    if (!url.searchParams.has(key)) url.searchParams.set(key, value);
  });
  return url.toString();
};

// La UTM de la URL actual manda; si no hay, se usa la de esta pestaña.
export const currentUtm = (search: string, storage: Storage | null): string => {
  const fromUrl = pickUtm(search);
  try {
    if (fromUrl) storage?.setItem(STORAGE_KEY, fromUrl);
    return fromUrl || storage?.getItem(STORAGE_KEY) || "";
  } catch {
    return fromUrl;
  }
};

export const forwardUtm = (doc: Document, search: string, storage: Storage | null) => {
  const utm = currentUtm(search, storage);
  if (!utm) return;
  doc.querySelectorAll<HTMLAnchorElement>(`a[href^="${SIGNUP_ORIGIN}"]`).forEach((link) => {
    link.href = withUtm(link.href, utm);
  });
};
