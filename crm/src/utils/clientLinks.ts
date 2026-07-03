export function clientPanelHref(siteId: string) {
  const pathPrefix = hubPathPrefix();
  const path = `${pathPrefix}/client_panel/${encodeURIComponent(siteId)}`;
  if (typeof window === 'undefined') return path;
  const { hostname, port, protocol } = window.location;
  if (window.location.pathname.includes('/crm')) return path;
  if ((hostname === '127.0.0.1' || hostname === 'localhost') && port !== '8585') {
    return `${protocol}//${hostname}:8585${path}`;
  }
  return path;
}

function hubPathPrefix() {
  if (typeof window === 'undefined') return '';
  const crmIndex = window.location.pathname.indexOf('/crm');
  if (crmIndex <= 0) return '';
  return window.location.pathname.slice(0, crmIndex).replace(/\/$/, '');
}
