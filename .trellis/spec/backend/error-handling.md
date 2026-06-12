# Error Handling

> Executable error contracts for vtf command and integration boundaries.

---

## Scenario: yt-dlp Bilibili HTTP 412 diagnostics

### 1. Scope / Trigger

- Trigger: Changes that touch `vtf fetch`, `vtf download`, platform cookie handling, or yt-dlp subprocess error reporting.
- Reason: Bilibili commonly returns HTTP 412 when browser cookies are unavailable or stale. A raw yt-dlp stderr line is not enough for agents to recover; the CLI must tell the caller which VTF config knobs to change.

### 2. Signatures

- `fetch(url: str, cfg: Any) -> dict[str, Any]`
- `download(meta: dict[str, Any], cfg: Any, workdir: Path, keep_video=False) -> tuple[Path, Path | None]`
- `format_yt_dlp_error(action: str, returncode: int, stderr: str, platform: Platform) -> str`
- Platform cookie contract: `Platform.cookie_args(cfg) -> list[str]`

### 3. Contracts

- `fetch` and `download` must detect the platform before invoking yt-dlp.
- yt-dlp subprocess failures are raised as `RemoteError`.
- The shared formatter is the single place that appends platform-specific recovery hints.
- For Bilibili HTTP 412, the error message must mention:
  - `HTTP 412`
  - browser login / cookie availability
  - `platform.bilibili.cookies_from_browser`
  - `platform.bilibili.cookies_file`
- Non-Bilibili failures and non-412 Bilibili failures must preserve the original concise yt-dlp error without adding the 412 cookie hint.

### 4. Validation & Error Matrix

| Condition | Behavior |
|---|---|
| `yt-dlp` executable missing | Raise `EnvironmentError("yt-dlp 未找到...")` |
| Bilibili stderr contains HTTP 412 / Precondition Failed | Raise `RemoteError` with Bilibili cookie recovery hint |
| YouTube or generic platform returns 403/412 | Raise `RemoteError` without Bilibili-specific hint |
| Bilibili returns another yt-dlp error | Raise `RemoteError` with original action, return code, and stderr summary |

### 5. Good / Base / Bad Cases

- Good: Bilibili download returns `HTTP Error 412: Precondition Failed`; CLI output tells the user to confirm browser login, adjust `cookies_from_browser`, or configure `cookies_file`.
- Base: YouTube returns `HTTP Error 403`; CLI reports the remote failure without mentioning Bilibili or cookie config.
- Bad: `fetch` has a Bilibili-specific hint but `download` does not, or either command hardcodes separate hint text that drifts over time.

### 6. Tests Required

- Regression test for Bilibili `fetch` HTTP 412 including cookie config hints.
- Regression test for Bilibili `download` HTTP 412 including cookie config hints.
- Regression test that a non-Bilibili yt-dlp failure does not include the Bilibili hint.

### 7. Wrong vs Correct

#### Wrong

```python
if r.returncode != 0:
    raise RemoteError(f"yt-dlp 下载失败({r.returncode}):{r.stderr.strip()[:200]}")
```

This loses the actionable recovery path for the most common Bilibili failure.

#### Correct

```python
if r.returncode != 0:
    raise RemoteError(
        format_yt_dlp_error(
            action="下载",
            returncode=r.returncode,
            stderr=r.stderr,
            platform=platform,
        )
    )
```

Use the shared formatter so `fetch` and `download` stay behaviorally consistent.
