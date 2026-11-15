// Presentación de las funciones de un plan: separa el «Todo lo de X» como encabezado,
// quita el renglón de límites (se muestra aparte) y asigna un ícono por palabra clave.

const ICONS = {
  infinity: '<path d="M12 12c-2-2.67-4-4-6-4a4 4 0 1 0 0 8c2 0 4-1.33 6-4zm0 0c2 2.67 4 4 6 4a4 4 0 0 0 0-8c-2 0-4 1.33-6 4z"/>',
  key: '<circle cx="7.5" cy="15.5" r="5.5"/><path d="m21 2-9.6 9.6M15.5 7.5l3 3L22 7l-3-3"/>',
  panel: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/>',
  palette: '<circle cx="13.5" cy="6.5" r="1.5"/><circle cx="17.5" cy="10.5" r="1.5"/><circle cx="8.5" cy="7.5" r="1.5"/><circle cx="6.5" cy="12.5" r="1.5"/><path d="M12 2a10 10 0 0 0 0 20c.9 0 1.5-.7 1.5-1.5 0-.4-.1-.7-.4-1-.3-.3-.4-.6-.4-1 0-.8.7-1.5 1.5-1.5H16a6 6 0 0 0 6-6c0-5-4.5-9-10-9z"/>',
  building: '<path d="M3 21h18M5 21V7l7-4 7 4v14"/><path d="M9 21v-6h6v6"/>',
  userCheck: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="m16 11 2 2 4-4"/>',
  calendar: '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18M9 16l2 2 4-4"/>',
  link: '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
  scissors: '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M20 4 8.12 15.88M14.47 14.48 20 20M8.12 8.12 12 12"/>',
  clock: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
  bag: '<path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><path d="M3 6h18M16 10a4 4 0 0 1-8 0"/>',
  chart: '<path d="M3 3v18h18"/><path d="m7 15 4-4 3 3 5-6"/>',
  users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
  check: '<path d="M4.5 12.75l6 6 9-13.5"/>',
};

const RULES: [RegExp, keyof typeof ICONS][] = [
  [/cupo/, "infinity"],
  [/acceso/, "key"],
  [/panel|un solo lugar/, "panel"],
  [/producto|cat[aá]logo|pedido/, "bag"],
  [/(^|\s)logo|marca|identidad|colores/, "palette"],
  [/sucursal|local|sede/, "building"],
  [/cliente/, "userCheck"],
  [/enlace|instagram/, "link"],
  [/reserv/, "calendar"],
  [/horario|agenda|disponibilidad/, "clock"],
  [/servicio/, "scissors"],
  [/ingreso|actividad|seguimiento/, "chart"],
  [/barbero/, "users"],
];

export const featureIcon = (text: string) => {
  const lower = text.toLowerCase();
  return ICONS[RULES.find(([re]) => re.test(lower))?.[1] ?? "check"];
};

const LIMITS = /^\d+\s+barberos?\s*·\s*\d+\s+sucursal/i;
const INHERITS = /^todo lo de\s+([^,]+)/i;

export const splitFeatures = (features: string[] = []) => {
  let inherits: string | null = null;
  const items = features.filter((feature) => {
    const match = feature.match(INHERITS);
    if (match) {
      inherits = match[1].trim();
      return false;
    }
    return !LIMITS.test(feature);
  });
  return { inherits, items };
};
