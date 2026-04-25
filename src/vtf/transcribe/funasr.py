from __future__ import annotations

import contextlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from vtf.errors import EnvironmentError as VtfEnvError
from vtf.errors import RemoteError

_TRANSCRIBE_TEMPLATE = r'''
import json, os
from funasr import AutoModel

with open({corr_path!r}) as f:
    corrections = json.load(f)

model = AutoModel(
    model={asr_model!r},
    vad_model={vad_model!r},
    punc_model={punc_model!r},
    disable_update=True,
)
result = model.generate(
    input={audio!r},
    batch_size_s={batch_size_s},
    sentence_timestamp=True,
)

sentences = []
for res in result:
    if "sentence_info" in res:
        for s in res["sentence_info"]:
            text = s["text"].strip()
            if text:
                sentences.append(text)

for i, s in enumerate(sentences):
    for wrong, right in corrections.items():
        sentences[i] = sentences[i].replace(wrong, right)

print("TRANSCRIPT_JSON_START")
print(json.dumps(sentences, ensure_ascii=False))
print("TRANSCRIPT_JSON_END")
'''


def find_funasr_python(cfg: Any) -> str | None:
    candidates: list[str] = []
    env_py = os.environ.get("VTF_TRANSCRIBE_FUNASR_PYTHON") or cfg.transcribe.funasr_python
    if env_py:
        candidates.append(env_py)
    candidates += [
        shutil.which("funasr") or "",
        shutil.which("python3") or "",
        shutil.which("python") or "",
    ]
    for c in candidates:
        if not c:
            continue
        try:
            r = subprocess.run([c, "-c", "import funasr"], capture_output=True, timeout=10)
        except (OSError, subprocess.SubprocessError):
            continue
        if r.returncode == 0:
            return c
    return None


def transcribe(*, audio_path: Path, cfg: Any) -> dict[str, Any]:
    py = find_funasr_python(cfg)
    if not py:
        raise VtfEnvError(
            "FunASR 未找到。请在某个 Python 环境中 `pip install funasr`,"
            "并通过 VTF_TRANSCRIBE_FUNASR_PYTHON 指向它"
        )
    corrections: dict[str, str] = {}
    if cfg.transcribe.corrections_file:
        try:
            with open(cfg.transcribe.corrections_file, encoding="utf-8") as f:
                corrections = json.load(f)
        except FileNotFoundError:
            pass
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(corrections, f, ensure_ascii=False)
        corr_path = f.name
    try:
        code = _TRANSCRIBE_TEMPLATE.format(
            corr_path=corr_path,
            asr_model=cfg.transcribe.asr_model,
            vad_model=cfg.transcribe.vad_model,
            punc_model=cfg.transcribe.punc_model,
            audio=str(audio_path),
            batch_size_s=cfg.transcribe.batch_size_s,
        )
        r = subprocess.run(
            [py, "-c", code], capture_output=True, text=True, timeout=1800
        )
    finally:
        with contextlib.suppress(OSError):
            os.unlink(corr_path)
    if r.returncode != 0:
        raise RemoteError(f"FunASR 转录失败({r.returncode}):{r.stderr.strip()[:300]}")
    sentences = _extract_marked_json(r.stdout)
    return {
        "audio_path": str(audio_path),
        "asr_model": cfg.transcribe.asr_model,
        "sentences": sentences,
    }


def _extract_marked_json(stdout: str) -> list[str]:
    start = stdout.find("TRANSCRIPT_JSON_START")
    end = stdout.find("TRANSCRIPT_JSON_END")
    if start >= 0 and end >= 0:
        body = stdout[start + len("TRANSCRIPT_JSON_START") : end].strip()
        return list(json.loads(body))
    return list(json.loads(stdout.strip()))


__all__ = ["find_funasr_python", "transcribe"]
