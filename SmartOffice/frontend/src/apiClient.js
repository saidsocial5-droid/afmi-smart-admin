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
