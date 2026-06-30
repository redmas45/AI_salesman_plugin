import {
  Activity,
  CalendarCheck,
  Calculator,
  ClipboardCheck,
  FileText,
  Gauge,
  PackageOpen,
  Plug,
  ShieldCheck,
  SlidersHorizontal,
  Users,
  type LucideIcon,
} from 'lucide-react';
import type { ClientWorkspaceTabDefinition, ClientWorkspaceTabId } from './types';

const TAB_ICONS: Record<ClientWorkspaceTabId, LucideIcon> = {
  overview: ShieldCheck,
  integration: ClipboardCheck,
  readiness: ShieldCheck,
  catalog: PackageOpen,
  crawl: Gauge,
  activity: Activity,
  adapter: Plug,
  controls: SlidersHorizontal,
  quote_flows: ClipboardCheck,
  bookings: CalendarCheck,
  appointments: CalendarCheck,
  calculators: Calculator,
  documents: FileText,
  leads: Users,
  compliance: ShieldCheck,
  prompt: FileText,
};

export function tab(id: ClientWorkspaceTabId, label: string): ClientWorkspaceTabDefinition {
  return { id, label, icon: TAB_ICONS[id] };
}
