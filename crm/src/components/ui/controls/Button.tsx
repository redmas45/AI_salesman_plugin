import type { ButtonHTMLAttributes } from 'react';
import { type LucideIcon } from 'lucide-react';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon?: LucideIcon;
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'lg';
  spinning?: boolean;
}

export function Button({
  children,
  icon: Icon,
  variant = 'primary',
  size,
  spinning = false,
  className = '',
  ...props
}: ButtonProps) {
  const sizeClass = size ? ` btn-${size}` : '';
  return (
    <button className={`btn btn-${variant}${sizeClass}${className ? ` ${className}` : ''}`} {...props}>
      {Icon ? <Icon className={spinning ? 'spin' : ''} size={15} aria-hidden="true" /> : null}
      <span>{children}</span>
    </button>
  );
}

export interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string;
  icon?: LucideIcon;
  tone?: 'default' | 'danger';
}

export function IconButton({
  label,
  icon: Icon,
  tone = 'default',
  ...props
}: IconButtonProps) {
  return (
    <button
      className={`btn ${tone === 'danger' ? 'btn-danger' : 'btn-secondary'} btn-icon`}
      type="button"
      title={label}
      aria-label={label}
      {...props}
    >
      {Icon ? <Icon size={16} aria-hidden="true" /> : <span>x</span>}
    </button>
  );
}
