#!/usr/bin/env node
import { readdir, readFile, writeFile, mkdir } from 'node:fs/promises';
import { basename, join } from 'node:path';

const root = new URL('..', import.meta.url).pathname;
const outDir = join(root, 'references');
const catalogDir = join(root, 'assets', 'themes');
const today = '2026-08-03';

const repos = {
  image: [
    ['guizang-ppt-skill', 'https://github.com/op7418/guizang-ppt-skill', '929c2ecb63a22b54d400c4911ed70bf96c2b355d'],
    ['codex-ppt-skill', 'https://github.com/ningzimu/codex-ppt-skill', 'f2ed80372f65bb05fe62dd07979b239a17ac065d'],
    ['GordenSuperPPTSkills', 'https://github.com/GordenSun/GordenSuperPPTSkills', '8c05583dab8334182b71738e8dfbbec5c56a1951'],
    ['gpt-image2-ppt-skills', 'https://github.com/JuneYaooo/gpt-image2-ppt-skills', '4576cd5aee5e2f7c2fbd47557045b150906ce98c'],
    ['wuming-cyan-circuit-launch-ppt', 'https://github.com/chujianyun/wuming-cyan-circuit-launch-ppt', '20915a2dcf775f937b53258007d09a5412c8d2ff'],
    ['wuming-ai-ppt-cover', 'https://github.com/chujianyun/wuming-ai-ppt-cover', '05e027cc55ac48b5664f628b69d0b750dbf9ce31'],
  ],
  html: [
    ['frontend-slides', 'https://github.com/zarazhangrui/frontend-slides', '9906a34d640d2111f724544cbc50f7f130569ae1'],
    ['visual-explainer', 'https://github.com/nicobailon/visual-explainer', '528b71feb85dab5d92b82c3554880826f50a75da'],
    ['open-codesign', 'https://github.com/OpenCoworkAI/open-codesign', 'b94d7156bf4aeb2c79892c91dc9934911a4e3741'],
    ['html-ppt-skill', 'https://github.com/lewislulu/html-ppt-skill', 'f3a8435d3901697d5ac5e64d356c933637e43107'],
    ['open-slide', 'https://github.com/1weiho/open-slide', '35dc46ca27716ea86f8a76710bbd3640e9590628'],
    ['dashi-ppt-skill', 'https://github.com/chuspeeism/dashi-ppt-skill', '7cb23347f91cda1a5519eafc8c040704e389535a'],
    ['beautiful-html-templates', 'https://github.com/zarazhangrui/beautiful-html-templates', 'e5e204fb1f3b06290846e7dcd7aceddabeceec8c'],
    ['bento', 'git@github.com:SwimmingLiu/bento.git', '3ad1bdf18e88cf04c79698b11a7cfc0d8570db63', 'output-editor'],
    ['baoyu-design', 'https://github.com/JimLiu/baoyu-design', '026d4ea012bdd5cada72ac8cc13f21ba4edf2245'],
  ],
};

const recipeIds = {
  image: ['editorial-ink','strict-swiss','clean-tech','research-evidence','analyst-blueprint','enterprise-infographic','teaching-explainer','technical-sketch','whiteboard-marker','retro-vector','handmade-paper','dark-aurora','bright-glass','y2k-holographic','risograph-zine','japanese-wabi','cyan-circuit','formal-red'],
  html: ['clean-professional','strict-swiss-html','editorial-paper','institutional-signal','neo-brutalist-grid','terminal-mono','blueprint-engineering','dark-aurora-html','glass-candy','data-spectrum','research-white','magazine-deep-blue','finance-index','growth-ember','retro-interface','pixel-arcade','riso-zine-html','organic-craft','playful-pastel','culture-poster','code-editorial','neon-entertainment'],
};

const classifyImage = id => {
  const s = id.toLowerCase();
  if (/cyan-circuit/.test(s)) return 'cyan-circuit';
  if (/party|government|formal-red/.test(s)) return 'formal-red';
  if (/research|thesis|clinical|academic|health-disparities/.test(s)) return 'research-evidence';
  if (/dashboard|data-science|consulting|economic|investment/.test(s)) return 'analyst-blueprint';
  if (/whiteboard/.test(s)) return 'whiteboard-marker';
  if (/technical-sketch/.test(s)) return 'technical-sketch';
  if (/hand|warm|scrapbook/.test(s)) return 'handmade-paper';
  if (/retro|vector|culinary|indigenous/.test(s)) return 'retro-vector';
  if (/risograph/.test(s)) return 'risograph-zine';
  if (/wabi/.test(s)) return 'japanese-wabi';
  if (/punk/.test(s)) return 'risograph-zine';
  if (/y2k|chrome|linzi-tech/.test(s)) return 'y2k-holographic';
  if (/aurora/.test(s)) return 'dark-aurora';
  if (/glass|ai-cover|flowery|lavender|candy/.test(s)) return 'bright-glass';
  if (/swiss/.test(s)) return 'strict-swiss';
  if (/teaching|mind-map|mindfulness|meeting-agenda/.test(s)) return 'teaching-explainer';
  if (/gorden|infographic|coal-industry/.test(s)) return 'enterprise-infographic';
  if (/clean|professional|business|eco-green|first-impressions/.test(s)) return 'clean-tech';
  if (/morandi/.test(s)) return 'japanese-wabi';
  return 'editorial-ink';
};

const htmlOverrides = {
  'frontend-slides:tech-product': 'clean-professional',
  'frontend-slides:business-professional': 'finance-index',
  'frontend-slides:light-minimal': 'strict-swiss-html',
  'frontend-slides:dark-elegant': 'dark-aurora-html',
  'frontend-slides:creative-vibrant': 'playful-pastel',
  'frontend-slides:warm-human': 'organic-craft',
  'frontend-slides:nature-organic': 'organic-craft',
  'frontend-slides:luxury-premium': 'magazine-deep-blue',
  'frontend-slides:data-dashboard': 'data-spectrum',
  'frontend-slides:academic-research': 'research-white',
  'frontend-slides:editorial-magazine': 'editorial-paper',
  'frontend-slides:developer-terminal': 'terminal-mono',
  'open-slide:bright-sans': 'clean-professional',
  'open-slide:minecraft': 'pixel-arcade',
  'open-slide:aurora': 'dark-aurora-html',
  'open-slide:replit': 'terminal-mono',
  'open-slide:sticker-pop': 'playful-pastel',
  'dashi-ppt-skill:theme01': 'clean-professional',
  'dashi-ppt-skill:theme02': 'dark-aurora-html',
  'dashi-ppt-skill:theme03': 'terminal-mono',
  'dashi-ppt-skill:theme04': 'glass-candy',
  'dashi-ppt-skill:theme05': 'data-spectrum',
  'dashi-ppt-skill:theme06': 'data-spectrum',
  'dashi-ppt-skill:theme07': 'research-white',
  'dashi-ppt-skill:theme08': 'neo-brutalist-grid',
  'dashi-ppt-skill:theme09': 'magazine-deep-blue',
  'dashi-ppt-skill:theme10': 'finance-index',
  'dashi-ppt-skill:theme11': 'growth-ember',
  'dashi-ppt-skill:theme12': 'neon-entertainment',
  'open-codesign:brand/vercel': 'strict-swiss-html',
  'open-codesign:brand/linear': 'dark-aurora-html',
  'open-codesign:brand/stripe': 'glass-candy',
  'open-codesign:brand/figma': 'playful-pastel',
  'open-codesign:brand/notion': 'editorial-paper',
  'open-codesign:brand/apple': 'clean-professional',
  'open-codesign:brand/airbnb': 'growth-ember',
  'open-codesign:brand/spotify': 'neon-entertainment',
  'open-codesign:brand/cursor': 'terminal-mono',
  'open-codesign:brand/supabase': 'dark-aurora-html',
  'open-codesign:brand/posthog': 'neo-brutalist-grid',
  'open-codesign:brand/framer': 'code-editorial',
  'open-codesign:brand/runwayml': 'dark-aurora-html',
  'open-codesign:brand/mistral': 'riso-zine-html',
  'open-codesign:brand/elevenlabs': 'code-editorial',
  'open-codesign:brand/coinbase': 'finance-index',
  'open-codesign:brand/revolut': 'finance-index',
  'open-codesign:brand/nike': 'neo-brutalist-grid',
  'open-codesign:brand/ferrari': 'growth-ember',
  'open-codesign:brand/spacex': 'blueprint-engineering',
  'open-codesign:brand/starbucks': 'organic-craft',
  'open-codesign:brand/shopify': 'growth-ember',
  'open-codesign:brand/ibm': 'institutional-signal',
  'open-codesign:brand/raycast': 'dark-aurora-html',
  'open-codesign:brand/cal-com': 'clean-professional',
  'open-codesign:direction/editorial-typography': 'editorial-paper',
  'open-codesign:direction/glassmorphism': 'glass-candy',
  'open-codesign:direction/dashboard': 'data-spectrum',
  'open-codesign:direction/slide-deck': 'clean-professional',
  'open-codesign:direction/neubrutalism': 'neo-brutalist-grid',
  'open-codesign:direction/aurora-mesh': 'dark-aurora-html',
  'open-codesign:direction/animated-gradient': 'glass-candy',
  'open-codesign:direction/bento-grid': 'clean-professional',
  'open-codesign:direction/dot-grid': 'blueprint-engineering',
  'open-codesign:direction/noise-grain': 'riso-zine-html',
};

const classifyHtml = id => {
  if (htmlOverrides[id]) return htmlOverrides[id];
  const s = id.toLowerCase();
  if (/pixel|8-bit|arcade/.test(s)) return 'pixel-arcade';
  if (/terminal|gruvbox|dracula|catppuccin|tokyo|nord|rose-pine/.test(s)) return 'terminal-mono';
  if (/blueprint|engineering|cartesian/.test(s)) return 'blueprint-engineering';
  if (/swiss|raw-grid|cobalt-grid/.test(s)) return 'strict-swiss-html';
  if (/neo|brutal|bold-poster|broadside|block-frame/.test(s)) return 'neo-brutalist-grid';
  if (/retro|midcentury|windows/.test(s)) return 'retro-interface';
  if (/riso|zine|stencil/.test(s)) return 'riso-zine-html';
  if (/dark|aurora|mocha/.test(s)) return 'dark-aurora-html';
  if (/glass|y2k|vapor|rainbow|sakura|chroma/.test(s)) return 'glass-candy';
  if (/neon|cyber|entertainment|theme08/.test(s)) return 'neon-entertainment';
  if (/academic|research|paper/.test(s)) return 'research-white';
  if (/finance|pitch|vc|corporate|blue-professional/.test(s)) return 'finance-index';
  if (/news|signal|institution/.test(s)) return 'institutional-signal';
  if (/editorial|serif|vellum|monochrome/.test(s)) return 'editorial-paper';
  if (/magazine|deep-blue|emerald|theme07/.test(s)) return 'magazine-deep-blue';
  if (/data|spectrum|dashboard/.test(s)) return 'data-spectrum';
  if (/growth|sunset|coral/.test(s)) return 'growth-ember';
  if (/organic|grove|forest|japanese/.test(s)) return 'organic-craft';
  if (/playful|pastel|daisy|pink|memphis|scatterbrain/.test(s)) return 'playful-pastel';
  if (/culture|biennale|peoples-platform/.test(s)) return 'culture-poster';
  if (/code|sharp-mono|creative-mode/.test(s)) return 'code-editorial';
  return 'clean-professional';
};

function theme(repository, sourceId, mode, extra = {}) {
  const key = `${repository}:${sourceId}`;
  return {
    key,
    repository,
    source_id: sourceId,
    name: extra.name || sourceId.replaceAll('-', ' '),
    traits: extra.traits || ['source-defined visual system'],
    best_for: extra.best_for || ['general presentation'],
    evidence_url: extra.evidence_url || `${repos[mode].find(r => r[0] === repository)?.[1] || ''}/tree/${repos[mode].find(r => r[0] === repository)?.[2] || 'main'}`,
    kind: extra.kind || 'theme',
    canonical_id: extra.kind === 'methodology' ? null : mode === 'image' ? classifyImage(key) : classifyHtml(key),
  };
}

async function imageThemes() {
  const result = [];
  for (const id of ['ink-classic','indigo-porcelain','forest-ink','kraft-paper','dune','swiss-ikb','swiss-lemon','swiss-lemon-green','swiss-safety-orange']) result.push(theme('guizang-ppt-skill', id, 'image'));
  for (const id of ['clean-professional','creative-magazine','electronic-ink','data-dashboard','retro-vector','technical-sketch','whiteboard','warm-handmade','research-defense','mckinsey','party-government-red','teaching']) result.push(theme('codex-ppt-skill', id, 'image'));
  for (const id of ['luxury-dark-infographic','light-enterprise-infographic','ink','handdrawn','blueprint','editorial']) result.push(theme('GordenSuperPPTSkills', id, 'image'));
  const base = process.env.GPT_IMAGE2_SOURCE || '/private/tmp/easy-gpt-image2/styles';
  for (const group of ['initial','featured','xiamulingzi']) {
    const files = (await readdir(join(base, group))).filter(file => file.endsWith('.md')).sort();
    for (const file of files) result.push(theme('gpt-image2-ppt-skills', `${group}/${basename(file, '.md')}`, 'image'));
  }
  result.push(theme('wuming-cyan-circuit-launch-ppt', 'cyan-circuit-launch', 'image'));
  for (const id of ['bright-glass-cover','blue-purple-ai-cover']) result.push(theme('wuming-ai-ppt-cover', id, 'image'));
  return result;
}

async function htmlThemes() {
  const result = [];
  for (const id of ['tech-product','business-professional','light-minimal','dark-elegant','creative-vibrant','warm-human','nature-organic','luxury-premium','data-dashboard','academic-research','editorial-magazine','developer-terminal']) result.push(theme('frontend-slides', id, 'html'));
  for (const id of ['midnight-editorial','warm-signal','terminal-mono','swiss-clean']) result.push(theme('visual-explainer', id, 'html'));
  for (const id of ['vercel','linear','stripe','figma','notion','apple','airbnb','spotify','cursor','supabase','posthog','framer','runwayml','mistral','elevenlabs','coinbase','revolut','nike','ferrari','spacex','starbucks','shopify','ibm','raycast','cal-com']) result.push(theme('open-codesign', `brand/${id}`, 'html'));
  for (const id of ['editorial-typography','glassmorphism','dashboard','slide-deck','neubrutalism','aurora-mesh','animated-gradient','bento-grid','dot-grid','noise-grain']) result.push(theme('open-codesign', `direction/${id}`, 'html'));
  const cssBase = process.env.HTML_PPT_SOURCE || '/private/tmp/easy-html-ppt/assets/themes';
  for (const file of (await readdir(cssBase)).filter(file => file.endsWith('.css')).sort()) result.push(theme('html-ppt-skill', `theme/${basename(file, '.css')}`, 'html'));
  for (const id of ['business-report','product-launch','academic-defense','training-course','annual-review','marketing-plan','project-proposal','data-report','company-profile','conference-keynote','portfolio','roadmap','case-study','workshop','event-intro']) result.push(theme('html-ppt-skill', `deck/${id}`, 'html'));
  for (const id of ['bright-sans','minecraft','aurora','replit','sticker-pop']) result.push(theme('open-slide', id, 'html'));
  const dashiBase = process.env.DASHI_SOURCE || '/private/tmp/easy-dashi/skills/dashi-ppt/project/src/components/themes';
  for (let i = 1; i <= 12; i++) {
    const sourceId = `theme${String(i).padStart(2, '0')}`;
    const raw = await readFile(join(dashiBase, sourceId, 'metadata.js'), 'utf8');
    const name = raw.match(/"displayName"\s*:\s*"([^"]+)"/)?.[1] || sourceId;
    result.push(theme('dashi-ppt-skill', sourceId, 'html', { name }));
  }
  const beautifulBase = process.env.BEAUTIFUL_SOURCE || '/private/tmp/easy-beautiful';
  const index = JSON.parse(await readFile(join(beautifulBase, 'index.json'), 'utf8'));
  for (const item of index.templates) result.push(theme('beautiful-html-templates', item.slug, 'html', { name: item.name, traits: item.mood, best_for: item.occasion }));
  result.push(theme('baoyu-design', 'methodology/design-system-bound', 'html', {
    name: 'Design-system-bound deck',
    kind: 'methodology',
    traits: ['no fixed theme library', 'load a user-selected design-system prompt as a binding constraint'],
    best_for: ['brand-governed decks', 'custom design systems'],
  }));
  return result;
}

const recipeInfo = {
  'editorial-ink':['Editorial Ink','paper, ink, restrained accent','asymmetric magazine spread','serif display / sans body / mono metadata'],
  'strict-swiss':['Strict Swiss','white, black, one primary accent','hard grid, hairlines, square blocks','grotesk sans'],
  'clean-tech':['Clean Tech','white, cool gray, blue and cyan','sparse product narrative','neutral sans'],
  'research-evidence':['Research Evidence','white, navy, formal red','evidence-first diagrams and tables','formal sans'],
  'analyst-blueprint':['Analyst Blueprint','white, blue gray, selective signal colors','KPI, matrix, funnel and comparison','compact sans'],
  'enterprise-infographic':['Enterprise Infographic','navy or white, metallic accent','high-density framework with one focal model','geometric sans'],
  'teaching-explainer':['Teaching Explainer','white, pale blue, multicolor cues','stepwise concept map','friendly sans'],
  'technical-sketch':['Technical Sketch','paper, graphite, restrained pastel','precise annotated diagram','handwritten labels / sans body'],
  'whiteboard-marker':['Whiteboard Marker','off-white, marker colors','boxes, arrows and workshop flow','marker hand'],
  'retro-vector':['Retro Vector','cream, coral, mint, mustard','flat monoline illustration','rounded display sans'],
  'handmade-paper':['Handmade Paper','cream, kraft, dusty pastel','torn paper, tape and scrapbook collage','humanist sans'],
  'dark-aurora':['Dark Aurora','near black, violet, cyan, pink','luminous arcs and depth','modern sans'],
  'bright-glass':['Bright Glass','white, pale blue, lavender','translucent layers and soft light','light geometric sans'],
  'y2k-holographic':['Y2K Holographic','lavender, sky, pink, chrome','holographic 3D focal object','wide grotesk'],
  'risograph-zine':['Risograph Zine','two or three spot colors','halftone, grain and rough registration','bold condensed sans'],
  'japanese-wabi':['Japanese Wabi','off-white, ink, one natural accent','large quiet whitespace and matte geometry','serif / minimal sans'],
  'cyan-circuit':['Cyan Circuit','white, cyan, blue-green, navy gray','circuit traces, HUD rings and numbered nodes','technical sans'],
  'formal-red':['Formal Red','Chinese red, ivory, restrained gold','formal hierarchy and ceremonial geometry','formal Chinese sans'],
};

const htmlInfo = {
  'clean-professional':['Clean Professional','white, gray, blue','calm modular grid','neutral sans'],
  'strict-swiss-html':['Strict Swiss HTML','white, black, one accent','12-column hard grid','grotesk sans'],
  'editorial-paper':['Editorial Paper','paper, ink, muted accent','asymmetric editorial composition','serif / sans'],
  'institutional-signal':['Institutional Signal','white, navy, signal red','broadcast labels and authoritative bands','condensed sans'],
  'neo-brutalist-grid':['Neo Brutalist Grid','white, black, saturated primary','thick rules and displaced blocks','heavy grotesk'],
  'terminal-mono':['Terminal Mono','charcoal, phosphor or muted syntax colors','console panels and code rhythm','monospace'],
  'blueprint-engineering':['Blueprint Engineering','blue or white, cyan linework','measured technical grid','technical mono / sans'],
  'dark-aurora-html':['Dark Aurora HTML','near black, violet and cyan','layered light with restrained glass','modern sans'],
  'glass-candy':['Glass Candy','bright pastel spectrum','translucent panels and chromatic depth','rounded geometric sans'],
  'data-spectrum':['Data Spectrum','white or dark neutral, semantic chart colors','dense but ordered analytical layout','compact sans'],
  'research-white':['Research White','white, navy, gray','citation-aware evidence layout','formal sans'],
  'magazine-deep-blue':['Magazine Deep Blue','deep blue, ivory, emerald accent','full-bleed image and editorial caption','serif / sans'],
  'finance-index':['Finance Index','white, navy, restrained red or green','KPI bands, tables and waterfall rhythm','tabular sans'],
  'growth-ember':['Growth Ember','white, coral, warm red','momentum curves and decisive callouts','bold sans'],
  'retro-interface':['Retro Interface','system gray, teal, nostalgic accents','window chrome and modular panes','pixel / system sans'],
  'pixel-arcade':['Pixel Arcade','deep navy, neon cyan and magenta','pixel grid and console framing','pixel mono'],
  'riso-zine-html':['Riso Zine HTML','spot red, blue, yellow','rough print blocks and halftone','condensed sans'],
  'organic-craft':['Organic Craft','forest, paper, botanical accent','soft irregular geometry and generous whitespace','humanist serif'],
  'playful-pastel':['Playful Pastel','light pastel mix with dark text','friendly loose grid and simple icons','rounded sans'],
  'culture-poster':['Culture Poster','parchment, solar yellow or civic blue','poster hierarchy and public-program rhythm','display serif'],
  'code-editorial':['Code Editorial','white or charcoal, syntax accents','editorial code fragments and sharp rules','mono / grotesk'],
  'neon-entertainment':['Neon Entertainment','black, electric cyan, hot pink','stage lighting and kinetic bands','display sans'],
};

function makeCatalog(inventories) {
  const build = (ids, info, themes, mode) => ids.map(id => {
    const [name, palette, composition, typography] = info[id];
    const aliases = themes.filter(item => item.canonical_id === id).map(item => item.key);
    const provenance = [...new Set(themes.filter(item => item.canonical_id === id).map(item => item.repository))];
    return {
      id, mode, name, aliases, provenance, palette, composition, typography,
      density: /data|enterprise|finance/.test(id) ? 'high' : /wabi|clean|editorial/.test(id) ? 'low' : 'medium',
      image_prompt_recipe: mode === 'ai-image' ? { require: [palette, composition, typography], forbid: ['generic UI card wall','unapproved visible text','watermark'] } : undefined,
      bento_recipe: mode === 'html' ? { primitives: ['text','shape','svg','chart','table'], constraints: [composition, 'no rasterized full-slide background'] } : undefined,
    };
  });
  return { schema_version: 1, generated_at: today, 'ai-image': build(recipeIds.image, recipeInfo, inventories.image, 'ai-image'), html: build(recipeIds.html, htmlInfo, inventories.html, 'html') };
}

await mkdir(outDir, { recursive: true });
await mkdir(catalogDir, { recursive: true });
const inventories = { image: await imageThemes(), html: await htmlThemes() };
for (const mode of ['image','html']) {
  const payload = {
    schema_version: 1,
    mode: mode === 'image' ? 'ai-image' : 'html',
    snapshot_date: today,
    repositories: repos[mode].map(([id, url, commit, role]) => {
      const entries = inventories[mode].filter(item => item.repository === id);
      const methodologyCount = entries.filter(item => item.kind === 'methodology').length;
      return {
        id,
        url,
        commit,
        theme_count: entries.filter(item => item.kind === 'theme').length,
        ...(methodologyCount ? { methodology_count: methodologyCount } : {}),
        ...(role ? { role } : {}),
      };
    }),
    themes: inventories[mode],
  };
  await writeFile(join(outDir, `${mode === 'image' ? 'image' : 'html'}-theme-inventory.json`), `${JSON.stringify(payload, null, 2)}\n`);
}
await writeFile(join(catalogDir, 'theme-catalog.json'), `${JSON.stringify(makeCatalog(inventories), null, 2)}\n`);
console.log(`wrote ${inventories.image.length} image sources and ${inventories.html.length} HTML sources`);
