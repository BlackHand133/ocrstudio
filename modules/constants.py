"""
Global constants for the application.

This module contains all hard-coded values that were previously scattered
throughout the codebase. Centralizing them here makes the code more maintainable.
"""

from modules.__version__ import __version__

# ===== Application Info =====
APP_NAME = "TextDet GUI"
APP_VERSION = __version__
APP_AUTHOR = "Your Name"
APP_DESCRIPTION = "Text Detection and Annotation Tool with OCR"

# ===== Workspace Constants =====
WORKSPACE_VERSION = "2.0.0"  # Workspace format version
DEFAULT_WORKSPACE_NAME = "default"
WORKSPACE_FILE = "workspace.json"
EXPORTS_FILE = "exports.json"
VERSION_FILE_PREFIX = "v"
VERSION_FILE_EXTENSION = ".json"

# ===== Annotation Constants =====
PLACEHOLDER_TEXT = "<no_label>"
MASK_TEXT = "###"
NO_LABEL_PLACEHOLDER = "<no_label>"

# Annotation types
ANNOTATION_TYPE_QUAD = "Quad"
ANNOTATION_TYPE_POLYGON = "Polygon"
ANNOTATION_TYPE_MASK = "Mask"

# ===== File Extensions =====
IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
LABEL_EXTENSION = '.txt'
JSON_EXTENSION = '.json'
YAML_EXTENSION = '.yaml'

# ===== Directory Names =====
DIR_WORKSPACES = "workspaces"
DIR_DATA = "data"
DIR_OUTPUT = "output"
DIR_OUTPUT_DET = "output_det"
DIR_OUTPUT_REC = "output_rec"
DIR_MODELS = "models"
DIR_LOGS = "logs"
DIR_CACHE = "cache"
DIR_CONFIG = "config"

# ===== Config Keys =====
# OCR Config
CONFIG_OCR_DEVICE = "ocr.device"
CONFIG_OCR_LANG = "ocr.lang"
CONFIG_OCR_USE_GPU = "ocr.use_gpu"
CONFIG_OCR_GPU_ID = "ocr.gpu_id"
CONFIG_OCR_GPU_MEM = "ocr.gpu_mem"

# App Config
CONFIG_APP_AUTO_SAVE = "app.auto_save"
CONFIG_APP_CACHE_ANNOTATIONS = "app.cache_annotations"
CONFIG_APP_RECENT_WORKSPACES = "app.recent_workspaces"
CONFIG_APP_WINDOW_SIZE = "app.window.size"
CONFIG_APP_WINDOW_POS = "app.window.position"

# Path Config
CONFIG_PATH_WORKSPACES = "paths.workspaces"
CONFIG_PATH_OUTPUT_DET = "paths.output_det"
CONFIG_PATH_OUTPUT_REC = "paths.output_rec"
CONFIG_PATH_MODELS = "paths.models"
CONFIG_PATH_LOGS = "paths.logs"
CONFIG_PATH_CACHE = "paths.cache"

# ===== OCR Constants =====
# Default PaddleOCR parameters
DEFAULT_OCR_LANG = "th"
DEFAULT_DET_DB_BOX_THRESH = 0.7
DEFAULT_DET_DB_UNCLIP_RATIO = 1.5
DEFAULT_USE_DOC_ORIENTATION = False
DEFAULT_USE_DOC_UNWARPING = False
DEFAULT_USE_TEXTLINE_ORIENTATION = False

# ===== Export Constants =====
# Dataset split ratios
DEFAULT_TRAIN_RATIO = 0.7
DEFAULT_VAL_RATIO = 0.2
DEFAULT_TEST_RATIO = 0.1

# Export formats
EXPORT_FORMAT_PPOCR = "ppocr"
EXPORT_FORMAT_DETECTION = "detection"
EXPORT_FORMAT_RECOGNITION = "recognition"

# ===== UI Constants =====
# Window
DEFAULT_WINDOW_WIDTH = 1400
DEFAULT_WINDOW_HEIGHT = 900
DEFAULT_WINDOW_TITLE = f"{APP_NAME} v{APP_VERSION}"

# Colors
COLOR_RED = (255, 0, 0)
COLOR_GREEN = (0, 255, 0)
COLOR_BLUE = (0, 0, 255)
COLOR_YELLOW = (255, 255, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_GRAY = (128, 128, 128)

# Box colors (Qt format)
QT_COLOR_BOX_NORMAL = "#00FF00"      # Green
QT_COLOR_BOX_SELECTED = "#FF0000"    # Red
QT_COLOR_BOX_HOVER = "#FFFF00"       # Yellow
QT_COLOR_MASK = "#000000"            # Black

# ===== Logging Constants =====
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_FILE_NAME = "app.log"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5

# ===== Cache Constants =====
CACHE_ANNOTATION_TTL = 3600  # 1 hour in seconds
CACHE_IMAGE_TTL = 1800       # 30 minutes
CACHE_MAX_SIZE_MB = 500      # 500MB

# ===== Model Constants =====
MODEL_TEXTLINE_ORIENTATION = "textline_orientation"
MODEL_TEXTLINE_ORIENTATION_PATH = "models/textline_orientation"

# ===== Validation Constants =====
MIN_BOX_SIZE = 10           # Minimum box width/height in pixels
MAX_IMAGE_SIZE_MB = 50      # Maximum image file size
MAX_ANNOTATION_POINTS = 100 # Maximum points in polygon

# ===== Keyboard Shortcuts =====
SHORTCUT_OPEN_FOLDER = "Ctrl+O"
SHORTCUT_SAVE = "Ctrl+S"
SHORTCUT_EXPORT = "Ctrl+E"
SHORTCUT_AUTO_CURRENT = "Ctrl+C"
SHORTCUT_AUTO_ALL = "Ctrl+A"
SHORTCUT_AUTO_SELECTED = "Ctrl+Shift+A"
SHORTCUT_DRAW_MODE = "D"
SHORTCUT_RECOG_MODE = "R"
SHORTCUT_MASK_MODE = "M"
SHORTCUT_DELETE = "Del"
SHORTCUT_SETTINGS = "Ctrl+,"
SHORTCUT_SWITCH_WORKSPACE = "Ctrl+W"

# ===== Error Messages =====
ERROR_NO_WORKSPACE = "No workspace loaded"
ERROR_NO_IMAGE = "No image selected"
ERROR_FILE_NOT_FOUND = "File not found"
ERROR_INVALID_FORMAT = "Invalid file format"
ERROR_EXPORT_FAILED = "Export failed"
ERROR_DETECTION_FAILED = "Detection failed"

# ===== Success Messages =====
SUCCESS_SAVED = "Saved successfully"
SUCCESS_EXPORTED = "Exported successfully"
SUCCESS_WORKSPACE_CREATED = "Workspace created successfully"
SUCCESS_SETTINGS_SAVED = "Settings saved successfully"

# ===== Status Messages =====
STATUS_READY = "Ready"
STATUS_LOADING = "Loading..."
STATUS_DETECTING = "Detecting text..."
STATUS_EXPORTING = "Exporting..."
STATUS_SAVING = "Saving..."
