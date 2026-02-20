import importlib
import sys
import types


def _fake_streamlit_module():
    st = types.SimpleNamespace()
    st.set_page_config = lambda **kwargs: None
    st.markdown = lambda *args, **kwargs: None
    st.warning = lambda *args, **kwargs: None
    st.info = lambda *args, **kwargs: None
    st.error = lambda *args, **kwargs: None
    st.success = lambda *args, **kwargs: None
    st.caption = lambda *args, **kwargs: None
    st.stop = lambda: None
    st.secrets = {}

    sidebar_ns = types.SimpleNamespace(
        warning=lambda *a, **k: None,
        title=lambda *a, **k: None,
        markdown=lambda *a, **k: None,
        radio=lambda *a, **k: "地表 DNA (语义视图)",
        selectbox=lambda *a, **k: "上海 · 陆家嘴",
        info=lambda *a, **k: None,
        write=lambda *a, **k: None,
        button=lambda *a, **k: False,
    )
    sidebar_ns.__enter__ = lambda self=sidebar_ns: self
    sidebar_ns.__exit__ = lambda *args, **kwargs: False
    st.sidebar = sidebar_ns

    return st


def _import_app_with_fakes(monkeypatch, fake_ee):
    monkeypatch.setitem(sys.modules, "streamlit", _fake_streamlit_module())
    monkeypatch.setitem(sys.modules, "ee", fake_ee)
    sys.modules.pop("geemap", None)
    sys.modules.pop("geemap.foliumap", None)
    if "app" in sys.modules:
        del sys.modules["app"]
    return importlib.import_module("app")


def test_smart_load_cache_hit(monkeypatch):
    class _FakeEE:
        class data:
            @staticmethod
            def getAsset(asset_id):
                return {"id": asset_id}

        @staticmethod
        def Image(asset_id):
            return f"asset::{asset_id}"

        @staticmethod
        def Initialize(*args, **kwargs):
            return None

    app = _import_app_with_fakes(monkeypatch, _FakeEE)

    monkeypatch.setattr(app, "get_layer_logic", lambda mode, region: ("computed", {"min": 0}, "dna"))

    layer, vis, status, is_cached, asset_id, computed, suffix, route_reason = app.smart_load(
        "地表 DNA (语义视图)",
        region="r",
        loc_code="shanghai",
        gee_user_path="users/demo/aef_demo",
    )

    assert is_cached is True
    assert layer == "asset::users/demo/aef_demo/shanghai_dna"
    assert vis == {"min": 0}
    assert "极速缓存" in status
    assert asset_id == "users/demo/aef_demo/shanghai_dna"
    assert computed == "computed"
    assert suffix == "dna"
    assert route_reason == "asset_hit"


def test_smart_load_cache_miss(monkeypatch):
    class _FakeEE:
        class data:
            @staticmethod
            def getAsset(asset_id):
                raise RuntimeError("not found")

        @staticmethod
        def Image(asset_id):
            return f"asset::{asset_id}"

        @staticmethod
        def Initialize(*args, **kwargs):
            return None

    app = _import_app_with_fakes(monkeypatch, _FakeEE)

    monkeypatch.setattr(app, "get_layer_logic", lambda mode, region: ("computed", {"min": 0}, "change"))

    layer, vis, status, is_cached, asset_id, computed, suffix, route_reason = app.smart_load(
        "变化雷达 (敏捷治理)",
        region="r",
        loc_code="xiongan",
        gee_user_path="users/demo/aef_demo",
    )

    assert is_cached is False
    assert layer == "computed"
    assert vis == {"min": 0}
    assert "实时计算" in status
    assert asset_id == "users/demo/aef_demo/xiongan_change"
    assert computed == "computed"
    assert suffix == "change"
    assert route_reason == "asset_miss"


def test_smart_load_asset_check_permission_error(monkeypatch):
    class _FakeEE:
        class data:
            @staticmethod
            def getAsset(asset_id):
                raise RuntimeError("Permission denied")

        @staticmethod
        def Image(asset_id):
            return f"asset::{asset_id}"

        @staticmethod
        def Initialize(*args, **kwargs):
            return None

    app = _import_app_with_fakes(monkeypatch, _FakeEE)
    monkeypatch.setattr(app, "get_layer_logic", lambda mode, region: ("computed", {"min": 0}, "eco"))

    layer, vis, status, is_cached, asset_id, computed, suffix, route_reason = app.smart_load(
        "生态韧性 (绿色底线)",
        region="r",
        loc_code="hangzhou",
        gee_user_path="users/demo/aef_demo",
    )

    assert is_cached is False
    assert layer == "computed"
    assert "Asset检查异常" in status
    assert route_reason == "asset_check_permission"


def test_trigger_export_start_task(monkeypatch):
    calls = {"started": False}

    class _Task:
        id = "TASK_001"

        def start(self):
            calls["started"] = True

    class _FakeEE:
        class batch:
            class Export:
                class image:
                    @staticmethod
                    def toAsset(**kwargs):
                        assert kwargs["assetId"] == "users/demo/aef_demo/shanghai_dna"
                        assert kwargs["description"] == "Cache_shanghai_dna"
                        assert kwargs["scale"] == 10
                        return _Task()

        @staticmethod
        def Initialize(*args, **kwargs):
            return None

    app = _import_app_with_fakes(monkeypatch, _FakeEE)

    task_id = app.trigger_export(
        image="img",
        description="Cache_shanghai_dna",
        asset_id="users/demo/aef_demo/shanghai_dna",
        region="region",
    )

    assert task_id == "TASK_001"
    assert calls["started"] is True


def test_validate_gee_user_path(monkeypatch):
    class _FakeEE:
        @staticmethod
        def Initialize(*args, **kwargs):
            return None

    app = _import_app_with_fakes(monkeypatch, _FakeEE)

    ok, _ = app._validate_gee_user_path("users/demo/aef_demo")
    assert ok is True

    ok, msg = app._validate_gee_user_path("users/demo")
    assert ok is True  # 至少2段即可
    
    # v5 已支持 projects/ 路径
    ok, msg = app._validate_gee_user_path("projects/demo/aef_demo")
    assert ok is True
    
    # 无效格式
    ok, msg = app._validate_gee_user_path("invalid/path")
    assert ok is False
    assert "users/" in msg or "projects/" in msg
