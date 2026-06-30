import { useEffect, useState } from 'react';
import { CheckCircle2, Copy, Plug, RefreshCw } from 'lucide-react';
import { crmApi } from '../../api';
import type { UniversalInstallerResponse } from '../../types';
import { Button } from '../ui/Button';
import { Panel } from '../ui/Panel';
import { StatusPill } from '../ui/Badge';

interface UniversalInstallerPanelProps {
  compact?: boolean;
}

export function UniversalInstallerPanel({ compact = false }: UniversalInstallerPanelProps) {
  const [installer, setInstaller] = useState<UniversalInstallerResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    void loadInstaller();
  }, []);

  async function loadInstaller() {
    setLoading(true);
    setError('');
    try {
      setInstaller(await crmApi.installer());
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Installer failed to load.');
    } finally {
      setLoading(false);
    }
  }

  async function copyInstaller() {
    if (!installer?.script_tag) return;
    await navigator.clipboard.writeText(installer.script_tag);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  }

  const scriptTag = installer?.script_tag || '<script defer src="/install.js"></script>';

  return (
    <Panel
      title="Universal installer"
      action={
        <div className="flex flex-wrap items-center gap-2">
          <StatusPill value={installer?.mode || 'auto_onboarding'} />
          <Button
            type="button"
            size="sm"
            variant="secondary"
            icon={loading ? RefreshCw : copied ? CheckCircle2 : Copy}
            spinning={loading}
            disabled={loading || !installer?.script_tag}
            onClick={copyInstaller}
          >
            {copied ? 'Copied' : 'Copy'}
          </Button>
        </div>
      }
    >
      <div className={compact ? 'universal-installer compact' : 'universal-installer'}>
        <div className="universal-installer-copy">
          <div className="installer-icon">
            <Plug size={18} aria-hidden="true" />
          </div>
          <div>
            <p className="text-sm text-muted">
              Paste this same script into any independent website. AI Hub will create the client from the live page,
              bind the origin, detect the vertical, generate prompts, and leave it Available until you explicitly move it to Current.
            </p>
            {installer?.script_url ? (
              <p className="mt-2 text-xs text-muted overflow-wrap-anywhere">{installer.script_url}</p>
            ) : null}
          </div>
        </div>
        {error ? <div className="notice notice-error">{error}</div> : null}
        <pre className="code-block install-script universal-code">{scriptTag}</pre>
      </div>
    </Panel>
  );
}
