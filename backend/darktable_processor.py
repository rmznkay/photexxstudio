"""
Darktable CLI integration for professional RAW processing
"""
import subprocess
import os
import shutil
import logging

logger = logging.getLogger(__name__)

def check_darktable():
    """Check if darktable-cli is installed"""
    return shutil.which('darktable-cli') is not None

def process_with_darktable(input_path, output_path, xmp_path=None):
    """
    Process RAW file using darktable-cli with optional XMP preset
    
    Args:
        input_path: Path to RAW file
        output_path: Path for output JPEG
        xmp_path: Optional path to XMP preset file
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not check_darktable():
            logger.error("darktable-cli not found. Please install darktable.")
            return False
        
        cmd = ['darktable-cli', input_path, output_path]
        
        # Add XMP style if provided
        if xmp_path and os.path.exists(xmp_path):
            cmd.extend(['--style', xmp_path])
        
        # Add quality settings
        cmd.extend([
            '--core',
            '--conf', 'plugins/imageio/format/jpeg/quality=95',
            '--hq', '1'  # High quality processing
        ])
        
        logger.info(f"Running darktable: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            logger.info(f"✅ Darktable processed successfully: {output_path}")
            return True
        else:
            logger.error(f"Darktable error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("Darktable processing timeout")
        return False
    except Exception as e:
        logger.error(f"Darktable error: {str(e)}")
        return False

def get_darktable_version():
    """Get installed darktable version"""
    try:
        result = subprocess.run(
            ['darktable-cli', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout.strip()
    except:
        return None
