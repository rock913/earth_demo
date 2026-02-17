import importlib
import sys
import types


def _fake_streamlit_module():
    st = types.SimpleNamespace()

    # Methods referenced by app.py functions. These won't be executed in import-only tests,
    # but having them prevents accidental AttributeError if a test calls them.
    st.set_page_config = lambda **kwargs: None
    st.markdown = lambda *args, **kwargs: None

    st.sidebar = types.SimpleNamespace(
        image=lambda *a, **k: None,
        title=lambda *a, **k: None,
        markdown=lambda *a, **k: None,
        radio=lambda *a, **k: "场景一：地表 DNA 语义视图（认知统一）",
        subheader=lambda *a, **k: None,
        number_input=lambda *a, **k: 30.9,
        slider=lambda *a, **k: 12,
        success=lambda *a, **k: None,
    )

    st.warning = lambda *a, **k: None
    st.info = lambda *a, **k: None
    st.error = lambda *a, **k: None
    st.stop = lambda: None

    st.title = lambda *a, **k: None
    st.columns = lambda *a, **k: (types.SimpleNamespace(), types.SimpleNamespace())
    st.metric = lambda *a, **k: None
    st.caption = lambda *a, **k: None

    return st


def test_app_imports_without_optional_deps(monkeypatch):
    # Ensure we can import app.py even if streamlit/ee/geemap are not installed.
    monkeypatch.setitem(sys.modules, "streamlit", _fake_streamlit_module())

    # Force ee/geemap to be absent
    sys.modules.pop("ee", None)
    sys.modules.pop("geemap", None)
    sys.modules.pop("geemap.foliumap", None)

    if "app" in sys.modules:
        del sys.modules["app"]

    app = importlib.import_module("app")

    assert hasattr(app, "_init_gee")
    ok, msg = app._init_gee()
    assert ok is False
    assert isinstance(msg, str)


def test_init_gee_service_account_env_does_not_nameerror(monkeypatch):
    monkeypatch.setitem(sys.modules, "streamlit", _fake_streamlit_module())

    # Provide a fake ee module that has the attributes we expect.
    class _FakeEE:
        class ServiceAccountCredentials:
            def __init__(self, *args, **kwargs):
                pass

        @staticmethod
        def Initialize(*args, **kwargs):
            raise RuntimeError("expected failure")

    monkeypatch.setitem(sys.modules, "ee", _FakeEE)

    if "app" in sys.modules:
        del sys.modules["app"]

    app = importlib.import_module("app")

    monkeypatch.setenv("EE_SERVICE_ACCOUNT", "x@y.iam.gserviceaccount.com")
    monkeypatch.setenv("EE_PRIVATE_KEY_FILE", "/tmp/key.json")

    ok, msg = app._init_gee()
    assert ok is False
    assert "初始化失败" in msg
