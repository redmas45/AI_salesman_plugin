import { useEffect, useMemo, useState, type ChangeEvent, type FormEvent } from 'react';
import { CheckCircle2, FileText, Send, ShieldCheck } from 'lucide-react';
import { crmApi } from '../../api';
import type { Client, PromptProfileResponse, PromptVersion } from '../../types';
import type { CrmVerticalDefinition } from '../../verticals/types';
import { Button } from '../../components/ui/Button';
import { Panel } from '../../components/ui/Panel';
import { EmptyState } from '../../components/ui/EmptyState';
import { StatusPill } from '../../components/ui/Badge';
import { shortTime } from '../../utils/format';

const DEFAULT_PROMPT_TEXT =
  'Answer from retrieved source data only. Keep responses concise. Ask a human to take over when the request is regulated, sensitive, or not supported by source data.';

function editablePromptState(response: PromptProfileResponse, clientName: string) {
  const editable = response.draft_version ?? response.active_version;
  return {
    name: response.profile.name || `${clientName} prompt`,
    systemPrompt: editable?.system_prompt || DEFAULT_PROMPT_TEXT,
    developerRules: editable?.developer_rules || '',
  };
}

interface PromptTabProps {
  client: Client;
  vertical: CrmVerticalDefinition;
}

export function PromptTab({ client, vertical }: PromptTabProps) {
  const [profile, setProfile] = useState<PromptProfileResponse | null>(null);
  const [name, setName] = useState('');
  const [systemPrompt, setSystemPrompt] = useState(DEFAULT_PROMPT_TEXT);
  const [developerRules, setDeveloperRules] = useState('');
  const [changelog, setChangelog] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setMessage('');
    crmApi
      .getPromptProfile(client.site_id)
      .then((response) => {
        if (cancelled) return;
        setProfile(response);
        const next = editablePromptState(response, client.name);
        setName(next.name);
        setSystemPrompt(next.systemPrompt);
        setDeveloperRules(next.developerRules);
        setChangelog('');
      })
      .catch((error: unknown) => {
        if (!cancelled) setMessage(error instanceof Error ? error.message : 'Prompt profile failed to load.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [client.name, client.site_id]);

  const activeVersion = profile?.active_version ?? null;
  const publishedVersion = profile?.published_version ?? null;
  const draftVersion = profile?.draft_version ?? null;
  const allowedActions = useMemo(
    () => activeVersion?.allowed_actions?.filter(Boolean).slice(0, 18) ?? [],
    [activeVersion],
  );
  const flowPrompts = useMemo(() => promptSuggestions(client.vertical_config), [client.vertical_config]);
  const intakeQuestions = useMemo(() => salesIntakeQuestions(client.vertical_config), [client.vertical_config]);

  async function saveDraft(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await persistPrompt(false);
  }

  async function persistPrompt(publish: boolean) {
    if (!systemPrompt.trim()) {
      setMessage('System prompt is required.');
      return;
    }
    setSaving(true);
    setMessage('');
    try {
      const response = await crmApi.savePromptProfile(client.site_id, {
        name: name.trim() || `${client.name} prompt`,
        system_prompt: systemPrompt,
        developer_rules: developerRules,
        publish,
        changelog,
      });
      setProfile(response);
      const next = editablePromptState(response, client.name);
      setName(next.name);
      setSystemPrompt(next.systemPrompt);
      setDeveloperRules(next.developerRules);
      setChangelog('');
      setMessage(publish ? 'Published prompt version saved.' : 'Draft prompt version saved.');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Prompt save failed.');
    } finally {
      setSaving(false);
    }
  }

  async function publishVersion(version: PromptVersion) {
    setSaving(true);
    setMessage('');
    try {
      await crmApi.publishPromptVersion(version.id);
      const response = await crmApi.getPromptProfile(client.site_id);
      setProfile(response);
      const next = editablePromptState(response, client.name);
      setName(next.name);
      setSystemPrompt(next.systemPrompt);
      setDeveloperRules(next.developerRules);
      setChangelog('');
      setMessage(`Version ${version.version} published.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Prompt publish failed.');
    } finally {
      setSaving(false);
    }
  }

  function applyPromptSuggestion(prompt: string) {
    const cleanPrompt = prompt.trim();
    if (!cleanPrompt) return;
    if (developerRules.includes(cleanPrompt)) {
      setMessage('Prompt suggestion is already in developer rules.');
      return;
    }
    const prefix = developerRules.trim() ? `${developerRules.trim()}\n` : '';
    setDeveloperRules(`${prefix}Customer prompt coverage: ${cleanPrompt}`);
    setMessage('Prompt suggestion added to developer rules. Save or publish to apply it.');
  }

  return (
    <div className="tab-content fade-in">
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">Prompt profile</h2>
          <p className="mt-1 text-sm text-muted">
            Published prompts control live {vertical.label} conversations for this client.
          </p>
        </div>
        <StatusPill value={publishedVersion ? 'published' : 'draft only'} />
      </section>

      <div className="prompt-layout">
        <Panel title="Prompt editor">
          {loading ? (
            <EmptyState text="Loading prompt profile..." />
          ) : (
            <form className="prompt-editor-form" onSubmit={saveDraft}>
              <label className="field">
                <span>Profile name</span>
                <input value={name} onChange={(event: ChangeEvent<HTMLInputElement>) => setName(event.currentTarget.value)} />
              </label>
              <label className="field">
                <span>System prompt</span>
                <textarea
                  className="textarea textarea-lg"
                  value={systemPrompt}
                  onChange={(event: ChangeEvent<HTMLTextAreaElement>) => setSystemPrompt(event.currentTarget.value)}
                />
              </label>
              <label className="field">
                <span>Developer rules</span>
                <textarea
                  className="textarea"
                  value={developerRules}
                  onChange={(event: ChangeEvent<HTMLTextAreaElement>) => setDeveloperRules(event.currentTarget.value)}
                />
              </label>
              <label className="field">
                <span>Changelog</span>
                <input value={changelog} onChange={(event: ChangeEvent<HTMLInputElement>) => setChangelog(event.currentTarget.value)} />
              </label>
              <div className="flex flex-wrap items-center gap-2">
                <Button type="submit" icon={FileText} disabled={saving}>
                  {saving ? 'Saving...' : 'Save draft'}
                </Button>
                <Button type="button" variant="secondary" icon={Send} disabled={saving} onClick={() => persistPrompt(true)}>
                  Save and publish
                </Button>
                {message ? <span className="text-sm text-muted">{message}</span> : null}
              </div>
            </form>
          )}
        </Panel>

        <div className="prompt-side">
          <Panel title="Runtime status">
            <div className="prompt-status-grid">
              <PromptFact label="Vertical" value={vertical.label} />
              <PromptFact label="Risk" value={vertical.riskLevel} />
              <PromptFact label="Published" value={publishedVersion ? `v${publishedVersion.version}` : 'none'} />
              <PromptFact label="Draft" value={draftVersion ? `v${draftVersion.version}` : 'none'} />
            </div>
          </Panel>
          <Panel title="Allowed actions">
            {allowedActions.length ? (
              <div className="prompt-chip-grid">
                {allowedActions.map((action) => (
                  <span key={action} className="action-chip">
                    {action}
                  </span>
                ))}
              </div>
            ) : (
              <EmptyState text="Allowed actions appear after the first prompt version is created." />
            )}
          </Panel>
          <Panel title="Discovered prompts">
            {flowPrompts.length ? (
              <div className="grid gap-2">
                {flowPrompts.map((prompt) => (
                  <div key={prompt} className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-line bg-soft p-2 text-sm">
                    <span>{prompt}</span>
                    <Button type="button" size="sm" variant="secondary" icon={CheckCircle2} onClick={() => applyPromptSuggestion(prompt)}>
                      Use
                    </Button>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState text="Prompt suggestions appear after flow discovery runs." />
            )}
          </Panel>
          <Panel title="Sales intake">
            {intakeQuestions.length ? (
              <div className="grid gap-2">
                {intakeQuestions.map((item) => (
                  <div key={item.key} className="rounded-md border border-line bg-soft p-2 text-sm">
                    <div className="flex flex-wrap items-center gap-2">
                      <strong>{item.label}</strong>
                      {item.required ? <StatusPill value="required" /> : null}
                    </div>
                    <p className="mt-1 text-muted">{item.question}</p>
                    {item.why ? <small>{item.why}</small> : null}
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState text="Intake questions appear after vertical discovery runs." />
            )}
          </Panel>
          <Panel title="Safety frame">
            <div className="prompt-safety-list">
              <SafetyLine text="Use retrieved source data only." />
              <SafetyLine text="Do not promise unavailable prices, terms, eligibility, or outcomes." />
              <SafetyLine text="Use human handoff for regulated or uncertain requests." />
            </div>
          </Panel>
        </div>
      </div>

      <Panel title="Version history">
        {profile?.versions.length ? (
          <div className="prompt-version-list">
            {profile.versions.map((version) => (
              <article key={version.id} className="prompt-version-row">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <strong>Version {version.version}</strong>
                    <StatusPill value={version.status} />
                  </div>
                  <p>{version.changelog || 'No changelog provided.'}</p>
                  <small>{shortTime(version.published_at || version.created_at)}</small>
                </div>
                {version.status !== 'published' ? (
                  <Button variant="secondary" size="sm" icon={CheckCircle2} disabled={saving} onClick={() => publishVersion(version)}>
                    Publish
                  </Button>
                ) : null}
              </article>
            ))}
          </div>
        ) : (
          <EmptyState text="No prompt versions are saved yet." />
        )}
      </Panel>
    </div>
  );

}

function PromptFact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function SafetyLine({ text }: { text: string }) {
  return (
    <div className="prompt-safety-line">
      <ShieldCheck size={15} aria-hidden="true" />
      <span>{text}</span>
    </div>
  );
}

function promptSuggestions(verticalConfig: Record<string, unknown> | undefined) {
  const flow = verticalConfig?.flow;
  if (!flow || typeof flow !== 'object') return [];
  const prompts = (flow as Record<string, unknown>).prompt_suggestions;
  return Array.isArray(prompts) ? prompts.map((item) => String(item || '').trim()).filter(Boolean).slice(0, 10) : [];
}

interface SalesIntakeQuestion {
  key: string;
  label: string;
  question: string;
  why: string;
  required: boolean;
}

function salesIntakeQuestions(verticalConfig: Record<string, unknown> | undefined): SalesIntakeQuestion[] {
  const rows = verticalConfig?.intake_questions;
  if (!Array.isArray(rows)) return [];
  return rows.map(salesIntakeQuestion).filter((item): item is SalesIntakeQuestion => Boolean(item)).slice(0, 8);
}

function salesIntakeQuestion(value: unknown): SalesIntakeQuestion | null {
  if (!value || typeof value !== 'object') return null;
  const row = value as Record<string, unknown>;
  const key = String(row.key || '').trim();
  const question = String(row.question || '').trim();
  if (!key || !question) return null;
  return {
    key,
    label: String(row.label || key).trim(),
    question,
    why: String(row.why || '').trim(),
    required: row.required === true,
  };
}
