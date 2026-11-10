const { app, BrowserWindow, shell, ipcMain } = require('electron');
const path = require('path');
const http = require('http');
const fs = require('fs');

let mainWindow;

function getBackendPort() {
  if (process.env.BACKEND_PORT) {
    return process.env.BACKEND_PORT;
  }
  const portFile = path.join(__dirname, '../../backend/data/.backend_port');
  if (fs.existsSync(portFile)) {
    try {
      const savedPort = fs.readFileSync(portFile, 'utf8').trim();
      if (savedPort) return savedPort;
    } catch (e) {}
  }
  return '8001';
}

function checkServerReady(port, callback) {
  const req = http.get(`http://127.0.0.1:${port}/api/agents`, (res) => {
    callback(res.statusCode === 200);
  });
  req.on('error', () => {
    callback(false);
  });
  req.setTimeout(800, () => {
    req.destroy();
    callback(false);
  });
}

function createWindow() {
  const backendPort = getBackendPort();
  process.env.BACKEND_PORT = backendPort;

  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    title: "المكتب الذكي للجمعية - إفران | AFMI-SmartOffice",
    icon: path.join(__dirname, 'icon.png'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: false
    },
    autoHideMenuBar: false,
  });

  const targetUrl = `http://127.0.0.1:${backendPort}/`;

  console.log(`[Electron] Tentative de connexion au backend sur ${targetUrl} ...`);

  let attempts = 0;
  const maxAttempts = 25;

  function tryLoad() {
    attempts++;
    checkServerReady(backendPort, (isReady) => {
      if (isReady) {
        console.log(`[Electron] Serveur backend actif sur le port ${backendPort} ! Chargement de ${targetUrl}`);
        mainWindow.loadURL(targetUrl);
      } else if (attempts < maxAttempts) {
        console.log(`[Electron] En attente du backend (tentative ${attempts}/${maxAttempts})...`);
        setTimeout(tryLoad, 400);
      } else {
        console.log(`[Electron] Délai dépassé. Chargement direct des fichiers dist statiques.`);
        mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
      }
    });
  }

  tryLoad();

  // Allow F12 or Ctrl+Shift+I to toggle DevTools
  mainWindow.webContents.on('before-input-event', (event, input) => {
    if (input.key === 'F12' || (input.control && input.shift && input.key.toLowerCase() === 'i')) {
      mainWindow.webContents.toggleDevTools();
      event.preventDefault();
    }
    if (input.key === 'F5' || (input.control && input.key.toLowerCase() === 'r')) {
      mainWindow.reload();
      event.preventDefault();
    }
  });

  // Open external links in user's browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http:') || url.startsWith('https:')) {
      shell.openExternal(url);
      return { action: 'deny' };
    }
    return { action: 'allow' };
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
