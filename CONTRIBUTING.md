# Contributing to Ajan OCR Annotation Tool

Thank you for your interest in contributing to Ajan OCR Annotation Tool! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Accept constructive criticism gracefully
- Focus on what's best for the community
- Show empathy towards other contributors

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- Basic understanding of PyQt5 and OpenCV
- Familiarity with OCR concepts

### Setting Up Development Environment

1. **Fork the repository**
   ```bash
   # Click "Fork" button on GitHub
   ```

2. **Clone your fork**
   ```bash
   git clone https://github.com/YOUR_USERNAME/ocrstudio.git
   cd ocrstudio
   ```

3. **Add upstream remote**
   ```bash
   git remote add upstream https://github.com/ORIGINAL_OWNER/ocrstudio.git
   ```

4. **Create virtual environment**
   ```bash
   python -m venv venv

   # Windows
   venv\Scripts\activate

   # Linux/Mac
   source venv/bin/activate
   ```

5. **Install development dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -e .[dev]
   ```

6. **Install code quality tools**
   ```bash
   pip install black flake8 mypy pytest pytest-qt
   ```

## How to Contribute

### Types of Contributions

We welcome various types of contributions:

- **Bug fixes**: Fix issues and improve stability
- **New features**: Add new functionality
- **Documentation**: Improve or add documentation
- **Tests**: Add or improve test coverage
- **Code quality**: Refactoring and optimization
- **Translations**: Add UI translations
- **Examples**: Add usage examples and tutorials

### Reporting Bugs

Before creating a bug report:
1. Check existing issues to avoid duplicates
2. Try the latest version
3. Collect relevant information

When reporting bugs, include:
- **Description**: Clear description of the bug
- **Steps to reproduce**: Detailed steps
- **Expected behavior**: What should happen
- **Actual behavior**: What actually happens
- **Environment**: OS, Python version, package versions
- **Screenshots**: If applicable
- **Logs**: Relevant error messages

**Bug Report Template:**
```markdown
**Description**
A clear description of the bug.

**To Reproduce**
1. Go to '...'
2. Click on '...'
3. See error

**Expected Behavior**
What you expected to happen.

**Screenshots**
If applicable, add screenshots.

**Environment:**
- OS: [e.g., Windows 10, Ubuntu 20.04]
- Python Version: [e.g., 3.9.7]
- Application Version: [e.g., 4.0.0]

**Additional Context**
Any other relevant information.
```

### Suggesting Features

When suggesting features:
- Check if it's already been suggested
- Explain the use case
- Describe the proposed solution
- Consider alternatives

**Feature Request Template:**
```markdown
**Problem Statement**
Describe the problem this feature would solve.

**Proposed Solution**
Describe your proposed solution.

**Alternatives Considered**
Describe alternative solutions you've considered.

**Additional Context**
Any other relevant information.
```

## Development Workflow

### 1. Create a Branch

```bash
# Update main branch
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/bug-description
```

### 2. Make Changes

- Write clear, concise code
- Follow coding standards (see below)
- Add tests for new functionality
- Update documentation

### 3. Test Your Changes

```bash
# Run tests
pytest

# Run specific test
pytest tests/test_specific.py

# Run with coverage
pytest --cov=modules tests/
```

### 4. Format and Lint

```bash
# Format code with Black
black modules/

# Check with Flake8
flake8 modules/

# Type check with MyPy
mypy modules/
```

### 5. Commit Changes

Write clear commit messages following this format:

```
<type>: <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Example:**
```bash
git add .
git commit -m "feat: Add polygon annotation tool

- Implement polygon drawing on canvas
- Add polygon editing functionality
- Update export to include polygon data
- Add tests for polygon operations

Closes #123"
```

### 6. Push and Create Pull Request

```bash
# Push to your fork
git push origin feature/your-feature-name

# Create Pull Request on GitHub
```

## Coding Standards

### Python Style Guide

Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) with these specifics:

- **Line length**: 100 characters (configured in Black)
- **Indentation**: 4 spaces (no tabs)
- **Quotes**: Prefer double quotes for strings
- **Imports**: Group and sort (stdlib, third-party, local)

### Code Organization

```python
# Standard library imports
import os
import sys
from typing import List, Optional

# Third-party imports
from PyQt5 import QtWidgets
import numpy as np

# Local imports
from modules.utils import handle_exceptions
from modules.core.workspace import WorkspaceManager
```

### Naming Conventions

- **Classes**: `PascalCase` (e.g., `WorkspaceManager`)
- **Functions/Methods**: `snake_case` (e.g., `load_workspace`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_IMAGE_SIZE`)
- **Private**: Prefix with `_` (e.g., `_internal_method`)

### Documentation

Use docstrings for all public modules, classes, and functions:

```python
def export_dataset(workspace_path: str, output_dir: str, split_ratio: dict) -> bool:
    """
    Export workspace annotations to PaddleOCR format.

    Args:
        workspace_path: Path to the workspace directory
        output_dir: Directory to save exported dataset
        split_ratio: Dictionary with train/test/val split ratios

    Returns:
        True if export successful, False otherwise

    Raises:
        ValueError: If split ratios don't sum to 1.0
        FileNotFoundError: If workspace_path doesn't exist

    Example:
        >>> export_dataset(
        ...     workspace_path="data/workspaces/my_project",
        ...     output_dir="output_det",
        ...     split_ratio={"train": 0.7, "test": 0.2, "val": 0.1}
        ... )
        True
    """
    pass
```

### Type Hints

Use type hints for function signatures:

```python
from typing import List, Dict, Optional, Tuple

def process_images(
    image_paths: List[str],
    config: Dict[str, any],
    output_dir: Optional[str] = None
) -> Tuple[int, int]:
    """Process multiple images."""
    pass
```

## Testing

### Writing Tests

- Write tests for all new functionality
- Use pytest framework
- Aim for >80% code coverage
- Test edge cases and error conditions

**Test Structure:**
```python
import pytest
from modules.core.workspace import WorkspaceManager

class TestWorkspaceManager:
    """Test suite for WorkspaceManager."""

    @pytest.fixture
    def workspace_manager(self, tmp_path):
        """Create a temporary workspace for testing."""
        return WorkspaceManager(str(tmp_path))

    def test_create_workspace(self, workspace_manager):
        """Test workspace creation."""
        result = workspace_manager.create("test_workspace")
        assert result is True
        assert workspace_manager.exists("test_workspace")

    def test_load_nonexistent_workspace(self, workspace_manager):
        """Test loading workspace that doesn't exist."""
        with pytest.raises(FileNotFoundError):
            workspace_manager.load("nonexistent")
```

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_workspace.py

# Run specific test
pytest tests/test_workspace.py::TestWorkspaceManager::test_create_workspace

# Run with coverage
pytest --cov=modules --cov-report=html
```

## Documentation

### Code Documentation

- Document all public APIs
- Include examples in docstrings
- Explain complex algorithms
- Document configuration options

### User Documentation

- Update README.md for user-facing changes
- Add screenshots for UI changes
- Update CHANGELOG.md
- Create tutorials for new features

## Pull Request Process

### Before Submitting

- [ ] Code follows style guidelines
- [ ] Tests pass locally
- [ ] Code is formatted (Black)
- [ ] Linting passes (Flake8)
- [ ] Type checking passes (MyPy)
- [ ] Documentation is updated
- [ ] CHANGELOG.md is updated (if applicable)
- [ ] Commits are clean and descriptive

### PR Template

```markdown
## Description
Brief description of changes.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Related Issues
Fixes #123

## Changes Made
- Change 1
- Change 2
- Change 3

## Testing
Describe testing performed.

## Screenshots (if applicable)
Add screenshots.

## Checklist
- [ ] Code follows style guidelines
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] All tests pass
```

### Review Process

1. **Automated checks**: CI/CD runs tests and linting
2. **Code review**: Maintainers review the code
3. **Feedback**: Address review comments
4. **Approval**: Get approval from maintainers
5. **Merge**: Maintainers merge the PR

### After Merge

- Delete your feature branch
- Update your fork:
  ```bash
  git checkout main
  git pull upstream main
  git push origin main
  ```

## Project Structure Guide

Understanding the project structure:

```
modules/
├── config/          # Configuration management
├── core/            # Core business logic
│   ├── ocr/        # OCR functionality
│   └── workspace/  # Workspace management
├── data/           # Data processing and augmentation
├── export/         # Export functionality
│   └── formats/    # Export format implementations
├── gui/            # GUI components
│   ├── handlers/   # Event handlers
│   ├── dialogs/    # Dialog windows
│   └── items/      # Canvas annotation items
└── utils/          # Utility functions
```

### Adding New Features

**1. OCR Feature:**
- Add to `modules/core/ocr/`
- Update PaddleOCR settings if needed

**2. GUI Feature:**
- Add components to `modules/gui/`
- Create handlers in `modules/gui/handlers/`
- Update main window if needed

**3. Export Format:**
- Create new format in `modules/export/formats/`
- Register in export manager
- Add tests

**4. Data Processing:**
- Add to `modules/data/`
- Ensure compatibility with existing pipeline

## Getting Help

- **Discord/Chat**: [Add link]
- **Issues**: Use GitHub Issues for questions
- **Email**: your.email@example.com

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Credited in documentation

Thank you for contributing to Ajan OCR Annotation Tool!
