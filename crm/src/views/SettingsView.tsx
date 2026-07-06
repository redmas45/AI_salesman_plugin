import { useEffect, useState, useMemo, type FormEvent } from 'react';
import { Bot, ChevronDown, Globe2, KeyRound, RotateCw, Search, ShieldCheck, WalletCards, X, type LucideIcon } from 'lucide-react';
import type { SettingsResponse, Setting } from '../types';
import { Button } from '../components/ui/Button';
import { NoticeBanner } from '../components/shared/NoticeBanner';
import { number } from '../utils/format';

interface SettingNotice {
  tone: 'success' | 'error' | 'info';
  message: string;
}

type SettingsFocus = 'all' | 'runtime' | 'provider' | 'crawler' | 'deployment' | 'secrets';

const NUMERIC_SETTING_LABELS: Record<string, string> = {
  LLM_TEMPERATURE: 'LLM temperature',
  LLM_MAX_TOKENS: 'LLM max tokens',
  LLM_MAX_TOKENS_HARD_CAP: 'LLM hard token cap',
  OPENAI_MONTHLY_BUDGET_USD: 'OpenAI monthly budget',
  OPENAI_USAGE_REFRESH_SECONDS: 'OpenAI usage refresh seconds',
  RAG_TOP_K: 'RAG top K',
  RAG_TOP_N: 'RAG top N',
  CRAWL_MAX_PAGES: 'Crawler max pages',
  CRAWL_MAX_DEPTH: 'Crawler max depth',
  PORT: 'Hub port',
  STOREFRONT_PORT: 'Storefront port',
  BACKEND_PORT: 'Backend port',
  HTTPS_PORT: 'HTTPS port',
};

const INTEGER_SETTING_RANGES: Record<string, [number, number]> = {
  RAG_TOP_K: [1, 100],
  RAG_TOP_N: [1, 100],
  CRAWL_MAX_PAGES: [1, 10000],
  CRAWL_MAX_DEPTH: [0, 20],
};

const SETTING_GROUPS = [
  {
    title: 'Speech-to-text',
    keys: ['STT_PROVIDER', 'STT_MODEL', 'GROQ_STT_MODEL', 'STT_LANGUAGE'],
  },
  {
    title: 'Text-to-speech',
    keys: [
      'TTS_PROVIDER',
      'TTS_MODEL',
      'FAST_TTS_MODEL',
      'TTS_VOICE',
      'GROQ_TTS_MODEL',
      'GROQ_TTS_VOICE',
      'GROQ_TTS_RESPONSE_FORMAT',
      'GROQ_FALLBACK_TO_OPENAI',
      'FAST_VOICE_MODE',
    ],
  },
  {
    title: 'LLM',
    keys: [
      'OPENAI_API_KEY',
      'GROQ_API_KEY',
      'LLM_MODEL',
      'LLM_TEMPERATURE',
      'LLM_MAX_TOKENS',
      'LLM_MAX_TOKENS_HARD_CAP',
    ],
  },
  {
    title: 'OpenAI provider usage',
    keys: ['OPENAI_ADMIN_KEY', 'OPENAI_MONTHLY_BUDGET_USD', 'OPENAI_USAGE_REFRESH_SECONDS'],
  },
  {
    title: 'RAG',
    keys: ['EMBEDDING_MODEL', 'RAG_TOP_K', 'RAG_TOP_N'],
  },
  {
    title: 'Deployment',
    keys: [
      'HUB_PUBLIC_URL',
      'CLIENT_STORE_URL',
      'CURRENT_URL',
      'CURRENT_SITE_ID',
      'DEFAULT_SITE_ID',
      'AI_DEFAULT_SITE_ID',
      'DATABASE_URL',
      'PUBLIC_API_URL',
      'PUBLIC_STOREFRONT_ORIGIN',
      'PUBLIC_WIDGET_SCRIPT_URL',
      'PUBLIC_HTTPS_ORIGIN',
      'VOICE_ORB_API_URL',
      'DEPLOYMENT_MODE',
      'HOST',
      'PORT',
      'STOREFRONT_PORT',
      'BACKEND_PORT',
      'HTTPS_PORT',
      'HUB_TLS_CERT_FILE',
      'HUB_TLS_KEY_FILE',
      'CORS_ORIGINS',
    ],
  },
  {
    title: 'Crawler',
    keys: ['CRAWL_MAX_PAGES', 'CRAWL_MAX_DEPTH', 'CRAWL_ON_STARTUP', 'CRAWL_PERIODIC_ENABLED'],
  },
  {
    title: 'Client panel and CRM',
    keys: ['CRM_ADMIN_TOKEN', 'CLIENT_PANEL_DEFAULT_PASSWORD', 'CLIENT_PANEL_TOKEN_SECRET'],
  },
];

export interface SettingsViewProps {
  settings: SettingsResponse | null;
  focusKey?: string;
  onSave: (values: Record<string, string>) => Promise<SettingsResponse>;
}

export function SettingsView({
  settings,
  focusKey = '',
  onSave,
}: SettingsViewProps) {
  const [notice, setNotice] = useState<SettingNotice | null>(null);
  const [saving, setSaving] = useState(false);
  const [pendingChanges, setPendingChanges] = useState(false);
  const [query, setQuery] = useState('');
  const [focus, setFocus] = useState<SettingsFocus>('all');
  const byKey = useMemo(() => new Map((settings?.settings ?? []).map((setting) => [setting.key, setting])), [settings]);
  const normalizedQuery = query.trim().toLowerCase();
  const allSettings = settings?.settings ?? [];
  const filteredGroups = useMemo(() => {
    return SETTING_GROUPS.map((group) => ({
      ...group,
      keys: group.keys.filter((key) => {
        const setting = byKey.get(key);
        if (!setting) return false;
        if (!settingMatchesFocus(group.title, setting, focus)) return false;
        if (!normalizedQuery) return true;
        return [group.title, key, setting?.value, setting?.source]
          .some((value) => String(value || '').toLowerCase().includes(normalizedQuery));
      }),
    })).filter((group) => group.keys.length > 0);
  }, [byKey, focus, normalizedQuery]);

  useEffect(() => {
    const cleanFocus = focusKey.trim();
    if (!cleanFocus) return;
    setQuery(cleanFocus);
    setFocus(settingFocusForKey(cleanFocus));
  }, [focusKey]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const values: Record<string, string> = {};
    formData.forEach((value, key) => {
      const text = String(value).trim();
      const setting = byKey.get(key);
      if (setting?.is_secret && !text) return;
      values[key] = text;
    });
    const validationError = validateSettings(values);
    if (validationError) {
      setNotice({ tone: 'error', message: validationError });
      return;
    }
    setSaving(true);
    setNotice(null);
    try {
      const response = await onSave(values);
      setNotice({
        tone: 'success',
        message: response.restart_required
          ? 'Settings saved. Restart AI Hub to apply runtime model changes.'
          : 'Settings saved.',
      });
      setPendingChanges(false);
    } catch (error) {
      setNotice({
        tone: 'error',
        message:
          error instanceof Error
            ? `${error.message} Refresh settings before retrying; some deployment files may already have changed.`
            : 'Settings save failed. Refresh settings before retrying.',
      });
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="settings-grid" onSubmit={submit} onChange={(event) => {
      const target = event.target as HTMLElement;
      if (target.closest('[data-settings-filter="true"]')) return;
      setPendingChanges(true);
    }}>
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">Settings</h2>
          <p className="mt-1 text-sm text-muted">Changes are saved to .env and require a hub restart.</p>
        </div>
        <Button type="submit" disabled={saving || !pendingChanges}>
          {saving ? 'Saving...' : 'Save settings'}
        </Button>
      </section>
      <SettingsControlSummary
        settings={allSettings}
        byKey={byKey}
        focus={focus}
        restartRequired={Boolean(settings?.restart_required)}
        pendingChanges={pendingChanges}
        onFocusChange={setFocus}
      />
      <section className="settings-toolbar" aria-label="Settings filters">
        <label className="client-search" data-settings-filter="true">
          <Search size={15} aria-hidden="true" />
          <span className="sr-only">Search settings</span>
          <input
            value={query}
            onChange={(event) => setQuery(event.currentTarget.value)}
            placeholder="Search settings, providers, ports, crawler, or CRM token"
          />
          {query ? (
            <button type="button" aria-label="Clear settings search" onClick={() => setQuery('')}>
              <X size={14} aria-hidden="true" />
            </button>
          ) : null}
        </label>
        <div className="client-board-counts">
          <button type="button" className={focus === 'all' ? 'active' : undefined} aria-pressed={focus === 'all'} data-settings-filter="true" onClick={() => setFocus('all')}>
            All
          </button>
          <button type="button" className={focus === 'runtime' ? 'active' : undefined} aria-pressed={focus === 'runtime'} data-settings-filter="true" onClick={() => setFocus('runtime')}>
            Runtime
          </button>
          <button type="button" className={focus === 'provider' ? 'active' : undefined} aria-pressed={focus === 'provider'} data-settings-filter="true" onClick={() => setFocus('provider')}>
            Provider
          </button>
          <button type="button" className={focus === 'crawler' ? 'active' : undefined} aria-pressed={focus === 'crawler'} data-settings-filter="true" onClick={() => setFocus('crawler')}>
            Crawler
          </button>
          <button type="button" className={focus === 'deployment' ? 'active' : undefined} aria-pressed={focus === 'deployment'} data-settings-filter="true" onClick={() => setFocus('deployment')}>
            Deployment
          </button>
          <button type="button" className={focus === 'secrets' ? 'active' : undefined} aria-pressed={focus === 'secrets'} data-settings-filter="true" onClick={() => setFocus('secrets')}>
            Secrets
          </button>
          <span>{number(filteredGroups.reduce((total, group) => total + group.keys.length, 0))} shown</span>
          <span>{number(settings?.settings.length ?? 0)} total</span>
        </div>
      </section>
      {pendingChanges ? (
        <div className="pending-banner">
          <span>You have unsaved changes.</span>
          <Button type="submit" disabled={saving}>
            {saving ? 'Saving...' : 'Save'}
          </Button>
        </div>
      ) : null}
      {notice ? <NoticeBanner tone={notice.tone} message={notice.message} /> : null}
      <div className="settings-grid">
        {filteredGroups.length ? filteredGroups.map((group, index) => (
          <details
            key={group.title}
            className="settings-section crm-disclosure"
            open={Boolean(normalizedQuery) || group.title === 'OpenAI provider usage' || index === 0}
          >
            <summary className="sticky-section-header">
              <h3>{group.title}</h3>
              <span>
                {number(group.keys.length)} settings
                <ChevronDown size={14} aria-hidden="true" />
              </span>
            </summary>
            <section className="card settings-group">
              <div className="settings-fields">
                {group.keys.map((key) => {
                  const setting = byKey.get(key);
                  return setting ? <SettingField key={key} setting={setting} /> : null;
                })}
              </div>
            </section>
          </details>
        )) : (
          <section className="card">
            <div className="empty-state">
              <h3>No matching settings</h3>
              <p>Clear the search to show every configurable AI Hub setting.</p>
            </div>
          </section>
        )}
      </div>
    </form>
  );
}

function SettingsControlSummary({
  settings,
  byKey,
  focus,
  restartRequired,
  pendingChanges,
  onFocusChange,
}: {
  settings: Setting[];
  byKey: Map<string, Setting>;
  focus: SettingsFocus;
  restartRequired: boolean;
  pendingChanges: boolean;
  onFocusChange: (focus: SettingsFocus) => void;
}) {
  const secretSettings = settings.filter((setting) => setting.is_secret);
  const configuredSecrets = secretSettings.filter((setting) => setting.configured).length;
  const startupCrawl = settingEnabled(byKey.get('CRAWL_ON_STARTUP'));
  const periodicCrawl = settingEnabled(byKey.get('CRAWL_PERIODIC_ENABLED'));
  const deploymentMode = settingText(byKey.get('DEPLOYMENT_MODE'), 'local');
  const llmModel = settingText(byKey.get('LLM_MODEL'), 'not configured');
  const sttProvider = settingText(byKey.get('STT_PROVIDER'), 'auto');
  const ttsProvider = settingText(byKey.get('TTS_PROVIDER'), 'auto');
  const restartText = pendingChanges
    ? 'Unsaved local edits'
    : restartRequired
    ? 'Restart required'
    : 'No pending restart';

  return (
    <section className="settings-control-summary" aria-label="Settings control summary">
      <SettingsSummaryCard
        icon={Bot}
        label="AI runtime"
        value={llmModel}
        detail={`${sttProvider} STT / ${ttsProvider} TTS`}
        active={focus === 'runtime'}
        onClick={() => onFocusChange('runtime')}
      />
      <SettingsSummaryCard
        icon={WalletCards}
        label="Provider usage"
        value={settingText(byKey.get('OPENAI_MONTHLY_BUDGET_USD'), 'No budget')}
        detail={settingText(byKey.get('OPENAI_ADMIN_KEY'), '') ? 'Cost reporting key configured' : 'Add admin key for spend reporting'}
        tone={settingText(byKey.get('OPENAI_ADMIN_KEY'), '') ? 'neutral' : 'warn'}
        active={focus === 'provider'}
        onClick={() => onFocusChange('provider')}
      />
      <SettingsSummaryCard
        icon={RotateCw}
        label="Crawler"
        value={startupCrawl || periodicCrawl ? 'Auto enabled' : 'Manual only'}
        detail={`Startup ${startupCrawl ? 'on' : 'off'} / periodic ${periodicCrawl ? 'on' : 'off'}`}
        tone={startupCrawl || periodicCrawl ? 'warn' : 'neutral'}
        active={focus === 'crawler'}
        onClick={() => onFocusChange('crawler')}
      />
      <SettingsSummaryCard
        icon={Globe2}
        label="Deployment"
        value={deploymentMode}
        detail={settingText(byKey.get('HUB_PUBLIC_URL'), 'hub URL not set')}
        active={focus === 'deployment'}
        onClick={() => onFocusChange('deployment')}
      />
      <SettingsSummaryCard
        icon={ShieldCheck}
        label="Secrets"
        value={`${number(configuredSecrets)}/${number(secretSettings.length)} configured`}
        detail={configuredSecrets === secretSettings.length ? 'Credential fields are configured' : 'Some secret fields are empty'}
        tone={configuredSecrets === secretSettings.length ? 'neutral' : 'warn'}
        active={focus === 'secrets'}
        onClick={() => onFocusChange('secrets')}
      />
      <SettingsSummaryCard
        icon={KeyRound}
        label="Save state"
        value={restartText}
        detail="Settings write to .env; runtime changes need restart"
        tone={pendingChanges || restartRequired ? 'warn' : 'neutral'}
        active={false}
        onClick={() => onFocusChange('all')}
      />
    </section>
  );
}

function SettingsSummaryCard({
  icon: Icon,
  label,
  value,
  detail,
  tone = 'neutral',
  active,
  onClick,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  detail: string;
  tone?: 'neutral' | 'warn';
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button className={`settings-summary-card ${tone} ${active ? 'active' : ''}`} type="button" aria-pressed={active} data-settings-filter="true" onClick={onClick}>
      <Icon size={17} aria-hidden="true" />
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </button>
  );
}

function settingMatchesFocus(groupTitle: string, setting: Setting, focus: SettingsFocus) {
  if (focus === 'all') return true;
  if (focus === 'secrets') return setting.is_secret || groupTitle === 'Client panel and CRM';
  if (focus === 'provider') return groupTitle === 'OpenAI provider usage';
  if (focus === 'crawler') return groupTitle === 'Crawler' || setting.key.startsWith('CRAWL_');
  if (focus === 'deployment') return groupTitle === 'Deployment';
  return ['Speech-to-text', 'Text-to-speech', 'LLM', 'RAG'].includes(groupTitle);
}

function settingFocusForKey(key: string): SettingsFocus {
  if (key.startsWith('OPENAI_ADMIN') || key.startsWith('OPENAI_MONTHLY') || key.startsWith('OPENAI_USAGE')) return 'provider';
  if (key.includes('CRAWL')) return 'crawler';
  if (key.includes('TOKEN') || key.includes('KEY') || key.includes('SECRET')) return 'secrets';
  return 'all';
}

function settingText(setting: Setting | undefined, fallback: string) {
  const value = String(setting?.value || '').trim();
  return value || fallback;
}

function settingEnabled(setting: Setting | undefined) {
  return ['1', 'true', 'yes', 'on'].includes(settingText(setting, '').toLowerCase());
}

function SettingField({ setting }: { setting: Setting }) {
  const placeholder = setting.is_secret && setting.configured ? setting.value : 'Not configured';
  const source = setting.source || (setting.configured ? 'env' : 'empty');
  return (
    <label className="field">
      <span className="flex items-center justify-between gap-3">
        <span>{setting.key}</span>
        <small className={`setting-source setting-source-${source.replace(/\s+/g, '-')}`}>{source}</small>
      </span>
      <input
        name={setting.key}
        type={setting.is_secret ? 'password' : 'text'}
        defaultValue={setting.is_secret ? '' : setting.value || ''}
        placeholder={placeholder}
      />
    </label>
  );
}

function validateSettings(values: Record<string, string>) {
  const temperature = values.LLM_TEMPERATURE;
  if (temperature && !isNumberInRange(temperature, 0, 2)) {
    return 'LLM temperature must be a number between 0 and 2. Example: 0.3';
  }
  for (const [key, label] of Object.entries(NUMERIC_SETTING_LABELS)) {
    if (key === 'LLM_TEMPERATURE') continue;
    const value = values[key];
    if (value && !Number.isFinite(Number(value))) return `${label} must be numeric.`;
    const range = INTEGER_SETTING_RANGES[key];
    if (value && range && !isIntegerInRange(value, range[0], range[1])) {
      return `${label} must be a whole number between ${range[0]} and ${range[1]}.`;
    }
  }
  return '';
}

function isNumberInRange(value: string, min: number, max: number) {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) && numberValue >= min && numberValue <= max;
}

function isIntegerInRange(value: string, min: number, max: number) {
  const numberValue = Number(value);
  return Number.isInteger(numberValue) && numberValue >= min && numberValue <= max;
}
