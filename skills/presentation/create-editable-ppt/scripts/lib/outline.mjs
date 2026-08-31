export const MODES = Object.freeze({ AI_IMAGE: 'ai-image', HTML: 'html' });

export function createOutline(title = 'AI 原生知识工作流') {
  return {
    schema_version: 2,
    status: 'draft',
    title,
    audience: '产品团队、知识工作者与组织管理者',
    purpose: '说明 AI 原生知识工作流的核心变化与行动路径',
    page_count: 6,
    central_message: '把散落的信息、判断和行动接成一条能持续复用的工作流。',
    narrative: {
      opening: '信息越来越多，但上下文仍在不断丢失。',
      problem: '资料、判断与行动分散在不同工具和短期记忆中。',
      insight: '真正需要积累的是可复用的上下文，而不是更多文件。',
      method: '通过收集、关联、判断、行动形成闭环。',
      action: '先改造一条高频流程，再逐步扩展。',
    },
    slides: [
      ['s01','cover','AI 原生知识工作流',['AI 原生知识工作流','让上下文持续产生价值'],'建立主题与核心判断'],
      ['s02','statement','问题不是信息太少，而是上下文不断丢失',['信息很多，上下文却在丢失','资料散落','判断失联','行动断点'],'明确问题'],
      ['s03','comparison','从文件堆积转向上下文复用',['从文件堆积，转向上下文复用','过去：保存结果','现在：保存判断过程'],'提出转变'],
      ['s04','process','四个动作构成闭环',['收集现场','建立关联','形成判断','推进行动'],'解释方法'],
      ['s05','data','价值来自复用次数，而不是文件数量',['价值 = 上下文质量 × 复用次数','一次整理，多次调用'],'给出价值判断'],
      ['s06','closing','先重做一条高频流程',['先重做一条高频流程','把上下文、判断和行动连起来'],'给出行动建议'],
    ].map(([id, role, claim, exact_text, purpose]) => ({ id, role, claim, exact_text, purpose, evidence: [], visual_brief: claim, transition: id === 's06' ? '结束' : '进入下一层叙事' })),
  };
}

export function validateOutline(outline) {
  const errors = [];
  if (!outline.central_message) errors.push('缺少中心含义');
  for (const key of ['opening','problem','insight','method','action']) if (!outline.narrative?.[key]) errors.push(`叙事逻辑缺少 ${key}`);
  if (!Number.isInteger(outline.page_count) || outline.page_count !== outline.slides?.length) errors.push('页数与逐页内容不一致');
  for (const [index, slide] of (outline.slides || []).entries()) {
    if (!slide.claim) errors.push(`第 ${index + 1} 页缺少单页主张`);
    if (!Array.isArray(slide.exact_text) || !slide.exact_text.length) errors.push(`第 ${index + 1} 页缺少准确文字`);
    if (!slide.visual_brief) errors.push(`第 ${index + 1} 页缺少视觉构思`);
  }
  return { valid: errors.length === 0, errors };
}

export function approveOutline(outline, { mode, theme }) {
  const check = validateOutline(outline);
  if (!check.valid) throw new Error(check.errors.join('；'));
  if (!Object.values(MODES).includes(mode)) throw new Error(`未知模式：${mode}`);
  if (!theme) throw new Error('缺少主题');
  return { ...outline, status: 'approved', mode, theme, approved_at: new Date().toISOString() };
}
