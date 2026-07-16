import type { Dispatch, SetStateAction } from 'react';
import type { AnalyticsSectionId, Client, ClientBoardSection, View } from '../types';
import type { ClientWorkspaceTabId } from '../verticals/types';

interface CrmNavigationDeps {
  setSelectedClient: Dispatch<SetStateAction<Client | null>>;
  setClientInitialTab: Dispatch<SetStateAction<ClientWorkspaceTabId>>;
  setSettingsFocusKey: Dispatch<SetStateAction<string>>;
  setView: Dispatch<SetStateAction<View>>;
  setMobileSidebarOpen: Dispatch<SetStateAction<boolean>>;
  setClientBoardSection: Dispatch<SetStateAction<ClientBoardSection>>;
  setAnalyticsSection: Dispatch<SetStateAction<AnalyticsSectionId>>;
}

export function useCrmNavigation({
  setSelectedClient,
  setClientInitialTab,
  setSettingsFocusKey,
  setView,
  setMobileSidebarOpen,
  setClientBoardSection,
  setAnalyticsSection,
}: CrmNavigationDeps) {
  const openView = (nextView: View) => {
    if (nextView !== 'client-detail') {
      setSelectedClient(null);
      setClientInitialTab('overview');
    }
    if (nextView !== 'settings') setSettingsFocusKey('');
    setView(nextView);
    setMobileSidebarOpen(false);
  };

  const openSettings = (focusKey = '') => {
    setSelectedClient(null);
    setClientInitialTab('overview');
    setSettingsFocusKey(focusKey);
    setView('settings');
    setMobileSidebarOpen(false);
  };

  const openClientBoardSection = (section: ClientBoardSection) => {
    setClientBoardSection(section);
    setSelectedClient(null);
    setClientInitialTab('overview');
    setView('clients');
    setMobileSidebarOpen(false);
  };

  const openAnalyticsSection = (section: AnalyticsSectionId) => {
    setAnalyticsSection(section);
    setSelectedClient(null);
    setClientInitialTab('overview');
    setView('analytics');
    setMobileSidebarOpen(false);
  };

  return { openView, openSettings, openClientBoardSection, openAnalyticsSection };
}
