import type { Theme } from '../theme';

interface ThemeToggleProps {
  className?: string;
  theme: Theme;
  onToggle: () => void;
}

export function ThemeToggle({ className = '', theme, onToggle }: ThemeToggleProps) {
  const darkThemeActive = theme === 'dark';
  const label = darkThemeActive ? 'Switch to light theme' : 'Switch to dark theme';

  return (
    <button
      className={`btn btn-secondary btn-icon theme-toggle${className ? ` ${className}` : ''}`}
      type="button"
      title={label}
      aria-label={label}
      onClick={onToggle}
    >
      {darkThemeActive ? <SunIcon /> : <MoonIcon />}
    </button>
  );
}

function SunIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42M17.65 17.65l1.42 1.42M2 12h2M20 12h2M4.93 19.07l1.42-1.42M17.65 6.35l1.42-1.42" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M20.5 14.2A8.5 8.5 0 0 1 9.8 3.5 8.5 8.5 0 1 0 20.5 14.2Z" />
    </svg>
  );
}
