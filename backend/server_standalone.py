"""
Standalone version of Flask server for PyInstaller packaging
This version is optimized to run as a bundled executable
"""
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import io
import base64
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import cv2
import numpy as np
import rawpy
import imageio
from werkzeug.utils import secure_filename
import json
import xml.etree.ElementTree as ET
import re
import sys
import logging

# Configure logging for standalone mode
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Get base path for PyInstaller
def get_base_path():
    """Get the base path for resources - works with PyInstaller"""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return sys._MEIPASS
    else:
        # Running as script
        return os.path.dirname(os.path.abspath(__file__))

# Configuration
BASE_PATH = get_base_path()
UPLOAD_FOLDER = os.path.join(os.path.expanduser('~'), '.photexx', 'uploads')
PROCESSED_FOLDER = os.path.join(os.path.expanduser('~'), '.photexx', 'processed')
PRESETS_FOLDER = os.path.join(os.path.expanduser('~'), '.photexx', 'presets')
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'raw', 'cr2', 'nef', 'arw', 'dng', 'orf'}

# Create directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)
os.makedirs(PRESETS_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER
app.config['PRESETS_FOLDER'] = PRESETS_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max

# Store projects in memory
projects = {}

# Cache for processed RAW files
raw_cache = {}

def parse_xmp_preset(xmp_path):
    """Parse XMP file and extract Lightroom adjustments - keep original LR values"""
    try:
        with open(xmp_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        adjustments = {}
        
        params = {
            'Exposure2012': 'exposure',
            'Contrast2012': 'contrast',
            'Highlights2012': 'highlights',
            'Shadows2012': 'shadows',
            'Whites2012': 'whites',
            'Blacks2012': 'blacks',
            'Vibrance': 'vibrance',
            'Saturation': 'saturation',
            'Temperature': 'temperature',
            'Tint': 'tint',
            'Sharpness': 'sharpness'
        }
        
        for xmp_key, adj_key in params.items():
            pattern = f'crs:{xmp_key}="([^"]+)"'
            match = re.search(pattern, content)
            if match:
                value = match.group(1)
                try:
                    adjustments[adj_key] = float(value)
                except ValueError:
                    adjustments[adj_key] = value
        
        logger.info(f"Parsed preset values: {adjustments}")
        return adjustments
        
    except Exception as e:
        logger.error(f"Error parsing XMP: {str(e)}")
        return {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_raw_file(filename):
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    return ext in {'cr2', 'nef', 'arw', 'dng', 'orf', 'raw'}

def load_image(filepath):
    """Load image - handle RAW files with caching"""
    try:
        if is_raw_file(filepath):
            if filepath in raw_cache:
                logger.info(f"Using cached RAW image: {filepath}")
                return raw_cache[filepath]
            
            logger.info(f"Loading RAW file: {filepath}")
            with rawpy.imread(filepath) as raw:
                rgb = raw.postprocess(
                    use_camera_wb=True,
                    half_size=False,
                    no_auto_bright=True,
                    output_bps=8
                )
            
            img = Image.fromarray(rgb)
            img = ImageOps.exif_transpose(img)
            
            max_width = 1920
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
            raw_cache[filepath] = img
            logger.info(f"RAW file loaded and cached: {img.size}")
            return img
        else:
            img = Image.open(filepath)
            img = ImageOps.exif_transpose(img)
            return img
            
    except Exception as e:
        logger.error(f"Error loading image: {str(e)}")
        raise

def apply_adjustments(img, adjustments):
    """Apply Lightroom-style adjustments to image"""
    try:
        img_array = np.array(img).astype(np.float32) / 255.0
        
        exposure = adjustments.get('exposure', 0) / 5.0
        contrast = adjustments.get('contrast', 0) / 100.0
        saturation = adjustments.get('saturation', 0) / 100.0
        vibrance = adjustments.get('vibrance', 0) / 100.0
        sharpness = adjustments.get('sharpness', 40)
        temperature = adjustments.get('temperature', 0)
        tint = adjustments.get('tint', 0)
        
        highlights = adjustments.get('highlights', 0) / 100.0
        shadows = adjustments.get('shadows', 0) / 100.0
        whites = adjustments.get('whites', 0) / 100.0
        blacks = adjustments.get('blacks', 0) / 100.0
        
        if exposure != 0:
            img_array = np.clip(img_array * (2.0 ** exposure), 0, 1)
        
        if temperature != 0:
            temp_factor = temperature / 100.0
            img_array[:, :, 0] = np.clip(img_array[:, :, 0] * (1 + temp_factor * 0.3), 0, 1)
            img_array[:, :, 2] = np.clip(img_array[:, :, 2] * (1 - temp_factor * 0.3), 0, 1)
        
        if tint != 0:
            tint_factor = tint / 100.0
            img_array[:, :, 1] = np.clip(img_array[:, :, 1] * (1 + tint_factor * 0.2), 0, 1)
        
        img_uint8 = (img_array * 255).astype(np.uint8)
        img_hsv = cv2.cvtColor(img_uint8, cv2.COLOR_RGB2HSV).astype(np.float32)
        h, s, v = cv2.split(img_hsv)
        
        if shadows != 0:
            shadow_mask = (v < 85).astype(np.float32)
            shadow_mask = cv2.GaussianBlur(shadow_mask, (21, 21), 0)
            v = v + (shadows * 50 * shadow_mask)
        
        if highlights != 0:
            highlight_mask = (v > 170).astype(np.float32)
            highlight_mask = cv2.GaussianBlur(highlight_mask, (21, 21), 0)
            v = v + (highlights * 50 * highlight_mask)
        
        if whites != 0:
            white_mask = (v > 200).astype(np.float32)
            white_mask = cv2.GaussianBlur(white_mask, (15, 15), 0)
            v = v + (whites * 30 * white_mask)
        
        if blacks != 0:
            black_mask = (v < 55).astype(np.float32)
            black_mask = cv2.GaussianBlur(black_mask, (15, 15), 0)
            v = v + (blacks * 30 * black_mask)
        
        v = np.clip(v, 0, 255)
        
        if contrast != 0:
            v = ((v / 255.0 - 0.5) * (1 + contrast) + 0.5) * 255.0
            v = np.clip(v, 0, 255)
        
        if saturation != 0:
            s = s * (1 + saturation)
            s = np.clip(s, 0, 255)
        
        if vibrance != 0:
            s_normalized = s / 255.0
            vibrance_mask = 1.0 - s_normalized
            s = s + (vibrance * 100 * vibrance_mask)
            s = np.clip(s, 0, 255)
        
        img_hsv = cv2.merge([h, s, v]).astype(np.uint8)
        img_array = cv2.cvtColor(img_hsv, cv2.COLOR_HSV2RGB)
        
        img = Image.fromarray(img_array)
        
        if sharpness > 0:
            sharpness_factor = sharpness / 100.0
            img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=int(sharpness_factor * 150), threshold=3))
        
        return img
        
    except Exception as e:
        logger.error(f"Error applying adjustments: {str(e)}")
        return img

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'Photexx Backend is running'})

@app.route('/upload', methods=['POST'])
def upload_file():
    """Upload multiple files for a project"""
    try:
        if 'files' not in request.files:
            logger.error('No files in request')
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        project_id = request.form.get('projectId')
        
        if not project_id:
            logger.error('No projectId provided')
            return jsonify({'error': 'No project ID provided'}), 400
        
        if project_id not in projects:
            logger.error(f'Project not found: {project_id}')
            return jsonify({'error': 'Project not found'}), 404
        
        logger.info(f'Uploading {len(files)} files for project {project_id}')
        uploaded_files = []
        
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                logger.info(f"File uploaded: {filename}")
                
                file_info = {
                    'filename': filename,
                    'path': filepath,
                    'previewUrl': f'/image/{filename}',
                    'type': 'raw' if is_raw_file(filename) else 'jpg'
                }
                
                projects[project_id]['images'].append(file_info)
                uploaded_files.append(file_info)
        
        logger.info(f'✅ Uploaded {len(uploaded_files)} files')
        
        return jsonify({
            'success': True,
            'uploaded': len(uploaded_files),
            'files': uploaded_files
        })
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/adjust', methods=['POST'])
@app.route('/process', methods=['POST'])
def adjust_image():
    """Apply adjustments to image"""
    try:
        data = request.json
        filename = data.get('filename')
        adjustments = data.get('adjustments', {})
        
        if not filename:
            return jsonify({'error': 'No filename provided'}), 400
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
        
        img = load_image(filepath)
        img = apply_adjustments(img, adjustments)
        
        output = io.BytesIO()
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        img.save(output, format='JPEG', quality=95)
        output.seek(0)
        
        img_base64 = base64.b64encode(output.getvalue()).decode('utf-8')
        
        return jsonify({
            'success': True,
            'image': f'data:image/jpeg;base64,{img_base64}'
        })
        
    except Exception as e:
        logger.error(f"Adjustment error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/presets', methods=['GET'])
@app.route('/presets/list', methods=['GET'])
def list_presets():
    """List all available XMP presets"""
    try:
        presets = []
        if os.path.exists(app.config['PRESETS_FOLDER']):
            for file in os.listdir(app.config['PRESETS_FOLDER']):
                if file.endswith('.xmp'):
                    presets.append(file)
        return jsonify({'presets': presets})
    except Exception as e:
        logger.error(f"Error listing presets: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/image/<filename>', methods=['GET'])
@app.route('/preview/<filename>', methods=['GET'])
def get_image(filename):
    """Get image file"""
    try:
        # Try upload folder first
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(filepath):
            # Load and return as JPEG
            img = load_image(filepath)
            
            # Resize for preview
            max_width = 1920
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
            output = io.BytesIO()
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            img.save(output, format='JPEG', quality=85)
            output.seek(0)
            
            return send_file(output, mimetype='image/jpeg')
        
        return jsonify({'error': 'File not found'}), 404
        
    except Exception as e:
        logger.error(f"Error serving image: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/preset/<preset_name>', methods=['GET'])
def get_preset(preset_name):
    """Load and parse a specific XMP preset"""
    try:
        preset_path = os.path.join(app.config['PRESETS_FOLDER'], preset_name)
        
        if not os.path.exists(preset_path):
            return jsonify({'error': 'Preset not found'}), 404
        
        adjustments = parse_xmp_preset(preset_path)
        
        return jsonify({
            'success': True,
            'preset': preset_name,
            'adjustments': adjustments
        })
        
    except Exception as e:
        logger.error(f"Error loading preset: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/project', methods=['POST'])
@app.route('/project/create', methods=['POST'])
def create_project():
    """Create new project"""
    try:
        data = request.json
        project_id = data.get('projectId') or data.get('project_id')
        album_name = data.get('albumName') or data.get('project_name')
        file_type = data.get('fileType', '')
        
        if not project_id or not album_name:
            return jsonify({'error': 'Missing project data'}), 400
        
        projects[project_id] = {
            'id': project_id,
            'albumName': album_name,
            'name': album_name,
            'fileType': file_type,
            'images': [],
            'createdAt': data.get('createdAt')
        }
        
        logger.info(f"✅ Project created: {project_id} - {album_name}")
        return jsonify({'success': True, 'project': projects[project_id]})
        
    except Exception as e:
        logger.error(f"Project creation error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/project/<project_id>', methods=['GET'])
def get_project(project_id):
    """Get project details"""
    if project_id in projects:
        return jsonify(projects[project_id])
    return jsonify({'error': 'Project not found'}), 404

def run_server(port=5001):
    """Run the Flask server"""
    logger.info("=" * 50)
    logger.info("🚀 Photexx Backend Server Starting...")
    logger.info(f"📍 Server running on http://localhost:{port}")
    logger.info(f"📁 Upload folder: {UPLOAD_FOLDER}")
    logger.info(f"📁 Presets folder: {PRESETS_FOLDER}")
    logger.info("=" * 50)
    
    # Disable Flask development server warning
    app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)

if __name__ == '__main__':
    run_server()
