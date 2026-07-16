import { Code2, Plug, RotateCcw, Save, ShieldCheck } from 'lucide-react';
import type { Dispatch, SetStateAction } from 'react';
import type { AdapterConfigResponse, Client } from '../../../types';
import type { CrmVerticalDefinition } from '../../../verticals/types';
import { Button } from '../../../components/ui/Button';
import { EmptyState } from '../../../components/ui/EmptyState';
import { Panel } from '../../../components/ui/Panel';
import {
  actionPolicySummary,
  barrierSummaryText,
  capabilitySummary,
  flowSummaryText,
  formatConfidence,
  initializationSummary,
  regressionSummaryText,
  rehearsalSummaryText,
  validationSummary,
  verticalDecisionLabel,
} from './adapterFormatters';

interface AdapterOverviewPanelsProps {
  client: Client;
  vertical: CrmVerticalDefinition;
  adapter: AdapterConfigResponse | null;
  discovery: Record<string, unknown>;
  initialization: Record<string, unknown>;
  validation: Record<string, unknown>;
  flowSummary: Record<string, unknown>;
  barrierSummary: Record<string, unknown>;
  rehearsalSummary: Record<string, unknown>;
  regression: Record<string, unknown>;
  regressionSummary: Record<string, unknown>;
  runtimeCapabilities: Record<string, unknown>;
  runtimeCapabilityRows: Array<{ label: string; value: string | number }>;
  actionNames: string[];
  blockedActions: string[];
  runtimeBlockedActions: string[];
  handoffActions: string[];
  actionCandidates: Record<string, unknown>[];
  actionDraft: string;
  savingActions: boolean;
  setActionDraft: Dispatch<SetStateAction<string>>;
  saveActionMap: () => void;
  resetActionDraft: () => void;
}

export function AdapterOverviewPanels({
  client,
  vertical,
  adapter,
  discovery,
  initialization,
  validation,
  flowSummary,
  barrierSummary,
  rehearsalSummary,
  regression,
  regressionSummary,
  runtimeCapabilities,
  runtimeCapabilityRows,
  actionNames,
  blockedActions,
  runtimeBlockedActions,
  handoffActions,
  actionCandidates,
  actionDraft,
  savingActions,
  setActionDraft,
  saveActionMap,
  resetActionDraft,
}: AdapterOverviewPanelsProps) {
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <div className="grid gap-4 align-start">
        <Panel title="Detected runtime binding" action={<Plug size={16} aria-hidden="true" />}>
          <div className="mt-3 grid gap-2 text-sm">
            <KeyValue label="Site ID" value={client.site_id} />
            <KeyValue label="Origin" value={client.allowed_origin || client.store_url} />
            <KeyValue label="Adapter mode" value={adapter?.runtime_config.adapter.mode || '-'} />
            <KeyValue label="Platform" value={adapter?.runtime_config.adapter.platform || 'auto'} />
            <KeyValue label="Vertical" value={String(adapter?.runtime_config.vertical.key || vertical.key)} />
            <KeyValue label="Discovery" value={formatConfidence(discovery.confidence)} />
            <KeyValue
              label="Vertical decision"
              value={verticalDecisionLabel(discovery, String(adapter?.runtime_config.vertical.key || vertical.key))}
            />
            <KeyValue label="Initialization" value={initializationSummary(initialization)} />
            <KeyValue label="Action policy" value={actionPolicySummary(blockedActions, handoffActions)} />
            <KeyValue label="Validation" value={validationSummary(validation.summary)} />
            <KeyValue label="Flow graph" value={flowSummaryText(flowSummary)} />
            <KeyValue label="Barriers" value={barrierSummaryText(barrierSummary)} />
            <KeyValue label="Rehearsal" value={rehearsalSummaryText(rehearsalSummary)} />
            <KeyValue label="Site changes" value={regressionSummaryText(regression.status, regressionSummary)} />
            <KeyValue label="Script runtime" value={capabilitySummary(runtimeCapabilities)} />
            <KeyValue label="Selectors" value={adapter?.runtime_config.adapter.selector_validated ? 'validated' : 'generated'} />
          </div>
        </Panel>

        <Panel title="Detected actions" action={<Code2 size={16} aria-hidden="true" />}>
          {actionNames.length ? (
            <div className="action-chip-grid">
              {actionNames.map((action) => (
                <span key={action} className="action-chip">
                  {action}
                </span>
              ))}
            </div>
          ) : (
            <EmptyState text="No generated actions yet. Open the client site with the install script, then run crawl/readiness." />
          )}
        </Panel>
      </div>

      <div className="grid gap-4 align-start">
        <Panel title="Runtime permissions" action={<ShieldCheck size={16} aria-hidden="true" />}>
          <div className="grid gap-3">
            <details className="crm-disclosure" open>
              <summary>
                <span>Allowed browser actions</span>
                <strong>{actionNames.length}</strong>
              </summary>
              {actionNames.length ? (
                <div className="action-chip-grid p-3">
                  {actionNames.map((action) => (
                    <span key={action} className="action-chip">
                      {action}
                    </span>
                  ))}
                </div>
              ) : (
                <div className="p-3">
                  <EmptyState text="No generated actions yet. Open the client site with the install script, then run setup." />
                </div>
              )}
            </details>

            <details className="crm-disclosure">
              <summary>
                <span>Restricted or handoff actions</span>
                <strong>{blockedActions.length + runtimeBlockedActions.length + handoffActions.length}</strong>
              </summary>
              <div className="grid gap-2 p-3 text-sm">
                <KeyValue label="Blocked" value={blockedActions.length ? blockedActions.join(', ') : 'none'} />
                <KeyValue label="Runtime repair blocked" value={runtimeBlockedActions.length ? runtimeBlockedActions.join(', ') : 'none'} />
                <KeyValue label="Handoff" value={handoffActions.length ? handoffActions.join(', ') : 'none'} />
              </div>
            </details>

            <details className="crm-disclosure">
              <summary>
                <span>Script capabilities</span>
                <strong>{capabilitySummary(runtimeCapabilities)}</strong>
              </summary>
              {runtimeCapabilityRows.length ? (
                <div className="grid gap-2 p-3 text-sm">
                  {runtimeCapabilityRows.map((row) => (
                    <KeyValue key={row.label} label={row.label} value={row.value} />
                  ))}
                </div>
              ) : (
                <div className="p-3">
                  <EmptyState text="Open the client site with the install script to report runtime capabilities." />
                </div>
              )}
            </details>

            {actionCandidates.length ? (
              <p className="text-xs text-muted">
                Low-confidence discoveries are kept as diagnostics only. Confident actions are approved automatically during setup.
              </p>
            ) : null}
          </div>
        </Panel>

        <Panel title="Action map editor">
          <div className="grid gap-3">
            <textarea
              className="textarea textarea-lg code-textarea"
              value={actionDraft}
              onChange={(event) => setActionDraft(event.currentTarget.value)}
              spellCheck={false}
            />
            <div className="flex flex-wrap items-center gap-2">
              <Button icon={Save} disabled={savingActions} onClick={saveActionMap}>
                {savingActions ? 'Saving...' : 'Save actions'}
              </Button>
              <Button variant="secondary" icon={RotateCcw} disabled={savingActions} onClick={resetActionDraft}>
                Reset
              </Button>
            </div>
          </div>
        </Panel>
      </div>
    </div>
  );
}

function KeyValue({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="grid grid-cols-[130px_minmax(0,1fr)] gap-3 border-b border-line py-2 last:border-b-0">
      <span className="text-muted">{label}</span>
      <strong className="min-w-0 overflow-wrap-anywhere">{value == null || value === '' ? '-' : value}</strong>
    </div>
  );
}
