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

# Try to import darktable processor
try:
    from darktable_processor import check_darktable, process_with_darktable, get_darktable_version
    DARKTABLE_AVAILABLE = check_darktable()
except ImportError:
    DARKTABLE_AVAILABLE = False
    logger.warning("Darktable processor module not available")

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
# Presets folder - use project directory (one level up from backend)
PRESETS_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'presets')
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
        
        # Basic adjustments
        params = {
            'Exposure2012': 'exposure',
            'Contrast2012': 'contrast',
            'Highlights2012': 'highlights',
            'Shadows2012': 'shadows',
            'Whites2012': 'whites',
            'Blacks2012': 'blacks',
            'Texture': 'texture',
            'Clarity2012': 'clarity',
            'Dehaze': 'dehaze',
            'Vibrance': 'vibrance',
            'Saturation': 'saturation',
            'IncrementalTemperature': 'temperature',
            'IncrementalTint': 'tint',
            'Sharpness': 'sharpness',
            # HSL - Hue
            'HueAdjustmentRed': 'hue_red',
            'HueAdjustmentOrange': 'hue_orange',
            'HueAdjustmentYellow': 'hue_yellow',
            'HueAdjustmentGreen': 'hue_green',
            'HueAdjustmentAqua': 'hue_aqua',
            'HueAdjustmentBlue': 'hue_blue',
            'HueAdjustmentPurple': 'hue_purple',
            'HueAdjustmentMagenta': 'hue_magenta',
            # HSL - Saturation
            'SaturationAdjustmentRed': 'sat_red',
            'SaturationAdjustmentOrange': 'sat_orange',
            'SaturationAdjustmentYellow': 'sat_yellow',
            'SaturationAdjustmentGreen': 'sat_green',
            'SaturationAdjustmentAqua': 'sat_aqua',
            'SaturationAdjustmentBlue': 'sat_blue',
            'SaturationAdjustmentPurple': 'sat_purple',
            'SaturationAdjustmentMagenta': 'sat_magenta',
            # HSL - Luminance
            'LuminanceAdjustmentRed': 'lum_red',
            'LuminanceAdjustmentOrange': 'lum_orange',
            'LuminanceAdjustmentYellow': 'lum_yellow',
            'LuminanceAdjustmentGreen': 'lum_green',
            'LuminanceAdjustmentAqua': 'lum_aqua',
            'LuminanceAdjustmentBlue': 'lum_blue',
            'LuminanceAdjustmentPurple': 'lum_purple',
            'LuminanceAdjustmentMagenta': 'lum_magenta',
            # Split Toning
            'SplitToningShadowHue': 'split_shadow_hue',
            'SplitToningShadowSaturation': 'split_shadow_sat',
            'SplitToningHighlightHue': 'split_highlight_hue',
            'SplitToningHighlightSaturation': 'split_highlight_sat',
            # Calibration
            'RedHue': 'cal_red_hue',
            'RedSaturation': 'cal_red_sat',
            'GreenHue': 'cal_green_hue',
            'GreenSaturation': 'cal_green_sat',
            'BlueHue': 'cal_blue_hue',
            'BlueSaturation': 'cal_blue_sat',
        }
        
        for xmp_key, adj_key in params.items():
            pattern = f'crs:{xmp_key}="([^"]+)"'
            match = re.search(pattern, content)
            if match:
                value = match.group(1)
                # Remove + sign if present
                if value.startswith('+'):
                    value = value[1:]
                try:
                    adjustments[adj_key] = float(value)
                except ValueError:
                    adjustments[adj_key] = 0
        
        logger.info(f"Parsed preset with {len(adjustments)} parameters")
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
    """Apply Lightroom-style adjustments to image with full HSL support"""
    try:
        img_array = np.array(img).astype(np.float32) / 255.0
        
        # Basic parameters
        exposure = adjustments.get('exposure', 0) / 5.0
        contrast = adjustments.get('contrast', 0) / 100.0
        saturation = adjustments.get('saturation', 0) / 100.0
        vibrance = adjustments.get('vibrance', 0) / 100.0
        sharpness = adjustments.get('sharpness', 40)
        temperature = adjustments.get('temperature', 0)
        tint = adjustments.get('tint', 0)
        texture = adjustments.get('texture', 0) / 100.0
        clarity = adjustments.get('clarity', 0) / 100.0
        dehaze = adjustments.get('dehaze', 0) / 100.0
        
        highlights = adjustments.get('highlights', 0) / 100.0
        shadows = adjustments.get('shadows', 0) / 100.0
        whites = adjustments.get('whites', 0) / 100.0
        blacks = adjustments.get('blacks', 0) / 100.0
        
        # Apply exposure
        if exposure != 0:
            img_array = np.clip(img_array * (2.0 ** exposure), 0, 1)
        
        # Apply temperature
        if temperature != 0:
            temp_factor = temperature / 100.0
            img_array[:, :, 0] = np.clip(img_array[:, :, 0] * (1 + temp_factor * 0.3), 0, 1)
            img_array[:, :, 2] = np.clip(img_array[:, :, 2] * (1 - temp_factor * 0.3), 0, 1)
        
        # Apply tint
        if tint != 0:
            tint_factor = tint / 100.0
            img_array[:, :, 1] = np.clip(img_array[:, :, 1] * (1 + tint_factor * 0.2), 0, 1)
        
        # Convert to HSV for tone/color adjustments
        img_uint8 = (img_array * 255).astype(np.uint8)
        img_hsv = cv2.cvtColor(img_uint8, cv2.COLOR_RGB2HSV).astype(np.float32)
        h, s, v = cv2.split(img_hsv)
        
        # Tone adjustments
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
        
        # HSL Color Adjustments - Apply to specific hue ranges
        # Red: 0-10, 350-360 (wrap around)
        # Orange: 11-35
        # Yellow: 36-65
        # Green: 66-165
        # Aqua: 166-200
        # Blue: 201-260
        # Purple: 261-290
        # Magenta: 291-349
        
        hsl_adjustments = {
            'red': (adjustments.get('hue_red', 0), adjustments.get('sat_red', 0), adjustments.get('lum_red', 0)),
            'orange': (adjustments.get('hue_orange', 0), adjustments.get('sat_orange', 0), adjustments.get('lum_orange', 0)),
            'yellow': (adjustments.get('hue_yellow', 0), adjustments.get('sat_yellow', 0), adjustments.get('lum_yellow', 0)),
            'green': (adjustments.get('hue_green', 0), adjustments.get('sat_green', 0), adjustments.get('lum_green', 0)),
            'aqua': (adjustments.get('hue_aqua', 0), adjustments.get('sat_aqua', 0), adjustments.get('lum_aqua', 0)),
            'blue': (adjustments.get('hue_blue', 0), adjustments.get('sat_blue', 0), adjustments.get('lum_blue', 0)),
            'purple': (adjustments.get('hue_purple', 0), adjustments.get('sat_purple', 0), adjustments.get('lum_purple', 0)),
            'magenta': (adjustments.get('hue_magenta', 0), adjustments.get('sat_magenta', 0), adjustments.get('lum_magenta', 0)),
        }
        
        color_ranges = {
            'red': [(0, 10), (170, 180)],  # HSV hue 0-10, 170-180 (wraps)
            'orange': [(11, 20)],
            'yellow': [(21, 35)],
            'green': [(36, 85)],
            'aqua': [(86, 110)],
            'blue': [(111, 140)],
            'purple': [(141, 155)],
            'magenta': [(156, 169)],
        }
        
        for color_name, (hue_shift, sat_shift, lum_shift) in hsl_adjustments.items():
            if hue_shift == 0 and sat_shift == 0 and lum_shift == 0:
                continue
            
            ranges = color_ranges[color_name]
            mask = np.zeros_like(h, dtype=np.float32)
            
            for hue_min, hue_max in ranges:
                mask_range = ((h >= hue_min) & (h <= hue_max)).astype(np.float32)
                mask = np.maximum(mask, mask_range)
            
            # Apply adjustments MUCH more gently (Lightroom uses subtle changes)
            if hue_shift != 0:
                h = np.where(mask > 0, h + (hue_shift * mask * 0.1), h)  # Reduced from 0.5 to 0.1
                h = np.clip(h, 0, 180)
            
            if sat_shift != 0:
                s = np.where(mask > 0, s * (1 + sat_shift / 100.0 * mask * 0.3), s)  # Added 0.3 factor
                s = np.clip(s, 0, 255)
            
            if lum_shift != 0:
                v = np.where(mask > 0, v + (lum_shift * 0.3 * mask), v)  # Reduced from 1.5 to 0.3
                v = np.clip(v, 0, 255)
        
        # Contrast
        if contrast != 0:
            v = ((v / 255.0 - 0.5) * (1 + contrast) + 0.5) * 255.0
            v = np.clip(v, 0, 255)
        
        # Clarity (midtone contrast)
        if clarity != 0:
            v_blur = cv2.GaussianBlur(v, (0, 0), 10)
            v = v + (v - v_blur) * clarity
            v = np.clip(v, 0, 255)
        
        # Texture (fine detail contrast)
        if texture != 0:
            v_blur = cv2.GaussianBlur(v, (0, 0), 2)
            v = v + (v - v_blur) * texture * 0.5
            v = np.clip(v, 0, 255)
        
        # Dehaze (increase contrast in hazy areas)
        if dehaze != 0:
            v = v * (1 + dehaze * 0.3)
            v = np.clip(v, 0, 255)
            s = s * (1 + dehaze * 0.2)
            s = np.clip(s, 0, 255)
        
        # Saturation
        if saturation != 0:
            s = s * (1 + saturation)
            s = np.clip(s, 0, 255)
        
        # Vibrance (selective saturation)
        if vibrance != 0:
            s_normalized = s / 255.0
            vibrance_mask = 1.0 - s_normalized
            s = s + (vibrance * 100 * vibrance_mask)
            s = np.clip(s, 0, 255)
        
        # Merge back to RGB
        img_hsv = cv2.merge([h, s, v]).astype(np.uint8)
        img_array = cv2.cvtColor(img_hsv, cv2.COLOR_HSV2RGB)
        
        # Calibration adjustments (primary color calibration)
        cal_red_hue = adjustments.get('cal_red_hue', 0)
        cal_red_sat = adjustments.get('cal_red_sat', 0)
        cal_green_hue = adjustments.get('cal_green_hue', 0)
        cal_green_sat = adjustments.get('cal_green_sat', 0)
        cal_blue_hue = adjustments.get('cal_blue_hue', 0)
        cal_blue_sat = adjustments.get('cal_blue_sat', 0)
        
        if any([cal_red_hue, cal_red_sat, cal_green_hue, cal_green_sat, cal_blue_hue, cal_blue_sat]):
            img_hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV).astype(np.float32)
            h, s, v = cv2.split(img_hsv)
            
            # Apply calibration (simplified version)
            if cal_red_hue != 0 or cal_red_sat != 0:
                red_mask = ((h < 10) | (h > 170)).astype(np.float32)
                h = np.where(red_mask > 0, h + cal_red_hue * 0.5, h)
                s = np.where(red_mask > 0, s * (1 + cal_red_sat / 100.0), s)
            
            if cal_green_hue != 0 or cal_green_sat != 0:
                green_mask = ((h >= 36) & (h <= 85)).astype(np.float32)
                h = np.where(green_mask > 0, h + cal_green_hue * 0.5, h)
                s = np.where(green_mask > 0, s * (1 + cal_green_sat / 100.0), s)
            
            if cal_blue_hue != 0 or cal_blue_sat != 0:
                blue_mask = ((h >= 111) & (h <= 140)).astype(np.float32)
                h = np.where(blue_mask > 0, h + cal_blue_hue * 0.5, h)
                s = np.where(blue_mask > 0, s * (1 + cal_blue_sat / 100.0), s)
            
            h = np.clip(h, 0, 180)
            s = np.clip(s, 0, 255)
            img_hsv = cv2.merge([h, s, v]).astype(np.uint8)
            img_array = cv2.cvtColor(img_hsv, cv2.COLOR_HSV2RGB)
        
        img = Image.fromarray(img_array)
        
        # Sharpness
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
    status = {
        'status': 'ok',
        'message': 'Photexx Backend is running',
        'darktable': {
            'available': DARKTABLE_AVAILABLE,
            'version': get_darktable_version() if DARKTABLE_AVAILABLE else None
        }
    }
    return jsonify(status)

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

@app.route('/preset/apply', methods=['POST'])
def apply_preset():
    """Apply preset to current image using darktable if available"""
    try:
        data = request.json
        preset_name = data.get('preset')
        filename = data.get('filename')
        
        if not preset_name or not filename:
            return jsonify({'error': 'Missing preset or filename'}), 400
        
        # Load preset
        preset_path = os.path.join(app.config['PRESETS_FOLDER'], preset_name)
        if not os.path.exists(preset_path):
            return jsonify({'error': 'Preset not found'}), 404
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
        
        # Try darktable first for RAW files
        if DARKTABLE_AVAILABLE and is_raw_file(filename):
            logger.info(f"Using darktable-cli for {filename} with preset {preset_name}")
            
            output_path = os.path.join(app.config['PROCESSED_FOLDER'], f'dt_{filename}.jpg')
            
            if process_with_darktable(filepath, output_path, preset_path):
                # Read processed image
                with open(output_path, 'rb') as f:
                    img_data = f.read()
                
                img_base64 = base64.b64encode(img_data).decode('utf-8')
                
                # Parse adjustments for UI update
                adjustments = parse_xmp_preset(preset_path)
                
                return jsonify({
                    'success': True,
                    'image': f'data:image/jpeg;base64,{img_base64}',
                    'adjustments': adjustments,
                    'processor': 'darktable'
                })
            else:
                logger.warning("Darktable processing failed, falling back to custom processor")
        
        # Fallback to custom processing
        adjustments = parse_xmp_preset(preset_path)
        logger.info(f"Using custom processor for {filename}")
        
        img = load_image(filepath)
        img = apply_adjustments(img, adjustments)
        
        # Return processed image
        output = io.BytesIO()
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        img.save(output, format='JPEG', quality=85)
        output.seek(0)
        
        img_base64 = base64.b64encode(output.getvalue()).decode('utf-8')
        
        return jsonify({
            'success': True,
            'image': f'data:image/jpeg;base64,{img_base64}',
            'adjustments': adjustments,
            'processor': 'custom'
        })
        
    except Exception as e:
        logger.error(f"Error applying preset: {str(e)}")
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
