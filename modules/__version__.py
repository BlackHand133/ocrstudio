"""
Version information for the application.
"""

__version__ = "4.0.0"
__version_info__ = (4, 0, 0)

# Version history
# 4.0.0 - Professional-grade refactor:
#         * Architecture: AppState/Services pattern with Qt signals; UICoordinator extracted
#         * MainWindow reduced from 1,533 → 451 lines (handler DI throughout)
#         * Config: Unified ConfigManager singleton with validate(); ConfigLoader removed
#         * Testing: pytest infrastructure + 121 unit tests (workspace, config, undo/redo,
#           file_io, validation, GUI smoke); coverage on core/utils/config
#         * Type safety: mypy gradual strictness on core/utils/config; bare-except < 60
#         * Docker: Multi-stage Dockerfile (CPU/GPU) + noVNC GUI + headless CLI mode
#         * CLI: ajan-ocr-cli for headless detect/export workflows
#         * CI/CD: GitHub Actions (lint + test + docker) + pre-commit hooks
#         * Polish: JSON logging, ExportValidationError, window state persistence,
#           lazy image-list loading for 1000+ image workspaces
#         * Docs: Rewritten README + new ARCHITECTURE.md
# 3.0.0 - Auto-orientation system: Fixed statistics tracking, added ML accuracy warnings
# 2.1.0 - Major restructure: Organized modules, unified config system
# 2.0.0 - Workspace system with versioning
# 1.0.0 - Initial release
