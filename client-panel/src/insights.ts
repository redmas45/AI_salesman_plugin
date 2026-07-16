
import type { Analytics, ClientSummary, RankRow } from './types';
import type { ConversationPreview } from './utils';
import { panelText } from './verticalText';

export type InsightTone = 'accent' | 'blue' | 'green' | 'amber' | 'red';

export interface BriefItem {
  title: string;
  detail: string;
  meta: string;
  tone: InsightTone;
}

export interface IntentSignal {
  key: string;
  label: string;
  count: number;
  sessions: number;
  detail: string;
  sample: string;
  action: string;
}

export interface VisitSnapshot {
  siteId: string;
  turns: number;
  sessions: number;
  tokens: number;
  remainingTokens: number;
  topProduct: string;
  capturedAt: number;
}

const STORAGE_PREFIX = 'clientPanel:lastVisit:';

const INTENT_RULES = [
  {
    key: 'buying',
    label: 'Ready to buy',
    regex: /\b(buy|order|purchase|checkout|cart|available|stock|in stock)\b/i,
    action: 'Make the path to product, price, and checkout obvious.',
  },
  {
    key: 'price',
    label: 'Price sensitive',
    regex: /\b(price|cost|cheap|budget|under|discount|offer|deal|rs|inr)\b/i,
    action: 'Show price, discount, and comparable alternatives quickly.',
  },
  {
    key: 'delivery',
    label: 'Delivery or policy',
    regex: /\b(delivery|shipping|return|refund|cod|cash on delivery|exchange)\b/i,
    action: 'Keep policy answers short and link to the next shopping step.',
  },
  {
    key: 'choice',
    label: 'Needs recommendation',
    regex: /\b(which|compare|difference|recommend|best|size|fit|color|variant)\b/i,
    action: 'Use product attributes to narrow options instead of listing everything.',
  },
  {
    key: 'weak',
    label: 'Weak answer risk',
    regex: /\b(sorry|not sure|do not know|don't know|cannot|can't|no information|not available)\b/i,
    action: 'Improve catalog text or assistant fallback for these questions.',
  },
] as const;

export function buildTodayBrief(client: ClientSummary, analytics: Analytics, sessions: ConversationPreview[]): BriefItem[] {
  const text = panelText(client);
  const topProduct = analytics.top_products[0];
  const catalogPct = percentage(client.catalog.active_products, client.catalog.total_products);
  const daysLeft = tokenDaysLeft(client, analytics);
  const items: BriefItem[] = [];

  if (topProduct) {
    items.push({
      title: `Demand is leaning toward ${topProduct.label}`,
      detail: `${topProduct.count} demand signals in the selected range.`,
      meta: `${text.entitySingular} focus`,
      tone: 'accent',
    });
  } else {
    items.push({
      title: 'Demand signal is still forming',
      detail: `Conversations will turn into ${text.entitySingular} priorities once ${text.customerPlural} ask more questions.`,
      meta: `${text.entitySingular} focus`,
      tone: 'amber',
    });
  }

  if (Number.isFinite(daysLeft) && daysLeft > 0) {
    items.push({
      title: `Token runway is about ${Math.ceil(daysLeft)} days`,
      detail: `${client.quota.client.remaining.toLocaleString()} tokens remain at the current pace.`,
      meta: 'Quota forecast',
      tone: daysLeft < 7 ? 'red' : daysLeft < 21 ? 'amber' : 'green',
    });
  } else {
    items.push({
      title: 'Token usage is quiet',
      detail: 'There is not enough daily usage yet to project quota life.',
      meta: 'Quota forecast',
      tone: 'blue',
    });
  }

  if (catalogPct < 85) {
    items.push({
      title: `${text.dataLabel} readiness is ${catalogPct}%`,
      detail: `${client.catalog.active_products.toLocaleString()} of ${client.catalog.total_products.toLocaleString()} ${text.entityPlural} are active for the assistant.`,
      meta: `${text.dataLabel} readiness`,
      tone: catalogPct < 60 ? 'red' : 'amber',
    });
  } else {
    items.push({
      title: `${text.dataLabel} is ready for ${text.customerSingular} questions`,
      detail: `${client.catalog.active_products.toLocaleString()} active ${text.entityPlural} across ${client.catalog.categories.toLocaleString()} groups.`,
      meta: `${text.dataLabel} readiness`,
      tone: 'green',
    });
  }

  if (analytics.peak_day) {
    items.push({
      title: `Peak activity was ${analytics.peak_day.date}`,
      detail: `${analytics.peak_day.turns.toLocaleString()} turns and ${analytics.peak_day.tokens.toLocaleString()} tokens.`,
      meta: 'Traffic pattern',
      tone: 'blue',
    });
  } else if (sessions.length) {
    items.push({
      title: `${sessions.length.toLocaleString()} recent sessions are ready to review`,
      detail: 'Open the intent inbox to find comparison questions, policy issues, and weak answers.',
      meta: 'Conversation review',
      tone: 'blue',
    });
  }

  return items.slice(0, 4);
}

export function buildIntentSignals(sessions: ConversationPreview[]): IntentSignal[] {
  const signals = INTENT_RULES.map((rule) => {
    const matchedSessions = new Set<string>();
    let count = 0;
    let sample = '';

    for (const session of sessions) {
      for (const turn of session.turns) {
        const text = `${turn.intent || ''} ${turn.transcript || ''} ${turn.response_text || ''}`;
        if (!rule.regex.test(text)) continue;
        count += 1;
        matchedSessions.add(session.session_id);
        if (!sample) sample = turnSample(turn.transcript, turn.response_text) || session.session_id;
      }
    }

    return {
      key: rule.key,
      label: rule.label,
      count,
      sessions: matchedSessions.size,
      detail: matchedSessions.size ? `${matchedSessions.size} sessions need attention` : 'No matching sessions in this range',
      sample,
      action: rule.action,
    };
  });

  return signals.sort((a, b) => b.count - a.count);
}

function turnSample(transcript: string, responseText: string): string {
  const parts = [];
  if (transcript) parts.push(`Customer: ${transcript}`);
  if (responseText) parts.push(`Maya: ${responseText}`);
  return parts.join(' | ');
}

export function buildCatalogOpportunities(client: ClientSummary, topProducts: RankRow[]): BriefItem[] {
  const text = panelText(client);
  const catalogPct = percentage(client.catalog.active_products, client.catalog.total_products);
  const opportunities = topProducts.slice(0, 5).map((row, index) => ({
    title: row.label,
    detail: `${row.count} demand signals. ${catalogAction(catalogPct, index, text.entitySingular, text.dataLabel)}`,
    meta: index === 0 ? 'Highest priority' : `Priority ${index + 1}`,
    tone: index === 0 ? 'accent' : catalogPct < 80 ? 'amber' : 'blue',
  })) satisfies BriefItem[];

  if (opportunities.length) return opportunities;

  return [{
    title: text.opportunityEmptyTitle,
    detail: text.opportunityEmptyDetail,
    meta: 'Waiting for signal',
    tone: 'amber',
  }];
}

export function makeVisitSnapshot(client: ClientSummary, analytics: Analytics, sessions: ConversationPreview[]): VisitSnapshot {
  return {
    siteId: client.site_id,
    turns: analytics.metrics.turns,
    sessions: analytics.metrics.sessions ?? sessions.length,
    tokens: analytics.metrics.tokens,
    remainingTokens: client.quota.client.remaining,
    topProduct: analytics.top_products[0]?.label ?? '',
    capturedAt: Date.now(),
  };
}

export function readVisitSnapshot(siteId: string): VisitSnapshot | null {
  try {
    const raw = localStorage.getItem(`${STORAGE_PREFIX}${siteId}`);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as VisitSnapshot;
    return parsed.siteId === siteId ? parsed : null;
  } catch {
    return null;
  }
}

export function writeVisitSnapshot(snapshot: VisitSnapshot): void {
  try {
    localStorage.setItem(`${STORAGE_PREFIX}${snapshot.siteId}`, JSON.stringify(snapshot));
  } catch {
    // Browser storage can be disabled. The panel should still render normally.
  }
}

export function visitChanges(previous: VisitSnapshot | null, current: VisitSnapshot): BriefItem[] {
  if (!previous) {
    return [{
      title: 'First tracked visit in this browser',
      detail: 'The next visit will show what changed since now.',
      meta: 'Baseline saved',
      tone: 'blue',
    }];
  }

  const items: BriefItem[] = [
    deltaItem('New customer sessions', current.sessions - previous.sessions, 'sessions', 'blue'),
    deltaItem('New conversation turns', current.turns - previous.turns, 'turns', 'accent'),
    deltaItem('Token movement', current.tokens - previous.tokens, 'tokens used', 'amber'),
  ].filter((item) => item.detail !== 'No change detected.');

  if (current.topProduct && current.topProduct !== previous.topProduct) {
    items.push({
      title: 'Top demand signal changed',
      detail: `${current.topProduct} is now leading demand.`,
      meta: 'Demand shift',
      tone: 'green',
    });
  }

  return items.length ? items : [{
    title: 'No major movement since last visit',
    detail: 'Demand, turns, and token usage are holding steady.',
    meta: 'Stable',
    tone: 'green',
  }];
}

export function tokenDaysLeft(client: ClientSummary, analytics: Analytics): number {
  const dailyTokens = analytics.series.length
    ? analytics.series.reduce((sum, row) => sum + row.tokens, 0) / analytics.series.length
    : analytics.metrics.tokens;
  if (!dailyTokens) return Number.POSITIVE_INFINITY;
  return client.quota.client.remaining / dailyTokens;
}

export function fullSessionsRemaining(client: ClientSummary): number {
  if (!client.session_token_limit) return 0;
  return Math.floor(client.quota.client.remaining / client.session_token_limit);
}

export function simulateQuestion(
  question: string,
  analytics: Analytics,
  sessions: ConversationPreview[],
  client?: ClientSummary,
): BriefItem[] {
  const text = panelText(client);
  const trimmed = question.trim();
  if (!trimmed) {
    return [{
      title: `Ask a ${text.customerSingular}-style question`,
      detail: 'The preview will classify intent and show what the client should verify.',
      meta: 'Signal preview',
      tone: 'blue',
    }];
  }

  const lower = trimmed.toLowerCase();
  const entities = analytics.top_products.filter((row) => lower.includes(row.label.toLowerCase())).slice(0, 2);
  const fallbackEntities = analytics.top_products.slice(0, 2);
  const matchedSignals = buildIntentSignals(sessions).filter((signal) => signal.count > 0 && lowerMatchesSignal(lower, signal.key));
  const primarySignal = matchedSignals[0] ?? buildIntentSignals(sessions).find((signal) => signal.count > 0);
  const entityText = (entities.length ? entities : fallbackEntities).map((row) => row.label).join(', ');

  return [
    {
      title: primarySignal ? `Likely intent: ${primarySignal.label}` : `Likely intent: ${text.entitySingular} discovery`,
      detail: primarySignal?.action ?? 'Answer with availability, comparison evidence, alternatives, and the clearest next action.',
      meta: 'Routing',
      tone: primarySignal?.key === 'weak' ? 'red' : 'accent',
    },
    {
      title: entityText ? `${text.dataLabel} focus: ${entityText}` : `${text.dataLabel} focus is unclear`,
      detail: entityText ? `Verify these ${text.entityPlural} have clear details, availability, comparison fields, and short descriptions.` : `Add ${text.entitySingular} names or category language that ${text.customerPlural} naturally use.`,
      meta: 'Owner check',
      tone: entityText ? 'green' : 'amber',
    },
  ];
}

function percentage(value: number, total: number): number {
  if (!total) return 0;
  return Math.max(0, Math.min(100, Math.round((value / total) * 100)));
}

function catalogAction(catalogPct: number, index: number, entitySingular = 'item', dataLabel = 'Data'): string {
  if (catalogPct < 60) return 'Fix indexing before spending on traffic.';
  if (catalogPct < 85) return `Check title, details, availability, and comparison fields for this ${entitySingular}.`;
  return index === 0 ? `Feature this in assistant answers and ${dataLabel.toLowerCase()} review.` : 'Keep alternatives ready for comparison questions.';
}

function deltaItem(title: string, delta: number, noun: string, tone: InsightTone): BriefItem {
  if (delta <= 0) {
    return {
      title,
      detail: 'No change detected.',
      meta: 'Since last visit',
      tone,
    };
  }
  return {
    title,
    detail: `+${delta.toLocaleString()} ${noun}.`,
    meta: 'Since last visit',
    tone,
  };
}

function lowerMatchesSignal(lower: string, key: string): boolean {
  if (key === 'buying') return /\b(buy|order|checkout|cart|available|stock)\b/.test(lower);
  if (key === 'price') return /\b(price|cost|cheap|budget|under|discount|offer|deal)\b/.test(lower);
  if (key === 'delivery') return /\b(delivery|shipping|return|refund|cod|exchange)\b/.test(lower);
  if (key === 'choice') return /\b(which|compare|recommend|best|size|fit|color|coverage|premium|plan)\b/.test(lower);
  if (key === 'weak') return /\b(confused|wrong|not answer|missing)\b/.test(lower);
  return false;
}
