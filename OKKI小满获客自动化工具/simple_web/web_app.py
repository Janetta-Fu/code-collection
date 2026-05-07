from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import sqlite3
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Cookie, Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from openpyxl import Workbook

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from okki_trade_automation import AppConfig, OKKI_SMART_TRADE_URL, RESULT_COLUMNS, OkkiTradeAutomation


DEFAULT_DATA_ROOT = Path(os.environ.get("LOCALAPPDATA") or BASE_DIR)
DATA_DIR = Path(os.environ.get("OKKI_WEB_DATA_DIR") or (DEFAULT_DATA_ROOT / "OKKI自动获客" / "web_data"))
EXPORT_DIR = DATA_DIR / "exports"
PROFILE_DIR = DATA_DIR / "chrome_profiles"
HISTORY_DIR = DATA_DIR / "histories"
TEMPLATE_PROFILE_DIR = PROJECT_ROOT / "okki_chrome_profile"
DB_PATH = DATA_DIR / "web.db"
SECRET_KEY = os.environ.get("OKKI_WEB_SECRET", "please-change-this-secret")
MAX_WORKERS = int(os.environ.get("OKKI_WEB_MAX_WORKERS", "2"))

DATA_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)
PROFILE_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="OKKI 获客采集网页版")
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
stop_events: dict[int, threading.Event] = {}


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def seed_task_profile(profile_dir: Path) -> str:
    if profile_dir.exists() and any(profile_dir.iterdir()):
        return "reuse"
    profile_dir.mkdir(parents=True, exist_ok=True)
    if not TEMPLATE_PROFILE_DIR.exists():
        return "missing-template"
    try:
        shutil.copytree(
            TEMPLATE_PROFILE_DIR,
            profile_dir,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(
                "Singleton*",
                "LOCK",
                "lockfile",
                "*.lock",
                "Crashpad",
                "ShaderCache",
                "GrShaderCache",
                "GraphiteDawnCache",
                "Code Cache",
                "GPUCache",
                "BrowserMetrics",
                "component_crx_cache",
            ),
        )
        return "seeded"
    except Exception:
        return "seed-failed"


def should_retry_with_clean_profile(exc: Exception) -> bool:
    message = f"{type(exc).__name__}: {exc}".lower()
    return any(
        hint in message
        for hint in (
            "timed out receiving message from renderer",
            "timeout receiving message from renderer",
            "chrome not reachable",
            "target crashed",
            "session deleted because of page crash",
            "unable to discover open pages",
            "err_connection_closed",
            "connection refused",
        )
    )


def db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with db_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                is_admin INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                okki_username TEXT NOT NULL DEFAULT '',
                okki_password TEXT NOT NULL DEFAULT '',
                okki_cookie TEXT NOT NULL DEFAULT '',
                okki_smart_trade_url TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                product_name TEXT NOT NULL DEFAULT '',
                hs_code TEXT NOT NULL DEFAULT '',
                country TEXT NOT NULL DEFAULT '',
                min_amount REAL NOT NULL DEFAULT 5000,
                max_pages INTEGER NOT NULL DEFAULT 0,
                headless INTEGER NOT NULL DEFAULT 0,
                okki_username TEXT NOT NULL DEFAULT '',
                okki_password TEXT NOT NULL DEFAULT '',
                okki_cookie TEXT NOT NULL DEFAULT '',
                okki_smart_trade_url TEXT NOT NULL DEFAULT '',
                progress TEXT NOT NULL DEFAULT '',
                log_text TEXT NOT NULL DEFAULT '',
                result_count INTEGER NOT NULL DEFAULT 0,
                export_excel_path TEXT NOT NULL DEFAULT '',
                export_html_path TEXT NOT NULL DEFAULT '',
                export_dir TEXT NOT NULL DEFAULT '',
                error_message TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                started_at TEXT NOT NULL DEFAULT '',
                finished_at TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS task_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                task_id INTEGER NOT NULL,
                unique_key TEXT NOT NULL,
                row_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(user_id, unique_key),
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(task_id) REFERENCES tasks(id)
            );
            """
        )
        admin = conn.execute("SELECT id FROM users WHERE username = ?", ("admin",)).fetchone()
        if not admin:
            conn.execute(
                "INSERT INTO users(username, password_hash, is_admin, created_at) VALUES (?, ?, 1, ?)",
                ("admin", hash_password("admin123"), now_text()),
            )
        ensure_task_columns(conn)


def ensure_task_columns(conn: sqlite3.Connection) -> None:
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
    columns = {
        "okki_username": "TEXT NOT NULL DEFAULT ''",
        "okki_password": "TEXT NOT NULL DEFAULT ''",
        "okki_cookie": "TEXT NOT NULL DEFAULT ''",
        "okki_smart_trade_url": "TEXT NOT NULL DEFAULT ''",
        "export_dir": "TEXT NOT NULL DEFAULT ''",
    }
    for name, definition in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE tasks ADD COLUMN {name} {definition}")


def get_user_settings(user_id: int) -> Dict[str, str]:
    with db_conn() as conn:
        row = conn.execute("SELECT * FROM user_settings WHERE user_id = ?", (user_id,)).fetchone()
    if not row:
        return {
            "okki_username": "",
            "okki_password": "",
            "okki_cookie": "",
            "okki_smart_trade_url": OKKI_SMART_TRADE_URL,
        }
    return {
        "okki_username": row["okki_username"] or "",
        "okki_password": row["okki_password"] or "",
        "okki_cookie": row["okki_cookie"] or "",
        "okki_smart_trade_url": row["okki_smart_trade_url"] or OKKI_SMART_TRADE_URL,
    }


def save_user_settings(
    user_id: int,
    okki_username: str,
    okki_password: str,
    okki_cookie: str,
    okki_smart_trade_url: str,
) -> None:
    with db_conn() as conn:
        conn.execute(
            """
            INSERT INTO user_settings(user_id, okki_username, okki_password, okki_cookie, okki_smart_trade_url, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                okki_username = excluded.okki_username,
                okki_password = excluded.okki_password,
                okki_cookie = excluded.okki_cookie,
                okki_smart_trade_url = excluded.okki_smart_trade_url,
                updated_at = excluded.updated_at
            """,
            (
                user_id,
                okki_username,
                okki_password,
                okki_cookie,
                okki_smart_trade_url,
                now_text(),
            ),
        )


def hash_password(password: str, salt: Optional[str] = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, expected = stored.split("$", 1)
    except ValueError:
        return False
    actual = hash_password(password, salt).split("$", 1)[1]
    return hmac.compare_digest(actual, expected)


SESSION_COOKIE_NAME = "session_token"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 365


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    with db_conn() as conn:
        conn.execute(
            "INSERT INTO sessions(token, user_id, created_at) VALUES (?, ?, ?)",
            (token, user_id, now_text()),
        )
    return token


def create_guest_session() -> str:
    suffix = secrets.token_hex(4)
    username = f"访客-{suffix}"
    with db_conn() as conn:
        cur = conn.execute(
            "INSERT INTO users(username, password_hash, is_admin, created_at) VALUES (?, ?, 0, ?)",
            (username, hash_password(secrets.token_urlsafe(12)), now_text()),
        )
        user_id = int(cur.lastrowid)
    return create_session(user_id)


def user_for_session(token: str) -> Optional[sqlite3.Row]:
    if not token:
        return None
    with db_conn() as conn:
        return conn.execute(
            """
            SELECT users.* FROM users
            JOIN sessions ON sessions.user_id = users.id
            WHERE sessions.token = ?
            """,
            (token,),
        ).fetchone()


@app.middleware("http")
async def auto_guest_session(request: Request, call_next):
    token = request.cookies.get(SESSION_COOKIE_NAME) or ""
    needs_cookie = False
    if not user_for_session(token):
        token = create_guest_session()
        needs_cookie = True
        request.state.session_token = token
    else:
        request.state.session_token = token
    response = await call_next(request)
    if needs_cookie:
        response.set_cookie(
            SESSION_COOKIE_NAME,
            token,
            httponly=True,
            samesite="lax",
            max_age=SESSION_MAX_AGE_SECONDS,
        )
    return response


def get_current_user(request: Request, session_token: str | None = Cookie(default=None)) -> sqlite3.Row:
    token = session_token or getattr(request.state, "session_token", "")
    if not token:
        token = create_guest_session()
    user = user_for_session(token)
    if not user:
        token = create_guest_session()
        user = user_for_session(token)
    if not user:
        raise HTTPException(status_code=401, detail="无法创建本地使用人")
    return user


def require_user_or_redirect(request: Request) -> Optional[sqlite3.Row]:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None
    try:
        return user_for_session(token)
    except HTTPException:
        return None


def page(title: str, body: str, user: Optional[sqlite3.Row] = None, refresh_seconds: int = 0) -> HTMLResponse:
    refresh = f'<meta http-equiv="refresh" content="{refresh_seconds}">' if refresh_seconds else ""
    username = escape(user["username"]) if user else ""
    nav = ""
    if user:
        nav = f"""
        <aside>
          <div class="brand">OKKI Web</div>
          <a href="/tasks">任务列表</a>
          <a href="/tasks/new">新建采集</a>
          <div class="user">本机使用人：{username}<br>无需网页登录密码</div>
        </aside>
        """
    html = f"""
    <!doctype html>
    <html lang="zh-CN">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      {refresh}
      <title>{escape(title)}</title>
      <style>
        body {{ margin:0; font-family: Arial, "Microsoft YaHei", sans-serif; background:#f5f7fb; color:#172033; }}
        a {{ color:#1f66d1; text-decoration:none; }}
        .layout {{ display:flex; min-height:100vh; }}
        aside {{ width:220px; background:#111b3d; color:#fff; padding:22px 18px; box-sizing:border-box; }}
        aside a {{ display:block; color:#dbe6ff; padding:10px 12px; margin:6px 0; border-radius:8px; }}
        aside a:hover {{ background:#1e2b5c; }}
        .brand {{ font-size:22px; font-weight:700; margin-bottom:22px; }}
        .user {{ color:#9fb1df; font-size:13px; margin-top:24px; line-height:1.6; }}
        main {{ flex:1; padding:28px; }}
        .card {{ background:#fff; border:1px solid #e4e8f0; border-radius:10px; padding:22px; box-shadow:0 8px 24px rgba(20,35,80,.05); margin-bottom:18px; }}
        h1 {{ margin:0 0 18px; font-size:24px; }}
        label {{ display:block; font-weight:600; margin:14px 0 6px; }}
        input, select, textarea {{ width:100%; box-sizing:border-box; border:1px solid #cfd6e4; border-radius:8px; padding:10px 12px; font-size:14px; }}
        button, .btn {{ display:inline-block; border:0; border-radius:8px; background:#1f66d1; color:#fff; padding:10px 16px; cursor:pointer; font-size:14px; }}
        .btn.secondary {{ background:#68758f; }}
        .btn.danger {{ background:#c93333; }}
        .btn.linklike {{ font-family:inherit; vertical-align:baseline; }}
        table {{ width:100%; border-collapse:collapse; background:#fff; }}
        th, td {{ border-bottom:1px solid #e8edf5; padding:10px; text-align:left; font-size:14px; vertical-align:top; }}
        th {{ color:#5b6780; background:#f8fafd; }}
        .grid {{ display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:14px 20px; }}
        .status {{ padding:4px 8px; border-radius:999px; background:#eef2ff; color:#234; font-size:12px; }}
        .hint {{ color:#5b6780; font-size:14px; line-height:1.6; }}
        .log {{ white-space:pre-wrap; background:#0d1324; color:#dbe6ff; border-radius:8px; padding:14px; max-height:360px; overflow:auto; }}
        .error {{ color:#b42318; }}
        .login {{ max-width:420px; margin:8vh auto; }}
        @media (max-width: 800px) {{ .layout {{ display:block; }} aside {{ width:auto; }} .grid {{ grid-template-columns:1fr; }} }}
      </style>
    </head>
    <body>
      <div class="layout">
        {nav}
        <main>{body}</main>
      </div>
      <script>
        async function saveExportFile(url, filename) {{
          if (!("showSaveFilePicker" in window)) {{
            alert("当前浏览器不支持直接选择保存路径。请在浏览器下载设置中开启“下载前询问每个文件的保存位置”，随后将使用普通下载。");
            window.location.href = url;
            return;
          }}

          try {{
            const response = await fetch(url, {{ credentials: "same-origin" }});
            if (!response.ok) {{
              alert("文件下载失败，请刷新页面后重试。");
              return;
            }}

            const blob = await response.blob();
            const extension = filename.toLowerCase().endsWith(".html") ? ".html" : ".xlsx";
            const pickerOptions = {{
              suggestedName: filename,
              types: [{{
                description: extension === ".html" ? "HTML 文件" : "Excel 文件",
                accept: extension === ".html"
                  ? {{ "text/html": [".html"] }}
                  : {{ "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx", ".xls"] }},
              }}],
            }};
            const handle = await window.showSaveFilePicker(pickerOptions);
            const writable = await handle.createWritable();
            await writable.write(blob);
            await writable.close();
          }} catch (error) {{
            if (error && error.name === "AbortError") return;
            alert("保存失败，请重试或改用浏览器普通下载。");
          }}
        }}

        document.addEventListener("click", function(event) {{
          const button = event.target.closest("[data-save-url]");
          if (!button) return;
          event.preventDefault();
          saveExportFile(button.dataset.saveUrl, button.dataset.filename || "export.xlsx");
        }});

        function clearUnsavedOkkiAutofill() {{
          document.querySelectorAll("[data-clear-unsaved-okki='1']").forEach(function(field) {{
            if (field.dataset.userEdited === "1") return;
            field.value = "";
          }});
        }}
        document.addEventListener("DOMContentLoaded", function() {{
          document.querySelectorAll("[data-clear-unsaved-okki='1']").forEach(function(field) {{
            field.addEventListener("input", function() {{
              field.dataset.userEdited = "1";
            }});
          }});
          clearUnsavedOkkiAutofill();
          setTimeout(clearUnsavedOkkiAutofill, 150);
          setTimeout(clearUnsavedOkkiAutofill, 700);
          setTimeout(clearUnsavedOkkiAutofill, 1600);
          setTimeout(clearUnsavedOkkiAutofill, 3000);
        }});
      </script>
    </body>
    </html>
    """
    return HTMLResponse(html)


def redirect(path: str) -> RedirectResponse:
    return RedirectResponse(path, status_code=303)


def task_owned(task_id: int, user_id: int) -> sqlite3.Row:
    with db_conn() as conn:
        task = conn.execute("SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id)).fetchone()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


def export_action_buttons(task: sqlite3.Row, compact: bool = False) -> str:
    task_id = task["id"]
    pieces = []
    prefix = "" if compact else "下载 "
    excel_name = escape(export_filename(task, "xlsx"))
    html_name = escape(export_filename(task, "html"))
    pieces.append(
        f'<button class="btn linklike" type="button" data-save-url="/download/{task_id}/excel" '
        f'data-filename="{excel_name}">{prefix}Excel</button>'
    )
    pieces.append(
        f'<button class="btn secondary linklike" type="button" data-save-url="/download/{task_id}/html" '
        f'data-filename="{html_name}">{prefix}HTML</button>'
    )
    separator = " " if compact else "\n        "
    return separator.join(pieces)


def safe_filename_part(value: Any, fallback: str) -> str:
    text = str(value or "").strip() or fallback
    text = re.sub(r'[\\/:*?"<>|\r\n]+', "_", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text[:80] or fallback


def export_filename(task: sqlite3.Row, extension: str) -> str:
    product = safe_filename_part(task["product_name"] or task["hs_code"], "OKKI采集")
    country = safe_filename_part(task["country"], "全部国家")
    return f"{product}-{country}-历史数据.{extension}"


def condition_result_dicts(task: sqlite3.Row) -> list[Dict[str, Any]]:
    with db_conn() as conn:
        rows = condition_rows_for_task(conn, task)
    result_rows = []
    seen = set()
    for item in rows:
        try:
            row = json.loads(item["row_json"])
        except json.JSONDecodeError:
            continue
        key = json.dumps(row, ensure_ascii=False, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        result_rows.append(row)
    return result_rows


def generate_excel_export(task: sqlite3.Row, output_path: Path) -> None:
    rows = condition_result_dicts(task)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "采集结果"
    worksheet.append(list(RESULT_COLUMNS))
    for row in rows:
        worksheet.append([str(row.get(column, "") or "") for column in RESULT_COLUMNS])
    workbook.save(output_path)
    workbook.close()


def render_export_html(task: sqlite3.Row, rows: list[Dict[str, Any]]) -> str:
    sections = []
    for index, row in enumerate(rows, start=1):
        title = escape(str(row.get("公司名称") or f"结果 {index}"))
        cells = []
        for column in RESULT_COLUMNS:
            cells.append(
                "<tr>"
                f"<th>{escape(str(column))}</th>"
                f"<td>{escape(str(row.get(column, '') or ''))}</td>"
                "</tr>"
            )
        sections.append(f"<section><h2>{index}. {title}</h2><table>{''.join(cells)}</table></section>")
    empty = "<p>当前还没有采集到数据。</p>" if not sections else ""
    condition = f"产品 {task['product_name'] or '-'} / HS {task['hs_code'] or '-'} / 国家 {task['country'] or '-'}"
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>OKKI 采集历史数据</title>
  <style>
    body {{ margin:24px; font-family:Arial, "Microsoft YaHei", sans-serif; color:#172033; background:#f5f7fb; }}
    h1 {{ font-size:22px; }}
    h2 {{ font-size:16px; margin-top:22px; }}
    table {{ width:100%; border-collapse:collapse; background:#fff; margin-bottom:18px; }}
    th, td {{ border:1px solid #e4e8f0; padding:8px 10px; text-align:left; vertical-align:top; }}
    th {{ width:180px; background:#f8fafd; }}
  </style>
</head>
<body>
  <h1>OKKI 采集历史数据</h1>
  <p>{escape(condition)}</p>
  <p>导出时间：{escape(now_text())}；数据条数：{len(rows)}</p>
  {empty}
  {''.join(sections)}
</body>
</html>
"""


def generate_html_export(task: sqlite3.Row, output_path: Path) -> None:
    rows = condition_result_dicts(task)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_export_html(task, rows), encoding="utf-8")


def ensure_download_file(task: sqlite3.Row, kind: str) -> Path:
    existing = task["export_excel_path"] if kind == "excel" else task["export_html_path"] if kind == "html" else ""
    if existing and Path(existing).exists():
        return Path(existing)
    if kind not in {"excel", "html"}:
        raise HTTPException(status_code=404, detail="不支持的下载类型")
    task_dir = EXPORT_DIR / f"user_{task['user_id']}" / f"task_{task['id']}"
    extension = "xlsx" if kind == "excel" else "html"
    output_path = task_dir / export_filename(task, extension)
    if kind == "excel":
        generate_excel_export(task, output_path)
        column = "export_excel_path"
    else:
        generate_html_export(task, output_path)
        column = "export_html_path"
    with db_conn() as conn:
        conn.execute(f"UPDATE tasks SET {column} = ? WHERE id = ?", (str(output_path), task["id"]))
    return output_path


def append_task_log(task_id: int, message: str) -> None:
    message = str(message)
    with db_conn() as conn:
        row = conn.execute("SELECT log_text FROM tasks WHERE id = ?", (task_id,)).fetchone()
        old = row["log_text"] if row else ""
        new_log = (old + f"[{now_text()}] {message}\n")[-20000:]
        conn.execute(
            "UPDATE tasks SET progress = ?, log_text = ? WHERE id = ?",
            (message[-1000:], new_log, task_id),
        )


def normalize_condition_value(value: Any) -> str:
    return str(value or "").strip().lower()


def normalize_amount(value: Any) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "0.00"


def task_condition_values(task: sqlite3.Row) -> Dict[str, str]:
    return {
        "product_name": normalize_condition_value(task["product_name"]),
        "hs_code": normalize_condition_value(task["hs_code"]),
        "country": normalize_condition_value(task["country"]),
        "min_amount": normalize_amount(task["min_amount"]),
    }


def condition_hash(user_id: int, product_name: str, hs_code: str, country: str, min_amount: Any) -> str:
    raw = "|".join(
        [
            str(user_id),
            normalize_condition_value(product_name),
            normalize_condition_value(hs_code),
            normalize_condition_value(country),
            normalize_amount(min_amount),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def task_condition_hash(task: sqlite3.Row) -> str:
    return condition_hash(task["user_id"], task["product_name"], task["hs_code"], task["country"], task["min_amount"])


def condition_rows_for_task(conn: sqlite3.Connection, task: sqlite3.Row) -> list[sqlite3.Row]:
    values = task_condition_values(task)
    return conn.execute(
        """
        SELECT tr.row_json
        FROM task_results tr
        JOIN tasks t ON t.id = tr.task_id
        WHERE tr.user_id = ?
          AND lower(trim(t.product_name)) = ?
          AND lower(trim(t.hs_code)) = ?
          AND lower(trim(t.country)) = ?
          AND printf('%.2f', t.min_amount) = ?
        ORDER BY tr.id ASC
        """,
        (
            task["user_id"],
            values["product_name"],
            values["hs_code"],
            values["country"],
            values["min_amount"],
        ),
    ).fetchall()


def count_condition_results(conn: sqlite3.Connection, task: sqlite3.Row) -> int:
    return len(condition_rows_for_task(conn, task))


def same_condition_tasks(conn: sqlite3.Connection, task: sqlite3.Row) -> list[sqlite3.Row]:
    values = task_condition_values(task)
    return conn.execute(
        """
        SELECT *
        FROM tasks
        WHERE user_id = ?
          AND lower(trim(product_name)) = ?
          AND lower(trim(hs_code)) = ?
          AND lower(trim(country)) = ?
          AND printf('%.2f', min_amount) = ?
        ORDER BY id DESC
        """,
        (
            task["user_id"],
            values["product_name"],
            values["hs_code"],
            values["country"],
            values["min_amount"],
        ),
    ).fetchall()


def migrate_legacy_incremental_state(task: sqlite3.Row, history_dir: Path) -> None:
    target = history_dir / "incremental_state.json"
    if target.exists():
        return
    with db_conn() as conn:
        candidates = same_condition_tasks(conn, task)
    for candidate in candidates:
        legacy_path = EXPORT_DIR / f"user_{candidate['user_id']}" / f"task_{candidate['id']}" / "incremental_state.json"
        if legacy_path.exists():
            shutil.copy2(legacy_path, target)
            append_task_log(task["id"], f"已识别同条件历史状态，继续沿用：任务 #{candidate['id']}")
            return


def make_result_key(user_id: int, task: sqlite3.Row, row: Dict[str, Any]) -> str:
    parts = [
        str(user_id),
        task["product_name"].strip().lower(),
        task["hs_code"].strip().lower(),
        task["country"].strip().lower(),
        str(task["min_amount"]),
        str(row.get("公司名称", "")).strip().lower(),
        str(row.get("官网地址", "")).strip().lower(),
        str(row.get("贸易记录金额", "")).strip().lower(),
        str(row.get("搜索关键词", "")).strip().lower(),
    ]
    return "|".join(parts)


def insert_task_result(task_id: int, row: Dict[str, Any], excel_path: str = "", html_path: str = "") -> bool:
    with db_conn() as conn:
        task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not task:
            return False
        key = make_result_key(task["user_id"], task, row)
        inserted = False
        try:
            conn.execute(
                """
                INSERT INTO task_results(user_id, task_id, unique_key, row_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (task["user_id"], task_id, key, json.dumps(row, ensure_ascii=False), now_text()),
            )
            inserted = True
        except sqlite3.IntegrityError:
            pass
        result_count = count_condition_results(conn, task)
        conn.execute(
            """
            UPDATE tasks
            SET result_count = ?,
                export_excel_path = CASE WHEN ? != '' THEN ? ELSE export_excel_path END,
                export_html_path = CASE WHEN ? != '' THEN ? ELSE export_html_path END
            WHERE id = ?
            """,
            (result_count, excel_path, excel_path, html_path, html_path, task_id),
        )
        return inserted


def run_collection_task(task_id: int) -> None:
    with db_conn() as conn:
        task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not task:
        return

    stop_event = stop_events.setdefault(task_id, threading.Event())
    with db_conn() as conn:
        conn.execute(
            "UPDATE tasks SET status = 'running', started_at = ?, progress = ? WHERE id = ?",
            (now_text(), "正在启动采集任务", task_id),
        )

    history_key = task_condition_hash(task)
    history_dir = HISTORY_DIR / f"user_{task['user_id']}" / history_key
    task_dir = EXPORT_DIR / f"user_{task['user_id']}" / f"task_{task_id}"
    custom_export_dir = Path(str(task["export_dir"] or "").strip()) if "export_dir" in task.keys() and str(task["export_dir"] or "").strip() else None
    output_dir = custom_export_dir or task_dir
    profile_dir = PROFILE_DIR / f"user_{task['user_id']}_task_{task_id}"
    history_dir.mkdir(parents=True, exist_ok=True)
    task_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    migrate_legacy_incremental_state(task, history_dir)
    profile_dir.mkdir(parents=True, exist_ok=True)
    append_task_log(task_id, f"已为当前任务创建独立浏览器环境：{profile_dir}")

    collector_holder: Dict[str, OkkiTradeAutomation] = {}

    def on_live_result(row: Dict[str, Any]) -> None:
        collector = collector_holder.get("collector")
        excel_path = collector.export_excel_path if collector else ""
        html_path = collector.export_html_path if collector else ""
        insert_task_result(task_id, row, excel_path, html_path)

    def build_collector(run_profile_dir: Path) -> OkkiTradeAutomation:
        config = AppConfig(
            okki_username=task["okki_username"] or "",
            okki_password=task["okki_password"] or "",
            cookie_string=task["okki_cookie"] or "",
            okki_smart_trade_url=task["okki_smart_trade_url"] or OKKI_SMART_TRADE_URL,
            product_name=task["product_name"],
            hs_code=task["hs_code"],
            country=task["country"],
            min_amount_threshold=float(task["min_amount"]),
            max_pages=int(task["max_pages"]),
            headless=bool(task["headless"]),
            auto_export=True,
            output_excel_path=str(output_dir),
            output_html_path=str(output_dir),
            chrome_user_data_dir=str(run_profile_dir),
            incremental_state_path=str(history_dir / "incremental_state.json"),
        )
        collector = OkkiTradeAutomation(
            config=config,
            logger=lambda msg: append_task_log(task_id, msg),
            stop_event=stop_event,
            on_result=on_live_result,
        )
        collector_holder["collector"] = collector
        submitted_country = str(task["country"] or "").strip()
        collector.build_country_run_plan = lambda: [submitted_country] if submitted_country else [""]
        return collector

    try:
        collector = build_collector(profile_dir)
        try:
            rows = collector.run()
        except Exception as exc:
            if should_retry_with_clean_profile(exc) and not stop_event.is_set():
                append_task_log(task_id, "检测到 Chrome 渲染超时，改用干净任务浏览器环境自动重试一次。")
                try:
                    shutil.rmtree(profile_dir, ignore_errors=True)
                except Exception:
                    pass
                profile_dir.mkdir(parents=True, exist_ok=True)
                collector = build_collector(profile_dir)
                rows = collector.run()
            else:
                raise
        inserted = 0
        with db_conn() as conn:
            fresh_task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            for row in rows:
                if insert_task_result(
                    task_id,
                    row,
                    collector.export_excel_path or "",
                    collector.export_html_path or "",
                ):
                    inserted += 1
            total_results = count_condition_results(conn, fresh_task)
            finished_message = f"任务完成，累计 {total_results} 条结果，本次新增 {inserted} 条"
            if total_results <= 0 and str(fresh_task["country"] or "").strip():
                finished_message = f"任务完成，但采购商国家/地区【{fresh_task['country']}】没有采集到可用信息"
            conn.execute(
                """
                UPDATE tasks
                SET status = 'success',
                    result_count = ?,
                    export_excel_path = ?,
                    export_html_path = ?,
                    progress = ?,
                    finished_at = ?
                WHERE id = ?
                """,
                (
                    total_results,
                    collector.export_excel_path or "",
                    collector.export_html_path or "",
                    finished_message,
                    now_text(),
                    task_id,
                ),
            )
    except Exception as exc:
        status = "stopped" if stop_event.is_set() else "failed"
        message = f"{type(exc).__name__}: {str(exc)[:1000]}"
        with db_conn() as conn:
            conn.execute(
                "UPDATE tasks SET status = ?, error_message = ?, progress = ?, finished_at = ? WHERE id = ?",
                (status, message, message, now_text(), task_id),
            )
        append_task_log(task_id, message)
    finally:
        stop_events.pop(task_id, None)


@app.on_event("startup")
def startup() -> None:
    init_db()
    with db_conn() as conn:
        conn.execute(
            """
            UPDATE tasks
            SET status = 'stopped',
                progress = '服务已重新启动，原后台任务已停止，可点击继续采集',
                finished_at = ?
            WHERE status = 'running'
            """,
            (now_text(),),
        )


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return redirect("/tasks")


@app.get("/login", response_class=HTMLResponse)
def login_page():
    return redirect("/tasks")


@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    return redirect("/tasks")


@app.get("/logout")
def logout(session_token: str | None = Cookie(default=None)):
    return redirect("/tasks")


@app.get("/tasks", response_class=HTMLResponse)
def tasks_page(user: sqlite3.Row = Depends(get_current_user)):
    with db_conn() as conn:
        tasks = conn.execute(
            "SELECT * FROM tasks WHERE user_id = ? ORDER BY id DESC LIMIT 100",
            (user["id"],),
        ).fetchall()
    rows = "".join(
        f"""
        <tr>
          <td>#{task['id']}</td>
          <td>{escape(task['product_name'] or '-')}</td>
          <td>{escape(task['hs_code'] or '-')}</td>
          <td>{escape(task['country'] or '-')}</td>
          <td><span class="status">{escape(task['status'])}</span></td>
          <td>{escape(task['progress'] or '-')}</td>
          <td>{task['result_count']}</td>
          <td>
            <a href="/tasks/{task['id']}">详情</a>
            {export_action_buttons(task, compact=True)}
          </td>
        </tr>
        """
        for task in tasks
    )
    body = f"""
    <div class="card">
      <h1>我的采集任务</h1>
      <p><a class="btn" href="/tasks/new">新建采集任务</a></p>
      <table>
        <thead><tr><th>ID</th><th>产品</th><th>HS</th><th>采购商国家</th><th>状态</th><th>进度</th><th>结果</th><th>操作</th></tr></thead>
        <tbody>{rows or '<tr><td colspan="8">暂无任务</td></tr>'}</tbody>
      </table>
    </div>
    """
    return page("任务列表", body, user=user, refresh_seconds=8)


@app.get("/tasks/new", response_class=HTMLResponse)
def new_task_page(user: sqlite3.Row = Depends(get_current_user)):
    settings = get_user_settings(user["id"])
    has_saved_okki = bool(settings["okki_username"] or settings["okki_password"] or settings["okki_cookie"])
    clear_unsaved_attr = "" if has_saved_okki else ' data-clear-unsaved-okki="1"'
    saved_cookie_hint = "已保存 Cookie，留空沿用；需要更新时粘贴新的 Cookie" if settings["okki_cookie"] else "从浏览器复制 Cookie 字符串，可留空"
    body = f"""
    <div class="card">
      <h1>新建采集任务</h1>
      <form method="post" action="/tasks/new" autocomplete="off">
        <input type="text" name="browser_dummy_username" autocomplete="username" style="position:absolute;left:-9999px;width:1px;height:1px;opacity:0" tabindex="-1">
        <input type="password" name="browser_dummy_password" autocomplete="current-password" style="position:absolute;left:-9999px;width:1px;height:1px;opacity:0" tabindex="-1">
        <div class="grid">
          <div>
            <label>产品名称</label>
            <input name="product_name" placeholder="例如 tomato paste">
          </div>
          <div>
            <label>HS 编码</label>
            <input name="hs_code" placeholder="例如 007985">
          </div>
          <div>
            <label>采购商国家/地区</label>
            <input name="country" placeholder="例如 马来西亚">
          </div>
          <div>
            <label>最低金额阈值</label>
            <input name="min_amount" type="number" step="100" value="10000">
          </div>
          <div>
            <label>最大翻页数（0=全部）</label>
            <input name="max_pages" type="number" min="0" value="0">
          </div>
          <div>
            <label>无头模式</label>
            <select name="headless">
              <option value="0" selected>否，显示浏览器（可最小化查看）</option>
              <option value="1">是，完全后台运行</option>
            </select>
          </div>
        </div>
        <h1 style="margin-top:28px">OKKI 登录配置</h1>
        <p class="hint">首次使用请填写自己的 OKKI 账号配置；提交后会只保存到当前浏览器身份，后续新建任务会自动带出。</p>
        <div class="grid">
          <div>
            <label>OKKI 账号</label>
            <input name="okki_username" value="{escape(settings['okki_username'])}" placeholder="OKKI 登录账号" autocomplete="new-password" autocapitalize="off" spellcheck="false"{clear_unsaved_attr}>
          </div>
          <div>
            <label>OKKI 密码</label>
            <input name="okki_password" type="password" value="{escape(settings['okki_password'])}" placeholder="OKKI 登录密码" autocomplete="new-password"{clear_unsaved_attr}>
          </div>
          <div>
            <label>智能贸易数据 URL</label>
            <input name="okki_smart_trade_url" value="{escape(settings['okki_smart_trade_url'])}">
          </div>
          <div>
            <label>Cookie（可选，留空则账号密码登录）</label>
            <textarea name="okki_cookie" rows="4" placeholder="{escape(saved_cookie_hint)}" autocomplete="off"></textarea>
          </div>
        </div>
        <p><button type="submit">提交任务</button></p>
      </form>
    </div>
    """
    return page("新建任务", body, user=user)


@app.post("/tasks/new")
def create_task(
    product_name: str = Form(""),
    hs_code: str = Form(""),
    country: str = Form(""),
    min_amount: float = Form(10000),
    max_pages: int = Form(0),
    headless: int = Form(0),
    export_dir: str = Form(""),
    okki_username: str = Form(""),
    okki_password: str = Form(""),
    okki_cookie: str = Form(""),
    okki_smart_trade_url: str = Form(""),
    user: sqlite3.Row = Depends(get_current_user),
):
    if not product_name.strip() and not hs_code.strip():
        raise HTTPException(status_code=400, detail="产品名称和 HS 编码至少填写一个")
    settings = get_user_settings(user["id"])
    submitted_username = okki_username.strip()
    submitted_password = okki_password.strip()
    submitted_cookie = okki_cookie.strip()
    submitted_url = okki_smart_trade_url.strip()
    resolved_username = submitted_username or settings["okki_username"]
    resolved_password = submitted_password or settings["okki_password"]
    resolved_url = submitted_url or settings["okki_smart_trade_url"] or OKKI_SMART_TRADE_URL
    same_saved_login = (
        resolved_username == settings["okki_username"]
        and resolved_password == settings["okki_password"]
        and resolved_url == settings["okki_smart_trade_url"]
    )
    resolved_cookie = submitted_cookie or (settings["okki_cookie"] if same_saved_login else "")
    if not resolved_cookie and (not resolved_username or not resolved_password):
        raise HTTPException(status_code=400, detail="首次使用请填写 OKKI 账号和密码，或填写 Cookie")
    save_user_settings(
        user["id"],
        resolved_username,
        resolved_password,
        resolved_cookie,
        resolved_url,
    )
    with db_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO tasks(
                user_id, status, product_name, hs_code, country, min_amount, max_pages, headless,
                okki_username, okki_password, okki_cookie, okki_smart_trade_url,
                export_dir, progress, created_at
            )
            VALUES (?, 'pending', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '等待后台执行', ?)
            """,
            (
                user["id"],
                product_name.strip(),
                hs_code.strip(),
                country.strip(),
                float(min_amount),
                int(max_pages),
                int(headless),
                resolved_username,
                resolved_password,
                resolved_cookie,
                resolved_url,
                "",
                now_text(),
            ),
        )
        task_id = int(cur.lastrowid)
        task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        historical_count = count_condition_results(conn, task)
        if historical_count:
            conn.execute(
                "UPDATE tasks SET result_count = ?, progress = ? WHERE id = ?",
                (historical_count, f"已识别同条件历史数据 {historical_count} 条，等待后台继续采集", task_id),
            )
    executor.submit(run_collection_task, task_id)
    return redirect(f"/tasks/{task_id}")


@app.get("/tasks/{task_id}", response_class=HTMLResponse)
def task_detail(task_id: int, user: sqlite3.Row = Depends(get_current_user)):
    task = task_owned(task_id, user["id"])
    with db_conn() as conn:
        results = list(reversed(condition_rows_for_task(conn, task)[-20:]))
    result_rows = ""
    for item in results:
        row = json.loads(item["row_json"])
        result_rows += f"""
        <tr>
          <td>{escape(str(row.get('公司名称', '-')))}</td>
          <td>{escape(str(row.get('联系电话', '-')))}</td>
          <td>{escape(str(row.get('邮箱', '-')))}</td>
          <td>{escape(str(row.get('官网地址', '-')))}</td>
          <td>{escape(str(row.get('所在国家', '-')))}</td>
        </tr>
        """
    stop_button = ""
    if task["status"] in {"pending", "running"}:
        stop_button = f'<form method="post" action="/tasks/{task_id}/stop" style="display:inline"><button class="danger" type="submit">停止任务</button></form>'
    resume_button = ""
    if task["status"] in {"stopped", "failed"}:
        resume_button = f'<form method="post" action="/tasks/{task_id}/resume" style="display:inline"><button type="submit">继续采集</button></form>'
    empty_country_alert = ""
    if task["status"] == "success" and int(task["result_count"] or 0) <= 0 and str(task["country"] or "").strip():
        alert_text = f"采购商国家/地区【{task['country']}】没有可采集的信息，请更换国家或留空国家后重试。"
        empty_country_alert = f"""
        <script>
          const alertKey = "okki-empty-country-task-{task_id}";
          if (!localStorage.getItem(alertKey)) {{
            alert({json.dumps(alert_text, ensure_ascii=False)});
            localStorage.setItem(alertKey, "1");
          }}
        </script>
        """
    body = f"""
    {empty_country_alert}
    <div class="card">
      <h1>任务 #{task_id}</h1>
      <p>状态：<span class="status">{escape(task['status'])}</span></p>
      <p>条件：产品 {escape(task['product_name'] or '-')} / HS {escape(task['hs_code'] or '-')} / 国家 {escape(task['country'] or '-')}</p>
      <p>进度：{escape(task['progress'] or '-')}</p>
      <p class="error">{escape(task['error_message'] or '')}</p>
      <p>
        <a class="btn secondary" href="/tasks">返回列表</a>
        {stop_button}
        {resume_button}
        {export_action_buttons(task)}
      </p>
    </div>
    <div class="card">
      <h1>日志</h1>
      <div class="log">{escape(task['log_text'] or '暂无日志')}</div>
    </div>
    <div class="card">
      <h1>最近结果</h1>
      <table>
        <thead><tr><th>公司</th><th>电话</th><th>邮箱</th><th>官网</th><th>国家</th></tr></thead>
        <tbody>{result_rows or '<tr><td colspan="5">暂无入库结果，任务完成后显示。</td></tr>'}</tbody>
      </table>
    </div>
    """
    refresh = 5 if task["status"] in {"pending", "running"} else 0
    return page(f"任务 #{task_id}", body, user=user, refresh_seconds=refresh)


@app.post("/tasks/{task_id}/stop")
def stop_task(task_id: int, user: sqlite3.Row = Depends(get_current_user)):
    task_owned(task_id, user["id"])
    event = stop_events.get(task_id)
    if event:
        event.set()
        with db_conn() as conn:
            conn.execute("UPDATE tasks SET progress = ? WHERE id = ?", ("已请求停止，等待当前步骤结束", task_id))
    else:
        with db_conn() as conn:
            conn.execute(
                "UPDATE tasks SET status = 'stopped', progress = ?, finished_at = ? WHERE id = ?",
                ("后台任务已停止，可点击继续采集", now_text(), task_id),
            )
    return redirect(f"/tasks/{task_id}")


@app.post("/tasks/{task_id}/resume")
def resume_task(task_id: int, user: sqlite3.Row = Depends(get_current_user)):
    task = task_owned(task_id, user["id"])
    if task["status"] in {"pending", "running"}:
        return redirect(f"/tasks/{task_id}")
    stop_events.pop(task_id, None)
    with db_conn() as conn:
        conn.execute(
            """
            UPDATE tasks
            SET status = 'pending',
                progress = ?,
                error_message = '',
                finished_at = ''
            WHERE id = ?
            """,
            ("等待继续采集，将沿用相同条件的历史数据", task_id),
        )
    executor.submit(run_collection_task, task_id)
    return redirect(f"/tasks/{task_id}")


@app.get("/download/{task_id}/{kind}")
def download(task_id: int, kind: str, user: sqlite3.Row = Depends(get_current_user)):
    task = task_owned(task_id, user["id"])
    path = ensure_download_file(task, kind)
    return FileResponse(path, filename=path.name)


@app.get("/password", response_class=HTMLResponse)
def password_page(user: sqlite3.Row = Depends(get_current_user)):
    body = """
    <div class="card">
      <h1>修改密码</h1>
      <form method="post" action="/password">
        <label>旧密码</label>
        <input name="old_password" type="password" required>
        <label>新密码</label>
        <input name="new_password" type="password" required>
        <p><button type="submit">保存</button></p>
      </form>
    </div>
    """
    return page("修改密码", body, user=user)


@app.post("/password")
def change_password(
    old_password: str = Form(...),
    new_password: str = Form(...),
    user: sqlite3.Row = Depends(get_current_user),
):
    if not verify_password(old_password, user["password_hash"]):
        return page("修改密码", '<div class="card"><p class="error">旧密码错误。</p><a href="/password">返回</a></div>', user=user)
    with db_conn() as conn:
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(new_password), user["id"]))
    return redirect("/tasks")


@app.get("/admin/users", response_class=HTMLResponse)
def users_page(user: sqlite3.Row = Depends(get_current_user)):
    if not user["is_admin"]:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    with db_conn() as conn:
        users = conn.execute("SELECT id, username, is_admin, created_at FROM users ORDER BY id DESC").fetchall()
    rows = "".join(
        f"<tr><td>{u['id']}</td><td>{escape(u['username'])}</td><td>{'是' if u['is_admin'] else '否'}</td><td>{escape(u['created_at'])}</td></tr>"
        for u in users
    )
    body = f"""
    <div class="card">
      <h1>用户管理</h1>
      <form method="post" action="/admin/users">
        <div class="grid">
          <div><label>账号</label><input name="username" required></div>
          <div><label>密码</label><input name="password" type="password" required></div>
          <div><label>权限</label><select name="is_admin"><option value="0">普通用户</option><option value="1">管理员</option></select></div>
        </div>
        <p><button type="submit">创建用户</button></p>
      </form>
      <table><thead><tr><th>ID</th><th>账号</th><th>管理员</th><th>创建时间</th></tr></thead><tbody>{rows}</tbody></table>
    </div>
    """
    return page("用户管理", body, user=user)


@app.post("/admin/users")
def create_user(
    username: str = Form(...),
    password: str = Form(...),
    is_admin: int = Form(0),
    user: sqlite3.Row = Depends(get_current_user),
):
    if not user["is_admin"]:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    try:
        with db_conn() as conn:
            conn.execute(
                "INSERT INTO users(username, password_hash, is_admin, created_at) VALUES (?, ?, ?, ?)",
                (username.strip(), hash_password(password), int(is_admin), now_text()),
            )
    except sqlite3.IntegrityError:
        return page("用户管理", '<div class="card"><p class="error">用户名已存在。</p><a href="/admin/users">返回</a></div>', user=user)
    return redirect("/admin/users")
