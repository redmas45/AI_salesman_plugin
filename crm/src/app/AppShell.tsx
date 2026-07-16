import type { FormEvent, RefObject } from 'react';
import type { Client, CreateClientPayload, Overview, Theme, View, ClientBoardSection, AnalyticsSectionId } from '../types';
import type { ClientWorkspaceTabId } from '../verticals/types';
import { Sidebar } from '../components/shared/Sidebar';
import { Topbar } from '../components/shared/Topbar';
import { AddClientDialog, ClientPanelPasswordDialog } from '../components/shared/Dialogs';
import { ErrorBoundary } from '../components/shared/ErrorBoundary';
import { ThemeToggle } from '../components/shared/controls/ThemeToggle';
import { ViewRenderer, type ViewRendererProps } from '../views/ViewRenderer';

interface AppShellProps {
  pageTitle: string;
  view: View;
  overview: Overview | null;
  selectedClient: Client | null;
  clientInitialTab: ClientWorkspaceTabId;
  clientBoardSection: ClientBoardSection;
  analyticsSection: AnalyticsSectionId;
  mobileSidebarOpen: boolean;
  contentRef: RefObject<HTMLElement | null>;
  authRequired: boolean;
  loading: boolean;
  loadError: string;
  busy: boolean;
  viewResetKey: string;
  viewRendererProps: ViewRendererProps;
  dialogOpen: boolean;
  passwordDialogClient: Client | null;
  toast: string;
  theme: Theme;
  onSubmitAdminToken: (event: FormEvent<HTMLFormElement>) => void;
  onToggleTheme: () => void;
  onRetryLoad: () => void;
  onToggleSidebar: () => void;
  onCloseSidebar: () => void;
  onRefresh: () => void;
  onLogout: () => void;
  onOpenDashboard: () => void;
  onOpenClients: () => void;
  onOpenView: (view: View) => void;
  onOpenClient: (siteId: string, initialTab?: ClientWorkspaceTabId) => void;
  onOpenClientBoardSection: (section: ClientBoardSection) => void;
  onOpenClientTab: (tabId: ClientWorkspaceTabId) => void;
  onOpenAnalyticsSection: (section: AnalyticsSectionId) => void;
  onCloseAddClient: () => void;
  onCreateClient: (payload: CreateClientPayload) => void;
  onClosePasswordDialog: () => void;
  onUpdatePassword: (siteId: string, password: string, autoGenerate: boolean) => Promise<string>;
  onRevokePassword: (siteId: string) => Promise<void>;
}

export function AppShell({
  pageTitle,
  view,
  overview,
  selectedClient,
  clientInitialTab,
  mobileSidebarOpen,
  contentRef,
  authRequired,
  loading,
  loadError,
  busy,
  viewResetKey,
  viewRendererProps,
  dialogOpen,
  passwordDialogClient,
  toast,
  theme,
  onSubmitAdminToken,
  onToggleTheme,
  onRetryLoad,
  onToggleSidebar,
  onCloseSidebar,
  onRefresh,
  onLogout,
  onOpenDashboard,
  onOpenClients,
  onOpenView,
  onOpenClient,
  onCloseAddClient,
  onCreateClient,
  onClosePasswordDialog,
  onUpdatePassword,
  onRevokePassword,
}: AppShellProps) {
  if (authRequired) {
    return (
      <main className="crm-auth-shell">
        <ThemeToggle className="auth-theme-toggle" theme={theme} onToggle={onToggleTheme} />
        <AdminTokenView busy={loading} error={loadError} onSubmit={onSubmitAdminToken} />
      </main>
    );
  }

  return (
    <>
      <div className="crm-shell">
        <Sidebar
          view={view}
          setView={onOpenView}
          health={overview?.health ?? {}}
          open={mobileSidebarOpen}
        />
        <div className="crm-body">
          <Topbar
            title={pageTitle}
            view={view}
            health={overview?.health ?? {}}
            selectedClient={selectedClient}
            activeClientTab={clientInitialTab}
            busy={busy}
            onToggleSidebar={onToggleSidebar}
            onRefresh={onRefresh}
            onLogout={onLogout}
            onOpenDashboard={onOpenDashboard}
            onOpenClients={onOpenClients}
            onOpenView={onOpenView}
            onOpenClient={onOpenClient}
            authenticated={!authRequired && Boolean(overview)}
            theme={theme}
            onToggleTheme={onToggleTheme}
          />
          <main className="crm-content" ref={contentRef}>
            <AppContent
              loading={loading}
              loadError={loadError}
              overview={overview}
              viewResetKey={viewResetKey}
              viewRendererProps={viewRendererProps}
              onRetryLoad={onRetryLoad}
            />
          </main>
        </div>
        {mobileSidebarOpen ? (
          <button
            className="fixed inset-0 z-40 border-0 bg-black/30 lg:hidden"
            type="button"
            aria-label="Close navigation"
            onClick={onCloseSidebar}
          />
        ) : null}
      </div>
      <AddClientDialog open={dialogOpen} busy={busy} onClose={onCloseAddClient} onCreate={onCreateClient} />
      <ClientPanelPasswordDialog
        client={passwordDialogClient}
        busy={busy}
        onClose={onClosePasswordDialog}
        onUpdatePassword={onUpdatePassword}
        onRevokePassword={onRevokePassword}
      />
      <div className={`toast ${toast ? 'visible' : ''}`}>{toast}</div>
    </>
  );
}

function AppContent({
  loading,
  loadError,
  overview,
  viewResetKey,
  viewRendererProps,
  onRetryLoad,
}: {
  loading: boolean;
  loadError: string;
  overview: Overview | null;
  viewResetKey: string;
  viewRendererProps: ViewRendererProps;
  onRetryLoad: () => void;
}) {
  if (loading || (!overview && !loadError)) return <SkeletonDashboard />;
  if (loadError && !overview) return <LoadErrorView message={loadError} onRetry={onRetryLoad} />;
  return (
    <ErrorBoundary resetKey={viewResetKey}>
      <ViewRenderer {...viewRendererProps} />
    </ErrorBoundary>
  );
}

function AdminTokenView({
  busy,
  error,
  onSubmit,
}: {
  busy: boolean;
  error: string;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <section className="crm-auth-card">
      <div>
        <div className="text-xs font-semibold uppercase text-muted">AI Hub</div>
        <h2 className="mt-2 text-lg font-semibold">Administration</h2>
        <p className="mt-1 text-sm text-muted">Sign in to manage clients, runtime health, and Maya configuration.</p>
      </div>
      <form className="grid gap-3" onSubmit={onSubmit}>
        <label className="field">
          <span>CRM admin token</span>
          <input name="admin_token" type="password" autoComplete="current-password" autoFocus required />
        </label>
        {error ? (
          <p className="text-sm" style={{ color: 'var(--red)' }}>
            {error}
          </p>
        ) : null}
        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy ? 'Checking...' : 'Sign in'}
        </button>
      </form>
    </section>
  );
}

function LoadErrorView({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <section className="mx-auto mt-12 grid w-full max-w-xl gap-4 rounded-lg border border-line bg-panel p-5 text-center shadow-xl">
      <div>
        <div className="text-xs font-semibold uppercase text-muted">CRM load failed</div>
        <h2 className="mt-2 text-lg font-semibold">Could not load AI Hub CRM</h2>
      </div>
      <p className="text-sm text-muted">{message}</p>
      <div className="flex justify-center">
        <button className="btn btn-secondary" type="button" onClick={onRetry}>
          Retry
        </button>
      </div>
    </section>
  );
}

function SkeletonCard({ height = 120 }: { height?: number }) {
  return <div className="skeleton" style={{ height, borderRadius: 'var(--radius)' }} />;
}

function SkeletonKpiStrip() {
  return (
    <div className="dashboard-bento">
      {Array.from({ length: 4 }).map((_, index) => (
        <div key={index} className="bento-kpi">
          <SkeletonCard height={116} />
        </div>
      ))}
    </div>
  );
}

function SkeletonDashboard() {
  return (
    <div className="grid gap-4">
      <SkeletonCard height={76} />
      <SkeletonKpiStrip />
      <div className="dashboard-bento">
        <div className="bento-wide">
          <SkeletonCard height={340} />
        </div>
        <div className="bento-narrow">
          <SkeletonCard height={340} />
        </div>
      </div>
    </div>
  );
}
