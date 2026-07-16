import { Moon, Sun } from 'lucide-react';
import type { Theme } from '../../../types';

interface ThemeToggleProps {
  className?: string;
  theme: Theme;
  onToggle: () => void;
}

export function ThemeToggle({ className = '', theme, onToggle }: ThemeToggleProps) {
  const darkThemeActive = theme === 'dark';
  const label = darkThemeActive ? 'Switch to light theme' : 'Switch to dark theme';
  const Icon = darkThemeActive ? Sun : Moon;

  return (
    <button
      className={`btn btn-secondary btn-icon theme-toggle${className ? ` ${className}` : ''}`}
      type="button"
      title={label}
      aria-label={label}
      onClick={onToggle}
    >
      <Icon size={17} aria-hidden="true" />
    </button>
  );
}
