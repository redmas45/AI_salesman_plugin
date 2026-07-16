import type { ReactNode } from 'react';

export interface PanelProps {
  title: string;
  action?: ReactNode;
  children: ReactNode;
  onClick?: () => void;
}

export function Panel({
  title,
  action,
  children,
  onClick,
}: PanelProps) {
  const content = (
    <>
      <div className="card-header">
        <h2>{title}</h2>
        {action}
      </div>
      {children}
    </>
  );
  if (onClick) {
    return (
      <button className="card interactive text-left" type="button" onClick={onClick}>
        {content}
      </button>
    );
  }
  return <section className="card">{content}</section>;
}
