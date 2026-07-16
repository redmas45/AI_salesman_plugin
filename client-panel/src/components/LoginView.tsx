import { type FormEvent, useState } from 'react';
import type { Theme } from '../theme';
import { ThemeToggle } from './ThemeToggle';

export function LoginView({
  siteHint,
  error,
  busy,
  theme,
  onToggleTheme,
  onSubmit,
}: {
  siteHint: string;
  error: string;
  busy: boolean;
  theme: Theme;
  onToggleTheme: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <main className="login-shell">
      <ThemeToggle className="login-theme-toggle" theme={theme} onToggle={onToggleTheme} />
      <section className="login-surface" aria-labelledby="login-title">
        <header className="login-hero">
          <span className="brand-mark">AI</span>
          <div>
            <p className="eyebrow">AI Hub</p>
            <h1 id="login-title">Client workspace</h1>
            <p>Sign in to view assistant activity, data coverage, and account usage.</p>
          </div>
        </header>
        <form className="login-card" onSubmit={onSubmit}>
          <label>
            <span>Account / Client ID</span>
            <input name="site_id" defaultValue={siteHint} autoComplete="username" required />
          </label>
          <label className="password-field">
            <span>Password</span>
            <input name="password" type={showPassword ? 'text' : 'password'} autoComplete="current-password" required />
            <button
              className="password-toggle"
              type="button"
              aria-label={showPassword ? 'Hide password' : 'Show password'}
              aria-pressed={showPassword}
              onClick={() => setShowPassword((visible) => !visible)}
            >
              {showPassword ? 'Hide' : 'Show'}
            </button>
          </label>
          {error ? <div className="notice error" role="alert">{error}</div> : null}
          <button className="btn btn-primary btn-lg" type="submit" disabled={busy}>
            {busy ? <span className="spinner" aria-hidden="true" /> : null}
            {busy ? 'Checking...' : 'Sign in'}
          </button>
          <p className="muted">Access is managed by your AI Hub administrator.</p>
        </form>
      </section>
    </main>
  );
}
