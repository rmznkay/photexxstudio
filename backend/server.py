from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import io
import base64
from PIL import Image, ImageEnhance, ImageFilter
import cv2
import numpy as np
import rawpy
import imageio
from werkzeug.utils import secure_filename
import json
import xml.etree.ElementTree as ET
import re

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
PRESETS_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'presets')
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'raw', 'cr2', 'nef', 'arw', 'dng', 'orf'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)
os.makedirs(PRESETS_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER
app.config['PRESETS_FOLDER'] = PRESETS_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max

# Store projects in memory (you can later move to database)
projects = {}

# Cache for processed RAW files (to speed up adjustments)
raw_cache = {}

def parse_xmp_preset(xmp_path):
    """Parse XMP file and extract Lightroom adjustments - keep original LR values"""
    try:
        with open(xmp_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract values using regex
        adjustments = {}
        
        # Lightroom parameters - store as-is
        params = {
            'Exposure2012': 'exposure',
            'Contrast2012': 'contrast',
            'Highlights2012': 'highlights',
            'Shadows2012': 'shadows',
            'Whites2012': 'whites',
            'Blacks2012': 'blacks',
            'Clarity2012': 'clarity',
            'Vibrance': 'vibrance',
            'Saturation': 'saturation',
            'Sharpness': 'sharpness',
            'IncrementalTemperature': 'temperature',
            'IncrementalTint': 'tint',
            'Texture': 'texture',
            'Dehaze': 'dehaze'
        }
        
        for xmp_param, our_param in params.items():
            # Try both with and without quotes
            match = re.search(f'crs:{xmp_param}="([^"]+)"', content)
            if not match:
                match = re.search(f'crs:{xmp_param}=([+-]?\\d+\\.?\\d*)', content)
            
            if match:
                value_str = match.group(1).replace('+', '')
                value = float(value_str)
                
                # Store Lightroom values as-is (no conversion)
                adjustments[our_param] = value
        
        print(f"Parsed preset values: {adjustments}")
        return adjustments
        
    except Exception as e:
        print(f"Error parsing XMP {xmp_path}: {str(e)}")
        return None

def load_presets_from_folder():
    """Load all XMP presets from presets folder"""
    presets = {}
    
    if not os.path.exists(PRESETS_FOLDER):
        return presets
    
    for filename in os.listdir(PRESETS_FOLDER):
        if filename.endswith('.xmp'):
            preset_name = filename[:-4]  # Remove .xmp extension
            xmp_path = os.path.join(PRESETS_FOLDER, filename)
            adjustments = parse_xmp_preset(xmp_path)
            
            if adjustments:
                presets[preset_name] = adjustments
                print(f"✅ Loaded preset: {preset_name}")
    
    return presets

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_raw_file(filename):
    raw_extensions = {'raw', 'cr2', 'nef', 'arw', 'dng', 'orf'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in raw_extensions

def convert_raw_to_rgb(raw_path):
    """Convert RAW file to RGB numpy array with proper orientation"""
    with rawpy.imread(raw_path) as raw:
        rgb = raw.postprocess(
            use_camera_wb=True,
            half_size=False,
            no_auto_bright=True,
            output_bps=8,
            use_auto_wb=False,
            output_color=rawpy.ColorSpace.sRGB,
            bright=1.0
        )
    
    # Convert to PIL Image to handle EXIF rotation
    img = Image.fromarray(rgb)
    
    # Auto-rotate based on EXIF orientation
    try:
        from PIL import ImageOps
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass
    
    return np.array(img)

def apply_adjustments(image, adjustments):
    """Apply Lightroom-style adjustments to image"""
    img = Image.fromarray(image) if isinstance(image, np.ndarray) else image
    
    # Convert to numpy for faster processing
    img_array = np.array(img).astype(np.float32)
    
    # Exposure (LR: -5.0 to +5.0)
    if 'exposure' in adjustments and adjustments['exposure'] != 0:
        exposure = adjustments['exposure']
        factor = 2 ** exposure
        img_array = np.clip(img_array * factor, 0, 255)
    
    # Shadows/Highlights/Whites/Blacks (LR: -100 to +100)
    # These work on specific tonal ranges
    if any(k in adjustments for k in ['shadows', 'highlights', 'whites', 'blacks']):
        # Convert to HSV to work on luminance
        img_hsv = cv2.cvtColor(img_array.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
        v_channel = img_hsv[:,:,2]
        
        # Shadows: affect dark areas (0-64)
        if 'shadows' in adjustments and adjustments['shadows'] != 0:
            shadow_val = adjustments['shadows'] / 100.0
            mask = np.clip((64 - v_channel) / 64.0, 0, 1)  # Stronger in darker areas
            v_channel += shadow_val * 30 * mask
        
        # Highlights: affect bright areas (192-255)
        if 'highlights' in adjustments and adjustments['highlights'] != 0:
            highlight_val = adjustments['highlights'] / 100.0
            mask = np.clip((v_channel - 192) / 64.0, 0, 1)  # Stronger in brighter areas
            v_channel += highlight_val * 30 * mask
        
        # Whites: affect very bright areas (224-255)
        if 'whites' in adjustments and adjustments['whites'] != 0:
            white_val = adjustments['whites'] / 100.0
            mask = np.clip((v_channel - 224) / 32.0, 0, 1)
            v_channel += white_val * 30 * mask
        
        # Blacks: affect very dark areas (0-32)
        if 'blacks' in adjustments and adjustments['blacks'] != 0:
            black_val = adjustments['blacks'] / 100.0
            mask = np.clip((32 - v_channel) / 32.0, 0, 1)
            v_channel += black_val * 30 * mask
        
        img_hsv[:,:,2] = np.clip(v_channel, 0, 255)
        img_array = cv2.cvtColor(img_hsv.astype(np.uint8), cv2.COLOR_HSV2RGB).astype(np.float32)
    
    # Temperature (LR: -100 to +100, incremental)
    if 'temperature' in adjustments and adjustments['temperature'] != 0:
        temp = adjustments['temperature'] / 100.0
        if temp > 0:  # Warmer (orange)
            img_array[:,:,0] = np.clip(img_array[:,:,0] * (1 + temp * 0.2), 0, 255)
            img_array[:,:,1] = np.clip(img_array[:,:,1] * (1 + temp * 0.1), 0, 255)
            img_array[:,:,2] = np.clip(img_array[:,:,2] * (1 - temp * 0.15), 0, 255)
        else:  # Cooler (blue)
            img_array[:,:,0] = np.clip(img_array[:,:,0] * (1 + temp * 0.15), 0, 255)
            img_array[:,:,1] = np.clip(img_array[:,:,1] * (1 + temp * 0.08), 0, 255)
            img_array[:,:,2] = np.clip(img_array[:,:,2] * (1 - temp * 0.2), 0, 255)
    
    # Tint (LR: -150 to +150, incremental)
    if 'tint' in adjustments and adjustments['tint'] != 0:
        tint = adjustments['tint'] / 100.0
        if tint > 0:  # More green
            img_array[:,:,1] = np.clip(img_array[:,:,1] * (1 + tint * 0.15), 0, 255)
        else:  # More magenta
            img_array[:,:,0] = np.clip(img_array[:,:,0] * (1 - tint * 0.12), 0, 255)
            img_array[:,:,2] = np.clip(img_array[:,:,2] * (1 - tint * 0.12), 0, 255)
    
    # Convert back to PIL Image for remaining adjustments
    img = Image.fromarray(img_array.astype(np.uint8))
    
    # Contrast (LR: -100 to +100)
    if 'contrast' in adjustments and adjustments['contrast'] != 0:
        contrast_value = 1.0 + (adjustments['contrast'] / 100.0)
        contrast_value = np.clip(contrast_value, 0.3, 3.0)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(contrast_value)
    
    # Vibrance (LR: -100 to +100) - selective saturation boost
    if 'vibrance' in adjustments and adjustments['vibrance'] != 0:
        vibrance_value = 1.0 + (adjustments['vibrance'] / 150.0)  # More subtle
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(vibrance_value)
    
    # Saturation (LR: -100 to +100)
    if 'saturation' in adjustments and adjustments['saturation'] != 0:
        saturation_value = 1.0 + (adjustments['saturation'] / 100.0)
        saturation_value = np.clip(saturation_value, 0, 3.0)
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(saturation_value)
    
    # Sharpness (LR: 0 to 150)
    if 'sharpness' in adjustments and adjustments['sharpness'] != 0:
        sharpness_value = adjustments['sharpness'] / 40.0
        sharpness_value = np.clip(sharpness_value, 0, 4.0)
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(sharpness_value)
    
    return img

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'message': 'Photexx Backend is running'})

@app.route('/project/create', methods=['POST'])
def create_project():
    """Create a new project"""
    data = request.json
    project_id = data.get('projectId')
    album_name = data.get('albumName')
    file_type = data.get('fileType')
    
    projects[project_id] = {
        'id': project_id,
        'albumName': album_name,
        'fileType': file_type,
        'images': [],
        'createdAt': data.get('createdAt')
    }
    
    return jsonify({'success': True, 'project': projects[project_id]})

@app.route('/upload', methods=['POST'])
def upload_files():
    """Upload multiple files"""
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400
    
    files = request.files.getlist('files')
    project_id = request.form.get('projectId')
    
    if project_id not in projects:
        return jsonify({'error': 'Project not found'}), 404
    
    uploaded_files = []
    
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Convert RAW to JPG for preview
            try:
                if is_raw_file(filename):
                    rgb = convert_raw_to_rgb(filepath)
                    preview_path = os.path.join(app.config['PROCESSED_FOLDER'], f'preview_{filename}.jpg')
                    imageio.imsave(preview_path, rgb)
                    preview_url = f'/preview/{os.path.basename(preview_path)}'
                else:
                    preview_url = f'/preview/{filename}'
                
                file_info = {
                    'filename': filename,
                    'originalPath': filepath,
                    'previewUrl': preview_url,
                    'type': 'raw' if is_raw_file(filename) else 'jpg'
                }
                
                projects[project_id]['images'].append(file_info)
                uploaded_files.append(file_info)
            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")
                continue
    
    return jsonify({
        'success': True,
        'uploaded': len(uploaded_files),
        'files': uploaded_files
    })

@app.route('/preview/<filename>', methods=['GET'])
def get_preview(filename):
    """Get preview image"""
    if filename.startswith('preview_'):
        filepath = os.path.join(app.config['PROCESSED_FOLDER'], filename)
    else:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='image/jpeg')
    return jsonify({'error': 'File not found'}), 404

@app.route('/process', methods=['POST'])
def process_image():
    """Apply adjustments to an image - optimized for speed"""
    data = request.json
    filename = data.get('filename')
    adjustments = data.get('adjustments', {})
    
    # Load original image
    if filename.startswith('preview_'):
        original_path = os.path.join(app.config['PROCESSED_FOLDER'], filename)
    else:
        original_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if not os.path.exists(original_path):
        return jsonify({'error': 'File not found'}), 404
    
    try:
        # Check if we have cached RAW data
        cache_key = filename
        
        if cache_key in raw_cache:
            # Use cached image
            image = raw_cache[cache_key].copy()
            print(f"Using cached image for {filename}")
        else:
            # Load image (first time)
            if is_raw_file(filename):
                image_array = convert_raw_to_rgb(original_path)
                image = Image.fromarray(image_array.astype('uint8'))
                # Cache the original for faster subsequent adjustments
                raw_cache[cache_key] = image.copy()
                print(f"Cached RAW image: {filename}")
            else:
                image = Image.open(original_path)
                raw_cache[cache_key] = image.copy()
        
        # Resize for faster processing (max 1920px width)
        max_width = 1920
        if image.width > max_width:
            ratio = max_width / image.width
            new_size = (max_width, int(image.height * ratio))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
            print(f"Resized to {new_size} for faster processing")
        
        # Apply adjustments
        processed = apply_adjustments(image, adjustments)
        
        # Convert to base64 for transmission
        buffered = io.BytesIO()
        processed.save(buffered, format="JPEG", quality=85, optimize=True)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return jsonify({
            'success': True,
            'image': f'data:image/jpeg;base64,{img_str}'
        })
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/presets/list', methods=['GET'])
def list_presets():
    """Get list of available presets"""
    presets = load_presets_from_folder()
    preset_list = [{'name': name, 'adjustments': adj} for name, adj in presets.items()]
    
    return jsonify({
        'success': True,
        'presets': preset_list,
        'count': len(preset_list)
    })

@app.route('/preset/apply', methods=['POST'])
def apply_preset():
    """Apply a preset to an image"""
    try:
        data = request.json
        filename = data.get('filename')
        preset_name = data.get('preset')
        
        if not filename or not preset_name:
            return jsonify({'error': 'Missing filename or preset'}), 400
        
        # Load presets from XMP files
        presets = load_presets_from_folder()
        
        if preset_name not in presets:
            return jsonify({'error': f'Preset "{preset_name}" not found'}), 404
        
        # Get file path
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        # Load image
        if is_raw_file(filename):
            image = convert_raw_to_rgb(file_path)
            img = Image.fromarray(image.astype('uint8'))
        else:
            img = Image.open(file_path)
        
        # Apply preset adjustments
        adjustments = presets[preset_name]
        img = apply_adjustments(img, adjustments)
        
        # Convert to base64
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=90)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return jsonify({
            'success': True,
            'image': f'data:image/jpeg;base64,{img_str}',
            'preset': preset_name,
            'adjustments': adjustments
        })
        
    except Exception as e:
        print(f"Error applying preset: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/project/<project_id>', methods=['GET'])
def get_project(project_id):
    """Get project details"""
    if project_id in projects:
        return jsonify(projects[project_id])
    return jsonify({'error': 'Project not found'}), 404

if __name__ == '__main__':
    print("🚀 Photexx Backend Server Starting...")
    print("📍 Server running on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
