import { useState } from 'react';
import { Copy, CheckCircle2, Play, RefreshCw } from 'lucide-react';
import { Button } from '../../ui/Button';
import type { Client } from '../../../types';

export interface CopyScriptButtonProps {
  client: Client;
  onCopyScript: (client: Client) => Promise<void>;
  compact?: boolean;
}

export function CopyScriptButton({
  client,
  onCopyScript,
  compact = false,
}: CopyScriptButtonProps) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    await onCopyScript(client);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  }

  return (
    <Button
      variant="secondary"
      size={compact ? 'sm' : undefined}
      icon={copied ? CheckCircle2 : Copy}
      type="button"
      onClick={handleCopy}
    >
      {copied ? 'Copied!' : compact ? 'Copy' : 'Copy script'}
    </Button>
  );
}

export interface CrawlButtonProps {
  siteId?: string;
  label: string;
  active: boolean;
  disabled?: boolean;
  compact?: boolean;
  onTriggerCrawl: ((siteId: string) => void) | (() => void);
}

export function CrawlButton({
  siteId,
  label,
  active,
  disabled = false,
  compact = false,
  onTriggerCrawl,
}: CrawlButtonProps) {
  return (
    <Button
      variant="secondary"
      size={compact ? 'sm' : undefined}
      icon={active ? RefreshCw : Play}
      spinning={active}
      disabled={active || disabled}
      type="button"
      onClick={() => {
        if (siteId) {
          (onTriggerCrawl as (nextSiteId: string) => void)(siteId);
        } else {
          (onTriggerCrawl as () => void)();
        }
      }}
    >
      {active ? 'Crawling...' : label}
    </Button>
  );
}
