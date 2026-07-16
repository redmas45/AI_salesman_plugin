import type { ClientBoardSection } from '../../types';
import { number } from '../../utils/format';

type ClientBoardCounts = {
  current: number;
  available: number;
  online: number;
  offline: number;
};

export function ClientBoardFocus({
  section,
  label,
  query,
  counts,
  onOpenSection,
}: {
  section: ClientBoardSection;
  label: string;
  query: string;
  counts: ClientBoardCounts;
  onOpenSection: (section: ClientBoardSection) => void;
}) {
  const next = clientBoardNextStep(section, counts);
  const target = clientBoardRecommendedSection(section, counts);
  return (
    <section className="client-board-focus" aria-label="Active client board section">
      <div className="client-board-focus-copy">
        <span>Viewing</span>
        <strong>{label}</strong>
        <small>
          {query
            ? `Filtered by "${query}"`
            : `${number(counts.current)} current / ${number(counts.available)} available / ${number(counts.online)} online / ${number(counts.offline)} offline`}
        </small>
      </div>
      <button className="client-board-next-step" type="button" onClick={() => onOpenSection(target)}>
        <span>Next step</span>
        <strong>{next}</strong>
        <small>{clientBoardRecommendedLabel(target)}</small>
      </button>
    </section>
  );
}

function clientBoardNextStep(section: ClientBoardSection, counts: ClientBoardCounts) {
  if (section === 'current') {
    if (!counts.current) return 'Move an online available install to Current before running setup or crawl.';
    return 'Open a client workspace, then run setup, readiness, or crawl only when you explicitly choose it.';
  }
  if (section === 'online') {
    if (!counts.online) return 'Start the test website and refresh AI Hub; online installs will appear here.';
    return 'Inspect the website and owner panel, then add the install to Current if it should be managed.';
  }
  if (section === 'offline') {
    if (!counts.offline) return 'No detected installs are unreachable right now.';
    return 'These installs were detected before, but the source website is not reachable from AI Hub right now.';
  }
  if (section === 'available') {
    if (!counts.available) return 'Install the script on a website and open that site once to create an Available install.';
    return 'Use Online installs for active testing; Offline installs are visible for traceability only.';
  }
  return 'Use Current for managed clients and Available for detected installs awaiting approval.';
}

function clientBoardRecommendedSection(section: ClientBoardSection, counts: ClientBoardCounts): ClientBoardSection {
  if (section === 'current' && !counts.current) return counts.online ? 'online' : 'available';
  if (section === 'available') return counts.online ? 'online' : counts.offline ? 'offline' : 'all';
  if (section === 'online' && !counts.online) return counts.available ? 'available' : 'all';
  if (section === 'offline' && !counts.offline) return counts.available ? 'available' : 'all';
  return section;
}

function clientBoardRecommendedLabel(section: ClientBoardSection) {
  if (section === 'current') return 'Open current clients';
  if (section === 'available') return 'Open available installs';
  if (section === 'online') return 'Open online installs';
  if (section === 'offline') return 'Open offline installs';
  return 'Open all clients';
}
