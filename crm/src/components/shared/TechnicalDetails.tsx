import { useState } from 'react';
import { ChevronDown, Code2 } from 'lucide-react';
import { EmptyState } from '../ui/EmptyState';

export interface TechnicalDetailsProps {
  title: string;
  data: unknown;
}

export function TechnicalDetails({ title, data }: TechnicalDetailsProps) {
  const [open, setOpen] = useState(false);
  if (!data) return <EmptyState text="No technical report is available yet." />;
  return (
    <div className="technical-details">
      <button className="summary-toggle" type="button" onClick={() => setOpen((current) => !current)}>
        <ChevronDown className={open ? 'open' : ''} size={16} aria-hidden="true" />
        <Code2 size={16} aria-hidden="true" />
        <span>{title}</span>
      </button>
      {open ? <pre className="code-block technical-json">{JSON.stringify(data, null, 2)}</pre> : null}
    </div>
  );
}
