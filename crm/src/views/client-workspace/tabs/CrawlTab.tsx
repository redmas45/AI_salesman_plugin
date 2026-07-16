import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import type { Client, CrawlReport, SyncRun } from '../../../types';
import { Panel } from '../../../components/ui/Panel';
import { StatusPill } from '../../../components/ui/Badge';
import { EmptyState } from '../../../components/ui/EmptyState';
import { NoticeBanner } from '../../../components/shared/NoticeBanner';
import { TechnicalDetails } from '../../../components/shared/TechnicalDetails';
import { CrawlButton } from '../../../components/shared/ClientActions';
import { number, percent, shortTime } from '../../../utils/format';
import type { CrmVerticalDefinition } from '../../../verticals/types';
import { KeyValue, Meter, MetricCard } from '../components/workspaceCards';
export function ClientCrawlTab({
  client,
  crawlReport,
  crawling,
  automationLocked,
  sourceReachable,
  sourceStatus,
  onTriggerCrawl,
  vertical,
}: {
  client: Client;
  crawlReport: CrawlReport | null;
  crawling: boolean;
  automationLocked: boolean;
  sourceReachable: boolean;
  sourceStatus: string;
  onTriggerCrawl: () => void;
  vertical: CrmVerticalDefinition;
}) {
  return (
    <div className="tab-content fade-in">
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">Crawl report</h2>
          <p className="mt-1 text-sm text-muted">Source coverage, page issues, extraction totals, and sync history.</p>
        </div>
        <CrawlButton label="Start crawl" active={crawling} disabled={automationLocked || !sourceReachable} onTriggerCrawl={onTriggerCrawl} />
      </section>
      {!automationLocked && !sourceReachable ? (
        <NoticeBanner
          tone="info"
          message={`Crawl is locked because the source website is ${sourceStatus}. AI Hub cannot refresh products, records, pages, or flows until the site is online.`}
        />
      ) : null}
      <CrawlReportSummary report={crawlReport} vertical={vertical} />
      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Panel title="Crawl issues">
          {crawlReport ? (
            <CrawlIssueBoard report={crawlReport} />
          ) : (
            <EmptyState text="No crawl report is saved yet. Run a crawl to generate one." />
          )}
        </Panel>
        <Panel title="Sync run history">
          <SyncRunTimeline runs={client.sync_runs ?? []} />
        </Panel>
      </div>
      {crawlReport ? <TechnicalDetails title="Advanced crawl JSON" data={crawlReport} /> : null}
    </div>
  );
}

function CrawlReportSummary({ report, vertical }: { report: CrawlReport | null; vertical: CrmVerticalDefinition }) {
  if (!report) return <EmptyState text="Crawl report will appear here after the next priority crawl." />;
  const issueCount = report.pages_failed + report.pages_blocked;
  return (
    <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-5">
      <MetricCard label={`${activeEntityTitle(vertical)} found`} value={report.product_count} detail="Extracted source rows" />
      <MetricCard label="Variants found" value={report.variant_count} detail="Entity options" />
      <MetricCard label="Categories found" value={report.category_count} detail="Navigation coverage" />
      <MetricCard label="Page issues" value={issueCount} detail={`${number(report.pages_failed)} failed, ${number(report.pages_blocked)} blocked`} />
      <MetricCard label="Stopped by limit" value={report.stopped_by_limit ? 'Yes' : 'No'} detail={report.source_type || 'crawler'} />
    </div>
  );
}

function CrawlIssueBoard({ report }: { report: CrawlReport }) {
  const issueCount = report.pages_failed + report.pages_blocked;
  return (
    <div className="crawl-report-board">
      <div className="crawl-coverage-card">
        <div>
          <span>Coverage score</span>
          <strong>{percent(report.coverage_score)}%</strong>
          <p>{issueCount ? `${number(issueCount)} page issue(s) need review.` : 'No failed or blocked pages were saved in this report.'}</p>
        </div>
        <Meter label="Coverage" value={percent(report.coverage_score)} tone="accent" />
      </div>
      <div className="crawl-issue-grid">
        <CrawlIssueCard title="Failed pages" count={report.pages_failed} urls={report.failed_urls} />
        <CrawlIssueCard title="Blocked pages" count={report.pages_blocked} urls={report.blocked_urls} />
      </div>
      <div className="crawl-run-meta">
        <KeyValue label="Visited pages" value={report.pages_visited} />
        <KeyValue label="Duration" value={`${number(report.duration_ms)} ms`} />
        <KeyValue label="Created" value={shortTime(report.created_at)} />
      </div>
    </div>
  );
}

function CrawlIssueCard({ title, count, urls }: { title: string; count: number; urls: string[] }) {
  return (
    <article className={`crawl-issue-card ${count ? 'warn' : 'ok'}`}>
      <div className="crawl-issue-head">
        <strong>{title}</strong>
        <StatusPill value={count ? 'needs review' : 'ok'} />
      </div>
      <span>{number(count)}</span>
      {count ? <UrlList title="Inspect URLs" urls={urls} /> : <p>No URLs in this group.</p>}
    </article>
  );
}

function SyncRunTimeline({ runs }: { runs: SyncRun[] }) {
  if (!runs.length) return <EmptyState text="No sync runs are recorded yet." />;
  return (
    <div className="sync-timeline">
      {runs.map((run) => (
        <article key={`${run.id}-${run.created_at}`} className="sync-run-card">
          <div className="sync-run-dot" />
          <div>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <strong>{run.source_name || 'catalog sync'}</strong>
              <span className="text-xs text-muted">{shortTime(run.created_at)}</span>
            </div>
            <div className="sync-run-metrics">
              <span>{number(run.source_count)} sourced</span>
              <span>{number(run.changed_count)} changed</span>
              <span>{number(run.vectorized_count)} vectorized</span>
              <span>{number(run.deactivated_count)} inactive</span>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}

function UrlList({ title, urls }: { title: string; urls: string[] }) {
  const [open, setOpen] = useState(false);
  if (!urls.length) return null;
  return (
    <div className="url-list">
      <button className="summary-toggle" type="button" onClick={() => setOpen((current) => !current)}>
        <ChevronDown className={open ? 'open' : ''} size={16} aria-hidden="true" />
        <span>{title} ({urls.length})</span>
      </button>
      {open ? (
        <div className="grid gap-2 pt-3">
        {urls.slice(0, 12).map((url) => (
          <code key={url}>{url}</code>
        ))}
        </div>
      ) : null}
    </div>
  );
}

function activeEntityTitle(vertical: CrmVerticalDefinition) {
  const text = vertical.entityLabelPlural || 'items';
  return text.charAt(0).toUpperCase() + text.slice(1);
}
