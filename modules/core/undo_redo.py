"""
Undo/Redo System using Command Pattern

This module provides a complete undo/redo system for annotation operations.
Each action is encapsulated in a Command object that can be executed and undone.

Usage:
    from modules.core.undo_redo import UndoRedoManager, Command

    # Get singleton instance
    manager = UndoRedoManager.instance()

    # Execute a command
    cmd = AddAnnotationCommand(annotation_data)
    manager.execute(cmd)

    # Undo/Redo
    manager.undo()
    manager.redo()
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from copy import deepcopy

logger = logging.getLogger("TextDetGUI")


class Command(ABC):
    """
    Abstract base class for all commands.

    Each command must implement execute() and undo() methods.
    """

    def __init__(self, description: str = ""):
        """
        Initialize command.

        Args:
            description: Human-readable description of the command
        """
        self.description = description

    @abstractmethod
    def execute(self) -> bool:
        """
        Execute the command.

        Returns:
            True if execution was successful
        """
        pass

    @abstractmethod
    def undo(self) -> bool:
        """
        Undo the command.

        Returns:
            True if undo was successful
        """
        pass

    def redo(self) -> bool:
        """
        Redo the command (default: re-execute).

        Returns:
            True if redo was successful
        """
        return self.execute()


class UndoRedoManager:
    """
    Manages undo/redo stack for annotation operations.

    Uses singleton pattern to ensure single instance across application.
    """

    _instance: Optional['UndoRedoManager'] = None

    @classmethod
    def instance(cls) -> 'UndoRedoManager':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """Reset singleton (useful for testing)."""
        cls._instance = None

    def __init__(self, max_history: int = 100):
        """
        Initialize UndoRedoManager.

        Args:
            max_history: Maximum number of commands to keep in history
        """
        self._undo_stack: List[Command] = []
        self._redo_stack: List[Command] = []
        self._max_history = max_history
        self._is_executing = False

        # Callbacks for UI updates
        self._on_change_callbacks: List[Callable] = []

    def execute(self, command: Command) -> bool:
        """
        Execute a command and add it to the undo stack.

        Args:
            command: Command to execute

        Returns:
            True if execution was successful
        """
        if self._is_executing:
            return False

        self._is_executing = True

        try:
            if command.execute():
                self._undo_stack.append(command)
                self._redo_stack.clear()  # Clear redo stack on new action

                # Trim history if too large
                while len(self._undo_stack) > self._max_history:
                    self._undo_stack.pop(0)

                logger.debug(f"Executed: {command.description}")
                self._notify_change()
                return True
            else:
                logger.warning(f"Failed to execute: {command.description}")
                return False

        finally:
            self._is_executing = False

    def undo(self) -> bool:
        """
        Undo the last command.

        Returns:
            True if undo was successful
        """
        if not self.can_undo():
            logger.debug("Nothing to undo")
            return False

        if self._is_executing:
            return False

        self._is_executing = True

        try:
            command = self._undo_stack.pop()

            if command.undo():
                self._redo_stack.append(command)
                logger.debug(f"Undone: {command.description}")
                self._notify_change()
                return True
            else:
                # Put back if undo failed
                self._undo_stack.append(command)
                logger.warning(f"Failed to undo: {command.description}")
                return False

        finally:
            self._is_executing = False

    def redo(self) -> bool:
        """
        Redo the last undone command.

        Returns:
            True if redo was successful
        """
        if not self.can_redo():
            logger.debug("Nothing to redo")
            return False

        if self._is_executing:
            return False

        self._is_executing = True

        try:
            command = self._redo_stack.pop()

            if command.redo():
                self._undo_stack.append(command)
                logger.debug(f"Redone: {command.description}")
                self._notify_change()
                return True
            else:
                # Put back if redo failed
                self._redo_stack.append(command)
                logger.warning(f"Failed to redo: {command.description}")
                return False

        finally:
            self._is_executing = False

    def can_undo(self) -> bool:
        """Check if undo is available."""
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        """Check if redo is available."""
        return len(self._redo_stack) > 0

    def get_undo_description(self) -> str:
        """Get description of the command that would be undone."""
        if self.can_undo():
            return self._undo_stack[-1].description
        return ""

    def get_redo_description(self) -> str:
        """Get description of the command that would be redone."""
        if self.can_redo():
            return self._redo_stack[-1].description
        return ""

    def get_undo_count(self) -> int:
        """Get number of available undo operations."""
        return len(self._undo_stack)

    def get_redo_count(self) -> int:
        """Get number of available redo operations."""
        return len(self._redo_stack)

    def clear(self):
        """Clear all history."""
        self._undo_stack.clear()
        self._redo_stack.clear()
        logger.debug("Undo/Redo history cleared")
        self._notify_change()

    def add_change_callback(self, callback: Callable):
        """Add callback to be notified on changes."""
        self._on_change_callbacks.append(callback)

    def remove_change_callback(self, callback: Callable):
        """Remove change callback."""
        if callback in self._on_change_callbacks:
            self._on_change_callbacks.remove(callback)

    def _notify_change(self):
        """Notify all callbacks of a change."""
        for callback in self._on_change_callbacks:
            try:
                callback()
            except Exception as e:
                logger.exception("Error in undo/redo callback")


# ===== Concrete Command Classes =====

class AddAnnotationCommand(Command):
    """Command for adding an annotation."""

    def __init__(self, manager, image_path: str, annotation: Dict[str, Any]):
        """
        Args:
            manager: WorkspaceManager or annotation handler
            image_path: Path to the image
            annotation: Annotation data to add
        """
        super().__init__(f"Add annotation to {image_path}")
        self.manager = manager
        self.image_path = image_path
        self.annotation = deepcopy(annotation)
        self.added_index = -1

    def execute(self) -> bool:
        try:
            annotations = self.manager.get_annotations(self.image_path)
            annotations.append(deepcopy(self.annotation))
            self.added_index = len(annotations) - 1
            self.manager.set_annotations(self.image_path, annotations)
            return True
        except (AttributeError, IndexError, TypeError, ValueError, RuntimeError) as e:
            logger.exception("Failed to add annotation")
            return False

    def undo(self) -> bool:
        try:
            annotations = self.manager.get_annotations(self.image_path)
            if self.added_index >= 0 and self.added_index < len(annotations):
                annotations.pop(self.added_index)
                self.manager.set_annotations(self.image_path, annotations)
                return True
            return False
        except (AttributeError, IndexError, TypeError, ValueError, RuntimeError) as e:
            logger.exception("Failed to undo add annotation")
            return False


class DeleteAnnotationCommand(Command):
    """Command for deleting an annotation."""

    def __init__(self, manager, image_path: str, index: int):
        """
        Args:
            manager: WorkspaceManager or annotation handler
            image_path: Path to the image
            index: Index of annotation to delete
        """
        super().__init__(f"Delete annotation from {image_path}")
        self.manager = manager
        self.image_path = image_path
        self.index = index
        self.deleted_annotation = None

    def execute(self) -> bool:
        try:
            annotations = self.manager.get_annotations(self.image_path)
            if 0 <= self.index < len(annotations):
                self.deleted_annotation = deepcopy(annotations[self.index])
                annotations.pop(self.index)
                self.manager.set_annotations(self.image_path, annotations)
                return True
            return False
        except (AttributeError, IndexError, TypeError, ValueError, RuntimeError) as e:
            logger.exception("Failed to delete annotation")
            return False

    def undo(self) -> bool:
        try:
            if self.deleted_annotation:
                annotations = self.manager.get_annotations(self.image_path)
                annotations.insert(self.index, deepcopy(self.deleted_annotation))
                self.manager.set_annotations(self.image_path, annotations)
                return True
            return False
        except (AttributeError, IndexError, TypeError, ValueError, RuntimeError) as e:
            logger.exception("Failed to undo delete annotation")
            return False


class ModifyAnnotationCommand(Command):
    """Command for modifying an annotation."""

    def __init__(self, manager, image_path: str, index: int, new_data: Dict[str, Any]):
        """
        Args:
            manager: WorkspaceManager or annotation handler
            image_path: Path to the image
            index: Index of annotation to modify
            new_data: New annotation data
        """
        super().__init__(f"Modify annotation in {image_path}")
        self.manager = manager
        self.image_path = image_path
        self.index = index
        self.new_data = deepcopy(new_data)
        self.old_data = None

    def execute(self) -> bool:
        try:
            annotations = self.manager.get_annotations(self.image_path)
            if 0 <= self.index < len(annotations):
                self.old_data = deepcopy(annotations[self.index])
                annotations[self.index] = deepcopy(self.new_data)
                self.manager.set_annotations(self.image_path, annotations)
                return True
            return False
        except (AttributeError, IndexError, TypeError, ValueError, RuntimeError) as e:
            logger.exception("Failed to modify annotation")
            return False

    def undo(self) -> bool:
        try:
            if self.old_data:
                annotations = self.manager.get_annotations(self.image_path)
                if 0 <= self.index < len(annotations):
                    annotations[self.index] = deepcopy(self.old_data)
                    self.manager.set_annotations(self.image_path, annotations)
                    return True
            return False
        except (AttributeError, IndexError, TypeError, ValueError, RuntimeError) as e:
            logger.exception("Failed to undo modify annotation")
            return False


class UpdateTranscriptionCommand(Command):
    """Command for updating annotation transcription."""

    def __init__(self, manager, image_path: str, index: int, new_text: str):
        """
        Args:
            manager: WorkspaceManager or annotation handler
            image_path: Path to the image
            index: Index of annotation
            new_text: New transcription text
        """
        super().__init__(f"Update text: '{new_text[:20]}...'")
        self.manager = manager
        self.image_path = image_path
        self.index = index
        self.new_text = new_text
        self.old_text = ""

    def execute(self) -> bool:
        try:
            annotations = self.manager.get_annotations(self.image_path)
            if 0 <= self.index < len(annotations):
                self.old_text = annotations[self.index].get('transcription', '')
                annotations[self.index]['transcription'] = self.new_text
                self.manager.set_annotations(self.image_path, annotations)
                return True
            return False
        except (AttributeError, IndexError, TypeError, ValueError, RuntimeError) as e:
            logger.exception("Failed to update transcription")
            return False

    def undo(self) -> bool:
        try:
            annotations = self.manager.get_annotations(self.image_path)
            if 0 <= self.index < len(annotations):
                annotations[self.index]['transcription'] = self.old_text
                self.manager.set_annotations(self.image_path, annotations)
                return True
            return False
        except (AttributeError, IndexError, TypeError, ValueError, RuntimeError) as e:
            logger.exception("Failed to undo update transcription")
            return False


class MoveAnnotationCommand(Command):
    """Command for moving an annotation (changing points)."""

    def __init__(self, manager, image_path: str, index: int, new_points: List):
        """
        Args:
            manager: WorkspaceManager or annotation handler
            image_path: Path to the image
            index: Index of annotation
            new_points: New points coordinates
        """
        super().__init__(f"Move annotation in {image_path}")
        self.manager = manager
        self.image_path = image_path
        self.index = index
        self.new_points = deepcopy(new_points)
        self.old_points = None

    def execute(self) -> bool:
        try:
            annotations = self.manager.get_annotations(self.image_path)
            if 0 <= self.index < len(annotations):
                self.old_points = deepcopy(annotations[self.index].get('points', []))
                annotations[self.index]['points'] = deepcopy(self.new_points)
                self.manager.set_annotations(self.image_path, annotations)
                return True
            return False
        except (AttributeError, IndexError, TypeError, ValueError, RuntimeError) as e:
            logger.exception("Failed to move annotation")
            return False

    def undo(self) -> bool:
        try:
            if self.old_points:
                annotations = self.manager.get_annotations(self.image_path)
                if 0 <= self.index < len(annotations):
                    annotations[self.index]['points'] = deepcopy(self.old_points)
                    self.manager.set_annotations(self.image_path, annotations)
                    return True
            return False
        except (AttributeError, IndexError, TypeError, ValueError, RuntimeError) as e:
            logger.exception("Failed to undo move annotation")
            return False


class BatchDeleteCommand(Command):
    """Command for deleting multiple annotations."""

    def __init__(self, manager, image_path: str, indices: List[int]):
        """
        Args:
            manager: WorkspaceManager or annotation handler
            image_path: Path to the image
            indices: List of indices to delete (will be sorted descending)
        """
        super().__init__(f"Delete {len(indices)} annotations")
        self.manager = manager
        self.image_path = image_path
        self.indices = sorted(indices, reverse=True)  # Delete from end first
        self.deleted_annotations: List[tuple] = []  # (index, annotation)

    def execute(self) -> bool:
        try:
            annotations = self.manager.get_annotations(self.image_path)
            self.deleted_annotations = []

            for index in self.indices:
                if 0 <= index < len(annotations):
                    self.deleted_annotations.append((index, deepcopy(annotations[index])))
                    annotations.pop(index)

            self.manager.set_annotations(self.image_path, annotations)
            return True
        except (AttributeError, IndexError, TypeError, ValueError, RuntimeError) as e:
            logger.exception("Failed to batch delete")
            return False

    def undo(self) -> bool:
        try:
            annotations = self.manager.get_annotations(self.image_path)

            # Restore in reverse order (smallest index first)
            for index, annotation in reversed(self.deleted_annotations):
                annotations.insert(index, deepcopy(annotation))

            self.manager.set_annotations(self.image_path, annotations)
            return True
        except (AttributeError, IndexError, TypeError, ValueError, RuntimeError) as e:
            logger.exception("Failed to undo batch delete")
            return False


class ClearAnnotationsCommand(Command):
    """Command for clearing all annotations from an image."""

    def __init__(self, manager, image_path: str):
        """
        Args:
            manager: WorkspaceManager or annotation handler
            image_path: Path to the image
        """
        super().__init__(f"Clear all annotations from {image_path}")
        self.manager = manager
        self.image_path = image_path
        self.old_annotations: List[Dict[str, Any]] = []

    def execute(self) -> bool:
        try:
            self.old_annotations = deepcopy(self.manager.get_annotations(self.image_path))
            self.manager.set_annotations(self.image_path, [])
            return True
        except (AttributeError, IndexError, TypeError, ValueError, RuntimeError) as e:
            logger.exception("Failed to clear annotations")
            return False

    def undo(self) -> bool:
        try:
            self.manager.set_annotations(self.image_path, deepcopy(self.old_annotations))
            return True
        except (AttributeError, IndexError, TypeError, ValueError, RuntimeError) as e:
            logger.exception("Failed to undo clear annotations")
            return False


# ===== Convenience Functions =====

def get_undo_manager() -> UndoRedoManager:
    """Get the singleton UndoRedoManager instance."""
    return UndoRedoManager.instance()


def undo() -> bool:
    """Convenience function to undo."""
    return get_undo_manager().undo()


def redo() -> bool:
    """Convenience function to redo."""
    return get_undo_manager().redo()


def can_undo() -> bool:
    """Check if undo is available."""
    return get_undo_manager().can_undo()


def can_redo() -> bool:
    """Check if redo is available."""
    return get_undo_manager().can_redo()
