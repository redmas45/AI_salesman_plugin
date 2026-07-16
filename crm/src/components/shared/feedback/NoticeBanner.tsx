import { CheckCircle2, AlertTriangle, FileText } from 'lucide-react';

export interface NoticeBannerProps {
  tone: 'success' | 'error' | 'info';
  message: string;
}

export function NoticeBanner({ tone, message }: NoticeBannerProps) {
  return (
    <div className={`notice-banner notice-banner-${tone}`}>
      {tone === 'success' ? <CheckCircle2 size={17} aria-hidden="true" /> : null}
      {tone === 'error' ? <AlertTriangle size={17} aria-hidden="true" /> : null}
      {tone === 'info' ? <FileText size={17} aria-hidden="true" /> : null}
      <span>{message}</span>
    </div>
  );
}
