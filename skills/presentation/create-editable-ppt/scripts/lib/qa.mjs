import { mergeDeckState, validateDeck } from './model.mjs';

function finding(code, severity, slideId, message, details = {}) {
  return { code, severity, ...(slideId ? { slide_id: slideId } : {}), message, ...details };
}

function roleChecks(slide, assetsById) {
  const findings = [];
  const evidence = slide.evidence ?? [];
  const props = slide.props ?? {};
  if (['data', 'quote'].includes(slide.role) && evidence.length === 0) {
    findings.push(finding('claim.evidence.missing', 'blocking', slide.id, 'Fact-bearing slide has no evidence locator.'));
  }
  if (slide.role === 'data' && (props.metrics ?? []).length === 0) {
    findings.push(finding('data.metrics.required', 'blocking', slide.id, 'Data slide needs at least one metric.'));
  }
  if (slide.role === 'process' && (props.steps ?? []).length < 2) {
    findings.push(finding('process.steps.insufficient', 'warning', slide.id, 'Process slide should contain at least two steps.'));
  }
  if (slide.role === 'closing' && !props.action) {
    findings.push(finding('closing.action.required', 'blocking', slide.id, 'Closing slide needs a clear next action.'));
  }
  if (slide.role === 'image-hero' && props.image && !assetsById.has(props.image)) {
    findings.push(finding(
      props.image_status === 'missing-approved' ? 'image.placeholder.approved' : 'image.asset.required',
      props.image_status === 'missing-approved' ? 'warning' : 'blocking',
      slide.id,
      props.image_status === 'missing-approved' ? 'An approved image placeholder remains in this slide.' : 'Image-hero slide references an unavailable asset.',
      { asset_id: props.image },
    ));
  }
  if (!['pass', 'skip'].includes(slide.review_status)) {
    findings.push(finding('review.unresolved', 'blocking', slide.id, 'Slide review status must be pass or skip before export.'));
  }
  for (const mediaId of slide.media ?? []) {
    const asset = assetsById.get(mediaId);
    if (!asset) continue;
    if (asset.source === 'generated' && asset.fact_bearing) {
      findings.push(finding('asset.generated.fact_bearing', 'blocking', slide.id, 'Generated imagery cannot be used as factual evidence.', { asset_id: mediaId }));
    }
    if (['search', 'generated'].includes(asset.source) && !asset.license) {
      findings.push(finding('asset.license.missing', 'warning', slide.id, 'External or generated imagery has no license record.', { asset_id: mediaId }));
    }
  }
  return findings;
}

function normalizeModelFindings(items) {
  return items.map((item) => ({ ...item, severity: item.severity === 'blocking' ? 'blocking' : 'warning' }));
}

export async function runQa(project, options = {}) {
  const deck = project.state ? mergeDeckState(project.deck, project.state) : structuredClone(project.deck);
  const activeSlides = deck.slides.filter((slide) => !slide.skipped);
  const assets = project.assets ?? { schema_version: 1, assets: [] };
  const assetsById = new Map(assets.assets.map((asset) => [asset.id, asset]));
  const model = validateDeck({ ...deck, slides: activeSlides }, { assets });
  const findings = normalizeModelFindings(model.findings);

  if (activeSlides.length && activeSlides[0].role !== 'cover') {
    findings.push(finding('deck.cover.missing', 'degraded', activeSlides[0].id, 'The first active slide is not a cover.'));
  }
  if (activeSlides.length && activeSlides.at(-1).role !== 'closing') {
    findings.push(finding('deck.closing.missing', 'degraded', activeSlides.at(-1).id, 'The last active slide is not a closing slide.'));
  }
  for (const slide of activeSlides) findings.push(...roleChecks(slide, assetsById));

  let mode = 'semantic';
  if (options.browserCheck) {
    const browser = await options.browserCheck(project);
    mode = browser.mode ?? 'browser';
    findings.push(...(browser.findings ?? []));
  } else if (options.requireBrowser) {
    findings.push(finding('browser.qa.unavailable', 'degraded', null, 'Browser geometry QA was requested but is unavailable.'));
  }

  const summary = { blocking: 0, degraded: 0, warning: 0 };
  for (const item of findings) summary[item.severity] = (summary[item.severity] ?? 0) + 1;
  return {
    schema_version: 1,
    generated_at: new Date().toISOString(),
    mode,
    export_ready: summary.blocking === 0,
    summary,
    slides: activeSlides.map((slide) => ({
      id: slide.id,
      status: findings.some((item) => item.slide_id === slide.id && item.severity === 'blocking') ? 'blocked' : 'ready',
      findings: findings.filter((item) => item.slide_id === slide.id).map((item) => item.code),
    })),
    findings,
  };
}
