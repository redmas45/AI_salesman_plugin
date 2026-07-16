import { type FormEvent, useEffect, useMemo, useState } from 'react';
import { clearToken, dashboard, login, storedToken } from './api';
import { Dashboard } from './components/Dashboard';
import { Header } from './components/Header';
import { LoadingPanel } from './components/ui';
import { LoginView } from './components/LoginView';
import { DEFAULT_RANGE } from './constants';
import type { DashboardResponse } from './types';
import { applyTheme, storedTheme, type Theme } from './theme';
import { clientSlugFromUrl } from './utils';

export function App() {
  const [range, setRange] = useState(DEFAULT_RANGE);
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [authenticated, setAuthenticated] = useState(Boolean(storedToken()));
  const [theme, setTheme] = useState<Theme>(storedTheme());
  const siteHint = useMemo(() => clientSlugFromUrl(), []);

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  useEffect(() => {
    if (!authenticated) return;
    loadDashboard(range);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authenticated, range]);

  async function loadDashboard(nextRange = range): Promise<void> {
    setBusy(true);
    setError('');
    try {
      setData(await dashboard(nextRange));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Panel failed to load.');
      clearToken();
      setAuthenticated(false);
    } finally {
      setBusy(false);
    }
  }

  async function submitLogin(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setBusy(true);
    setError('');
    const formData = new FormData(event.currentTarget);
    try {
      await login(String(formData.get('site_id') || siteHint), String(formData.get('password') || ''));
      setAuthenticated(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed.');
    } finally {
      setBusy(false);
    }
  }

  function logout(): void {
    clearToken();
    setData(null);
    setAuthenticated(false);
  }

  if (!authenticated) {
    return (
      <LoginView
        siteHint={siteHint}
        error={error}
        busy={busy}
        theme={theme}
        onToggleTheme={() => setTheme((current) => (current === 'dark' ? 'light' : 'dark'))}
        onSubmit={submitLogin}
      />
    );
  }

  return (
    <main className="client-app">
      <Header
        clientName={data?.client.name || siteHint}
        range={range}
        busy={busy}
        theme={theme}
        onRangeChange={setRange}
        onRefresh={() => loadDashboard()}
        onToggleTheme={() => setTheme((current) => (current === 'dark' ? 'light' : 'dark'))}
        onLogout={logout}
      />
      <section className="client-shell">
        {error ? <div className="notice error">{error}</div> : null}
        {data ? <Dashboard data={data} range={range} onLimitUpdated={(client) => setData({ ...data, client })} /> : <LoadingPanel />}
      </section>
    </main>
  );
}
