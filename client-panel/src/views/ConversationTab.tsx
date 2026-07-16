import { ConversationPanel } from '../components/ConversationPanel';
import { IntentInbox } from '../components/InsightPanels';
import { number, type ConversationPreview } from '../utils';
import type { ClientSummary } from '../types';
import { panelText } from '../verticalText';

export function ConversationTab({ client, sessions }: { client: ClientSummary; sessions: ConversationPreview[] }) {
  const text = panelText(client);
  return (
    <div className="tab-stack tab-content fade-in">
      <div className="section-intro">
        <div>
          <p className="eyebrow">Conversations</p>
          <h2>Recent {text.customerSingular} sessions</h2>
        </div>
        <span>{number(sessions.length)} sessions in range</span>
      </div>
      <IntentInbox client={client} sessions={sessions} />
      <ConversationPanel client={client} sessions={sessions} />
    </div>
  );
}
