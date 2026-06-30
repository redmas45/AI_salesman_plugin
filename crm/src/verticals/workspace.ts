import type { Client } from '../types';
import { getCrmVertical } from './registry';
import { tab as verticalTab } from './shared';
import type { ClientWorkspaceTabDefinition, ClientWorkspaceTabId } from './types';

export function clientWorkspaceTabs(client: Client): ClientWorkspaceTabDefinition[] {
  const vertical = getCrmVertical(client.vertical_key);
  const withSetupEvidence = ensureTabAfter(vertical.clientTabs, 'readiness', verticalTab('integration', 'Setup evidence'));
  return ensureTabBefore(withSetupEvidence, 'prompt', verticalTab('adapter', 'Adapter'));
}

function ensureTabAfter(
  tabs: ClientWorkspaceTabDefinition[],
  anchor: ClientWorkspaceTabId,
  tab: ClientWorkspaceTabDefinition,
) {
  if (tabs.some((item) => item.id === tab.id)) return tabs;
  const index = tabs.findIndex((item) => item.id === anchor);
  const insertAt = index >= 0 ? index + 1 : 1;
  return [...tabs.slice(0, insertAt), tab, ...tabs.slice(insertAt)];
}

function ensureTabBefore(
  tabs: ClientWorkspaceTabDefinition[],
  anchor: ClientWorkspaceTabId,
  tab: ClientWorkspaceTabDefinition,
) {
  if (tabs.some((item) => item.id === tab.id)) return tabs;
  const index = tabs.findIndex((item) => item.id === anchor);
  const insertAt = index >= 0 ? index : tabs.length;
  return [...tabs.slice(0, insertAt), tab, ...tabs.slice(insertAt)];
}
