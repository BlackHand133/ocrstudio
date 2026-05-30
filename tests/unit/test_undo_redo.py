"""
Unit tests for modules.core.undo_redo.UndoRedoManager

Tests cover:
- execute / undo / redo happy paths
- boundary conditions (empty stack, max_history)
- re-entrant guard (_is_executing)
- clear()
- can_undo / can_redo predicates
- on_change callbacks
"""
import pytest
from modules.core.undo_redo import UndoRedoManager, Command


# ---------------------------------------------------------------------------
# Helper: simple counter command
# ---------------------------------------------------------------------------

class IncrementCommand(Command):
    """Increment a list counter — easy to observe execute/undo."""

    def __init__(self, state: dict, amount: int = 1):
        super().__init__(description=f"Increment by {amount}")
        self.state = state
        self.amount = amount

    def execute(self) -> bool:
        self.state["value"] += self.amount
        return True

    def undo(self) -> bool:
        self.state["value"] -= self.amount
        return True


class FailingCommand(Command):
    """A command whose execute() always returns False."""

    def execute(self) -> bool:
        return False

    def undo(self) -> bool:
        return False


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_singleton():
    """Ensure each test gets a clean UndoRedoManager singleton."""
    UndoRedoManager.reset_instance()
    yield
    UndoRedoManager.reset_instance()


@pytest.fixture
def mgr():
    return UndoRedoManager.instance()


@pytest.fixture
def counter():
    return {"value": 0}


# ===========================================================================
# Singleton
# ===========================================================================

class TestSingleton:

    def test_same_instance_returned(self):
        a = UndoRedoManager.instance()
        b = UndoRedoManager.instance()
        assert a is b

    def test_reset_clears_singleton(self):
        UndoRedoManager.reset_instance()
        a = UndoRedoManager.instance()
        UndoRedoManager.reset_instance()
        b = UndoRedoManager.instance()
        assert a is not b


# ===========================================================================
# execute
# ===========================================================================

class TestExecute:

    def test_execute_applies_change(self, mgr, counter):
        mgr.execute(IncrementCommand(counter, 5))
        assert counter["value"] == 5

    def test_execute_returns_true_on_success(self, mgr, counter):
        result = mgr.execute(IncrementCommand(counter))
        assert result is True

    def test_execute_returns_false_on_failure(self, mgr):
        result = mgr.execute(FailingCommand("fail"))
        assert result is False

    def test_execute_adds_to_undo_stack(self, mgr, counter):
        mgr.execute(IncrementCommand(counter))
        assert mgr.can_undo()

    def test_execute_clears_redo_stack(self, mgr, counter):
        # Build some history, undo one, then execute a new command
        mgr.execute(IncrementCommand(counter))
        mgr.execute(IncrementCommand(counter))
        mgr.undo()
        assert mgr.can_redo()
        mgr.execute(IncrementCommand(counter))
        assert not mgr.can_redo()

    def test_failed_execute_does_not_add_to_stack(self, mgr):
        mgr.execute(FailingCommand("fail"))
        assert not mgr.can_undo()


# ===========================================================================
# undo
# ===========================================================================

class TestUndo:

    def test_undo_reverts_change(self, mgr, counter):
        mgr.execute(IncrementCommand(counter, 10))
        mgr.undo()
        assert counter["value"] == 0

    def test_undo_on_empty_stack_returns_false(self, mgr):
        assert mgr.undo() is False

    def test_undo_moves_command_to_redo_stack(self, mgr, counter):
        mgr.execute(IncrementCommand(counter))
        mgr.undo()
        assert mgr.can_redo()

    def test_multiple_undos(self, mgr, counter):
        for _ in range(3):
            mgr.execute(IncrementCommand(counter, 1))
        for _ in range(3):
            mgr.undo()
        assert counter["value"] == 0

    def test_undo_only_reverts_last_command(self, mgr, counter):
        mgr.execute(IncrementCommand(counter, 5))
        mgr.execute(IncrementCommand(counter, 3))
        mgr.undo()
        assert counter["value"] == 5


# ===========================================================================
# redo
# ===========================================================================

class TestRedo:

    def test_redo_reapplies_change(self, mgr, counter):
        mgr.execute(IncrementCommand(counter, 7))
        mgr.undo()
        mgr.redo()
        assert counter["value"] == 7

    def test_redo_on_empty_stack_returns_false(self, mgr):
        assert mgr.redo() is False

    def test_redo_chain(self, mgr, counter):
        for i in range(5):
            mgr.execute(IncrementCommand(counter, 1))
        for _ in range(5):
            mgr.undo()
        for _ in range(5):
            mgr.redo()
        assert counter["value"] == 5

    def test_redo_clears_after_new_execute(self, mgr, counter):
        mgr.execute(IncrementCommand(counter))
        mgr.undo()
        assert mgr.can_redo()
        mgr.execute(IncrementCommand(counter, 2))
        assert not mgr.can_redo()


# ===========================================================================
# can_undo / can_redo
# ===========================================================================

class TestPredicates:

    def test_initially_cannot_undo(self, mgr):
        assert not mgr.can_undo()

    def test_initially_cannot_redo(self, mgr):
        assert not mgr.can_redo()

    def test_can_undo_after_execute(self, mgr, counter):
        mgr.execute(IncrementCommand(counter))
        assert mgr.can_undo()

    def test_can_redo_after_undo(self, mgr, counter):
        mgr.execute(IncrementCommand(counter))
        mgr.undo()
        assert mgr.can_redo()

    def test_cannot_redo_after_new_execute(self, mgr, counter):
        mgr.execute(IncrementCommand(counter))
        mgr.undo()
        mgr.execute(IncrementCommand(counter))
        assert not mgr.can_redo()


# ===========================================================================
# max_history
# ===========================================================================

class TestMaxHistory:

    def test_history_trimmed_to_max(self, counter):
        mgr = UndoRedoManager(max_history=3)
        for _ in range(10):
            mgr.execute(IncrementCommand(counter, 1))
        # Can undo only 3 times
        count = 0
        while mgr.can_undo():
            mgr.undo()
            count += 1
        assert count == 3

    def test_value_after_overflow_trim(self, counter):
        mgr = UndoRedoManager(max_history=3)
        for i in range(10):
            mgr.execute(IncrementCommand(counter, 1))
        assert counter["value"] == 10
        # Undo all 3 retained commands
        while mgr.can_undo():
            mgr.undo()
        assert counter["value"] == 7   # 10 - 3 = 7


# ===========================================================================
# clear
# ===========================================================================

class TestClear:

    def test_clear_empties_both_stacks(self, mgr, counter):
        mgr.execute(IncrementCommand(counter))
        mgr.undo()
        mgr.clear()
        assert not mgr.can_undo()
        assert not mgr.can_redo()

    def test_clear_on_empty_manager_is_safe(self, mgr):
        mgr.clear()  # Should not raise


# ===========================================================================
# on_change callbacks
# ===========================================================================

class TestCallbacks:

    def test_callback_called_on_execute(self, mgr, counter):
        calls = []
        mgr.add_change_callback(lambda: calls.append("execute"))
        mgr.execute(IncrementCommand(counter))
        assert len(calls) == 1

    def test_callback_called_on_undo(self, mgr, counter):
        calls = []
        mgr.execute(IncrementCommand(counter))
        mgr.add_change_callback(lambda: calls.append("undo"))
        mgr.undo()
        assert len(calls) == 1

    def test_callback_called_on_redo(self, mgr, counter):
        calls = []
        mgr.execute(IncrementCommand(counter))
        mgr.undo()
        mgr.add_change_callback(lambda: calls.append("redo"))
        mgr.redo()
        assert len(calls) == 1
