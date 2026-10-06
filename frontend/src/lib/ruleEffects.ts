export type RuleMatch = { unit_id: string; char_start: number; char_end: number; keyword: string };
export type RuleEffect = { rule_version: string; effect: string; outcome: string; before: unknown; after: unknown; target?: string; source?: string; matches?: RuleMatch[]; config_version?: number };

export function ruleLabel(effect: RuleEffect): string {
  return (effect.source?.replace(/^rule:/, '') || effect.rule_version.replace(/@(\d+)$/, '@v$1')).replace('@v', ' v');
}

export function ruleOverrides(effects: RuleEffect[] = []): Record<string, RuleEffect> {
  return Object.fromEntries(effects.filter((effect) => effect.effect === 'rule' && effect.outcome === 'used' &&
    ['ai_need', 'feasibility', 'urgency', 'lead_org'].includes(effect.target || '') && effect.before !== effect.after)
    .map((effect) => [effect.target!, effect]));
}
