import {
  ClipboardCheck,
  Gauge,
  KeyRound,
  PackageOpen,
  Settings,
  ShieldCheck,
  type LucideIcon,
} from 'lucide-react';
import type { CapabilitiesSummary, Client, CrawlReport, ReadinessReport } from '../../../types';
import type { ClientWorkspaceTabId, CrmVerticalDefinition } from '../../../verticals/types';
import { Button } from '../../../components/ui/Button';
import { Panel } from '../../../components/ui/Panel';
import { StatusPill } from '../../../components/ui/Badge';
import { EmptyState } from '../../../components/ui/EmptyState';
import { NoticeBanner } from '../../../components/shared/NoticeBanner';
import { TechnicalDetails } from '../../../components/shared/TechnicalDetails';
import { number, panelPasswordLabel } from '../../../utils/format';
import { KeyValue } from '../components/workspaceCards';
import { SmokeTestEvidence } from '../evidence/SmokeTestEvidence';
import { DomainActionCoveragePanel, ReadinessGapEvidencePanel } from '../evidence/SetupEvidencePanels';
import { PromptSmokeRunConsole } from '../operations/PromptSmokeRunConsole';
import type { SmokeTestFeedbackState } from '../operations/promptSmokeModel';
import {
  actionHealthSummary,
  assistantSmokeSummary,
  currentIntegrationStageLabel,
  integrationFixes,
  integrationGaps,
  integrationInitializationSummary,
  integrationScore,
  integrationSmokeTests,
  integrationStageRows,
  liveIntegrationStageRows,
  nextIntegrationAction,
  safeRecord,
  smokeTestHeadline,
  type IntegrationStageRow,
} from '../evidence/integrationEvidence';

export function ClientIntegrationTab({
  client,
  capabilities,
  scanReport,
  crawlReport,
  standaloneSmokeReport,
  smokeTestFeedback,
  smokeTesting,
  crawling,
  autoIntegrating,
  automationLocked,
  onRunAssistantSmokeTests,
  onOpenTab,
  vertical,
}: {
  client: Client;
  capabilities: CapabilitiesSummary | null;
  scanReport: ReadinessReport | null;
  crawlReport: CrawlReport | null;
  standaloneSmokeReport: Record<string, unknown> | null;
  smokeTestFeedback: SmokeTestFeedbackState | null;
  smokeTesting: boolean;
  crawling: boolean;
  autoIntegrating: boolean;
  automationLocked: boolean;
  onRunAssistantSmokeTests: () => void;
  onOpenTab: (tab: ClientWorkspaceTabId) => void;
  vertical: CrmVerticalDefinition;
}) {
  const verticalConfig = safeRecord(client.vertical_config);
  const initialization = safeRecord(verticalConfig.initialization);
  const flow = safeRecord(verticalConfig.flow);
  const rehearsal = safeRecord(verticalConfig.rehearsal);
  const regression = safeRecord(verticalConfig.regression);
  const actionHealth = safeRecord(verticalConfig.action_health);
  const actionPolicy = safeRecord(verticalConfig.action_policy);
  const savedStandaloneSmokeReport = safeRecord(verticalConfig.assistant_smoke_tests);
  const latestStandaloneSmokeReport = standaloneSmokeReport ?? savedStandaloneSmokeReport;
  const stageRows = integrationStageRows(initialization, {
    crawlReport,
    flow,
    rehearsal,
    regression,
    scanReport,
  });
  const visibleStageRows = liveIntegrationStageRows(stageRows, autoIntegrating);
  const preferStandaloneSmokeReport = Boolean(standaloneSmokeReport);
  const smokeTests = integrationSmokeTests(stageRows, latestStandaloneSmokeReport, preferStandaloneSmokeReport);
  const score = integrationScore(client, capabilities, stageRows, flow, rehearsal, actionHealth, smokeTests);
  const gaps = integrationGaps(client, capabilities, stageRows, flow, actionHealth, actionPolicy, automationLocked, smokeTests);
  const fixes = integrationFixes(gaps, vertical);

  return (
    <div className="tab-content fade-in">
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">Setup run</h2>
          <p className="mt-1 text-sm text-muted">
            One guided evidence run for crawl, adapter discovery, action rehearsal, readiness, prompt checks, gaps, and next fixes.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" icon={ClipboardCheck} disabled={smokeTesting || automationLocked} onClick={onRunAssistantSmokeTests}>
            {smokeTesting ? 'Testing prompts...' : 'Run prompt tests'}
          </Button>
        </div>
      </section>

      {automationLocked ? (
        <NoticeBanner
          tone="info"
          message="This client is Available. Move it to Current before running setup; activation itself will not crawl or start setup."
        />
      ) : null}
      {autoIntegrating ? (
        <NoticeBanner
          tone="info"
          message="Setup run is queued or running now. This view refreshes backend stage evidence every 10 seconds until the run finishes."
        />
      ) : null}
      <PromptSmokeRunConsole
        feedback={smokeTestFeedback}
        latestReport={latestStandaloneSmokeReport}
        onOpenEvidence={() => {
          document.getElementById('assistant-prompt-evidence')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }}
      />

      <div className="integration-score-grid">
        <section className="card integration-score-card">
          <span className="kpi-label">Setup picture</span>
          <strong className="kpi-value">{score}%</strong>
          <p className="text-sm text-muted">Weighted from lifecycle, crawl data, vectors, flow discovery, rehearsal, readiness, action health, and prompt evidence.</p>
        </section>
        <Panel title="Current status">
          <KeyValue label="Lifecycle" value={automationLocked ? 'Available discovery' : 'Current client'} />
          <KeyValue label="Pipeline" value={integrationInitializationSummary(initialization, autoIntegrating)} />
          <KeyValue label="Current stage" value={currentIntegrationStageLabel(visibleStageRows)} />
          <KeyValue label="Next action" value={nextIntegrationAction(gaps, automationLocked, autoIntegrating)} />
          <KeyValue label="Catalog / knowledge" value={`${number(client.catalog.active_products)} active, ${number(client.catalog.missing_embeddings)} missing vectors`} />
          <KeyValue label="Readiness" value={capabilities ? `${capabilities.supported.length} supported, ${capabilities.unsupported.length} needs work` : 'not scanned'} />
          <KeyValue label="Prompt tests" value={assistantSmokeSummary(stageRows, latestStandaloneSmokeReport, preferStandaloneSmokeReport)} />
          <KeyValue label="Action health" value={actionHealthSummary(actionHealth)} />
          <KeyValue label="Evidence refresh" value={autoIntegrating || crawling ? 'polling from backend' : 'refreshes after setup, crawl, or scan changes'} />
        </Panel>
        <IntegrationEvidenceMap
          client={client}
          capabilities={capabilities}
          crawlReport={crawlReport}
          visibleStageRows={visibleStageRows}
          smokeSummary={assistantSmokeSummary(stageRows, latestStandaloneSmokeReport, preferStandaloneSmokeReport)}
          onOpenTab={onOpenTab}
        />
      </div>

      <DomainActionCoveragePanel scanReport={scanReport} vertical={vertical} onOpenTab={onOpenTab} />
      <ReadinessGapEvidencePanel scanReport={scanReport} onOpenTab={onOpenTab} />

      <Panel title="Setup stages">
        <div className="integration-stage-list">
          {visibleStageRows.map((stage) => (
            <article key={stage.name} className={`integration-stage integration-stage-${stage.status}`}>
              <div className="integration-stage-head">
                <StatusPill value={stage.status} />
                <strong>{stage.label}</strong>
              </div>
              <p>{stage.message}</p>
              <small>{stage.detail}</small>
            </article>
          ))}
        </div>
      </Panel>

      {smokeTests.length ? (
        <Panel title="Assistant prompt smoke tests">
          <div id="assistant-prompt-evidence" className="panel-anchor" />
          <div className="integration-list">
            {smokeTests.map((test) => (
              <article key={test.name} className={`integration-list-item ${test.status === 'failed' ? 'high' : ''}`}>
                <StatusPill value={test.status} />
                <div>
                  <strong>{test.prompt}</strong>
                  <p>{smokeTestHeadline(test)}</p>
                  <SmokeTestEvidence test={test} />
                </div>
              </article>
            ))}
          </div>
        </Panel>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-2">
        <Panel title="What is still pending">
          {gaps.length ? (
            <div className="integration-list">
              {gaps.map((gap) => (
                <article key={gap.title} className={`integration-list-item ${gap.severity}`}>
                  <StatusPill value={gap.severity} />
                  <div>
                    <strong>{gap.title}</strong>
                    <p>{gap.detail}</p>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <EmptyState title="No blocking gaps found" message="The latest CRM evidence does not show a blocking setup gap. Keep testing real prompts after site layout changes." />
          )}
        </Panel>
        <Panel title="Recommended fixes">
          <div className="integration-list">
            {fixes.map((fix) => (
              <article key={fix.title} className="integration-list-item">
                <StatusPill value={fix.kind} />
                <div>
                  <strong>{fix.title}</strong>
                  <p>{fix.detail}</p>
                </div>
              </article>
            ))}
          </div>
        </Panel>
      </div>

      <div className="grid gap-4">
        <TechnicalDetails title="Saved initialization report JSON" data={initialization} />
      </div>
    </div>
  );
}

function IntegrationEvidenceMap({
  client,
  capabilities,
  crawlReport,
  visibleStageRows,
  smokeSummary,
  onOpenTab,
}: {
  client: Client;
  capabilities: CapabilitiesSummary | null;
  crawlReport: CrawlReport | null;
  visibleStageRows: IntegrationStageRow[];
  smokeSummary: string;
  onOpenTab: (tab: ClientWorkspaceTabId) => void;
}) {
  const readinessTotal = (capabilities?.supported.length ?? 0) + (capabilities?.unsupported.length ?? 0);
  return (
    <Panel title="Evidence map">
      <div className="evidence-link-grid">
        <EvidenceLink
          icon={PackageOpen}
          label="Data"
          value={`${number(client.catalog.active_products)} active`}
          detail={`${number(client.catalog.missing_embeddings)} missing vectors`}
          onClick={() => onOpenTab('catalog')}
        />
        <EvidenceLink
          icon={Gauge}
          label="Crawl"
          value={crawlReport ? `${number(crawlReport.pages_visited)} pages` : 'not saved'}
          detail={client.last_crawl_status || 'not started'}
          onClick={() => onOpenTab('crawl')}
        />
        <EvidenceLink
          icon={ShieldCheck}
          label="Readiness"
          value={capabilities ? `${capabilities.supported.length}/${readinessTotal} checks` : 'not scanned'}
          detail={capabilities ? `${capabilities.unsupported.length} need work` : 'run setup'}
          onClick={() => onOpenTab('readiness')}
        />
        <EvidenceLink
          icon={Settings}
          label="Adapter"
          value={currentIntegrationStageLabel(visibleStageRows)}
          detail="actions, candidates, repairs"
          onClick={() => onOpenTab('adapter')}
        />
        <EvidenceLink
          icon={ClipboardCheck}
          label="Prompts"
          value={smokeSummary}
          detail="profile and smoke checks"
          onClick={() => onOpenTab('prompt')}
        />
        <EvidenceLink
          icon={KeyRound}
          label="Owner access"
          value={panelPasswordLabel(client)}
          detail="managed from Controls"
          onClick={() => onOpenTab('controls')}
        />
      </div>
    </Panel>
  );
}

function EvidenceLink({
  icon: Icon,
  label,
  value,
  detail,
  onClick,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  detail: string;
  onClick: () => void;
}) {
  return (
    <button className="evidence-link-card" type="button" onClick={onClick}>
      <Icon aria-hidden="true" />
      <span>
        <small>{label}</small>
        <strong>{value}</strong>
        <em>{detail}</em>
      </span>
    </button>
  );
}
