import { summaryLines } from '../utils';
import { PanelHeader } from './ui';

export function StoreSummary({ title, summary, source }: { title: string; summary: string; source: string }) {
  const lines = summaryLines(summary);
  return (
    <section className="panel summary-panel">
      <PanelHeader title={title} detail={source} />
      <div className="summary-list">
        {lines.map((line) => (
          <p key={line}>{line}</p>
        ))}
      </div>
    </section>
  );
}
