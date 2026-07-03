import { useState, useEffect, type FormEvent } from 'react';
import { Copy, RefreshCw, Trash2, Eye, EyeOff } from 'lucide-react';
import { Button } from '../ui/Button';
import { Field } from '../ui/Field';
import { NoticeBanner } from './NoticeBanner';
import type { Client, CreateClientPayload } from '../../types';
import { panelPasswordLabel } from '../../utils/format';
import { CRM_VERTICALS, DEFAULT_CRM_VERTICAL_KEY } from '../../verticals/registry';

export interface AddClientDialogProps {
  open: boolean;
  busy: boolean;
  onClose: () => void;
  onCreate: (payload: CreateClientPayload) => void;
}

export function AddClientDialog({
  open,
  busy,
  onClose,
  onCreate,
}: AddClientDialogProps) {
  const [verticalKey, setVerticalKey] = useState(DEFAULT_CRM_VERTICAL_KEY);
  const selectedVertical = CRM_VERTICALS.find((vertical) => vertical.key === verticalKey) ?? CRM_VERTICALS[0];

  if (!open) return null;
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const payload = Object.fromEntries(formData.entries()) as unknown as CreateClientPayload;
    if (!payload.site_id) delete payload.site_id;
    onCreate(payload);
  }
  return (
    <div className="modal-backdrop">
      <form className="modal modal-wide" onSubmit={submit}>
        <div className="modal-header">
          <div>
            <div className="text-xs font-semibold text-muted">Manual fallback</div>
            <h2>Create client manually</h2>
            <p className="mt-1 text-sm text-muted">
              Use this only when a site cannot run the universal installer auto-registration flow.
            </p>
          </div>
          <button className="modal-close" type="button" aria-label="Close" onClick={onClose}>
            x
          </button>
        </div>
        <Field label="Client name" name="name" placeholder="Example Client" required />
        <Field label="Website URL" name="store_url" placeholder="https://example.com" required />
        <Field label="Site ID" name="site_id" placeholder="auto generated" />
        <label className="field">
          <span>Vertical</span>
          <select name="vertical_key" value={verticalKey} onChange={(event) => setVerticalKey(event.currentTarget.value)}>
            {CRM_VERTICALS.map((vertical) => (
              <option key={vertical.key} value={vertical.key}>
                {vertical.label}
              </option>
            ))}
          </select>
        </label>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="field">
            <span>Deploy mode</span>
            <select name="deploy_mode" defaultValue="public-ip">
              <option value="public-ip">public IP / path route</option>
              <option value="domain">domain</option>
              <option value="custom">custom</option>
            </select>
          </label>
          <Field key={selectedVertical.key} label="Plan" name="plan" defaultValue={selectedVertical.defaultPlanLabel} />
        </div>
        <Field label="Adapter" name="adapter_name" defaultValue="generic_adapter.js" />
        <div className="modal-footer">
          <Button variant="secondary" type="button" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={busy}>
            Create
          </Button>
        </div>
      </form>
    </div>
  );
}

export interface ClientPanelPasswordDialogProps {
  client: Client | null;
  busy: boolean;
  onClose: () => void;
  onUpdatePassword: (siteId: string, password: string, autoGenerate: boolean) => Promise<string>;
  onRevokePassword: (siteId: string) => Promise<void>;
}

export function ClientPanelPasswordDialog({
  client,
  busy,
  onClose,
  onUpdatePassword,
  onRevokePassword,
}: ClientPanelPasswordDialogProps) {
  const [password, setPassword] = useState('');
  const [generatedPassword, setGeneratedPassword] = useState('');
  const [message, setMessage] = useState('');
  const [working, setWorking] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);

  useEffect(() => {
    setPassword('');
    setGeneratedPassword('');
    setMessage('');
    setShowPassword(false);
    setShowCurrentPassword(false);
  }, [client?.site_id]);

  if (!client) return null;
  const activeClient = client;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextPassword = password.trim();
    if (nextPassword.length < 12) {
      setMessage('Password must be at least 12 characters.');
      return;
    }
    setWorking(true);
    setGeneratedPassword('');
    setMessage('');
    try {
      const returnedPassword = await onUpdatePassword(activeClient.site_id, nextPassword, false);
      setGeneratedPassword(returnedPassword || nextPassword);
      setShowCurrentPassword(true);
      setPassword('');
      setMessage('Password updated. Current password is visible below.');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Password update failed.');
    } finally {
      setWorking(false);
    }
  }

  async function generateAndSetPassword() {
    setWorking(true);
    setGeneratedPassword('');
    setMessage('');
    try {
      const nextPassword = await onUpdatePassword(activeClient.site_id, '', true);
      setGeneratedPassword(nextPassword);
      setShowCurrentPassword(true);
      setPassword('');
      setMessage('Password generated and set. Current password is visible below.');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Password update failed.');
    } finally {
      setWorking(false);
    }
  }

  async function revokePassword() {
    setWorking(true);
    setGeneratedPassword('');
    setMessage('');
    try {
      await onRevokePassword(activeClient.site_id);
      setPassword('');
      setShowCurrentPassword(false);
      setMessage('Client panel login is revoked.');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Password revoke failed.');
    } finally {
      setWorking(false);
    }
  }

  async function copyGeneratedPassword() {
    if (!generatedPassword) return;
    await navigator.clipboard.writeText(generatedPassword);
    setMessage('Current password copied.');
  }

  const disabled = busy || working;
  const passwordStatus = panelPasswordLabel(client);
  const messageTone: 'success' | 'error' | 'info' =
    message.toLowerCase().includes('failed') || message.toLowerCase().includes('must')
      ? 'error'
      : message.toLowerCase().includes('updated') || message.toLowerCase().includes('copied') || message.toLowerCase().includes('generated')
        ? 'success'
        : 'info';

  return (
    <div className="modal-backdrop">
      <form className="modal modal-wide" onSubmit={submit}>
        <div className="modal-header">
          <div>
            <div className="text-xs font-semibold text-muted">Client panel password</div>
            <h2>{client.name}</h2>
            <p className="mt-1 text-sm text-muted">
              {client.site_id} - {panelPasswordLabel(client)}
            </p>
          </div>
          <button className="modal-close" type="button" aria-label="Close" onClick={onClose}>
            x
          </button>
        </div>
        <div className="generated-password-box current-password-box">
          <div>
            <span className="text-xs font-semibold uppercase text-muted">Current password</span>
            {generatedPassword ? (
              <code>{showCurrentPassword ? generatedPassword : 'Hidden'}</code>
            ) : (
              <p className="mt-1 text-sm text-muted">
                {passwordStatus === 'configured'
                  ? 'Configured. Set or generate a new password to reveal it here.'
                  : passwordStatus === 'revoked'
                    ? 'Revoked. Generate or set a password to enable owner login.'
                    : 'Not configured yet.'}
              </p>
            )}
          </div>
          {generatedPassword ? (
            <div className="flex flex-wrap justify-end gap-2">
              <Button
                type="button"
                variant="secondary"
                icon={showCurrentPassword ? EyeOff : Eye}
                onClick={() => setShowCurrentPassword(!showCurrentPassword)}
              >
                {showCurrentPassword ? 'Hide' : 'Show'}
              </Button>
              <Button type="button" variant="secondary" icon={Copy} onClick={copyGeneratedPassword}>
                Copy
              </Button>
            </div>
          ) : (
            <span className="password-status-pill">{passwordStatus}</span>
          )}
        </div>
        <div className="flex gap-2 items-end">
          <div className="flex-1">
            <Field
              label="New password"
              type={showPassword ? 'text' : 'password'}
              minLength={12}
              value={password}
              onChange={(event) => setPassword(event.currentTarget.value)}
              placeholder="Minimum 12 characters"
              autoComplete="new-password"
            />
          </div>
          <Button
            type="button"
            variant="secondary"
            icon={showPassword ? EyeOff : Eye}
            onClick={() => setShowPassword(!showPassword)}
          >
            {showPassword ? 'Hide' : 'Show'}
          </Button>
        </div>
        {message ? <NoticeBanner tone={messageTone} message={message} /> : null}
        <div className="modal-footer">
          <Button type="button" variant="danger" icon={Trash2} disabled={disabled} onClick={revokePassword}>
            Revoke password
          </Button>
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="secondary" disabled={disabled} icon={RefreshCw} onClick={generateAndSetPassword}>
              Generate and set
            </Button>
            <Button type="submit" disabled={disabled}>
              Set password
            </Button>
          </div>
        </div>
      </form>
    </div>
  );
}
