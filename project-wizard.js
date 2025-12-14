// Project Wizard State
let wizardData = {
    albumName: '',
    fileType: '',
    files: [],
    projectId: ''
};

const API_URL = 'http://localhost:5001';

// Open wizard
function openProjectWizard() {
    console.log('=== PROJE OLUŞTUR BUTONUNA BASILDI ===');
    document.getElementById('projectWizardModal').style.display = 'flex';
    document.getElementById('albumName').focus();
    wizardData = { albumName: '', fileType: '', files: [], projectId: '' };
    console.log('Modal açıldı, wizard data sıfırlandı');
}

// Close wizard
function closeProjectWizard() {
    document.getElementById('projectWizardModal').style.display = 'none';
    // Reset all steps
    for (let i = 1; i <= 4; i++) {
        document.getElementById(`step${i}`).style.display = 'none';
    }
    document.getElementById('step1').style.display = 'block';
}

// Navigation
function nextStep(step) {
    console.log(`=== İLERİ BUTONUNA BASILDI - Step ${step}'e geçiliyor ===`);
    
    // Validate current step
    if (step === 2) {
        const albumName = document.getElementById('albumName').value.trim();
        console.log('Albüm adı:', albumName);
        if (!albumName) {
            console.log('❌ Albüm adı boş!');
            alert('Lütfen albüm adı girin');
            return;
        }
        wizardData.albumName = albumName;
        console.log('✅ Albüm adı kaydedildi:', albumName);
    }
    
    if (step === 3) {
        console.log('Dosya tipi kontrolü:', wizardData.fileType);
        if (!wizardData.fileType) {
            console.log('❌ Dosya tipi seçilmemiş!');
            alert('Lütfen dosya tipi seçin');
            return;
        }
        console.log('✅ Dosya tipi OK:', wizardData.fileType);
        updateUploadArea();
        // Disable upload button until files are selected
        const uploadNext = document.getElementById('uploadNext');
        if (uploadNext) {
            uploadNext.disabled = true;
            uploadNext.style.opacity = '0.5';
            console.log('Upload next butonu disabled');
        }
    }
    
    if (step === 4) {
        console.log('Yüklenen dosya sayısı:', wizardData.files.length);
        if (wizardData.files.length === 0) {
            console.log('❌ Hiç dosya yüklenmemiş!');
            alert('Lütfen en az bir fotoğraf yükleyin');
            return;
        }
        console.log('✅ Dosyalar OK, özet güncelleniyor...');
        updateSummary();
    }
    
    // Hide all steps
    for (let i = 1; i <= 4; i++) {
        document.getElementById(`step${i}`).style.display = 'none';
    }
    
    // Show target step
    document.getElementById(`step${step}`).style.display = 'block';
    console.log(`✅ Step ${step} gösteriliyor`);
}

function prevStep(step) {
    for (let i = 1; i <= 4; i++) {
        document.getElementById(`step${i}`).style.display = 'none';
    }
    document.getElementById(`step${step}`).style.display = 'block';
}

// File type selection
function selectFileType(type) {
    console.log('=== DOSYA TİPİ SEÇİLDİ ===');
    console.log('Seçilen tip:', type);
    wizardData.fileType = type;
    
    // Update UI
    const cards = document.querySelectorAll('.file-type-card');
    cards.forEach(card => card.classList.remove('selected'));
    event.currentTarget.classList.add('selected');
    
    // Enable next button
    const fileTypeNext = document.getElementById('fileTypeNext');
    if (fileTypeNext) {
        fileTypeNext.disabled = false;
        fileTypeNext.removeAttribute('disabled');
        console.log('✅ File type next butonu aktif edildi');
    }
}

// Update upload area based on file type
function updateUploadArea() {
    const uploadDesc = document.getElementById('uploadDescription');
    const acceptedTypes = document.getElementById('acceptedTypes');
    const fileInput = document.getElementById('fileInput');
    
    if (wizardData.fileType === 'raw') {
        uploadDesc.textContent = 'RAW dosyalarınızı seçin';
        acceptedTypes.textContent = 'RAW, CR2, NEF, ARW, DNG, ORF';
        fileInput.setAttribute('accept', '.raw,.cr2,.nef,.arw,.dng,.orf,.RAW,.CR2,.NEF,.ARW,.DNG,.ORF');
    } else {
        uploadDesc.textContent = 'JPG dosyalarınızı seçin';
        acceptedTypes.textContent = 'JPG, JPEG';
        fileInput.setAttribute('accept', '.jpg,.jpeg,.JPG,.JPEG');
    }
}

// Handle file selection
function handleFileSelect(event) {
    console.log('=== DOSYA SEÇİMİ YAPILDI ===');
    const files = Array.from(event.target.files);
    
    console.log('Seçilen dosya sayısı:', files.length);
    files.forEach((file, i) => {
        console.log(`Dosya ${i + 1}:`, file.name, '-', formatFileSize(file.size));
    });
    
    if (files.length === 0) {
        console.log('❌ Hiç dosya seçilmedi');
        return;
    }
    
    wizardData.files = files;
    console.log('✅ Dosyalar wizardData\'ya kaydedildi');
    
    // Show uploaded files
    const uploadedFilesDiv = document.getElementById('uploadedFiles');
    uploadedFilesDiv.innerHTML = '';
    
    const fileList = document.createElement('div');
    fileList.className = 'file-list';
    
    files.forEach((file, index) => {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.innerHTML = `
            <span class="file-icon">📄</span>
            <span class="file-name">${file.name}</span>
            <span class="file-size">${formatFileSize(file.size)}</span>
        `;
        fileList.appendChild(fileItem);
    });
    
    uploadedFilesDiv.appendChild(fileList);
    uploadedFilesDiv.style.display = 'block';
    
    // Enable next button
    const uploadNext = document.getElementById('uploadNext');
    if (uploadNext) {
        uploadNext.disabled = false;
        uploadNext.style.opacity = '1';
    }
    
    console.log(`${files.length} dosya yüklendi, İleri butonu aktif edildi`);
}

// Drag and drop
const uploadArea = document.getElementById('uploadArea');
if (uploadArea) {
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('drag-over');
    });
    
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('drag-over');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('drag-over');
        
        const files = Array.from(e.dataTransfer.files);
        const fileInput = document.getElementById('fileInput');
        
        // Create a new FileList-like object
        const dataTransfer = new DataTransfer();
        files.forEach(file => dataTransfer.items.add(file));
        fileInput.files = dataTransfer.files;
        
        handleFileSelect({ target: fileInput });
    });
}

// Update summary
function updateSummary() {
    document.getElementById('summaryAlbumName').textContent = wizardData.albumName;
    document.getElementById('summaryFileType').textContent = 
        wizardData.fileType === 'raw' ? 'RAW Dosyalar' : 'JPG/JPEG';
    document.getElementById('summaryPhotoCount').textContent = wizardData.files.length;
    
    const totalSize = wizardData.files.reduce((sum, file) => sum + file.size, 0);
    document.getElementById('summaryTotalSize').textContent = formatFileSize(totalSize);
}

// Format file size
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
}

// Create project
async function createProject() {
    console.log('=== OLUŞTUR BUTONUNA BASILDI ===');
    console.log('Wizard Data:', wizardData);
    
    const createBtn = event.currentTarget;
    createBtn.disabled = true;
    createBtn.innerHTML = '<div class="spinner"></div><span>Oluşturuluyor...</span>';
    
    try {
        // Generate project ID
        wizardData.projectId = 'project_' + Date.now();
        console.log('Proje ID oluşturuldu:', wizardData.projectId);
        
        // Create project in backend
        console.log('Backend\'e proje oluşturma isteği gönderiliyor...');
        const projectResponse = await fetch(`${API_URL}/project/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                projectId: wizardData.projectId,
                albumName: wizardData.albumName,
                fileType: wizardData.fileType,
                createdAt: new Date().toISOString()
            })
        });
        
        console.log('Proje oluşturma response status:', projectResponse.status);
        
        if (!projectResponse.ok) {
            throw new Error('Proje oluşturulamadı');
        }
        
        console.log('✅ Proje backend\'de oluşturuldu');
        
        // Upload files
        console.log('Dosyalar yükleniyor...');
        const formData = new FormData();
        wizardData.files.forEach(file => {
            formData.append('files', file);
        });
        formData.append('projectId', wizardData.projectId);
        
        const uploadResponse = await fetch(`${API_URL}/upload`, {
            method: 'POST',
            body: formData
        });
        
        console.log('Upload response status:', uploadResponse.status);
        
        if (!uploadResponse.ok) {
            throw new Error('Dosyalar yüklenemedi');
        }
        
        const uploadData = await uploadResponse.json();
        console.log('✅ Dosyalar yüklendi:', uploadData);
        
        // Save project ID to localStorage
        localStorage.setItem('currentProjectId', wizardData.projectId);
        localStorage.setItem('editorProjectId', wizardData.projectId);
        console.log('✅ Project ID localStorage\'a kaydedildi');
        console.log('currentProjectId:', localStorage.getItem('currentProjectId'));
        console.log('editorProjectId:', localStorage.getItem('editorProjectId'));
        
        // Close wizard
        console.log('Wizard kapatılıyor...');
        closeProjectWizard();
        
        // Open editor window
        console.log('Editor penceresi açılıyor...');
        openEditorWindow(wizardData.projectId);
        
    } catch (error) {
        console.error('❌ HATA:', error);
        alert('Hata: ' + error.message);
        createBtn.disabled = false;
        createBtn.innerHTML = '<svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M4 10L8 14L16 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg><span>Oluştur</span>';
    }
}

// Open editor window
function openEditorWindow(projectId) {
    console.log('=== EDITOR PENCERESİ AÇILIYOR ===');
    console.log('Project ID:', projectId);
    
    const remote = require('@electron/remote');
    const { BrowserWindow } = remote;
    
    console.log('Remote yüklendi:', !!remote);
    console.log('BrowserWindow:', !!BrowserWindow);
    
    // Save to localStorage before opening
    localStorage.setItem('editorProjectId', projectId);
    console.log('editorProjectId tekrar kaydedildi:', localStorage.getItem('editorProjectId'));
    
    const editorWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        frame: false,
        transparent: true,
        backgroundColor: '#00000000',
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false,
            enableRemoteModule: true
        }
    });
    
    console.log('Editor window oluşturuldu');
    
    // Enable remote BEFORE loading file
    const remoteMain = require('@electron/remote/main');
    remoteMain.enable(editorWindow.webContents);
    console.log('Remote enabled for editor');
    
    editorWindow.loadFile('editor.html');
    console.log('editor.html yükleniyor...');
    
    // DevTools'u aç
    editorWindow.webContents.openDevTools();
    console.log('✅ DevTools açıldı');
    
    // Send project ID after load
    editorWindow.webContents.on('did-finish-load', () => {
        console.log('✅ EDITOR.HTML YÜKLEME TAMAMLANDI');
        editorWindow.webContents.send('load-project', projectId);
    });
    
    console.log('✅ Editor penceresi açıldı');
}

// Make functions global
window.openProjectWizard = openProjectWizard;
window.closeProjectWizard = closeProjectWizard;
window.nextStep = nextStep;
window.prevStep = prevStep;
window.selectFileType = selectFileType;
window.handleFileSelect = handleFileSelect;
window.createProject = createProject;
