const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  platform: process.platform,
  version: '1.0.0',
  backendPort: parseInt(process.env.BACKEND_PORT || '8001', 10)
});
