/**
 * Small design-token module. Palette follows the web client (frontend/tailwind.config.js):
 * calming blue primary, soft pink accent, pale sky "calm" backgrounds, trust green.
 */
export const colors = {
  primary50: '#e6f4ff',
  primary100: '#bae0ff',
  primary200: '#91caff',
  primary400: '#4096ff',
  primary500: '#1677ff',
  primary600: '#0958d9',
  primary700: '#003eb3',

  accent50: '#fff0f6',
  accent100: '#ffd6e7',
  accent500: '#eb2f96',
  accent600: '#c41d7f',

  calm50: '#f0f9ff',
  calm100: '#e0f2fe',

  trust50: '#f0fdf4',
  trust500: '#22c55e',
  trust700: '#15803d',

  danger50: '#fef2f2',
  danger600: '#dc2626',
  danger700: '#b91c1c',

  warn50: '#fffbeb',
  warn700: '#b45309',

  text: '#1f2937',
  textMuted: '#4b5563',
  textSubtle: '#6b7280',
  border: '#e5e7eb',
  borderStrong: '#d1d5db',
  surface: '#ffffff',
  background: '#f0f9ff',
  white: '#ffffff',
} as const;

export const spacing = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 } as const;

export const radius = { sm: 8, md: 12, lg: 16, xl: 24, pill: 999 } as const;

/** Minimum touch target (Apple HIG 44pt / Material 48dp). */
export const touchTarget = 48;

export const typography = {
  title: { fontSize: 28, fontWeight: '700' as const, color: colors.text },
  heading: { fontSize: 20, fontWeight: '600' as const, color: colors.text },
  body: { fontSize: 16, color: colors.text, lineHeight: 24 },
  label: { fontSize: 15, fontWeight: '600' as const, color: colors.text },
  small: { fontSize: 13, color: colors.textSubtle, lineHeight: 18 },
};

export const shadow = {
  card: {
    shadowColor: '#0f172a',
    shadowOpacity: 0.06,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
    elevation: 2,
  },
};
