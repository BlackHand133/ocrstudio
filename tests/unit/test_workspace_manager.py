"""
Unit tests for WorkspaceManager: create, load, save, rename, delete, version ops.

All tests run against a fresh temporary directory — no real workspace files are touched.
"""
import pytest

from modules.core.workspace.manager import WorkspaceManager


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def wm(tmp_path):
    """WorkspaceManager backed by a temporary directory."""
    return WorkspaceManager(str(tmp_path))


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

class TestCreateWorkspace:
    def test_create_succeeds(self, wm):
        assert wm.create_workspace("ws1", "My Workspace", "/images/path") is True

    def test_creates_workspace_json(self, wm, tmp_path):
        wm.create_workspace("ws1", "My Workspace", "/images/path")
        ws_json = tmp_path / "workspaces" / "ws1" / "workspace.json"
        assert ws_json.exists()

    def test_creates_v1_json(self, wm, tmp_path):
        wm.create_workspace("ws1", "My Workspace", "/images/path")
        v1_json = tmp_path / "workspaces" / "ws1" / "v1.json"
        assert v1_json.exists()

    def test_creates_exports_json(self, wm, tmp_path):
        wm.create_workspace("ws1", "My Workspace", "/images/path")
        exports_json = tmp_path / "workspaces" / "ws1" / "exports.json"
        assert exports_json.exists()

    def test_duplicate_id_fails(self, wm):
        wm.create_workspace("ws1", "My Workspace", "/images")
        assert wm.create_workspace("ws1", "Duplicate", "/images") is False

    def test_source_folder_stored(self, wm):
        wm.create_workspace("ws1", "WS", "/some/folder")
        data = wm.load_workspace("ws1")
        assert data["source"]["folder"] == "/some/folder"

    def test_description_stored(self, wm):
        wm.create_workspace("ws1", "WS", "/images", description="test desc")
        data = wm.load_workspace("ws1")
        assert data["workspace"]["description"] == "test desc"


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

class TestLoadWorkspace:
    def test_load_returns_dict(self, wm):
        wm.create_workspace("ws1", "My Workspace", "/images")
        data = wm.load_workspace("ws1")
        assert isinstance(data, dict)

    def test_load_contains_top_level_keys(self, wm):
        wm.create_workspace("ws1", "My Workspace", "/images")
        data = wm.load_workspace("ws1")
        for key in ("workspace", "versions", "source", "settings"):
            assert key in data, f"Missing key: {key}"

    def test_load_nonexistent_returns_none(self, wm):
        assert wm.load_workspace("nonexistent") is None

    def test_load_preserves_name(self, wm):
        wm.create_workspace("ws1", "Named WS", "/images")
        data = wm.load_workspace("ws1")
        assert data["workspace"]["name"] == "Named WS"

    def test_versions_default_to_v1(self, wm):
        wm.create_workspace("ws1", "WS", "/images")
        data = wm.load_workspace("ws1")
        assert data["versions"]["current"] == "v1"
        assert "v1" in data["versions"]["available"]


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

class TestSaveWorkspace:
    def test_save_persists_changes(self, wm):
        wm.create_workspace("ws1", "WS", "/images")
        data = wm.load_workspace("ws1")
        data["workspace"]["description"] = "Updated"
        wm.save_workspace("ws1", data)
        reloaded = wm.load_workspace("ws1")
        assert reloaded["workspace"]["description"] == "Updated"

    def test_save_updates_modified_at(self, wm):
        wm.create_workspace("ws1", "WS", "/images")
        data = wm.load_workspace("ws1")
        original_ts = data["workspace"]["modified_at"]
        import time; time.sleep(0.01)
        wm.save_workspace("ws1", data)
        reloaded = wm.load_workspace("ws1")
        # modified_at should have been refreshed by write_workspace_file
        assert reloaded["workspace"]["modified_at"] >= original_ts


# ---------------------------------------------------------------------------
# Rename
# ---------------------------------------------------------------------------

class TestRenameWorkspace:
    def test_rename_returns_success(self, wm):
        wm.create_workspace("ws1", "Old Name", "/images")
        ok, _ = wm.rename_workspace("ws1", "New Name")
        assert ok is True

    def test_rename_updates_persisted_name(self, wm):
        wm.create_workspace("ws1", "Old Name", "/images")
        wm.rename_workspace("ws1", "New Name")
        data = wm.load_workspace("ws1")
        assert data["workspace"]["name"] == "New Name"

    def test_rename_nonexistent_fails(self, wm):
        ok, msg = wm.rename_workspace("no_such", "New Name")
        assert ok is False
        assert msg  # some error message


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

class TestDeleteWorkspace:
    def test_delete_returns_true(self, wm):
        wm.create_workspace("ws1", "WS", "/images")
        assert wm.delete_workspace("ws1") is True

    def test_deleted_workspace_not_found(self, wm):
        wm.create_workspace("ws1", "WS", "/images")
        wm.delete_workspace("ws1")
        assert wm.load_workspace("ws1") is None

    def test_delete_removes_from_list(self, wm):
        wm.create_workspace("ws1", "WS", "/images")
        wm.delete_workspace("ws1")
        ids = [ws["id"] for ws in wm.get_workspace_list()]
        assert "ws1" not in ids

    def test_delete_nonexistent_fails(self, wm):
        assert wm.delete_workspace("no_such") is False


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------

class TestWorkspaceList:
    def test_empty_initially(self, wm):
        assert wm.get_workspace_list() == []

    def test_list_contains_created(self, wm):
        wm.create_workspace("ws1", "WS", "/images")
        ids = [ws["id"] for ws in wm.get_workspace_list()]
        assert "ws1" in ids

    def test_list_multiple_workspaces(self, wm):
        for i in range(3):
            wm.create_workspace(f"ws{i}", f"WS {i}", "/images")
        assert len(wm.get_workspace_list()) == 3

    def test_list_item_has_expected_fields(self, wm):
        wm.create_workspace("ws1", "My WS", "/images")
        item = wm.get_workspace_list()[0]
        for field in ("id", "name", "created_at", "modified_at", "current_version"):
            assert field in item, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# Version operations
# ---------------------------------------------------------------------------

class TestVersionOperations:
    def test_initial_version_is_v1(self, wm):
        wm.create_workspace("ws1", "WS", "/images")
        assert wm.get_current_version("ws1") == "v1"

    def test_load_v1_is_valid(self, wm):
        wm.create_workspace("ws1", "WS", "/images")
        v_data = wm.load_version("ws1", "v1")
        assert v_data is not None
        assert v_data["data_version"] == "v1"
        assert "annotations" in v_data

    def test_create_new_version(self, wm):
        wm.create_workspace("ws1", "WS", "/images")
        ok, _ = wm.create_version("ws1", "v2", source_version="v1")
        assert ok is True

    def test_new_version_appears_in_list(self, wm):
        wm.create_workspace("ws1", "WS", "/images")
        wm.create_version("ws1", "v2", source_version="v1")
        versions = [v["name"] for v in wm.get_version_list("ws1")]
        assert "v2" in versions

    def test_switch_version(self, wm):
        wm.create_workspace("ws1", "WS", "/images")
        wm.create_version("ws1", "v2", source_version="v1")
        assert wm.switch_version("ws1", "v2") is True
        assert wm.get_current_version("ws1") == "v2"

    def test_delete_non_current_version(self, wm):
        wm.create_workspace("ws1", "WS", "/images")
        wm.create_version("ws1", "v2", source_version="v1")
        ok, _ = wm.delete_version("ws1", "v2")
        assert ok is True

    def test_cannot_delete_only_version(self, wm):
        wm.create_workspace("ws1", "WS", "/images")
        ok, _ = wm.delete_version("ws1", "v1")
        assert ok is False


# ---------------------------------------------------------------------------
# Repair
# ---------------------------------------------------------------------------

class TestRepairWorkspace:
    def test_repair_healthy_workspace(self, wm):
        wm.create_workspace("ws1", "WS", "/images")
        ok, _ = wm.repair_workspace("ws1")
        assert ok is True

    def test_repair_nonexistent_fails(self, wm):
        ok, _ = wm.repair_workspace("no_such")
        assert ok is False
