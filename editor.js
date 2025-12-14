alert('🔥 EDITOR.JS YÜKLENDI - ALERT ÇALIŞIYOR! 🔥');

console.log('========================================');
console.log('EDITOR.JS LOADED - SCRIPT BAŞLADI');
console.log('========================================');

// Remote'u daha sonra kullanacağız, önce localStorage'ı kontrol edelim
let remote = null;
let currentWindow = null;

try {
    remote = require('@electron/remote');
    currentWindow = remote ? remote.getCurrentWindow() : null;
    console.log('Remote loaded:', !!remote);
    console.log('Current window:', !!currentWindow);
} catch (error) {
    console.log('Remote yüklenemedi (henüz hazır değil):', error.message);
}

const API_URL = 'http://localhost:5001';
console.log('API URL:', API_URL);

// Get project ID
let projectId = null;

// Try localStorage first
projectId = localStorage.getItem('editorProjectId') || localStorage.getItem('currentProjectId');

console.log('Checking localStorage...');
console.log('editorProjectId:', localStorage.getItem('editorProjectId'));
console.log('currentProjectId:', localStorage.getItem('currentProjectId'));
console.log('Final projectId:', projectId);

if (projectId) {
    console.log('✅ Project ID from localStorage:', projectId);
} else {
    console.error('❌ No project ID found in localStorage!');
}

// State
let currentProject = null;
let currentImageIndex = 0;
let images = [];
let adjustments = {
    exposure: 0,
    contrast: 0,
    highlights: 0,
    shadows: 0,
    whites: 0,
    blacks: 0,
    vibrance: 0,
    saturation: 0,
    temperature: 0,
    tint: 0,
    sharpness: 40
};

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

// Load project
async function loadProject() {
    console.log('=== LOAD PROJECT STARTED ===');
    console.log('Loading project:', projectId);
    console.log('API URL:', API_URL);
    
    if (!projectId) {
        console.error('No project ID found!');
        alert('Proje ID bulunamadı. Lütfen yeniden açın.');
        return;
    }
    
    try {
        const url = `${API_URL}/project/${projectId}`;
        console.log('Fetching:', url);
        
        const response = await fetch(url);
        console.log('Response status:', response.status);
        
        if (!response.ok) throw new Error('Project not found');
        
        currentProject = await response.json();
        images = currentProject.images;
        
        console.log('Project loaded:', currentProject);
        console.log('Images:', images);
        
        // Load presets
        await loadPresets();
        
        // Update title
        document.getElementById('projectTitle').textContent = currentProject.albumName;
        
        // Load thumbnails
        loadThumbnails();
        
        // Load first image
        if (images.length > 0) {
            loadImage(0);
        }
    } catch (error) {
        console.error('Error loading project:', error);
        alert('Proje yüklenemedi: ' + error.message);
    }
}

// Load thumbnails
function loadThumbnails() {
    const container = document.getElementById('thumbnailsContainer');
    container.innerHTML = '';
    
    console.log('Loading thumbnails for', images.length, 'images');
    
    images.forEach((img, index) => {
        const thumb = document.createElement('img');
        thumb.className = 'thumbnail';
        thumb.src = `${API_URL}${img.previewUrl}`;
        thumb.alt = img.filename;
        thumb.onclick = () => loadImage(index);
        
        thumb.onerror = () => {
            console.error('Failed to load thumbnail:', img.previewUrl);
            thumb.src = 'data:image/svg+xml,<svg width="90" height="90" xmlns="http://www.w3.org/2000/svg"><rect width="90" height="90" fill="%23333"/><text x="50%" y="50%" text-anchor="middle" fill="white" font-size="12">Error</text></svg>';
        };
        
        if (index === 0) thumb.classList.add('active');
        
        container.appendChild(thumb);
    });
    
    console.log('Thumbnails loaded');
}

// Load image
async function loadImage(index) {
    currentImageIndex = index;
    
    // Update active thumbnail
    const thumbnails = document.querySelectorAll('.thumbnail');
    thumbnails.forEach((t, i) => {
        t.classList.toggle('active', i === index);
    });
    
    // Load image
    const img = images[index];
    const mainImage = document.getElementById('mainImage');
    mainImage.src = `${API_URL}${img.previewUrl}`;
    
    // Update info
    document.getElementById('fileName').textContent = img.filename;
    document.getElementById('fileType').textContent = img.type.toUpperCase();
    
    // Don't reset adjustments here - it causes infinite loop
    // Only reset sliders to default values
    if (!adjustments.brightness) {
        document.getElementById('brightness').value = 1;
        document.getElementById('brightnessValue').textContent = '1.0';
        document.getElementById('contrast').value = 1;
        document.getElementById('contrastValue').textContent = '1.0';
        document.getElementById('saturation').value = 1;
        document.getElementById('saturationValue').textContent = '1.0';
        document.getElementById('sharpness').value = 1;
        document.getElementById('sharpnessValue').textContent = '1.0';
        document.getElementById('exposure').value = 0;
        document.getElementById('exposureValue').textContent = '0';
        document.getElementById('temperature').value = 0;
        document.getElementById('temperatureValue').textContent = '0';
        document.getElementById('tint').value = 0;
        document.getElementById('tintValue').textContent = '0';
    }
}

// Update adjustment
let adjustmentTimeout = null;
window.updateAdjustment = function(key, value) {
    adjustments[key] = parseFloat(value);
    
    // Update value display with proper formatting
    const displayValue = (key === 'exposure' || key === 'temperature' || key === 'tint') 
        ? parseInt(value) 
        : parseFloat(value).toFixed(2);
    document.getElementById(`${key}Value`).textContent = displayValue;
    
    // Longer debounce for smoother experience
    clearTimeout(adjustmentTimeout);
    adjustmentTimeout = setTimeout(() => {
        processImage();
    }, 600); // Increased from 300ms to 600ms
};

// Process image with adjustments
async function processImage() {
    const loadingOverlay = document.getElementById('loadingOverlay');
    loadingOverlay.style.display = 'flex';
    
    try {
        const currentImage = images[currentImageIndex];
        
        const response = await fetch(`${API_URL}/process`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                filename: currentImage.filename,
                adjustments: adjustments
            })
        });
        
        if (!response.ok) throw new Error('Processing failed');
        
        const data = await response.json();
        
        // Update main image
        document.getElementById('mainImage').src = data.image;
        
    } catch (error) {
        console.error('Error processing image:', error);
        alert('Resim işlenemedi: ' + error.message);
    } finally {
        loadingOverlay.style.display = 'none';
    }
}

// Load presets from backend
async function loadPresets() {
    try {
        console.log('Loading presets from XMP files...');
        const response = await fetch(`${API_URL}/presets/list`);
        
        if (!response.ok) {
            console.error('Failed to load presets');
            return;
        }
        
        const data = await response.json();
        console.log(`Loaded ${data.count} presets:`, data.presets);
        
        // Update preset list in UI
        const presetList = document.querySelector('.preset-list');
        if (!presetList) return;
        
        // Clear existing presets
        presetList.innerHTML = '';
        
        // Add presets from XMP files
        data.presets.forEach(preset => {
            const presetDiv = document.createElement('div');
            presetDiv.className = 'preset-item';
            presetDiv.onclick = () => applyPreset(preset.name);
            
            // Create preview (you can enhance this later)
            const previewDiv = document.createElement('div');
            previewDiv.className = 'preset-preview';
            previewDiv.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
            
            const nameSpan = document.createElement('span');
            nameSpan.textContent = preset.name;
            
            presetDiv.appendChild(previewDiv);
            presetDiv.appendChild(nameSpan);
            presetList.appendChild(presetDiv);
        });
        
        console.log('✅ Presets loaded to UI');
        
    } catch (error) {
        console.error('Error loading presets:', error);
    }
}

// Apply preset
window.applyPreset = async function(presetName) {
    const loadingOverlay = document.getElementById('loadingOverlay');
    loadingOverlay.style.display = 'flex';
    
    try {
        const currentImage = images[currentImageIndex];
        
        const response = await fetch(`${API_URL}/preset/apply`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                filename: currentImage.filename,
                preset: presetName
            })
        });
        
        if (!response.ok) throw new Error('Preset application failed');
        
        const data = await response.json();
        
        // Update main image
        document.getElementById('mainImage').src = data.image;
        
        // Update sliders with preset values
        if (data.adjustments) {
            console.log('Preset adjustments:', data.adjustments);
            
            // Update global adjustments object
            adjustments = {
                exposure: data.adjustments.exposure || 0,
                contrast: data.adjustments.contrast || 0,
                highlights: data.adjustments.highlights || 0,
                shadows: data.adjustments.shadows || 0,
                whites: data.adjustments.whites || 0,
                blacks: data.adjustments.blacks || 0,
                vibrance: data.adjustments.vibrance || 0,
                saturation: data.adjustments.saturation || 0,
                temperature: data.adjustments.temperature || 0,
                tint: data.adjustments.tint || 0,
                sharpness: data.adjustments.sharpness || 40
            };
            
            // Update UI sliders dynamically
            const sliders = ['exposure', 'contrast', 'highlights', 'shadows', 'whites', 'blacks', 
                           'vibrance', 'saturation', 'temperature', 'tint', 'sharpness'];
            
            sliders.forEach(slider => {
                if (data.adjustments[slider] !== undefined) {
                    const element = document.getElementById(slider);
                    const valueElement = document.getElementById(`${slider}Value`);
                    
                    if (element && valueElement) {
                        element.value = data.adjustments[slider];
                        const displayValue = (slider === 'exposure') 
                            ? data.adjustments[slider].toFixed(1)
                            : parseInt(data.adjustments[slider]);
                        valueElement.textContent = displayValue;
                    }
                }
            });
            
            console.log('✅ Sliders updated with preset values');
        }
        
    } catch (error) {
        console.error('Error applying preset:', error);
        alert('Preset uygulanamadı: ' + error.message);
    } finally {
        loadingOverlay.style.display = 'none';
    }
};

// Reset adjustments
window.resetAdjustments = function() {
    adjustments = {
        contrast: 0,
        saturation: 0,
        sharpness: 40,
        exposure: 0,
        temperature: 0,
        tint: 0
    };
    
    // Update all sliders to Lightroom defaults
    document.getElementById('contrast').value = 0;
    document.getElementById('contrastValue').textContent = '0';
    document.getElementById('saturation').value = 0;
    document.getElementById('saturationValue').textContent = '0';
    document.getElementById('sharpness').value = 40;
    document.getElementById('sharpnessValue').textContent = '40';
    document.getElementById('exposure').value = 0;
    document.getElementById('exposureValue').textContent = '0';
    document.getElementById('temperature').value = 0;
    document.getElementById('temperatureValue').textContent = '0';
    document.getElementById('tint').value = 0;
    document.getElementById('tintValue').textContent = '0';
    
    // Show original image without reloading
    const currentImage = images[currentImageIndex];
    document.getElementById('mainImage').src = `${API_URL}/preview/${currentImage.filename}`;
};

// Scroll thumbnails
window.scrollThumbnails = function(direction) {
    const container = document.getElementById('thumbnailsContainer');
    const scrollAmount = 200;
    container.scrollLeft += direction * scrollAmount;
};

// Export current
window.exportCurrent = async function() {
    alert('Dışa aktarma özelliği yakında eklenecek!');
};

// Export all
window.exportAll = async function() {
    alert('Toplu dışa aktarma özelliği yakında eklenecek!');
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('========================================');
    console.log('DOM CONTENT LOADED EVENT FIRED!');
    console.log('========================================');
    console.log('Editor DOM loaded');
    console.log('Project ID:', projectId);
    
    if (projectId) {
        console.log('Calling loadProject()...');
        loadProject();
    } else {
        console.error('❌ No project ID - cannot load!');
        alert('Proje ID bulunamadı. Lütfen dashboard\'dan yeniden açın.');
    }
});

console.log('========================================');
console.log('EDITOR.JS SON SATIR - DOMContentLoaded listener eklendi');
console.log('========================================');
