import { useState, useMemo, type FormEvent } from 'react';
import type { SettingsResponse, Setting } from '../types';
import { Button } from '../components/ui/Button';
import { NoticeBanner } from '../components/shared/NoticeBanner';
import { number } from '../utils/format';

interface SettingNotice {
  tone: 'success' | 'error' | 'info';
  message: string;
}

const NUMERIC_SETTING_LABELS: Record<string, string> = {
  LLM_TEMPERATURE: 'LLM temperature',
  LLM_MAX_TOKENS: 'LLM max tokens',
  LLM_MAX_TOKENS_HARD_CAP: 'LLM hard token cap',
  RAG_TOP_K: 'RAG top K',
  RAG_TOP_N: 'RAG top N',
  CRAWL_MAX_PAGES: 'Crawler max pages',
  CRAWL_MAX_DEPTH: 'Crawler max depth',
  PORT: 'Hub port',
  STOREFRONT_PORT: 'Storefront port',
  BACKEND_PORT: 'Backend port',
  HTTPS_PORT: 'HTTPS port',
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
  onSave: (values: Record<string, string>) => Promise<SettingsResponse>;
}

export function SettingsView({
  settings,
  onSave,
}: SettingsViewProps) {
  const [notice, setNotice] = useState<SettingNotice | null>(null);
  const [saving, setSaving] = useState(false);
  const [pendingChanges, setPendingChanges] = useState(false);
  const byKey = useMemo(() => new Map((settings?.settings ?? []).map((setting) => [setting.key, setting])), [settings]);

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
    <form className="settings-grid" onSubmit={submit} onChange={() => setPendingChanges(true)}>
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">Settings</h2>
          <p className="mt-1 text-sm text-muted">Changes are saved to .env and require a hub restart.</p>
        </div>
        <Button type="submit" disabled={saving || !pendingChanges}>
          {saving ? 'Saving...' : 'Save settings'}
        </Button>
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
        {SETTING_GROUPS.map((group) => (
          <div key={group.title} className="settings-section">
            <div className="sticky-section-header">
              <h3>{group.title}</h3>
              <span>{number(group.keys.length)} settings</span>
            </div>
            <section className="card settings-group">
              <div className="settings-fields">
                {group.keys.map((key) => {
                  const setting = byKey.get(key);
                  return setting ? <SettingField key={key} setting={setting} /> : null;
                })}
              </div>
            </section>
          </div>
        ))}
      </div>
    </form>
  );
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
  }
  return '';
}

function isNumberInRange(value: string, min: number, max: number) {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) && numberValue >= min && numberValue <= max;
}
