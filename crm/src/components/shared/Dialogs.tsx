import { useState, useEffect, type FormEvent } from 'react';
import { Copy, RefreshCw, Trash2 } from 'lucide-react';
import { Button } from '../ui/Button';
import { Field } from '../ui/Field';
import { NoticeBanner } from './NoticeBanner';
import type { Client, CreateClientPayload } from '../../types';
import { panelPasswordLabel } from '../../utils/format';

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
            <div className="text-xs font-semibold text-muted">Client</div>
            <h2>Add client</h2>
          </div>
          <button className="modal-close" type="button" aria-label="Close" onClick={onClose}>
            x
          </button>
        </div>
        <Field label="Client name" name="name" placeholder="AI-KART" required />
        <Field label="Website URL" name="store_url" placeholder="https://client-store.com" required />
        <Field label="Site ID" name="site_id" placeholder="auto generated" />
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="field">
            <span>Deploy mode</span>
            <select name="deploy_mode" defaultValue="public-ip">
              <option value="public-ip">public IP / path route</option>
              <option value="domain">domain</option>
              <option value="custom">custom</option>
            </select>
          </label>
          <Field label="Plan" name="plan" defaultValue="Commerce plan" />
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

  useEffect(() => {
    setPassword('');
    setGeneratedPassword('');
    setMessage('');
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
      await onUpdatePassword(activeClient.site_id, nextPassword, false);
      setPassword('');
      setMessage('Password updated.');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Password update failed.');
    } finally {
      setWorking(false);
    }
  }

  async function generateAndSetPassword() {
    const chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*';
    let nextPassword = '';
    for (let i = 0; i < 16; i++) {
      nextPassword += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    setGeneratedPassword(nextPassword);
    setPassword(nextPassword);
    setWorking(true);
    try {
      await onUpdatePassword(activeClient.site_id, nextPassword, false);
      setMessage('Password generated and updated automatically.');
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
    setMessage('Generated password copied.');
  }

  const disabled = busy || working;
  const messageTone: 'success' | 'error' | 'info' =
    message.toLowerCase().includes('failed') || message.toLowerCase().includes('must') ? 'error' : 'info';

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
        <Field
          label="New password"
          type="password"
          minLength={12}
          value={password}
          onChange={(event) => setPassword(event.currentTarget.value)}
          placeholder="Minimum 12 characters"
          autoComplete="new-password"
        />
        {generatedPassword ? (
          <div className="generated-password-box">
            <div>
              <span className="text-xs font-semibold uppercase text-muted">Generated password</span>
              <code>{generatedPassword}</code>
            </div>
            <Button type="button" variant="secondary" icon={Copy} onClick={copyGeneratedPassword}>
              Copy
            </Button>
          </div>
        ) : null}
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
