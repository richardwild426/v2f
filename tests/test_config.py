from vtf.config import load_config


def test_default_config_values():
    cfg = load_config(user_path=None, project_path=None, env={}, overrides={})
    assert cfg.output.sink == "markdown"
    assert cfg.transcribe.asr_model == "paraformer-zh"
    assert cfg.transcribe.vad_model == "fsmn-vad"
    assert cfg.transcribe.punc_model == "ct-punc"
    assert cfg.transcribe.batch_size_s == 300
    assert cfg.platform.bilibili.cookies_from_browser == "chrome"
    assert cfg.platform.youtube.cookies_from_browser == ""
    assert cfg.download.audio_format == "mp3"
    assert cfg.download.audio_quality == "0"
    assert cfg.download.retries == 3
    assert cfg.sink.feishu.lark_cli == "lark-cli"
    assert cfg.sink.feishu.identity == "bot"
    assert cfg.sink.feishu.identity == "bot"


def test_project_overrides_user(tmp_path):
    user = tmp_path / "user.toml"
    user.write_text(
        '[output]\nsink = "feishu"\n[transcribe]\nasr_model = "u-model"\n',
        encoding="utf-8",
    )
    project = tmp_path / "vtf.toml"
    project.write_text('[transcribe]\nasr_model = "p-model"\n', encoding="utf-8")
    cfg = load_config(user_path=user, project_path=project, env={}, overrides={})
    assert cfg.output.sink == "feishu"
    assert cfg.transcribe.asr_model == "p-model"


def test_env_overrides_files(tmp_path):
    user = tmp_path / "user.toml"
    user.write_text('[output]\nsink = "markdown"\n', encoding="utf-8")
    cfg = load_config(
        user_path=user,
        project_path=None,
        env={
            "VTF_OUTPUT_SINK": "feishu",
            "VTF_TRANSCRIBE_BATCH_SIZE_S": "120",
            "VTF_DOWNLOAD_RETRIES": "5",
        },
        overrides={},
    )
    assert cfg.output.sink == "feishu"
    assert cfg.transcribe.batch_size_s == 120
    assert cfg.download.retries == 5


def test_legacy_table_token_alias():
    cfg = load_config(
        user_path=None,
        project_path=None,
        env={"TABLE_TOKEN": "tok123", "TABLE_ID": "tbl456"},
        overrides={},
    )
    assert cfg.sink.feishu.base_token == "tok123"
    assert cfg.sink.feishu.table_id == "tbl456"


def test_overrides_have_highest_priority(tmp_path):
    user = tmp_path / "user.toml"
    user.write_text('[output]\nsink = "feishu"\n', encoding="utf-8")
    cfg = load_config(
        user_path=user,
        project_path=None,
        env={"VTF_OUTPUT_SINK": "feishu"},
        overrides={"output": {"sink": "markdown"}},
    )
    assert cfg.output.sink == "markdown"
