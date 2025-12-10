import { loginUser, logoutUser, observeAuthState } from './firebase-config.js';

// Window controls (Electron)
let currentWindow = null;
try {
    const { remote } = require('electron');
    currentWindow = remote ? remote.getCurrentWindow() : null;
} catch (e) {
    console.log('Running without Electron remote');
}

// Window controls
window.minimizeWindow = () => {
    if (currentWindow) currentWindow.minimize();
};

window.maximizeWindow = () => {
    if (currentWindow) {
        if (currentWindow.isMaximized()) {
            currentWindow.unmaximize();
        } else {
            currentWindow.maximize();
        }
    }
};

window.closeWindow = () => {
    if (currentWindow) currentWindow.close();
};

// Page elements
const loginPage = document.getElementById('loginPage');
const dashboardPage = document.getElementById('dashboardPage');
const loginButton = document.getElementById('loginButton');
const errorMessage = document.getElementById('errorMessage');

// Show/Hide loading state
function setLoading(isLoading) {
    const buttonText = loginButton.querySelector('.button-text');
    const buttonLoader = loginButton.querySelector('.button-loader');
    
    if (isLoading) {
        buttonText.style.display = 'none';
        buttonLoader.style.display = 'block';
        loginButton.disabled = true;
    } else {
        buttonText.style.display = 'block';
        buttonLoader.style.display = 'none';
        loginButton.disabled = false;
    }
}

// Show error message
function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
    setTimeout(() => {
        errorMessage.style.display = 'none';
    }, 5000);
}

// Handle login
window.handleLogin = async (event) => {
    event.preventDefault();
    
    console.log('=== GİRİŞ BAŞLADI ===');
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    
    console.log('Email:', email);
    
    setLoading(true);
    errorMessage.style.display = 'none';
    
    const result = await loginUser(email, password);
    
    console.log('Login sonucu:', result);
    
    setLoading(false);
    
    if (result.success) {
        console.log('✅ GİRİŞ BAŞARILI');
        console.log('Kullanıcı:', result.user.email);
        console.log('Firma:', result.userData.firma || result.userData.firmName);
        
        // Update user info in dashboard
        updateDashboardUser(result.user, result.userData);
        
        // Switch to dashboard
        console.log('Dashboard\'a geçiliyor...');
        loginPage.style.display = 'none';
        dashboardPage.style.display = 'flex';
        console.log('✅ DASHBOARD AÇILDI');
    } else {
        let errorMsg = 'Giriş yapılamadı';
        
        if (result.error.includes('firma')) {
            errorMsg = 'Bu hesap firma yetkisine sahip değil';
        } else if (result.error.includes('wrong-password') || result.error.includes('user-not-found')) {
            errorMsg = 'E-posta veya şifre hatalı';
        } else if (result.error.includes('network')) {
            errorMsg = 'İnternet bağlantınızı kontrol edin';
        }
        
        showError(errorMsg);
    }
};

// Update dashboard with user info
function updateDashboardUser(user, userData) {
    const userName = document.getElementById('userName');
    const userEmail = document.getElementById('userEmail');
    const userInitials = document.getElementById('userInitials');
    
    // Use firmName, contactName, or email
    if (userData.firmName) {
        userName.textContent = userData.firmName;
    } else if (userData.contactName) {
        userName.textContent = userData.contactName;
    } else if (userData.firma) {
        userName.textContent = userData.firma;
    } else {
        userName.textContent = user.displayName || user.email.split('@')[0];
    }
    
    userEmail.textContent = user.email;
    
    // Get initials
    const name = userName.textContent;
    const initials = name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
    userInitials.textContent = initials;
}

// Handle logout
window.handleLogout = async () => {
    const result = await logoutUser();
    
    if (result.success) {
        // Clear form
        document.getElementById('email').value = '';
        document.getElementById('password').value = '';
        
        // Switch to login page
        dashboardPage.style.display = 'none';
        loginPage.style.display = 'flex';
    }
};

// Observe auth state changes
observeAuthState((user) => {
    if (user) {
        console.log('User is signed in:', user.email);
    } else {
        console.log('User is signed out');
        // Make sure we're on login page
        if (dashboardPage.style.display !== 'none') {
            dashboardPage.style.display = 'none';
            loginPage.style.display = 'flex';
        }
    }
});

// Initialize
console.log('Photexx Studio initialized');
