import type { ClientBoardSection } from '../../types';

export function clientBoardSectionLabel(section: ClientBoardSection): string {
  if (section === 'current') return 'Current clients';
  if (section === 'available') return 'Available installs';
  if (section === 'online') return 'Online installs';
  if (section === 'offline') return 'Offline installs';
  return 'All clients';
}
