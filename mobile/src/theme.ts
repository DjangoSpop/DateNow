/** Palette ported from frontend/tailwind.config.js ("calming blue" + soft pink accents). */
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
  gray50: '#f9fafb',
  gray100: '#f3f4f6',
  gray200: '#e5e7eb',
  gray400: '#9ca3af',
  gray500: '#6b7280',
  gray600: '#4b5563',
  gray700: '#374151',
  gray800: '#1f2937',
  danger50: '#fef2f2',
  danger200: '#fecaca',
  danger700: '#b91c1c',
  white: '#ffffff',
} as const;

export const spacing = { xs: 4, sm: 8, md: 16, lg: 24, xl: 32 } as const;
export const radius = { md: 12, lg: 16, xl: 20, pill: 999 } as const;

export const type = {
  title: { fontSize: 28, fontWeight: '700' as const, color: colors.gray800 },
  heading: { fontSize: 20, fontWeight: '700' as const, color: colors.gray800 },
  body: { fontSize: 16, color: colors.gray700, lineHeight: 24 },
  caption: { fontSize: 13, color: colors.gray500 },
  label: { fontSize: 14, fontWeight: '600' as const, color: colors.gray700 },
};
