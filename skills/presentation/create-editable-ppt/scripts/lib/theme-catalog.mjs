import { readFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const skillRoot = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const files = { 'ai-image': 'image-theme-inventory.json', html: 'html-theme-inventory.json' };

export async function loadThemeInventory(mode, root = skillRoot) {
  if (!files[mode]) throw new Error(`Unknown mode: ${mode}`);
  const data = JSON.parse(await readFile(join(root, 'references', files[mode]), 'utf8'));
  if (data.mode !== mode) throw new Error(`Inventory mode mismatch: ${data.mode}`);
  const keys = data.themes.map(theme => theme.key);
  if (new Set(keys).size !== keys.length) throw new Error(`Duplicate ${mode} source theme key`);
  return data;
}

export async function loadThemeCatalog(root = skillRoot) {
  return JSON.parse(await readFile(join(root, 'assets', 'themes', 'theme-catalog.json'), 'utf8'));
}

export function resolveThemeRecipe(catalog, mode, id) {
  return catalog?.[mode]?.find(recipe => recipe.id === id || recipe.aliases?.includes(id));
}

export function validateThemeCatalog(catalog) {
  const errors = [];
  const retired = new Set(['business-minimal','editorial','swiss-grid','launch-tech','data-consulting','academic','brand-bold','premium-dark']);
  for (const mode of ['ai-image','html']) {
    const ids = new Set();
    const aliases = new Set();
    for (const recipe of catalog?.[mode] || []) {
      if (recipe.mode !== mode) errors.push(`${recipe.id}: mode mismatch`);
      if (ids.has(recipe.id)) errors.push(`${recipe.id}: duplicate id`);
      if (retired.has(recipe.id)) errors.push(`${recipe.id}: retired id`);
      ids.add(recipe.id);
      if (!recipe.provenance?.length) errors.push(`${recipe.id}: missing provenance`);
      for (const alias of recipe.aliases || []) {
        if (aliases.has(alias)) errors.push(`${alias}: duplicate alias`);
        aliases.add(alias);
      }
    }
  }
  return { valid: errors.length === 0, errors };
}
