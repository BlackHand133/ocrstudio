"""
Unit tests for modules.config.manager.ConfigManager

Tests cover:
- Singleton pattern
- Profile loading from config.yaml
- get / set with dot notation
- Profile management (list, get, set current)
- get_paddleocr_params
- update_profile_setting
- save / reload round-trip
- snapshot / restore_snapshot
- Legacy compat API (get_default_profile_name etc.)
- app settings
"""
import os
import pytest
import yaml


# ===========================================================================
# Singleton behaviour
# ===========================================================================

class TestSingleton:

    def test_same_instance_returned(self, config_manager):
        from modules.config.manager import ConfigManager
        a = ConfigManager.instance()
        b = ConfigManager.instance()
        assert a is b

    def test_reset_clears_singleton(self, minimal_config_yaml):
        from modules.config.manager import ConfigManager
        ConfigManager.reset_instance()
        first = ConfigManager.instance(root_dir=str(minimal_config_yaml))
        ConfigManager.reset_instance()
        second = ConfigManager.instance(root_dir=str(minimal_config_yaml))
        assert first is not second
        ConfigManager.reset_instance()


# ===========================================================================
# Profile loading
# ===========================================================================

class TestProfileLoading:

    def test_profiles_loaded(self, config_manager):
        profiles = config_manager.list_profiles()
        assert "cpu" in profiles
        assert "gpu" in profiles

    def test_default_profile_is_cpu(self, config_manager):
        assert config_manager.get_current_profile() == "cpu"

    def test_profile_config_has_paddleocr_key(self, config_manager):
        cfg = config_manager.get_profile_config("cpu")
        assert "paddleocr" in cfg

    def test_gpu_profile_loaded(self, config_manager):
        cfg = config_manager.get_profile_config("gpu")
        assert cfg["device"]["type"] == "gpu"

    def test_fallback_used_when_no_config_file(self, tmp_path):
        from modules.config.manager import ConfigManager
        ConfigManager.reset_instance()
        mgr = ConfigManager.instance(root_dir=str(tmp_path))
        assert "cpu" in mgr.list_profiles()
        ConfigManager.reset_instance()


# ===========================================================================
# get / set with dot notation
# ===========================================================================

class TestGetSet:

    def test_get_app_key(self, config_manager):
        val = config_manager.get("auto_save")
        assert val is True

    def test_get_unknown_key_returns_default(self, config_manager):
        val = config_manager.get("does.not.exist", default="fallback")
        assert val == "fallback"

    def test_set_and_get_roundtrip(self, config_manager):
        config_manager.set("auto_save", False)
        assert config_manager.get("auto_save") is False

    def test_set_nested_creates_intermediate_dicts(self, config_manager):
        config_manager.set("new_section.deep.key", 42)
        assert config_manager.get("new_section.deep.key") == 42


# ===========================================================================
# Profile management
# ===========================================================================

class TestProfileManagement:

    def test_set_current_profile_cpu(self, config_manager):
        config_manager.set_current_profile("cpu")
        assert config_manager.get_current_profile() == "cpu"

    def test_set_current_profile_gpu(self, config_manager):
        config_manager.set_current_profile("gpu")
        assert config_manager.get_current_profile() == "gpu"

    def test_set_unknown_profile_raises(self, config_manager):
        with pytest.raises(ValueError):
            config_manager.set_current_profile("nonexistent")

    def test_list_profiles_returns_list(self, config_manager):
        result = config_manager.list_profiles()
        assert isinstance(result, list)
        assert len(result) >= 1


# ===========================================================================
# get_paddleocr_params
# ===========================================================================

class TestGetPaddleocrParams:

    def test_returns_dict(self, config_manager):
        params = config_manager.get_paddleocr_params("cpu")
        assert isinstance(params, dict)

    def test_cpu_params_have_expected_keys(self, config_manager):
        params = config_manager.get_paddleocr_params("cpu")
        assert "lang" in params
        assert "det_db_box_thresh" in params

    def test_default_profile_used_when_none(self, config_manager):
        params_default = config_manager.get_paddleocr_params()
        params_cpu     = config_manager.get_paddleocr_params("cpu")
        assert params_default == params_cpu

    def test_gpu_params_differ_from_cpu(self, config_manager):
        cpu = config_manager.get_paddleocr_params("cpu")
        gpu = config_manager.get_paddleocr_params("gpu")
        # device field should differ
        assert cpu.get("device") != gpu.get("device")


# ===========================================================================
# update_profile_setting
# ===========================================================================

class TestUpdateProfileSetting:

    def test_simple_key_update(self, config_manager):
        config_manager.update_profile_setting("cpu", "paddleocr.lang", "en")
        params = config_manager.get_paddleocr_params("cpu")
        assert params["lang"] == "en"

    def test_numeric_value_update(self, config_manager):
        config_manager.update_profile_setting(
            "cpu", "paddleocr.det_db_box_thresh", 0.8
        )
        params = config_manager.get_paddleocr_params("cpu")
        assert abs(params["det_db_box_thresh"] - 0.8) < 1e-9

    def test_creates_new_nested_key(self, config_manager):
        config_manager.update_profile_setting("cpu", "paddleocr.new_param", 99)
        params = config_manager.get_paddleocr_params("cpu")
        assert params["new_param"] == 99

    def test_unknown_profile_raises(self, config_manager):
        with pytest.raises(ValueError):
            config_manager.update_profile_setting("bad", "paddleocr.lang", "th")


# ===========================================================================
# save / reload round-trip
# ===========================================================================

class TestSaveReload:

    def test_save_and_reload_preserves_profile_change(
        self, config_manager, minimal_config_yaml
    ):
        from modules.config.manager import ConfigManager

        config_manager.update_profile_setting(
            "cpu", "paddleocr.det_db_box_thresh", 0.99
        )
        config_manager.save()

        # Create a fresh instance pointing to the same root
        ConfigManager.reset_instance()
        reloaded = ConfigManager.instance(root_dir=str(minimal_config_yaml))

        params = reloaded.get_paddleocr_params("cpu")
        assert abs(params["det_db_box_thresh"] - 0.99) < 1e-9
        ConfigManager.reset_instance()

    def test_save_preserves_default_profile(
        self, config_manager, minimal_config_yaml
    ):
        from modules.config.manager import ConfigManager

        config_manager.set_current_profile("gpu")
        config_manager.save()

        ConfigManager.reset_instance()
        reloaded = ConfigManager.instance(root_dir=str(minimal_config_yaml))
        assert reloaded.get_current_profile() == "gpu"
        ConfigManager.reset_instance()


# ===========================================================================
# snapshot / restore_snapshot
# ===========================================================================

class TestSnapshotRestore:

    def test_snapshot_returns_dict(self, config_manager):
        snap = config_manager.snapshot()
        assert "current_profile" in snap
        assert "profiles" in snap
        assert "app_config" in snap

    def test_snapshot_is_deep_copy(self, config_manager):
        snap = config_manager.snapshot()
        # Mutating the snapshot should not affect the live config
        snap["profiles"]["cpu"]["paddleocr"]["lang"] = "MUTATED"
        params = config_manager.get_paddleocr_params("cpu")
        assert params.get("lang") != "MUTATED"

    def test_restore_reverts_profile_change(self, config_manager):
        snap = config_manager.snapshot()
        config_manager.set_current_profile("gpu")
        assert config_manager.get_current_profile() == "gpu"

        config_manager.restore_snapshot(snap)
        assert config_manager.get_current_profile() == "cpu"

    def test_restore_reverts_paddleocr_change(self, config_manager):
        original_thresh = config_manager.get_paddleocr_params("cpu")[
            "det_db_box_thresh"
        ]
        snap = config_manager.snapshot()

        config_manager.update_profile_setting(
            "cpu", "paddleocr.det_db_box_thresh", 0.001
        )
        config_manager.restore_snapshot(snap)

        restored = config_manager.get_paddleocr_params("cpu")["det_db_box_thresh"]
        assert abs(restored - original_thresh) < 1e-9


# ===========================================================================
# Legacy compat API
# ===========================================================================

class TestLegacyCompatAPI:

    def test_config_file_property(self, config_manager, minimal_config_yaml):
        expected = os.path.join(str(minimal_config_yaml), "config", "config.yaml")
        assert config_manager.config_file == expected

    def test_get_default_profile_name(self, config_manager):
        assert config_manager.get_default_profile_name() == "cpu"

    def test_set_default_profile(self, config_manager):
        config_manager.set_default_profile("gpu")
        assert config_manager.get_default_profile_name() == "gpu"

    def test_get_profile_alias(self, config_manager):
        via_alias  = config_manager.get_profile("cpu")
        via_direct = config_manager.get_profile_config("cpu")
        assert via_alias == via_direct

    def test_get_app_settings_returns_dict(self, config_manager):
        app = config_manager.get_app_settings()
        assert isinstance(app, dict)
        assert "auto_save" in app
