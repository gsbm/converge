import json

from converge.extensions.connectors.sidecar import _load_sidecar_config


def test_load_sidecar_config_json(tmp_path):
    cfg = {
        "bind": "127.0.0.1",
        "port": 8080,
        "providers": [{"name": "acme", "secret_ref": "s1"}],
        "secrets": {"s1": "secret"},
    }
    path = tmp_path / "sidecar.json"
    path.write_text(json.dumps(cfg), encoding="utf-8")
    providers, secrets, bind, port = _load_sidecar_config(str(path))
    assert bind == "127.0.0.1"
    assert port == 8080
    assert "acme" in providers
    assert secrets["s1"] == "secret"


def test_load_sidecar_config_toml(tmp_path):
    path = tmp_path / "sidecar.toml"
    path.write_text(
        """
bind = "0.0.0.0"
port = 8090

[[providers]]
name = "acme"
secret_ref = "s1"

[secrets]
s1 = "x"
""".strip(),
        encoding="utf-8",
    )
    providers, secrets, bind, port = _load_sidecar_config(str(path))
    assert bind == "0.0.0.0"
    assert port == 8090
    assert "acme" in providers
    assert secrets["s1"] == "x"
