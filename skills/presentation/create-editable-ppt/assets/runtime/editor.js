(() => {
  const model = JSON.parse(document.getElementById('deck-view-model').textContent);
  const deckNode = document.querySelector('.deck');
  const counter = document.querySelector('[data-page-counter]');
  const statusNode = document.querySelector('[data-save-status]');
  const state = structuredClone(model.state || {
    revision: 0, slide_order: model.deck.slides.map((slide) => slide.id), deleted_slides: [], skipped_slides: [], duplicated_slides: [], text_overrides: {}, prop_overrides: {}, review_status: {}, theme_override: null,
  });
  let slides = [...document.querySelectorAll('.slide')];
  let index = Math.max(0, slides.findIndex((slide) => !slide.classList.contains('is-skipped')));
  let saveTimer;

  const active = () => slides[index];
  const setStatus = (text) => { if (statusNode) statusNode.textContent = text; };
  const patchArray = (name, value, enabled) => {
    const set = new Set(state[name] || []);
    enabled ? set.add(value) : set.delete(value);
    state[name] = [...set];
  };

  async function save() {
    clearTimeout(saveTimer);
    setStatus('保存中');
    try {
      const response = await fetch('/api/save', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ expected_revision: state.revision, patch: state }) });
      if (response.status === 409) throw new Error('版本冲突，请刷新');
      if (!response.ok) throw new Error('当前为离线预览');
      Object.assign(state, (await response.json()).state);
      setStatus('已保存');
    } catch (error) {
      localStorage.setItem(`editable-ppt:${model.deck.title}`, JSON.stringify(state));
      setStatus(error.message);
    }
  }

  function scheduleSave() {
    setStatus('未保存');
    clearTimeout(saveTimer);
    saveTimer = setTimeout(save, 600);
  }

  function scale() {
    const viewport = document.querySelector('.viewport');
    const factor = Math.min(viewport.clientWidth / 1600, viewport.clientHeight / 900);
    deckNode.style.transform = `translate(-50%, -50%) scale(${factor})`;
  }

  function show(next) {
    index = Math.min(slides.length - 1, Math.max(0, next));
    slides.forEach((slide, i) => slide.classList.toggle('is-active', i === index));
    document.querySelectorAll('[data-thumbnail]').forEach((node) => node.classList.toggle('is-active', node.dataset.thumbnail === active()?.dataset.slideId));
    counter.textContent = `${index + 1} / ${slides.length}`;
    location.hash = active()?.dataset.slideId || '';
    const review = state.review_status?.[active()?.dataset.slideId] || active()?.dataset.reviewStatus;
    document.querySelectorAll('[data-action^="review-"]').forEach((node) => node.classList.toggle('is-active', node.dataset.action === `review-${review}`));
    const layoutSelect = document.querySelector('[data-layout-select]');
    if (layoutSelect && active()) {
      const choices = model.layouts?.[active().dataset.role] || [active().dataset.layout];
      layoutSelect.replaceChildren(...choices.map((value) => new Option(value, value, false, value === active().dataset.layout)));
    }
  }

  function visibleIndex(direction) {
    let next = index;
    do {
      next = Math.min(slides.length - 1, Math.max(0, next + direction));
      if (next === index || !slides[next].classList.contains('is-skipped')) return next;
    } while (next >= 0 && next < slides.length);
    return index;
  }

  function updateField(node) {
    const id = node.dataset.slideId;
    const field = node.dataset.field;
    if (field === 'claim' || field === 'layout') {
      state.text_overrides[id] = { ...(state.text_overrides[id] || {}), [field]: node.textContent.trim() };
    } else if (field.startsWith('props.')) {
      const parts = field.slice(6).split('.');
      const current = structuredClone(state.prop_overrides[id] || model.deck.slides.find((slide) => slide.id === id)?.props || {});
      let target = current;
      for (let i = 0; i < parts.length - 1; i += 1) target = target[parts[i]] ??= /^\d+$/u.test(parts[i + 1]) ? [] : {};
      target[parts.at(-1)] = node.textContent.trim();
      state.prop_overrides[id] = current;
    }
    const thumb = document.querySelector(`[data-thumbnail="${id}"] strong`);
    if (field === 'claim' && thumb) thumb.textContent = node.textContent.trim();
    scheduleSave();
  }

  function duplicateActive() {
    const source = active();
    if (!source) return;
    const id = `${source.dataset.slideId}-copy-${Date.now().toString(36)}`;
    const clone = source.cloneNode(true);
    clone.dataset.slideId = id;
    clone.querySelectorAll('[data-slide-id]').forEach((node) => { node.dataset.slideId = id; });
    source.after(clone);
    const thumbnail = document.querySelector(`[data-thumbnail="${source.dataset.slideId}"]`).cloneNode(true);
    thumbnail.dataset.thumbnail = id;
    thumbnail.querySelector('strong').textContent += '（副本）';
    document.querySelector(`[data-thumbnail="${source.dataset.slideId}"]`).after(thumbnail);
    state.duplicated_slides.push({ source_id: source.dataset.slideId, id });
    state.slide_order.splice(index + 1, 0, id);
    slides = [...document.querySelectorAll('.slide')];
    show(index + 1);
    scheduleSave();
  }

  function deleteActive() {
    if (slides.length <= 1 || !active()) return;
    const id = active().dataset.slideId;
    patchArray('deleted_slides', id, true);
    active().remove();
    document.querySelector(`[data-thumbnail="${id}"]`)?.remove();
    slides = [...document.querySelectorAll('.slide')];
    show(Math.min(index, slides.length - 1));
    scheduleSave();
  }

  document.addEventListener('input', (event) => {
    const editable = event.target.closest('[data-field]');
    if (editable) updateField(editable);
  });

  document.addEventListener('click', (event) => {
    const thumb = event.target.closest('[data-thumbnail]');
    if (thumb) show(slides.findIndex((slide) => slide.dataset.slideId === thumb.dataset.thumbnail));
    const action = event.target.closest('[data-action]')?.dataset.action;
    if (action === 'previous') show(visibleIndex(-1));
    if (action === 'next') show(visibleIndex(1));
    if (action === 'present') { document.body.classList.toggle('presentation'); document.documentElement.requestFullscreen?.().catch(() => {}); scale(); }
    if (action === 'save') save();
    if (action === 'duplicate') duplicateActive();
    if (action === 'delete') deleteActive();
    if (action === 'skip') { const node = active(); node.classList.toggle('is-skipped'); patchArray('skipped_slides', node.dataset.slideId, node.classList.contains('is-skipped')); scheduleSave(); }
    if (action === 'review-pass' || action === 'review-revise') { const value = action.slice(7); state.review_status[active().dataset.slideId] = value; active().dataset.reviewStatus = value; show(index); scheduleSave(); }
    if (action === 'export') document.querySelector('[data-export-menu]').toggleAttribute('hidden');
    const format = event.target.closest('[data-export-format]')?.dataset.exportFormat;
    if (format) fetch('/api/export', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ format }) }).then((response) => response.json()).then((result) => { setStatus(result.error || '导出完成'); }).catch(() => setStatus('请通过命令行导出'));
  });

  document.querySelector('[data-theme-select]')?.addEventListener('change', (event) => {
    deckNode.dataset.theme = event.target.value;
    state.theme_override = { family: event.target.value, variant: model.deck.theme.variant };
    scheduleSave();
  });
  document.querySelector('[data-layout-select]')?.addEventListener('change', (event) => {
    active().dataset.layout = event.target.value;
    state.text_overrides[active().dataset.slideId] = { ...(state.text_overrides[active().dataset.slideId] || {}), layout: event.target.value };
    scheduleSave();
  });
  document.querySelector('[data-image-input]')?.addEventListener('change', async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    const content_base64 = await new Promise((resolve) => { const reader = new FileReader(); reader.onload = () => resolve(reader.result.split(',')[1]); reader.readAsDataURL(file); });
    const response = await fetch('/api/media', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ filename: file.name, content_base64, purpose: `Slide ${active().dataset.slideId}` }) });
    if (!response.ok) return setStatus('图片上传失败');
    const { asset } = await response.json();
    const frame = active().querySelector('.media-frame');
    if (frame) frame.innerHTML = `<img src="${asset.path}" alt="" data-asset-id="${asset.id}">`;
    state.prop_overrides[active().dataset.slideId] = { ...(state.prop_overrides[active().dataset.slideId] || {}), image: asset.id };
    scheduleSave();
  });

  document.addEventListener('dragstart', (event) => { const thumb = event.target.closest('[data-thumbnail]'); if (thumb) event.dataTransfer.setData('text/plain', thumb.dataset.thumbnail); });
  document.addEventListener('dragover', (event) => { if (event.target.closest('[data-thumbnail]')) event.preventDefault(); });
  document.addEventListener('drop', (event) => {
    const target = event.target.closest('[data-thumbnail]');
    const id = event.dataTransfer.getData('text/plain');
    const source = document.querySelector(`[data-thumbnail="${id}"]`);
    if (!target || !source || source === target) return;
    target.before(source);
    state.slide_order = [...document.querySelectorAll('[data-thumbnail]')].map((node) => node.dataset.thumbnail);
    for (const slideId of state.slide_order) deckNode.append(document.querySelector(`.slide[data-slide-id="${slideId}"]`));
    slides = [...document.querySelectorAll('.slide')];
    show(slides.findIndex((slide) => slide.dataset.slideId === id));
    scheduleSave();
  });

  document.addEventListener('keydown', (event) => {
    if (event.target.closest('[contenteditable="true"], input, select')) return;
    if (['ArrowRight', 'PageDown', ' '].includes(event.key)) show(visibleIndex(1));
    if (['ArrowLeft', 'PageUp'].includes(event.key)) show(visibleIndex(-1));
    if (event.key === 'Escape') { document.body.classList.remove('presentation'); document.exitFullscreen?.().catch(() => {}); scale(); }
  });
  window.addEventListener('resize', scale);
  window.__PPT_MODEL__ = model;
  show(index);
  scale();
})();
