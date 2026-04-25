from vtf.config import Config
from vtf.sinks.feishu import Feishu


def test_feishu_not_available_without_config():
    f = Feishu()
    cfg = Config()
    ok, reason = f.available(cfg)
    assert not ok
    assert "base_token" in reason


def test_feishu_available_when_configured():
    f = Feishu()
    cfg = Config()
    cfg.sink.feishu.base_token = "tok"
    cfg.sink.feishu.table_id = "tbl"
    cfg.sink.feishu.schema = "schema.toml"
    ok, reason = f.available(cfg)
    assert ok
