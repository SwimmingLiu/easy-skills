import { readFileSync } from 'node:fs';

const themeFile = new URL('../../assets/themes/themes.json', import.meta.url);

export const THEMES = Object.freeze(JSON.parse(readFileSync(themeFile, 'utf8')));

export function resolveTheme(id) {
  if (THEMES[id]) return THEMES[id];
  for (const theme of Object.values(THEMES)) {
    if (theme.aliases.includes(id)) return theme;
  }
  return THEMES['business-minimal'];
}

export function themeCss() {
  return Object.values(THEMES).map((theme) => {
    const t = theme.tokens;
    return `.deck[data-theme="${theme.id}"] {\n` +
      `  --slide-bg: ${t.background}; --surface: ${t.surface}; --text: ${t.text};\n` +
      `  --muted: ${t.muted}; --accent: ${t.accent}; --support: ${t.support};\n` +
      `  --line: ${t.line}; --radius: ${t.radius}; --heading: ${t.heading}; --body: ${t.body};\n` +
      `}`;
  }).join('\n');
}
