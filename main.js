const { app, BrowserWindow } = require('electron');
const path = require('path');
const remoteMain = require('@electron/remote/main');
const { spawn } = require('child_process');
const net = require('net');

remoteMain.initialize();

let mainWindow;
let backendProcess = null;
const BACKEND_PORT = 5001;

/**
 * Check if port is available
 */
function isPortAvailable(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    
    server.once('error', (err) => {
      if (err.code === 'EADDRINUSE') {
        resolve(false); // Port is in use
      } else {
        resolve(false); // Other error, consider unavailable
      }
    });
    
    server.once('listening', () => {
      server.close();
      resolve(true); // Port is available
    });
    
    server.listen(port);
  });
}

/**
 * Get backend executable path based on platform and packaging
 */
function getBackendPath() {
  const platform = process.platform;
  let backendName;
  
  if (platform === 'win32') {
    backendName = 'photexx-backend.exe';
  } else if (platform === 'darwin') {
    backendName = 'photexx-backend.app/Contents/MacOS/photexx-backend';
  } else {
    backendName = 'photexx-backend';
  }
  
  // Check if running as packaged app
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'backend', backendName);
  } else {
    // Development mode
    return path.join(__dirname, 'backend', 'dist', backendName);
  }
}

/**
 * Start backend server
 */
async function startBackend() {
  try {
    console.log('🔍 Checking if backend is already running...');
    
    // Check if port is already in use
    const portAvailable = await isPortAvailable(BACKEND_PORT);
    
    if (!portAvailable) {
      console.log(`✅ Backend already running on port ${BACKEND_PORT}`);
      return true;
    }
    
    const backendPath = getBackendPath();
    console.log(`🚀 Starting backend from: ${backendPath}`);
    
    // Spawn backend process
    backendProcess = spawn(backendPath, [], {
      stdio: 'inherit', // Inherit stdio for logging
      detached: false
    });
    
    backendProcess.on('error', (err) => {
      console.error('❌ Failed to start backend:', err);
    });
    
    backendProcess.on('exit', (code) => {
      console.log(`⚠️ Backend process exited with code ${code}`);
      backendProcess = null;
    });
    
    // Wait for backend to be ready
    console.log('⏳ Waiting for backend to start...');
    await new Promise((resolve) => setTimeout(resolve, 2000));
    
    console.log('✅ Backend server started successfully');
    return true;
    
  } catch (error) {
    console.error('❌ Error starting backend:', error);
    return false;
  }
}

/**
 * Stop backend server
 */
function stopBackend() {
  if (backendProcess) {
    console.log('🛑 Stopping backend server...');
    backendProcess.kill();
    backendProcess = null;
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    frame: false,
    transparent: true,
    backgroundColor: '#00000000',
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    },
    titleBarStyle: 'hidden',
    vibrancy: 'under-window',
    visualEffectState: 'active'
  });

  mainWindow.loadFile('index.html');

  // Enable remote module for this window
  remoteMain.enable(mainWindow.webContents);

  // DevTools'u development modunda aç
  if (process.argv.includes('--dev')) {
    mainWindow.webContents.openDevTools();
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// Start backend before creating window
app.whenReady().then(async () => {
  console.log('=' * 50);
  console.log('🎨 Photexx Studio Starting...');
  console.log('=' * 50);
  
  await startBackend();
  createWindow();
});

app.on('window-all-closed', () => {
  stopBackend(); // Stop backend when app closes
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

// Cleanup on quit
app.on('quit', () => {
  stopBackend();
});
