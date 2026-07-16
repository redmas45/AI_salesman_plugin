import type { Dispatch, SetStateAction } from 'react';
import { crmApi } from '../api';
import type { Client, ClientBoardSection, Overview, View } from '../types';
import type { ClientWorkspaceTabId } from '../verticals/types';
import { pollAutoIntegrationStatus, pollCrawlStatus } from './clientStatusPolling';

interface UseClientOperationsParams {
  selectedClient: Client | null;
  setAutoIntegratingSites: Dispatch<SetStateAction<Set<string>>>;
  setBusy: Dispatch<SetStateAction<boolean>>;
  setClientBoardSection: Dispatch<SetStateAction<ClientBoardSection>>;
  setClientInitialTab: Dispatch<SetStateAction<ClientWorkspaceTabId>>;
  setCrawlingSites: Dispatch<SetStateAction<Set<string>>>;
  setOverview: Dispatch<SetStateAction<Overview | null>>;
  setPasswordDialogClient: Dispatch<SetStateAction<Client | null>>;
  setSelectedClient: Dispatch<SetStateAction<Client | null>>;
  setToast: Dispatch<SetStateAction<string>>;
  setView: Dispatch<SetStateAction<View>>;
  showError: (error: unknown, fallback: string) => void;
}

export function useClientOperations({
  selectedClient,
  setAutoIntegratingSites,
  setBusy,
  setClientBoardSection,
  setClientInitialTab,
  setCrawlingSites,
  setOverview,
  setPasswordDialogClient,
  setSelectedClient,
  setToast,
  setView,
  showError,
}: UseClientOperationsParams) {
  function syncClient(client: Client) {
    setSelectedClient((current) => (current?.site_id === client.site_id ? client : current));
    setPasswordDialogClient((current) => (current?.site_id === client.site_id ? client : current));
  }

  async function removeClient(siteId: string) {
    if (!window.confirm(`Remove ${siteId} from the CRM client list? Tenant data is kept for traceability.`)) return;
    setBusy(true);
    try {
      await crmApi.removeClient(siteId);
      setSelectedClient(null);
      setPasswordDialogClient((current) => (current?.site_id === siteId ? null : current));
      setOverview(await crmApi.overview());
      setClientBoardSection('available');
      setView('clients');
      setToast('Client removed from CRM list.');
    } catch (error) {
      showError(error, 'Client removal failed.');
    } finally {
      setBusy(false);
    }
  }

  async function moveClientToAvailable(siteId: string) {
    if (!window.confirm(`Move ${siteId} back to Available? Tenant data and setup evidence are kept.`)) return;
    setBusy(true);
    try {
      const response = await crmApi.moveClientToAvailable(siteId);
      setSelectedClient(response.client);
      setPasswordDialogClient((current) => (current?.site_id === siteId ? response.client : current));
      setOverview(await crmApi.overview());
      setClientBoardSection('available');
      setView('clients');
      setToast('Client moved to Available.');
    } catch (error) {
      showError(error, 'Move to Available failed.');
    } finally {
      setBusy(false);
    }
  }

  async function activateClient(siteId: string) {
    setBusy(true);
    try {
      const response = await crmApi.activateClient(siteId);
      setSelectedClient(response.client);
      setClientInitialTab('overview');
      setOverview(await crmApi.overview());
      setView('client-detail');
      setToast('Client moved to Current.');
    } catch (error) {
      showError(error, 'Client activation failed.');
    } finally {
      setBusy(false);
    }
  }

  async function toggleClient(siteId: string, enabled: boolean) {
    setBusy(true);
    try {
      await crmApi.setClientEnabled(siteId, enabled);
      setOverview(await crmApi.overview());
      if (selectedClient?.site_id === siteId) {
        const response = await crmApi.client(siteId);
        syncClient(response.client);
      }
      setToast(enabled ? 'Client enabled.' : 'Client disabled.');
    } catch (error) {
      showError(error, 'Client status update failed.');
    } finally {
      setBusy(false);
    }
  }

  async function updateClientTokenLimits(siteId: string, tokenLimit: number, sessionTokenLimit: number) {
    setBusy(true);
    try {
      const response = await crmApi.updateClientTokenLimits(siteId, {
        token_limit: tokenLimit,
        session_token_limit: sessionTokenLimit,
      });
      syncClient(response.client);
      setOverview(await crmApi.overview());
      setToast('Token limits saved.');
    } catch (error) {
      showError(error, 'Token limit update failed.');
      throw error;
    } finally {
      setBusy(false);
    }
  }

  async function updateClientPanelPassword(siteId: string, password: string, autoGenerate: boolean) {
    setBusy(true);
    try {
      const response = await crmApi.updateClientPanelPassword(siteId, {
        password: autoGenerate ? undefined : password,
        auto_generate: autoGenerate,
      });
      syncClient(response.client);
      setOverview(await crmApi.overview());
      setToast(autoGenerate ? 'Panel password generated.' : 'Panel password updated.');
      return response.generated_password || '';
    } catch (error) {
      showError(error, 'Client panel password update failed.');
      throw error;
    } finally {
      setBusy(false);
    }
  }

  async function revokeClientPanelPassword(siteId: string) {
    setBusy(true);
    try {
      const response = await crmApi.revokeClientPanelPassword(siteId);
      syncClient(response.client);
      setOverview(await crmApi.overview());
      setToast('Panel password revoked.');
    } catch (error) {
      showError(error, 'Client panel password revoke failed.');
      throw error;
    } finally {
      setBusy(false);
    }
  }

  async function triggerCrawl(siteId: string) {
    const cleanSiteId = typeof siteId === 'string' ? siteId.trim() : '';
    if (!cleanSiteId) {
      setToast('Crawler could not start because the client site ID was missing.');
      return;
    }
    setCrawlingSites((current) => new Set(current).add(cleanSiteId));
    setBusy(true);
    try {
      await crmApi.crawlClient(cleanSiteId);
      setOverview(await crmApi.overview());
      if (selectedClient?.site_id === cleanSiteId) {
        const response = await crmApi.client(cleanSiteId);
        setSelectedClient(response.client);
      }
      setToast('Crawler started.');
      void pollCrawlStatus({
        siteId: cleanSiteId,
        syncClient,
        setOverview,
        setCrawlingSites,
        showError,
      });
    } catch (error) {
      setCrawlingSites((current) => {
        const next = new Set(current);
        next.delete(cleanSiteId);
        return next;
      });
      showError(error, 'Crawler failed to start.');
    } finally {
      setBusy(false);
    }
  }

  async function triggerAutoIntegration(siteId: string) {
    setAutoIntegratingSites((current) => new Set(current).add(siteId));
    setBusy(true);
    try {
      await crmApi.autoIntegrateClient(siteId);
      setToast('Setup run queued.');
      setOverview(await crmApi.overview());
      if (selectedClient?.site_id === siteId) {
        const response = await crmApi.client(siteId);
        syncClient(response.client);
      }
      void pollAutoIntegrationStatus({
        siteId,
        syncClient,
        setOverview,
        setAutoIntegratingSites,
        showError,
      });
    } catch (error) {
      setAutoIntegratingSites((current) => {
        const next = new Set(current);
        next.delete(siteId);
        return next;
      });
      showError(error, 'Setup run failed to start.');
    } finally {
      setBusy(false);
    }
  }

  return {
    activateClient,
    moveClientToAvailable,
    removeClient,
    revokeClientPanelPassword,
    toggleClient,
    triggerAutoIntegration,
    triggerCrawl,
    updateClientPanelPassword,
    updateClientTokenLimits,
  };
}
