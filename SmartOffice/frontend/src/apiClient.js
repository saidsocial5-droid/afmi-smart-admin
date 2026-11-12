// Smart API client that handles HTTP origin, Vite dev server, and Electron file:// origin
export const getApiBaseUrl = () => {
  if (typeof window !== 'undefined') {
    if (window.location.protocol === 'file:') {
      const port = window.electronAPI?.backendPort || 8001;
      return `http://127.0.0.1:${port}`;
    }
    if (window.location.port === '5173') {
      const port = window.electronAPI?.backendPort || 8001;
      return `http://127.0.0.1:${port}`;
    }
  }
  return '';
};

export const apiFetch = async (endpoint, options = {}) => {
  const base = getApiBaseUrl();
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const url = endpoint.startsWith('http') ? endpoint : `${base}${cleanEndpoint}`;
  return fetch(url, options);
};

/** Télécharge un fichier produit par l'API (nom de fichier donné par le serveur, nommage configurable). */
export const apiDownload = async (endpoint, options = {}) => {
  const res = await apiFetch(endpoint, options);
  if (!res.ok) {
    let detail = `Erreur ${res.status}`;
    try { detail = (await res.json()).detail || detail; } catch { /* réponse non JSON */ }
    throw new Error(detail);
  }
  const name = decodeURIComponent(res.headers.get('X-AFMI-Filename') || 'export');
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
  return name;
};
