# modules/gui/dialogs/help_dialog.py
"""
Help dialog showing keyboard shortcuts and usage guide
"""

from PyQt5 import QtWidgets, QtCore


class HelpDialog(QtWidgets.QDialog):
    """Dialog showing keyboard shortcuts and help information"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Keyboard Shortcuts & Help")
        self.setMinimumSize(600, 500)
        self.setup_ui()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # Create tab widget
        tabs = QtWidgets.QTabWidget()

        # Shortcuts tab
        shortcuts_tab = self._create_shortcuts_tab()
        tabs.addTab(shortcuts_tab, "Keyboard Shortcuts")

        # Quick Guide tab
        guide_tab = self._create_guide_tab()
        tabs.addTab(guide_tab, "Quick Guide")

        layout.addWidget(tabs)

        # Close button
        close_btn = QtWidgets.QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=QtCore.Qt.AlignRight)

    def _create_shortcuts_tab(self):
        """Create the keyboard shortcuts tab"""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)

        # Shortcuts text
        shortcuts_text = """
<style>
    table { border-collapse: collapse; width: 100%; }
    th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
    th { background-color: #f0f0f0; font-weight: bold; }
    .category { background-color: #e8e8e8; font-weight: bold; }
</style>

<h3>Navigation</h3>
<table>
    <tr><td><b>↑ / Page Up</b></td><td>Previous image</td></tr>
    <tr><td><b>↓ / Page Down</b></td><td>Next image</td></tr>
    <tr><td><b>Tab</b></td><td>Select next annotation</td></tr>
    <tr><td><b>Shift+Tab</b></td><td>Select previous annotation</td></tr>
</table>

<h3>Annotation</h3>
<table>
    <tr><td><b>D</b></td><td>Toggle draw mode</td></tr>
    <tr><td><b>Space</b></td><td>Toggle draw mode (alternative)</td></tr>
    <tr><td><b>R</b></td><td>Toggle recognition mode</td></tr>
    <tr><td><b>M</b></td><td>Toggle mask mode</td></tr>
    <tr><td><b>Delete / Backspace</b></td><td>Delete selected annotations</td></tr>
    <tr><td><b>Escape</b></td><td>Deselect all / Cancel drawing</td></tr>
</table>

<h3>Editing</h3>
<table>
    <tr><td><b>Ctrl+Z</b></td><td>Undo</td></tr>
    <tr><td><b>Ctrl+Y</b></td><td>Redo</td></tr>
    <tr><td><b>Ctrl+C</b></td><td>Copy annotations</td></tr>
    <tr><td><b>Ctrl+X</b></td><td>Cut annotations</td></tr>
    <tr><td><b>Ctrl+V</b></td><td>Paste annotations</td></tr>
    <tr><td><b>Ctrl+A</b></td><td>Select all annotations</td></tr>
</table>

<h3>View / Zoom</h3>
<table>
    <tr><td><b>+ / =</b></td><td>Zoom in</td></tr>
    <tr><td><b>-</b></td><td>Zoom out</td></tr>
    <tr><td><b>0 / F</b></td><td>Fit to window</td></tr>
    <tr><td><b>1</b></td><td>Reset zoom (100%)</td></tr>
    <tr><td><b>Ctrl+Scroll</b></td><td>Zoom in/out</td></tr>
</table>

<h3>File / Workspace</h3>
<table>
    <tr><td><b>Ctrl+S</b></td><td>Save annotations</td></tr>
    <tr><td><b>Ctrl+O</b></td><td>Open folder</td></tr>
    <tr><td><b>Ctrl+W</b></td><td>Switch workspace</td></tr>
    <tr><td><b>Ctrl+N</b></td><td>New workspace</td></tr>
    <tr><td><b>Ctrl+Tab</b></td><td>Next version</td></tr>
    <tr><td><b>Ctrl+Shift+Tab</b></td><td>Previous version</td></tr>
</table>

<h3>Auto Annotate</h3>
<table>
    <tr><td><b>Ctrl+D</b></td><td>Auto detect current image</td></tr>
    <tr><td><b>Ctrl+Shift+D</b></td><td>Auto detect all images</td></tr>
    <tr><td><b>Ctrl+Alt+D</b></td><td>Auto detect selected images</td></tr>
</table>

<h3>Transform</h3>
<table>
    <tr><td><b>Ctrl+L</b></td><td>Rotate left 90°</td></tr>
    <tr><td><b>Ctrl+R</b></td><td>Rotate right 90°</td></tr>
</table>

<h3>Export</h3>
<table>
    <tr><td><b>Ctrl+E</b></td><td>Export recognition dataset</td></tr>
    <tr><td><b>Ctrl+Shift+E</b></td><td>Export detection dataset</td></tr>
</table>
"""

        text_browser = QtWidgets.QTextBrowser()
        text_browser.setHtml(shortcuts_text)
        text_browser.setOpenExternalLinks(True)
        layout.addWidget(text_browser)

        return widget

    def _create_guide_tab(self):
        """Create the quick guide tab"""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)

        guide_text = """
<h2>Quick Start Guide</h2>

<h3>1. Create or Open Workspace</h3>
<p>Start by creating a new workspace or opening an existing one. A workspace contains your images and annotations organized by versions.</p>

<h3>2. Drawing Annotations</h3>
<ol>
    <li>Press <b>D</b> or <b>Space</b> to enter draw mode</li>
    <li>Choose annotation type: <b>Quad</b> (rectangle) or <b>Polygon</b></li>
    <li>For Quad: Click and drag to draw a rectangle</li>
    <li>For Polygon: Click to add points, right-click or press Enter to finish</li>
</ol>

<h3>3. Editing Transcriptions</h3>
<ol>
    <li>Press <b>R</b> to enable Recognition mode</li>
    <li>Double-click on the transcription cell to edit</li>
    <li>Press Enter to save changes</li>
</ol>

<h3>4. Auto Detection</h3>
<p>Use PaddleOCR to automatically detect text regions:</p>
<ul>
    <li><b>Ctrl+D</b>: Detect current image</li>
    <li><b>Ctrl+Shift+D</b>: Detect all images</li>
    <li><b>Ctrl+Alt+D</b>: Detect only selected (checked) images</li>
</ul>

<h3>5. Masking Sensitive Data</h3>
<ol>
    <li>Press <b>M</b> to enter mask mode</li>
    <li>Draw mask areas over sensitive data</li>
    <li>Masks will be exported as solid color regions</li>
</ol>

<h3>6. Exporting Datasets</h3>
<p>Export your annotations for training:</p>
<ul>
    <li><b>Detection</b>: For training text detection models</li>
    <li><b>Recognition</b>: For training text recognition models (crops individual text regions)</li>
</ul>

<h3>7. Version Control</h3>
<p>Use versions to save different annotation states:</p>
<ul>
    <li>Create new versions to experiment safely</li>
    <li>Switch between versions with <b>Ctrl+Tab</b></li>
</ul>

<h3>Tips</h3>
<ul>
    <li>Use <b>Ctrl+Z/Y</b> to undo/redo changes</li>
    <li>Auto-save runs every 5 minutes</li>
    <li>Use filters to show only annotated or empty images</li>
    <li>Search annotations by text content</li>
</ul>
"""

        text_browser = QtWidgets.QTextBrowser()
        text_browser.setHtml(guide_text)
        layout.addWidget(text_browser)

        return widget
