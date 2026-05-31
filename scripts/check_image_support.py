"""
Check which image formats are supported by Qt and OpenCV
"""
import sys
from pathlib import Path

# Set UTF-8 encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.insert(0, str(Path(__file__).parent))

print("\n" + "="*70)
print("Image Format Support Analysis")
print("="*70)

# Check Qt support
try:
    from PyQt5 import QtGui
    qt_formats = QtGui.QImageReader.supportedImageFormats()
    qt_exts = set()
    for fmt in qt_formats:
        ext = '.' + bytes(fmt).decode('utf-8').lower()
        qt_exts.add(ext)

    print("\n📊 Qt5 Supported Formats:")
    for ext in sorted(qt_exts):
        print(f"   ✓ {ext}")
    print(f"\nTotal: {len(qt_exts)} formats")
except Exception as e:
    print(f"\n❌ Qt check failed: {e}")

# Check OpenCV support
try:
    import cv2
    print("\n" + "="*70)
    print("📊 OpenCV (cv2) Supported Formats:")

    # Common formats that OpenCV typically supports
    opencv_formats = {
        '.jpg': 'JPEG (Joint Photographic Experts Group)',
        '.jpeg': 'JPEG (Joint Photographic Experts Group)',
        '.jpe': 'JPEG variant',
        '.jp2': 'JPEG 2000',
        '.png': 'PNG (Portable Network Graphics)',
        '.bmp': 'BMP (Windows Bitmap)',
        '.dib': 'DIB (Device Independent Bitmap)',
        '.tiff': 'TIFF (Tagged Image File Format)',
        '.tif': 'TIFF variant',
        '.webp': 'WebP (Modern image format by Google)',
        '.pbm': 'PBM (Portable Bitmap)',
        '.pgm': 'PGM (Portable Graymap)',
        '.ppm': 'PPM (Portable Pixmap)',
        '.pxm': 'PXM (Portable Any Map)',
        '.pnm': 'PNM (Portable Any Map)',
        '.sr': 'Sun Raster',
        '.ras': 'Sun Raster',
        '.exr': 'OpenEXR (High Dynamic Range)',
        '.hdr': 'HDR (Radiance HDR)',
        '.pic': 'PIC (Softimage)'
    }

    for ext, desc in sorted(opencv_formats.items()):
        print(f"   ✓ {ext:<8} - {desc}")

    print(f"\nTotal: {len(opencv_formats)} formats")
    print(f"\nOpenCV version: {cv2.__version__}")

except Exception as e:
    print(f"\n❌ OpenCV check failed: {e}")

# Recommendation
print("\n" + "="*70)
print("📋 RECOMMENDED IMAGE_EXTENSIONS")
print("="*70)

recommended = {
    '.jpg': 'Most common, widely supported',
    '.jpeg': 'Same as JPG',
    '.png': 'Lossless, supports transparency',
    '.bmp': 'Windows bitmap, uncompressed',
    '.jfif': 'JPEG variant',
    '.tiff': 'High quality, supports layers',
    '.tif': 'TIFF variant',
    '.webp': 'Modern format, good compression',
    '.gif': 'Supports animation',
    '.ico': 'Icon format',
    '.jp2': 'JPEG 2000, better compression',
    '.dib': 'Device Independent Bitmap',
    '.pbm': 'Portable Bitmap',
    '.pgm': 'Portable Graymap',
    '.ppm': 'Portable Pixmap',
    '.svg': 'Vector graphics (if Qt supports)',
}

print("\n🌟 Core formats (must have):")
core = ['.jpg', '.jpeg', '.png', '.bmp']
for ext in core:
    print(f"   {ext:<8} - {recommended.get(ext, '')}")

print("\n✨ Extended formats (recommended):")
extended = ['.jfif', '.tiff', '.tif', '.webp', '.gif', '.ico']
for ext in extended:
    print(f"   {ext:<8} - {recommended.get(ext, '')}")

print("\n🔧 Advanced formats (optional):")
advanced = ['.jp2', '.dib', '.pbm', '.pgm', '.ppm']
for ext in advanced:
    print(f"   {ext:<8} - {recommended.get(ext, '')}")

print("\n" + "="*70)
print("💡 Suggestion: Add core + extended formats for best compatibility")
print("="*70 + "\n")
