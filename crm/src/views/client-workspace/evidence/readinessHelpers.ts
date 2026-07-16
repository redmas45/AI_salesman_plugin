import type { ReadinessReport } from '../../../types';

export function readinessGapRows(scanReport: ReadinessReport | null): ReadinessReport['capabilities'] {
  return (scanReport?.capabilities ?? []).filter(isBlockingCapabilityGap);
}

export function automationHintForCapability(name: string): string {
  const key = String(name || '').toLowerCase().replace(/[_-]+/g, ' ');
  if (key.includes('flow graph')) return 'Run setup to discover browser flows and save routes/actions.';
  if (key.includes('rehearsal')) return 'Run setup to safely rehearse discovered actions without submitting final outcomes.';
  if (key.includes('confirmation')) return 'Review adapter policy so risky steps require confirmation.';
  if (key.includes('cart') || key.includes('checkout')) return 'Run setup to re-crawl and validate cart or checkout readiness.';
  if (key.includes('catalog') || key.includes('variant')) return 'Run setup or crawl source data to refresh records and vectors.';
  return 'Run setup to refresh crawl, flow discovery, rehearsal, regression, and readiness evidence.';
}

export function isBlockingCapabilityGap(capability: ReadinessReport['capabilities'][number]): boolean {
  return !capability.supported && capability.blocking !== false && !capability.name.startsWith('expected_action:');
}
