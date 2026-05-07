import configparser
import csv
import json
import os
import re
import secrets
import socket
import sqlite3
import subprocess
import threading
import time
import hashlib
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from functools import lru_cache
from pathlib import Path

from flask import Flask, Response, flash, g, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from app import (
    AppConfig,
    AIReplyEngine,
    CustomerRecord,
    DEFAULT_BUSINESS_DESC,
    EMAIL_FORMAT_OPTIONS,
    EMAIL_PATTERN,
    ExcelLoader,
    InboxMessage,
    MailClient,
    REPLIED_EMAILS_PATH,
    SENT_LOG_PATH,
    TemplateEngine,
    build_email_template_html,
    build_email_template_preview_text,
    extract_clean_reply_body,
    extract_customer_display_name,
)


BASE_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = Path(os.environ.get("MAIL_WORKSPACE_DIR", str(BASE_DIR))).resolve()
WORKSPACE_LABEL = os.environ.get("MAIL_INSTANCE_NAME", WORKSPACE_DIR.name if WORKSPACE_DIR != BASE_DIR else "本机工作区")
WEB_DATA = Path(os.environ.get("MAIL_WEB_DATA_DIR", str(WORKSPACE_DIR / "web_data"))).resolve()
UPLOAD_DIR = WEB_DATA / "uploads"
DB_PATH = WEB_DATA / "mail_system.db"
SECRET_PATH = WEB_DATA / "secret.key"
DEFAULT_CONFIG_PATH = BASE_DIR / "config.ini.example"
DESKTOP_CONFIG_PATH = Path(os.environ.get("MAIL_CONFIG_PATH", str(WORKSPACE_DIR / "config.ini"))).resolve()
WEB_PORT = int(os.environ.get("MAIL_WEB_PORT", "5000"))
FIXED_MAIL_SETTINGS = {
    "smtp_host": "smtp-n.global-mail.cn",
    "smtp_port_ssl": "465",
    "smtp_port_starttls": "25",
    "imap_host": "imap-n.global-mail.cn",
    "imap_port_ssl": "993",
    "imap_port_starttls": "143",
}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 30 * 1024 * 1024

jobs: dict[int, dict] = {}
jobs_lock = threading.Lock()
DEFAULT_INBOX_DAYS = 30
MAX_INBOX_DAYS = 365
INBOX_DAY_OPTIONS = [7, 15, 30, 90]

BUSINESS_KEYWORDS = [
    "catalog", "catalogue", "brochure", "product list", "price", "quote", "quotation",
    "sample", "samples", "cost", "how much", "product", "products", "spec", "specification",
    "details", "parameter", "parameters", "size", "height", "density", "quality", "warranty",
    "guarantee", "lead time", "shipping", "delivery", "order", "wholesale", "dealer",
    "distributor", "cooperation", "cooperate", "partner", "partnership", "interested",
    "need", "want", "looking for", "send me", "provide", "manufacturer", "factory",
    "artificial grass", "synthetic grass", "synthetic turf", "turf", "grass", "installation",
]
AUTO_REPLY_KEYWORDS = [
    "automatic reply", "auto reply", "autoreply", "out of office", "away from office",
    "away from the office", "vacation responder", "on leave", "i am currently out",
    "this is an automated response", "this is an automatic response", "i will be back",
]
SPAM_KEYWORDS = [
    "seo", "search engine optimization", "website design", "web design", "guest post",
    "backlink", "digital marketing", "lead generation", "credit card fees", "merchant services",
    "loan offer", "crypto", "bitcoin", "casino", "forex", "app development", "software development",
    "data scraping", "domain registration", "unsubscribe", "remove me from your mailing list",
]
SIGNATURE_KEYWORDS = [
    "best regards", "kind regards", "regards", "thanks and regards", "sincerely",
    "phone", "tel", "mobile", "email", "website", "www.", "http://", "https://",
    "inc", "llc", "ltd", "company", "co.", "address",
]
MEANINGLESS_SHORT_PHRASES = {
    "thanks", "thank you", "ok", "okay", "noted", "received", "got it", "sure",
    "fine", "great", "good", "hello", "hi", "test", "welcome",
}


def db() -> sqlite3.Connection:
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db


def load_secret_key() -> str:
    WEB_DATA.mkdir(exist_ok=True)
    if SECRET_PATH.exists():
        return SECRET_PATH.read_text(encoding="utf-8").strip()
    key = os.environ.get("MAIL_WEB_SECRET", "").strip() or secrets.token_hex(32)
    SECRET_PATH.write_text(key, encoding="utf-8")
    return key


app.secret_key = load_secret_key()


@app.teardown_appcontext
def close_db(_exc=None) -> None:
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db() -> None:
    WEB_DATA.mkdir(exist_ok=True)
    UPLOAD_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(
        """
        create table if not exists users (
            id integer primary key autoincrement,
            username text not null unique,
            password_hash text not null,
            is_admin integer not null default 0,
            created_at text not null
        );
        create table if not exists user_configs (
            user_id integer primary key,
            config_json text not null,
            updated_at text not null
        );
        create table if not exists customers (
            id integer primary key autoincrement,
            user_id integer not null,
            import_order integer not null default 0,
            company_name text not null,
            email text not null,
            business_intro text,
            phone text,
            website text,
            country text,
            city text,
            search_keyword text,
            status text not null default '待发送',
            last_error text,
            created_at text not null
        );
        create table if not exists sent_logs (
            id integer primary key autoincrement,
            user_id integer not null,
            company text,
            recipient text,
            status text not null,
            subject text,
            body text,
            business_summary text,
            error text,
            created_at text not null
        );
        create table if not exists sent_emails (
            user_id integer not null,
            email text not null,
            created_at text not null,
            primary key (user_id, email)
        );
        create table if not exists inbox_messages (
            id integer primary key autoincrement,
            user_id integer not null,
            uid text,
            message_id text,
            sender text,
            sender_email text,
            subject text,
            date text,
            body text,
            status text not null default '未处理',
            created_at text not null
        );
        create table if not exists replied_messages (
            user_id integer not null,
            message_key text not null,
            created_at text not null,
            primary key (user_id, message_key)
        );
        """
    )
    columns = [row[1] for row in conn.execute("pragma table_info(customers)").fetchall()]
    if "import_order" not in columns:
        conn.execute("alter table customers add column import_order integer not null default 0")
    if "search_keyword" not in columns:
        conn.execute("alter table customers add column search_keyword text")
    user_ids = [row[0] for row in conn.execute("select distinct user_id from customers where import_order=0 order by user_id").fetchall()]
    for user_id in user_ids:
        customer_ids = [
            row[0]
            for row in conn.execute(
                "select id from customers where user_id=? and import_order=0 order by id",
                (user_id,),
            ).fetchall()
        ]
        for import_order, customer_id in enumerate(customer_ids, start=1):
            conn.execute("update customers set import_order=? where id=?", (import_order, customer_id))
    count = conn.execute("select count(*) from users").fetchone()[0]
    if count == 0:
        conn.execute(
            "insert into users(username,password_hash,is_admin,created_at) values(?,?,1,?)",
            ("admin", generate_password_hash("admin123"), now()),
        )
    conn.commit()
    conn.close()


def now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def parse_mail_datetime(value: str) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        dt = parsedate_to_datetime(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass
    for fmt in ("%A, %b %d, %Y %I:%M %p", "%A, %B %d, %Y %I:%M %p", "%b %d, %Y %I:%M %p", "%B %d, %Y %I:%M %p"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def original_sent_datetime(body: str) -> datetime | None:
    compact = re.sub(r"\s+", " ", body or "")
    match = re.search(
        r"\bSent:\s*([A-Za-z]+,\s+[A-Za-z]+\s+\d{1,2},\s+\d{4}\s+\d{1,2}:\d{2}\s*(?:AM|PM))",
        compact,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return parse_mail_datetime(match.group(1))


def effective_mail_datetime(message_or_row) -> datetime | None:
    if isinstance(message_or_row, InboxMessage):
        body = message_or_row.body
        date_value = message_or_row.date
    else:
        body = message_or_row["body"] if "body" in message_or_row.keys() else ""
        date_value = message_or_row["date"] if "date" in message_or_row.keys() else ""
    return original_sent_datetime(body) or parse_mail_datetime(date_value)


def display_mail_time(row) -> str:
    dt = effective_mail_datetime(row)
    if dt is None:
        return row["date"] or row["created_at"]
    return dt.astimezone().strftime("%Y-%m-%d %H:%M")


def mail_timestamp(message_or_row) -> float:
    dt = effective_mail_datetime(message_or_row)
    if dt is None:
        return 0.0
    return dt.timestamp()


def parse_inbox_days(value: str | None) -> int:
    try:
        days = int(value or DEFAULT_INBOX_DAYS)
    except (TypeError, ValueError):
        days = DEFAULT_INBOX_DAYS
    return max(1, min(MAX_INBOX_DAYS, days))


def parse_sort_order(value: str | None) -> str:
    return "asc" if (value or "").lower() == "asc" else "desc"


def parse_local_datetime_timestamp(value: str | None) -> float:
    text = (value or "").strip()
    if not text:
        return 0.0
    try:
        return datetime.strptime(text, "%Y-%m-%d %H:%M:%S").timestamp()
    except ValueError:
        return 0.0


def parse_uid(value: str | int | None) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def max_message_uid(messages: list[InboxMessage]) -> int:
    max_uid = 0
    for message in messages:
        max_uid = max(max_uid, parse_uid(message.uid))
    return max_uid


def get_inbox_max_uid(user_id: int) -> int:
    data = get_config_dict(user_id)
    return parse_uid(data.get("runtime", {}).get("inbox_max_uid", "0"))


def get_inbox_fetched_days(user_id: int) -> int:
    data = get_config_dict(user_id)
    return parse_inbox_days(data.get("runtime", {}).get("inbox_fetched_days", "0"))


def set_inbox_refresh_state(user_id: int, uid: int, days: int) -> None:
    data = get_config_dict(user_id)
    data.setdefault("runtime", {})
    current = parse_uid(data["runtime"].get("inbox_max_uid", "0"))
    if uid > current:
        data["runtime"]["inbox_max_uid"] = str(uid)
    current_days = parse_inbox_days(data["runtime"].get("inbox_fetched_days", "0"))
    data["runtime"]["inbox_fetched_days"] = str(max(current_days, days))
    data["runtime"]["inbox_last_refresh_at"] = now()
    save_config_dict(user_id, data)


def load_default_config() -> dict:
    parser = configparser.ConfigParser()
    source_path = DESKTOP_CONFIG_PATH if DESKTOP_CONFIG_PATH.exists() else DEFAULT_CONFIG_PATH
    parser.read(source_path, encoding="utf-8")
    data = {section: dict(parser[section]) for section in parser.sections()}
    data.setdefault("project", {})
    data.setdefault("mail", {})
    data.setdefault("runtime", {})
    data.setdefault("templates", {})
    data.setdefault("email_template", {})
    if source_path == DEFAULT_CONFIG_PATH:
        data["mail"]["password"] = ""
    return data


def normalize_config_data(data: dict) -> dict:
    defaults = load_default_config()
    for section, values in defaults.items():
        data.setdefault(section, {})
        for key, value in values.items():
            data[section].setdefault(key, value)
    for section in ("project", "mail", "runtime", "templates", "email_template", "ai", "attachments"):
        data.setdefault(section, {})
    data["ai"].setdefault("base_url", "https://api.openai.com")
    data["ai"].setdefault("model", "gpt-4o-mini")
    data["ai"].setdefault("api_key", "")
    data["ai"].setdefault("local_reply_docx_path", "")
    data["attachments"].setdefault("fixed_attachment_enabled", "false")
    data["attachments"].setdefault("fixed_attachment_path", "")
    data["attachments"].setdefault("quote_path", "")
    data["attachments"].setdefault("catalog_path", "")
    data["attachments"].setdefault("certificate_path", "")
    data.setdefault("mail", {})
    for key, value in FIXED_MAIL_SETTINGS.items():
        data["mail"].setdefault(key, value)
    return data


def merge_desktop_config_for_missing_values(data: dict) -> dict:
    if not DESKTOP_CONFIG_PATH.exists():
        return data
    parser = configparser.ConfigParser()
    parser.read(DESKTOP_CONFIG_PATH, encoding="utf-8")
    for section in parser.sections():
        data.setdefault(section, {})
        for key, value in parser[section].items():
            if not str(data[section].get(key, "")).strip():
                data[section][key] = value
    return data


def get_config_dict(user_id: int) -> dict:
    row = db().execute("select config_json from user_configs where user_id=?", (user_id,)).fetchone()
    if row:
        return normalize_config_data(merge_desktop_config_for_missing_values(json.loads(row["config_json"])))
    data = normalize_config_data(merge_desktop_config_for_missing_values(load_default_config()))
    save_config_dict(user_id, data)
    return data


def save_config_dict(user_id: int, data: dict) -> None:
    db().execute(
        """
        insert into user_configs(user_id, config_json, updated_at)
        values(?,?,?)
        on conflict(user_id) do update set config_json=excluded.config_json, updated_at=excluded.updated_at
        """,
        (user_id, json.dumps(data, ensure_ascii=False), now()),
    )
    db().commit()


def make_app_config(user_id: int) -> AppConfig:
    data = get_config_dict(user_id)
    WEB_DATA.mkdir(parents=True, exist_ok=True)
    cfg = AppConfig(WEB_DATA / "web_virtual_config.ini")
    for section, values in data.items():
        cfg.parser[section] = {k: str(v) for k, v in values.items()}
    for section in ("project", "mail", "runtime", "templates", "email_template", "ai", "attachments"):
        if section not in cfg.parser:
            cfg.parser[section] = {}
    return cfg


def client_ip() -> str:
    forwarded = request.headers.get("X-Forwarded-For", "").split(",", 1)[0].strip()
    return forwarded or request.remote_addr or "local"


def workspace_username() -> str:
    ip = client_ip()
    if ip in {"127.0.0.1", "::1", "localhost"}:
        return "admin"
    safe_ip = re.sub(r"[^0-9a-zA-Z]+", "_", ip).strip("_") or "unknown"
    return f"device_{safe_ip}"


def workspace_label(username: str) -> str:
    if WORKSPACE_LABEL and WORKSPACE_LABEL != "本机工作区":
        return WORKSPACE_LABEL if username == "admin" else f"{WORKSPACE_LABEL} / {username.replace('device_', '电脑 ').replace('_', '.')}"
    if username == "admin":
        return "本机工作区"
    return username.replace("device_", "电脑 ").replace("_", ".")


def is_local_request() -> bool:
    return client_ip() in {"127.0.0.1", "::1", "localhost"}


def is_local_admin() -> bool:
    return is_local_request() and g.user["username"] == "admin" and bool(g.user["is_admin"])


def get_or_create_user(username: str):
    user = db().execute("select * from users where username=?", (username,)).fetchone()
    if user:
        return user
    db().execute(
        "insert into users(username,password_hash,is_admin,created_at) values(?,?,0,?)",
        (username, generate_password_hash(secrets.token_urlsafe(16)), now()),
    )
    db().commit()
    return db().execute("select * from users where username=?", (username,)).fetchone()


def current_user():
    username = workspace_username()
    if username != "admin":
        return get_or_create_user(username)
    user = db().execute("select * from users where username='admin'").fetchone()
    if user:
        return user
    user = db().execute("select * from users order by id limit 1").fetchone()
    if user:
        return user
    db().execute(
        "insert into users(username,password_hash,is_admin,created_at) values(?,?,1,?)",
        ("admin", generate_password_hash("admin123"), now()),
    )
    db().commit()
    return db().execute("select * from users where username='admin'").fetchone()


@app.before_request
def load_user() -> None:
    g.user = current_user()
    g.workspace_label = workspace_label(g.user["username"])
    g.is_local_admin = is_local_admin()


def login_required(fn):
    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper


def admin_required(fn):
    def wrapper(*args, **kwargs):
        if not getattr(g, "is_local_admin", False):
            return Response("forbidden", status=403)
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper


def row_to_record(row) -> CustomerRecord:
    search_keyword = row["search_keyword"] if "search_keyword" in row.keys() else ""
    return CustomerRecord(
        company_name=row["company_name"],
        email=row["email"],
        business_intro=row["business_intro"] or DEFAULT_BUSINESS_DESC,
        phone=row["phone"] or "",
        website=row["website"] or "",
        country=row["country"] or "",
        city=row["city"] or "",
        search_keyword=search_keyword or "",
    )


def apply_vars(text: str, record: CustomerRecord, cfg: AppConfig, business_summary: str) -> str:
    project = cfg.project
    values = {
        "company_name": record.company_name,
        "email": record.email,
        "business_intro": record.business_intro,
        "business_summary": business_summary,
        "phone": record.phone,
        "website": record.website,
        "country": record.country,
        "city": record.city,
        "project_name": project.get("project_name", "").strip(),
        "project_website": project.get("project_website", "").strip(),
        "product_advantages": project.get("product_advantages", "").strip(),
        "contact_name": project.get("contact_name", "").strip(),
    }
    result = text or ""
    for key, value in values.items():
        result = result.replace("{" + key + "}", value or "")
    return result


def has_cjk_text(value: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in value or "")


def normalize_subject_template(value: str) -> str:
    template = (value or "").strip()
    if not template or "{business_intro}" in template or has_cjk_text(template):
        return "Quick note on your {business_summary}"
    return template


def split_business_summary(value: str) -> list[str]:
    text = (value or "").replace(", and ", ", ").replace(" and ", ", ")
    return [part.strip(" ,.;:") for part in text.split(",") if part.strip(" ,.;:")]


def build_web_subject(record: CustomerRecord, cfg: AppConfig) -> str:
    engine = TemplateEngine(cfg)
    keyword = (getattr(record, "search_keyword", "") or "").strip()
    keyword_summary = engine.summarize_business_intro(keyword) if keyword else ""
    intro_summary = engine.summarize_business_intro(record.business_intro)
    summary_parts: list[str] = []
    for part in split_business_summary(keyword_summary) + split_business_summary(intro_summary):
        if part and part not in summary_parts:
            summary_parts.append(part)
    summary = engine._join_keywords(summary_parts[:3])
    template = normalize_subject_template(cfg.templates.get("subject", ""))
    template = template.replace("{business_intro}", "{business_summary}")
    safe_record = CustomerRecord(
        company_name=record.company_name,
        email=record.email,
        business_intro=summary,
        phone=record.phone,
        website=record.website,
        country=record.country,
        city=record.city,
    )
    subject = apply_vars(template, safe_record, cfg, summary)
    subject = re.sub(r"\s+", " ", subject.replace("\r", " ").replace("\n", " ")).strip()
    if has_cjk_text(subject):
        return f"Quick note on your {summary}"
    return subject


def build_web_body(record: CustomerRecord, cfg: AppConfig) -> str:
    engine = TemplateEngine(cfg)
    summary = engine.summarize_business_intro(record.business_intro)
    project = cfg.project
    project_name = project.get("project_name", "").strip() or "our company"
    website = project.get("project_website", "").strip()
    product_advantages = project.get("product_advantages", "").strip() or "reliable products and services"
    contact_name = project.get("contact_name", "").strip() or project_name

    first = (
        f"Hi {record.company_name} team,\n\n"
        f"I noticed from your company profile that {record.company_name} is connected with {summary}. "
        f"That kind of work usually requires steady product support, clear communication, and partners who understand different project needs."
    )
    second = (
        f"I am writing from {project_name}. We support overseas partners with {product_advantages}, "
        f"stable follow-up, and practical cooperation for different markets."
    )
    third_template = cfg.templates.get("manual_third_paragraph", "").strip()
    third = apply_vars(third_template, record, cfg, summary) if third_template else (
        "If there is ever a suitable opportunity in the future, we would be glad to exchange more details "
        "and see whether our work could be useful for your business."
    )
    tail = f"Best regards,\n{contact_name}"
    if project_name and contact_name != project_name:
        tail += f"\n{project_name}"
    if website:
        tail += f"\n{website}"
    return "\n\n".join([first, second, third, tail])


def web_logo_src(user_id: int, cfg: AppConfig) -> str:
    logo_path = cfg.email_template.get("logo_path", "").strip()
    if not logo_path:
        return ""
    path = Path(logo_path)
    if path.exists() and path.is_file():
        return url_for("logo_file", user_id=user_id, filename=path.name)
    if logo_path.lower().startswith(("http://", "https://", "data:", "cid:", "file://")):
        return logo_path
    return ""


def display_file_name(path_text: str) -> str:
    if not path_text:
        return ""
    return Path(path_text).name


def save_user_upload(user_id: int, file_storage, target_name: str, default_suffix: str = "") -> str:
    if not file_storage or not file_storage.filename:
        return ""
    upload_dir = UPLOAD_DIR / str(user_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    original_name = secure_filename(file_storage.filename)
    suffix = Path(original_name).suffix.lower() or default_suffix
    stem = Path(original_name).stem or target_name
    filename = f"{target_name}-{stem}{suffix}" if target_name else f"{stem}{suffix}"
    path = upload_dir / filename
    counter = 2
    while path.exists():
        path = upload_dir / f"{Path(filename).stem}-{counter}{suffix}"
        counter += 1
    file_storage.save(path)
    return str(path)


def configured_send_attachments(cfg: AppConfig) -> list[Path]:
    attachments: list[Path] = []
    if cfg.attachments.get("fixed_attachment_enabled", "false").strip().lower() in {"1", "true", "yes", "on"}:
        fixed_path = cfg.attachments.get("fixed_attachment_path", "").strip()
        if fixed_path:
            attachments.append(Path(fixed_path))
    for key in ("quote_path", "catalog_path", "certificate_path"):
        path_text = cfg.attachments.get(key, "").strip()
        if path_text:
            attachments.append(Path(path_text))

    unique: list[Path] = []
    seen: set[str] = set()
    for item in attachments:
        key = str(item).lower()
        if key not in seen:
            unique.append(item)
            seen.add(key)
    return unique


def build_reply_attachments(
    ai_engine: AIReplyEngine,
    ai_result: dict,
    message: InboxMessage,
    include_fixed_attachment: bool,
    extra_attachment: Path | None = None,
) -> list[Path]:
    attachments = ai_engine.build_attachment_list(ai_result, message)
    fixed_path = ai_engine.config.attachments.get("fixed_attachment_path", "").strip()

    filtered = attachments
    if fixed_path:
        fixed = Path(fixed_path)
        fixed_key = str(fixed).lower()
        filtered = [path for path in attachments if str(path).lower() != fixed_key]
    if include_fixed_attachment and fixed_path:
        filtered.insert(0, fixed)
    if extra_attachment:
        filtered.insert(0, extra_attachment)

    unique: list[Path] = []
    seen: set[str] = set()
    for item in filtered:
        key = str(item).lower()
        if key not in seen:
            unique.append(item)
            seen.add(key)
    return unique


def format_auto_reply_body(message: InboxMessage, body_text: str, ai_engine: AIReplyEngine, cfg: AppConfig) -> str:
    customer_name = extract_customer_display_name(message.sender, message.sender_email)
    company_name = cfg.project.get("project_name", "").strip() or "Our Team"
    website = cfg.project.get("project_website", "").strip()
    core_body = ai_engine._normalize_reply_paragraphs(body_text)
    parts = [
        f"Dear {customer_name},",
        "",
        core_body,
        "",
        "Best regards,",
        company_name,
    ]
    if website:
        parts.append(website)
    return "\n".join(parts).strip()


def already_sent(user_id: int, email: str) -> bool:
    return db().execute("select 1 from sent_emails where user_id=? and email=?", (user_id, email.lower())).fetchone() is not None


def valid_email(value: str) -> bool:
    return bool(value and EMAIL_PATTERN.match(value.strip()))


def email_domain(value: str) -> str:
    return value.rsplit("@", 1)[-1].strip().lower() if "@" in value else ""


@lru_cache(maxsize=4096)
def domain_has_mx_record(domain: str) -> bool:
    try:
        result = subprocess.run(
            ["nslookup", "-type=mx", domain],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return False
    output = f"{result.stdout}\n{result.stderr}".lower()
    return "mail exchanger" in output or "mx preference" in output


@lru_cache(maxsize=4096)
def domain_has_address_record(domain: str) -> bool:
    try:
        socket.getaddrinfo(domain, None)
        return True
    except OSError:
        return False


def mail_route_error(email: str) -> str:
    domain = email_domain(email)
    if not domain:
        return "邮箱域名为空"
    if domain_has_mx_record(domain):
        return ""
    if domain_has_address_record(domain):
        return f"邮箱域名无 MX 记录，容易退信：{domain}"
    return f"邮箱域名无 MX/A 解析，无法投递：{domain}"


def log_send(user_id: int, record: CustomerRecord, status: str, subject: str = "", body: str = "", error: str = "") -> None:
    business_summary = TemplateEngine(make_app_config(user_id)).summarize_business_intro(record.business_intro)
    db().execute(
        """
        insert into sent_logs(user_id,company,recipient,status,subject,body,business_summary,error,created_at)
        values(?,?,?,?,?,?,?,?,?)
        """,
        (user_id, record.company_name, record.email, status, subject, body, business_summary, error, now()),
    )
    db().commit()


def log_mail(user_id: int, company: str, recipient: str, status: str, subject: str = "", body: str = "", error: str = "", business_summary: str = "") -> None:
    db().execute(
        """
        insert into sent_logs(user_id,company,recipient,status,subject,body,business_summary,error,created_at)
        values(?,?,?,?,?,?,?,?,?)
        """,
        (user_id, company, recipient, status, subject, body, business_summary, error, now()),
    )
    db().commit()


def run_send_job(user_id: int) -> None:
    with app.app_context():
        cfg = make_app_config(user_id)
        engine = TemplateEngine(cfg)
        mailer = MailClient(cfg)
        min_delay = cfg.runtime.getint("min_delay_seconds", fallback=10)
        max_delay = cfg.runtime.getint("max_delay_seconds", fallback=15)
        rows = db().execute("select * from customers where user_id=? order by import_order, id", (user_id,)).fetchall()
        total = len(rows)
        sent = failed = filtered = 0
        for index, row in enumerate(rows, start=1):
            with jobs_lock:
                state = jobs.setdefault(user_id, {})
                if state.get("stop"):
                    state.update(running=False, message="已停止")
                    break
                state.update(
                    running=True,
                    current=index,
                    total=total,
                    sent=sent,
                    failed=failed,
                    filtered=filtered,
                    current_company=row["company_name"],
                    current_email=row["email"],
                    message=f"正在处理 {row['company_name']}",
                )

            record = row_to_record(row)
            if not valid_email(record.email):
                filtered += 1
                db().execute("update customers set status=?, last_error=? where id=?", ("过滤", "邮箱无效", row["id"]))
                log_send(user_id, record, "过滤", error="邮箱无效")
                db().commit()
                continue
            route_error = mail_route_error(record.email)
            if route_error:
                filtered += 1
                db().execute("update customers set status=?, last_error=? where id=?", ("过滤", route_error, row["id"]))
                log_send(user_id, record, "过滤", error=route_error)
                db().commit()
                continue
            if already_sent(user_id, record.email):
                filtered += 1
                db().execute("update customers set status=?, last_error=? where id=?", ("过滤", "已发送过", row["id"]))
                log_send(user_id, record, "过滤", error="已发送过")
                db().commit()
                continue

            try:
                subject = build_web_subject(record, cfg)
                body = build_web_body(record, cfg)
                attachments: list[Path] = []
                mailer.send_mail(record.email, subject, body, attachments)
                sent += 1
                db().execute("update customers set status=?, last_error='' where id=?", ("已发送", row["id"]))
                db().execute(
                    "insert or ignore into sent_emails(user_id,email,created_at) values(?,?,?)",
                    (user_id, record.email.lower(), now()),
                )
                attachment_note = ", ".join(path.name for path in attachments) if attachments else ""
                log_send(user_id, record, "已发送", subject, body, attachment_note)
            except Exception as exc:
                failed += 1
                db().execute("update customers set status=?, last_error=? where id=?", ("失败", str(exc), row["id"]))
                log_send(user_id, record, "失败", error=str(exc))
            db().commit()

            if index < total:
                time.sleep(max(min_delay, min(max_delay, min_delay)))
        with jobs_lock:
            jobs[user_id] = {
                "running": False,
                "stop": False,
                "current": total,
                "total": total,
                "sent": sent,
                "failed": failed,
                "filtered": filtered,
                "message": f"完成：已发送 {sent}，失败 {failed}，过滤 {filtered}",
            }


def is_bounce(subject: str, sender: str, body: str) -> bool:
    text = f"{subject} {sender} {body}".lower()
    keys = [
        "mailer-daemon", "postmaster", "undelivered", "delivery failure", "failure notice",
        "returned mail", "delivery status notification", "mail delivery subsystem",
        "delivery has failed", "message not delivered", "550 ", " 550", "544 ", " 544",
        "退信", "发送失败", "投递失败",
    ]
    return any(k in text for k in keys)


def normalize_keyword_text(text: str) -> str:
    value = (text or "").lower()
    value = value.replace("-", " ")
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def extract_effective_customer_text(message: InboxMessage) -> str:
    text = extract_clean_reply_body(message.body)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in text.splitlines()]
    meaningful_lines: list[str] = []
    for line in lines:
        if not line:
            continue
        lowered = line.lower()
        if lowered.startswith(("from:", "sent:", "to:", "subject:", "cc:", "bcc:")):
            continue
        meaningful_lines.append(line)
    return "\n".join(meaningful_lines).strip()


def contains_keyword(text: str, keywords: list[str]) -> bool:
    normalized = f" {normalize_keyword_text(text)} "
    for keyword in keywords:
        key = normalize_keyword_text(keyword)
        if key and f" {key} " in normalized:
            return True
    return False


def is_meaningless_short_text(text: str) -> bool:
    normalized = normalize_keyword_text(text)
    if not normalized:
        return True
    if normalized in MEANINGLESS_SHORT_PHRASES:
        return True
    words = normalized.split()
    if len(words) <= 4 and all(word in {"thanks", "thank", "you", "ok", "okay", "noted", "received", "sure", "hi", "hello"} for word in words):
        return True
    return False


def is_signature_only_text(text: str) -> bool:
    if not (text or "").strip():
        return True
    if is_effective_business_mail_text(text, sent_by_us=True):
        return False
    lines = [line.strip().lower() for line in text.splitlines() if line.strip()]
    if not lines:
        return True
    if len(lines) > 6:
        return False
    signature_lines = 0
    for line in lines:
        if any(keyword in line for keyword in SIGNATURE_KEYWORDS):
            signature_lines += 1
            continue
        if re.fullmatch(r"[a-z .,&/()+-]{2,50}", line) and len(line.split()) <= 6:
            signature_lines += 1
            continue
    return signature_lines == len(lines)


def invalid_mail_reason(message: InboxMessage) -> str:
    text = f"{message.subject}\n{message.sender}\n{message.sender_email}\n{message.body}".lower()
    customer_text = extract_effective_customer_text(message)
    if is_bounce(message.subject, message.sender_email, message.body):
        return "退信/投递失败"
    if any(keyword in text for keyword in AUTO_REPLY_KEYWORDS):
        return "系统自动回复"
    if any(keyword in customer_text.lower() for keyword in SPAM_KEYWORDS) and not is_effective_business_mail_text(customer_text, sent_by_us=True):
        return "广告垃圾邮件"
    if is_signature_only_text(customer_text) or is_meaningless_short_text(customer_text):
        return "空内容/仅签名客套"
    return ""


def is_effective_business_mail_text(text: str, sent_by_us: bool) -> bool:
    normalized = normalize_keyword_text(text)
    if not normalized:
        return False
    request_phrases = (
        "price", "quote", "quotation", "cost", "how much", "catalog", "catalogue",
        "brochure", "product list", "spec", "specification", "details", "parameter",
        "sample", "lead time", "delivery", "shipping", "warranty", "cooperation",
        "partnership", "interested", "looking for", "send me", "provide", "need ",
        "want ", "can you", "could you", "please send", "please provide",
    )
    if any(phrase in normalized for phrase in request_phrases):
        return True
    if "?" in text and contains_keyword(text, BUSINESS_KEYWORDS):
        return True
    if sent_by_us:
        positive_phrases = (
            "yes", "sounds good", "interested", "tell me more", "send more", "please share",
            "please send", "we are interested", "i am interested", "can you send",
            "could you send", "provide more information", "more information",
        )
        if any(phrase in normalized for phrase in positive_phrases):
            return True
    return False


def is_effective_business_mail(message: InboxMessage, sent_by_us: bool) -> bool:
    customer_text = extract_effective_customer_text(message)
    return is_effective_business_mail_text(customer_text, sent_by_us)


def inbox_row_to_message(row) -> InboxMessage:
    return InboxMessage(
        uid=row["uid"] or "",
        message_id=row["message_id"] or "",
        sender=row["sender"] or "",
        sender_email=row["sender_email"] or "",
        subject=row["subject"] or "",
        date=row["date"] or "",
        body=row["body"] or "",
        references="",
    )


def normalize_reply_subject(subject: str) -> str:
    text = (subject or "").strip().lower()
    while True:
        new_text = re.sub(r"^(re|fw|fwd|回复|答复)\s*[:：]\s*", "", text, flags=re.IGNORECASE).strip()
        if new_text == text:
            return text
        text = new_text


def customer_reply_text(body: str) -> str:
    text = (body or "").strip()
    patterns = [
        r"\n[- ]{2,}\s*回复的原邮件\s*[- ]{2,}",
        r"\n[- ]{2,}\s*original message\s*[- ]{2,}",
        r"\nfrom:\s",
        r"\n发件人\s*[|:：]",
    ]
    for pattern in patterns:
        parts = re.split(pattern, text, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) > 1:
            text = parts[0].strip()
            break
    return re.sub(r"\s+", " ", text).strip().lower()


def inbox_fingerprint(message: InboxMessage) -> str:
    raw = "|".join([
        message.sender_email.strip().lower(),
        normalize_reply_subject(message.subject),
        customer_reply_text(message.body)[:500],
    ])
    return hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()


def inbox_message_key(message: InboxMessage) -> str:
    message_id = (message.message_id or "").strip()
    if message_id:
        return message_id
    uid = (message.uid or "").strip()
    if uid:
        return f"uid:{uid}"
    raw = "|".join([
        message.sender_email.strip().lower(),
        normalize_reply_subject(message.subject),
        (message.date or "").strip(),
        customer_reply_text(message.body)[:1000],
    ])
    return hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()


def desktop_replied_message_ids() -> set[str]:
    if not REPLIED_EMAILS_PATH.exists():
        return set()
    try:
        return {
            line.strip()
            for line in REPLIED_EMAILS_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
    except Exception:
        return set()


def replied(user_id: int, message: InboxMessage) -> bool:
    desktop_ids = desktop_replied_message_ids()
    if (message.uid and message.uid in desktop_ids) or (message.message_id and message.message_id in desktop_ids):
        return True
    if db().execute(
        "select 1 from replied_messages where user_id=? and message_key=?",
        (user_id, inbox_message_key(message)),
    ).fetchone() is not None:
        return True
    return replied_after_message(user_id, message)


def has_exact_auto_reply_log(user_id: int, message: InboxMessage) -> bool:
    message_ts = mail_timestamp(message)
    row = db().execute(
        """
        select 1 from sent_logs
        where user_id=? and lower(recipient)=lower(?) and status='自动回复成功'
          and lower(subject)=lower(?) and created_at >= ?
        """,
        (
            user_id,
            message.sender_email,
            MailClient._build_reply_subject(message.subject),
            datetime.fromtimestamp(message_ts).strftime("%Y-%m-%d %H:%M:%S") if message_ts else "",
        ),
    ).fetchone()
    return row is not None


def mark_replied(user_id: int, message: InboxMessage) -> None:
    key = inbox_message_key(message)
    db().execute("insert or ignore into replied_messages(user_id,message_key,created_at) values(?,?,?)", (user_id, key, now()))
    db().execute(
        """
        update inbox_messages
        set status='已回复'
        where user_id=? and message_id=?
        """,
        (user_id, key),
    )
    db().commit()


def email_domain(email: str) -> str:
    normalized = (email or "").strip().lower()
    if "@" not in normalized:
        return ""
    return normalized.split("@", 1)[1]


def desktop_sent_log_items() -> list[dict[str, str]]:
    if not SENT_LOG_PATH.exists():
        return []
    try:
        with SENT_LOG_PATH.open("r", encoding="utf-8", newline="") as file:
            return list(csv.DictReader(file))
    except Exception:
        return []


def matching_auto_reply_times(user_id: int, message: InboxMessage) -> list[float]:
    sender_email = (message.sender_email or "").strip().lower()
    normalized_subject = normalize_reply_subject(message.subject)
    if not sender_email or not normalized_subject:
        return []

    timestamps: list[float] = []
    rows = db().execute(
        "select recipient, subject, created_at from sent_logs where user_id=? and status='自动回复成功'",
        (user_id,),
    ).fetchall()
    for row in rows:
        if (row["recipient"] or "").strip().lower() != sender_email:
            continue
        if normalize_reply_subject(row["subject"] or "") != normalized_subject:
            continue
        ts = parse_local_datetime_timestamp(row["created_at"])
        if ts:
            timestamps.append(ts)

    for item in desktop_sent_log_items():
        if item.get("status") != "自动回复成功":
            continue
        if (item.get("recipient", "") or "").strip().lower() != sender_email:
            continue
        if normalize_reply_subject(item.get("subject", "") or "") != normalized_subject:
            continue
        ts = parse_local_datetime_timestamp(item.get("time", ""))
        if ts:
            timestamps.append(ts)
    return timestamps


def replied_after_message(user_id: int, message: InboxMessage) -> bool:
    message_ts = mail_timestamp(message)
    if not message_ts:
        return False
    return any(reply_ts >= message_ts for reply_ts in matching_auto_reply_times(user_id, message))


def is_reply_to_sent_mail(user_id: int, message: InboxMessage) -> bool:
    sender_email = (message.sender_email or "").strip().lower()
    if not sender_email:
        return False

    subject = (message.subject or "").strip()
    normalized_subject = normalize_reply_subject(subject)
    if not normalized_subject:
        return False

    has_reply_prefix = bool(re.match(r"^\s*(re|回复)\s*[:：]", subject, flags=re.IGNORECASE))
    if not has_reply_prefix and not message.references:
        return False

    sender_domain = email_domain(sender_email)
    rows = [
        {"recipient": row["recipient"] or "", "subject": row["subject"] or ""}
        for row in db().execute(
        "select recipient, subject from sent_logs where user_id=? and status='已发送'",
        (user_id,),
        ).fetchall()
    ]
    for item in desktop_sent_log_items():
        if item.get("status") == "发送成功":
            rows.append({"recipient": item.get("recipient", ""), "subject": item.get("subject", "")})

    for row in rows:
        recipient_email = (row.get("recipient", "") or "").strip().lower()
        recipient_domain = email_domain(recipient_email)
        sent_subject = normalize_reply_subject(row.get("subject", "") or "")
        same_recipient = bool(recipient_email and recipient_email == sender_email)
        same_domain = bool(sender_domain and recipient_domain and sender_domain == recipient_domain)
        if sent_subject and sent_subject == normalized_subject and (same_recipient or same_domain):
            return True
    return False


def is_reply_candidate(user_id: int, message: InboxMessage, cfg: AppConfig) -> tuple[bool, str]:
    own = cfg.mail.get("username", "").strip().lower()
    if not message.sender_email or message.sender_email.strip().lower() == own:
        return False, "我方邮箱/空发件人"
    if not is_reply_to_sent_mail(user_id, message):
        return False, "非开发信回复"
    if replied(user_id, message):
        return False, "已回复"
    invalid_reason = invalid_mail_reason(message)
    if invalid_reason:
        return False, invalid_reason
    if is_effective_business_mail(message, sent_by_us=True):
        return True, "可回复"
    return False, "无明确业务内容"


def cleanup_inbox_threads(user_id: int, cfg: AppConfig) -> None:
    rows = db().execute(
        "select * from inbox_messages where user_id=? order by id desc limit 1000",
        (user_id,),
    ).fetchall()
    changed = False
    for row in rows:
        msg = inbox_row_to_message(row)
        can_reply, reason = is_reply_candidate(user_id, msg, cfg)
        expected = "待回复" if can_reply else reason
        if row["status"] != expected:
            db().execute("update inbox_messages set status=? where id=?", (expected, row["id"]))
            changed = True
    if changed:
        db().commit()


def inbox_row_payload(row) -> dict:
    payload = dict(row)
    payload["display_time"] = display_mail_time(row)
    payload["timestamp"] = mail_timestamp(row)
    return payload


def fetch_and_store_inbox(user_id: int, cfg: AppConfig, days: int, incremental: bool = True) -> dict:
    fetched_days = get_inbox_fetched_days(user_id)
    min_uid = get_inbox_max_uid(user_id) if incremental and fetched_days >= days else 0
    messages = MailClient(cfg).fetch_inbox_messages(
        limit=1000,
        unread_only=False,
        recent_days=days,
        min_uid=min_uid,
    )
    fetched_max_uid = max_message_uid(messages)

    added = pending = bounced = ignored = 0
    for msg in messages:
        message_key = inbox_message_key(msg)
        existing = db().execute(
            "select 1 from inbox_messages where user_id=? and message_id=?",
            (user_id, message_key),
        ).fetchone()
        if existing:
            continue
        can_reply, reason = is_reply_candidate(user_id, msg, cfg)
        status = "退信" if is_bounce(msg.subject, msg.sender_email, msg.body) else ("待回复" if can_reply else reason)
        if status == "待回复":
            pending += 1
        elif status == "退信":
            bounced += 1
        else:
            ignored += 1
        db().execute(
            """
            insert into inbox_messages(user_id,uid,message_id,sender,sender_email,subject,date,body,status,created_at)
            values(?,?,?,?,?,?,?,?,?,?)
            """,
            (user_id, msg.uid, message_key, msg.sender, msg.sender_email, msg.subject, msg.date, msg.body, status, now()),
        )
        if status == "退信":
            log_mail(user_id, msg.sender, msg.sender_email, "退信", msg.subject, msg.body[:3000], "系统识别为退信/系统邮件")
        added += 1

    set_inbox_refresh_state(user_id, fetched_max_uid, days)
    cleanup_inbox_threads(user_id, cfg)
    db().commit()

    cutoff = datetime.now(timezone.utc).timestamp() - days * 86400
    all_rows = db().execute(
        "select * from inbox_messages where user_id=? order by id desc limit 500",
        (user_id,),
    ).fetchall()
    rows = []
    for row in all_rows:
        timestamp = mail_timestamp(row)
        if not timestamp or timestamp < cutoff:
            continue
        rows.append(inbox_row_payload(row))
    rows.sort(key=lambda item: item["timestamp"], reverse=True)
    rows = rows[:50]

    return {
        "added": added,
        "pending": pending,
        "bounced": bounced,
        "ignored": ignored,
        "rows": rows,
        "last_refresh_time": now(),
        "max_uid": max(get_inbox_max_uid(user_id), fetched_max_uid),
    }


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = db().execute("select * from users where username=?", (username,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard"))
        flash("账号或密码错误。", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("dashboard"))


@app.route("/")
@login_required
def dashboard():
    counts = {
        "customers": db().execute("select count(*) from customers where user_id=?", (g.user["id"],)).fetchone()[0],
        "sent": db().execute("select count(*) from sent_logs where user_id=? and status='已发送'", (g.user["id"],)).fetchone()[0],
        "failed": db().execute("select count(*) from sent_logs where user_id=? and status='失败'", (g.user["id"],)).fetchone()[0],
        "filtered": db().execute("select count(*) from sent_logs where user_id=? and status in ('过滤','退信')", (g.user["id"],)).fetchone()[0],
    }
    recent = db().execute("select * from sent_logs where user_id=? order by id desc limit 8", (g.user["id"],)).fetchall()
    return render_template("dashboard.html", counts=counts, recent=recent, job=jobs.get(g.user["id"], {}))


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    data = get_config_dict(g.user["id"])
    if request.method == "POST":
        old_password = data.get("mail", {}).get("password", "")
        old_api_key = data.get("ai", {}).get("api_key", "")
        for section in ("project", "mail", "runtime", "templates", "email_template", "ai", "attachments"):
            data.setdefault(section, {})
        fields = {
            "project": ["project_name", "project_website", "product_advantages", "contact_name", "contact_phone", "contact_email", "office_address", "factory_address", "copyright_text"],
            "mail": ["username", "password", "smtp_host", "smtp_port_ssl", "smtp_port_starttls", "imap_host", "imap_port_ssl"],
            "runtime": ["min_delay_seconds", "max_delay_seconds"],
            "templates": ["subject", "body", "manual_third_paragraph"],
            "email_template": ["header_line_color", "footer_background_color", "footer_text_color", "email_format"],
            "ai": ["base_url", "api_key", "model", "local_reply_docx_path"] if g.is_local_admin else [],
            "attachments": ["fixed_attachment_enabled", "fixed_attachment_path", "quote_path", "catalog_path", "certificate_path"],
        }
        for section, names in fields.items():
            for name in names:
                data[section][name] = request.form.get(f"{section}.{name}", "").strip()
        data["templates"]["subject"] = normalize_subject_template(data["templates"].get("subject", ""))
        for key, value in FIXED_MAIL_SETTINGS.items():
            data["mail"][key] = value
        if not data["mail"].get("password"):
            data["mail"]["password"] = old_password
        if not data["ai"].get("api_key"):
            data["ai"]["api_key"] = old_api_key
        logo = request.files.get("logo")
        logo_path = save_user_upload(g.user["id"], logo, "logo", ".png")
        if logo_path:
            data["email_template"]["logo_path"] = logo_path
        reply_path = save_user_upload(g.user["id"], request.files.get("reply_docx"), "reply_rules", ".docx")
        if reply_path:
            data["ai"]["local_reply_docx_path"] = reply_path
        upload_map = {
            "fixed_attachment_file": ("attachments", "fixed_attachment_path", "fixed_attachment"),
            "quote_file": ("attachments", "quote_path", "quote"),
            "catalog_file": ("attachments", "catalog_path", "catalog"),
            "certificate_file": ("attachments", "certificate_path", "certificate"),
        }
        for field_name, (section, key, target_name) in upload_map.items():
            uploaded_path = save_user_upload(g.user["id"], request.files.get(field_name), target_name)
            if uploaded_path:
                data[section][key] = uploaded_path
        save_config_dict(g.user["id"], data)
        flash("配置已保存。", "success")
        return redirect(url_for("settings"))
    cfg_obj = make_app_config(g.user["id"])
    reply_note = AIReplyEngine(cfg_obj).local_rules_load_note
    return render_template(
        "settings.html",
        cfg=data,
        formats=EMAIL_FORMAT_OPTIONS,
        logo_name=display_file_name(data.get("email_template", {}).get("logo_path", "")),
        reply_docx_name=display_file_name(data.get("ai", {}).get("local_reply_docx_path", "")),
        fixed_attachment_name=display_file_name(data.get("attachments", {}).get("fixed_attachment_path", "")),
        quote_name=display_file_name(data.get("attachments", {}).get("quote_path", "")),
        catalog_name=display_file_name(data.get("attachments", {}).get("catalog_path", "")),
        certificate_name=display_file_name(data.get("attachments", {}).get("certificate_path", "")),
        reply_note=reply_note,
    )


@app.route("/send", methods=["GET", "POST"])
@login_required
def send_page():
    if request.method == "POST":
        with jobs_lock:
            state = jobs.get(g.user["id"], {})
            if state.get("running"):
                flash("发送任务正在运行，请先停止发送后再导入新的 Excel。", "error")
                return redirect(url_for("send_page"))
        file = request.files.get("excel")
        if not file or not file.filename:
            flash("请选择 Excel 文件。", "error")
            return redirect(url_for("send_page"))
        upload_dir = UPLOAD_DIR / str(g.user["id"])
        upload_dir.mkdir(parents=True, exist_ok=True)
        original_excel_name = Path(file.filename).name
        safe_excel_name = secure_filename(file.filename) or f"customers_{int(time.time())}.xlsx"
        path = upload_dir / safe_excel_name
        file.save(path)
        try:
            records = ExcelLoader(DEFAULT_BUSINESS_DESC).load_records(str(path))
            db().execute("delete from customers where user_id=?", (g.user["id"],))
            for import_order, record in enumerate(records, start=1):
                db().execute(
                    """
                    insert into customers(user_id,import_order,company_name,email,business_intro,phone,website,country,city,search_keyword,status,last_error,created_at)
                    values(?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        g.user["id"],
                        import_order,
                        record.company_name,
                        record.email,
                        record.business_intro,
                        record.phone,
                        record.website,
                        record.country,
                        record.city,
                        record.search_keyword,
                        "待发送",
                        "",
                        now(),
                    ),
                )
            db().commit()
            data = get_config_dict(g.user["id"])
            data.setdefault("runtime", {})
            data["runtime"]["latest_excel_name"] = original_excel_name or path.name
            data["runtime"]["latest_excel_saved_name"] = path.name
            save_config_dict(g.user["id"], data)
            with jobs_lock:
                jobs[g.user["id"]] = {
                    "running": False,
                    "stop": False,
                    "current": 0,
                    "total": len(records),
                    "sent": 0,
                    "failed": 0,
                    "filtered": 0,
                    "message": "空闲",
                }
            flash(f"已导入 {len(records)} 条客户数据：{original_excel_name or path.name}", "success")
        except Exception as exc:
            flash(str(exc), "error")
        return redirect(url_for("send_page"))
    rows = db().execute("select * from customers where user_id=? order by import_order, id limit 300", (g.user["id"],)).fetchall()
    total_customers = db().execute("select count(*) from customers where user_id=?", (g.user["id"],)).fetchone()[0]
    first = db().execute("select * from customers where user_id=? order by import_order, id limit 1", (g.user["id"],)).fetchone()
    data = get_config_dict(g.user["id"])
    latest_excel_name = data.get("runtime", {}).get("latest_excel_name", "")
    upload_dir = UPLOAD_DIR / str(g.user["id"])
    if not latest_excel_name and upload_dir.exists():
        excel_files = [path for path in upload_dir.iterdir() if path.is_file() and path.suffix.lower() in {".xlsx", ".xls"}]
        if excel_files:
            latest_excel_name = max(excel_files, key=lambda path: path.stat().st_mtime).name
    preview = ""
    subject = ""
    send_attachment_names: list[str] = []
    if first:
        cfg = make_app_config(g.user["id"])
        record = row_to_record(first)
        subject = build_web_subject(record, cfg)
        preview = build_email_template_html(build_web_body(record, cfg), cfg, web_logo_src(g.user["id"], cfg))
    return render_template(
        "send.html",
        rows=rows,
        preview=preview,
        subject=subject,
        job=jobs.get(g.user["id"], {}),
        latest_excel_name=latest_excel_name,
        total_customers=total_customers,
        send_attachment_names=send_attachment_names,
    )


@app.route("/start-send", methods=["POST"])
@login_required
def start_send():
    with jobs_lock:
        state = jobs.get(g.user["id"], {})
        if state.get("running"):
            flash("发送任务正在运行。", "error")
            return redirect(url_for("send_page"))
        jobs[g.user["id"]] = {"running": True, "stop": False, "current": 0, "total": 0, "message": "准备发送"}
    db().execute("update customers set status='待发送', last_error='' where user_id=?", (g.user["id"],))
    db().commit()
    threading.Thread(target=run_send_job, args=(g.user["id"],), daemon=True).start()
    flash("批量发送已开始。", "success")
    return redirect(url_for("send_page"))


@app.route("/stop-send", methods=["POST"])
@login_required
def stop_send():
    with jobs_lock:
        jobs.setdefault(g.user["id"], {})["stop"] = True
    flash("已请求停止。", "success")
    return redirect(url_for("send_page"))


@app.route("/job-status")
@login_required
def job_status():
    counts = db().execute(
        """
        select
          sum(case when status='已发送' then 1 else 0 end) as sent,
          sum(case when status='失败' then 1 else 0 end) as failed,
          sum(case when status='过滤' then 1 else 0 end) as filtered,
          count(*) as total
        from customers where user_id=?
        """,
        (g.user["id"],),
    ).fetchone()
    state = jobs.get(g.user["id"], {"running": False, "current": 0, "total": counts["total"] or 0, "message": "空闲"})
    state = dict(state)
    state.update({
        "sent": counts["sent"] or state.get("sent", 0) or 0,
        "failed": counts["failed"] or state.get("failed", 0) or 0,
        "filtered": counts["filtered"] or state.get("filtered", 0) or 0,
    })
    return jsonify(state)


@app.route("/send-table")
@login_required
def send_table():
    rows = db().execute("select * from customers where user_id=? order by import_order, id limit 300", (g.user["id"],)).fetchall()
    return render_template("_customer_rows.html", rows=rows)


@app.route("/customer/<int:customer_id>")
@login_required
def customer_detail(customer_id: int):
    row = db().execute("select * from customers where user_id=? and id=?", (g.user["id"], customer_id)).fetchone()
    if not row:
        return jsonify({"error": "未找到客户"}), 404
    cfg = make_app_config(g.user["id"])
    record = row_to_record(row)
    subject = build_web_subject(record, cfg)
    body = build_web_body(record, cfg)
    html = build_email_template_html(body, cfg, web_logo_src(g.user["id"], cfg))
    log = db().execute(
        "select * from sent_logs where user_id=? and lower(recipient)=lower(?) order by id desc limit 1",
        (g.user["id"], record.email),
    ).fetchone()
    return jsonify({
        "company": record.company_name,
        "email": record.email,
        "status": row["status"],
        "error": row["last_error"] or "",
        "subject": subject,
        "body": body,
        "html": html,
        "last_log": dict(log) if log else None,
    })


@app.route("/logs")
@login_required
def logs():
    rows = db().execute("select * from sent_logs where user_id=? order by id desc limit 500", (g.user["id"],)).fetchall()
    return render_template("logs.html", rows=rows)


@app.route("/log/<int:log_id>")
@login_required
def log_detail(log_id: int):
    row = db().execute("select * from sent_logs where user_id=? and id=?", (g.user["id"], log_id)).fetchone()
    if not row:
        return jsonify({"error": "未找到记录"}), 404
    cfg = make_app_config(g.user["id"])
    html = build_email_template_html(row["body"] or "", cfg, web_logo_src(g.user["id"], cfg)) if row["body"] else ""
    return jsonify({**dict(row), "html": html})


@app.route("/inbox")
@login_required
def inbox():
    show_all = request.args.get("all") == "1"
    inbox_days = parse_inbox_days(request.args.get("days"))
    sort_order = parse_sort_order(request.args.get("order"))
    cutoff = datetime.now(timezone.utc).timestamp() - inbox_days * 86400
    cfg_obj = make_app_config(g.user["id"])
    cleanup_inbox_threads(g.user["id"], cfg_obj)

    if show_all:
        raw_rows = db().execute("select * from inbox_messages where user_id=? order by id desc limit 500", (g.user["id"],)).fetchall()
    else:
        raw_rows = db().execute("select * from inbox_messages where user_id=? and status='待回复' order by id desc limit 500", (g.user["id"],)).fetchall()
    
    filtered_rows = []
    for row in raw_rows:
        timestamp = mail_timestamp(row)
        if not timestamp or timestamp < cutoff:
            continue
        item = dict(row)
        item["_timestamp"] = timestamp
        filtered_rows.append(item)
    filtered_rows.sort(key=lambda item: item["_timestamp"], reverse=(sort_order == "desc"))

    rows = [inbox_row_payload(row) for row in filtered_rows[:200]]
    
    ai_engine = AIReplyEngine(cfg_obj)
    reply_note = ai_engine.local_rules_load_note
    data = get_config_dict(g.user["id"])
    last_refresh_time = data.get("runtime", {}).get("inbox_last_refresh_at", "") or "尚未刷新"
    return render_template(
        "inbox.html",
        rows=rows,
        show_all=show_all,
        inbox_days=inbox_days,
        inbox_day_options=INBOX_DAY_OPTIONS,
        sort_order=sort_order,
        next_sort_order="asc" if sort_order == "desc" else "desc",
        last_refresh_time=last_refresh_time,
        reply_docx_name=display_file_name(data.get("ai", {}).get("local_reply_docx_path", "")),
        fixed_attachment_name=display_file_name(data.get("attachments", {}).get("fixed_attachment_path", "")),
        fixed_attachment_enabled=data.get("attachments", {}).get("fixed_attachment_enabled", "false"),
        reply_note=reply_note,
        reply_rules_ready=bool(ai_engine.local_rules),
    )


@app.route("/fetch-inbox", methods=["POST"])
@login_required
def fetch_inbox():
    try:
        inbox_days = parse_inbox_days(request.form.get("days"))
        sort_order = parse_sort_order(request.form.get("order"))
        show_all = request.form.get("all") == "1"
        cfg = make_app_config(g.user["id"])
        result = fetch_and_store_inbox(g.user["id"], cfg, inbox_days, incremental=True)
        flash(
            f"收信完成，仅拉取最近 {inbox_days} 天邮件；新增 {result['added']} 封；"
            f"待回复 {result['pending']}，退信 {result['bounced']}，过滤 {result['ignored']}。",
            "success",
        )
    except Exception as exc:
        flash(f"收信失败：{exc}", "error")
        inbox_days = DEFAULT_INBOX_DAYS
        sort_order = "desc"
        show_all = False
    return redirect(url_for("inbox", days=inbox_days, order=sort_order, all=1 if show_all else 0))


@app.route("/fetch-inbox-json", methods=["POST"])
@login_required
def fetch_inbox_json():
    payload = request.get_json(silent=True) or {}
    inbox_days = parse_inbox_days(payload.get("days") or request.form.get("days"))
    force = str(payload.get("force") or request.form.get("force") or "").lower() in {"1", "true", "yes", "on"}
    cfg = make_app_config(g.user["id"])
    try:
        result = fetch_and_store_inbox(g.user["id"], cfg, inbox_days, incremental=not force)
        return jsonify({"ok": True, **result})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc), "last_refresh_time": now()}), 500


def require_reply_rules_confirmation(ai_engine: AIReplyEngine) -> bool:
    if ai_engine.local_rules:
        return True
    return request.form.get("confirm_no_rules") == "1"


@app.route("/reply-settings", methods=["POST"])
@login_required
def reply_settings():
    data = get_config_dict(g.user["id"])
    data.setdefault("ai", {})
    data.setdefault("attachments", {})
    data["ai"]["local_reply_docx_path"] = request.form.get("ai.local_reply_docx_path", "").strip() or data["ai"].get("local_reply_docx_path", "")
    if "attachments.fixed_attachment_enabled" in request.form:
        data["attachments"]["fixed_attachment_enabled"] = "true" if request.form.get("attachments.fixed_attachment_enabled") else "false"
    if "attachments.fixed_attachment_path" in request.form:
        data["attachments"]["fixed_attachment_path"] = request.form.get("attachments.fixed_attachment_path", "").strip() or data["attachments"].get("fixed_attachment_path", "")
    reply_path = save_user_upload(g.user["id"], request.files.get("reply_docx"), "reply_rules", ".docx")
    fixed_path = save_user_upload(g.user["id"], request.files.get("fixed_attachment_file"), "fixed_attachment")
    if reply_path:
        data["ai"]["local_reply_docx_path"] = reply_path
    if fixed_path:
        data["attachments"]["fixed_attachment_path"] = fixed_path
    save_config_dict(g.user["id"], data)
    flash("回复配置已保存。", "success")
    return redirect(url_for("inbox"))


@app.route("/test-mail-config", methods=["POST"])
@login_required
def test_mail_config():
    cfg = make_app_config(g.user["id"])
    mailer = MailClient(cfg)
    messages = []
    ok = True
    try:
        messages.extend(mailer.test_smtp_connection())
    except Exception as exc:
        ok = False
        messages.append(f"SMTP 测试失败：{exc}")
    try:
        mailer.fetch_inbox_messages(limit=1, unread_only=False)
        messages.append("IMAP 收信登录成功。")
    except Exception as exc:
        ok = False
        messages.append(f"IMAP 收信失败：{exc}")
    flash("；".join(messages), "success" if ok else "error")
    return redirect(request.referrer or url_for("settings"))


@app.route("/inbox/<int:message_id>")
@login_required
def inbox_detail(message_id: int):
    row = db().execute("select * from inbox_messages where user_id=? and id=?", (g.user["id"], message_id)).fetchone()
    if not row:
        return jsonify({"error": "未找到邮件"}), 404
    reply_log = db().execute(
        """
        select * from sent_logs
        where user_id=? and lower(recipient)=lower(?) and status in ('自动回复成功','自动回复失败')
        order by id desc limit 1
        """,
        (g.user["id"], row["sender_email"]),
    ).fetchone()
    payload = dict(row)
    payload["reply_log"] = dict(reply_log) if reply_log else None
    return jsonify(payload)


@app.route("/auto-reply/<int:message_id>", methods=["POST"])
@login_required
def auto_reply(message_id: int):
    """生成回复预览，返回JSON而不是直接发送"""
    row = db().execute("select * from inbox_messages where user_id=? and id=?", (g.user["id"], message_id)).fetchone()
    if not row:
        return jsonify({"error": "未找到邮件"}), 404
    
    cfg = make_app_config(g.user["id"])
    msg = inbox_row_to_message(row)
    ai_engine = AIReplyEngine(cfg)
    
    try:
        try:
            result = ai_engine.generate_reply(msg)
        except Exception:
            result = ai_engine.build_fallback_reply(msg)
        
        body = format_auto_reply_body(msg, result.get("reply_body", "").strip(), ai_engine, cfg)
        fixed_attachment_name = display_file_name(cfg.attachments.get("fixed_attachment_path", "").strip())
        automatic_attachments = build_reply_attachments(ai_engine, result, msg, False)
        
        return jsonify({
            "ok": True,
            "message_id": message_id,
            "sender": msg.sender,
            "sender_email": msg.sender_email,
            "subject": MailClient._build_reply_subject(msg.subject),
            "body": body,
            "attachments": [path.name for path in automatic_attachments],
            "automatic_attachments": [path.name for path in automatic_attachments],
            "fixed_attachment_name": fixed_attachment_name,
            "include_fixed_attachment": False,
            "matched_keyword": result.get("matched_keyword", ""),
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/confirm-auto-reply/<int:message_id>", methods=["POST"])
@login_required
def confirm_auto_reply(message_id: int):
    """用户确认后真正发送回复"""
    row = db().execute("select * from inbox_messages where user_id=? and id=?", (g.user["id"], message_id)).fetchone()
    if not row:
        flash("未找到邮件。", "error")
        return redirect(url_for("inbox"))
    
    cfg = make_app_config(g.user["id"])
    msg = inbox_row_to_message(row)
    ai_engine = AIReplyEngine(cfg)
    include_fixed_attachment = bool(request.form.get("include_fixed_attachment"))
    reply_attachment_path = request.form.get("reply_attachment_path", "").strip()
    uploaded_attachment_path = save_user_upload(g.user["id"], request.files.get("reply_attachment_file"), f"reply_attachment-{message_id}")
    extra_attachment = Path(uploaded_attachment_path or reply_attachment_path) if (uploaded_attachment_path or reply_attachment_path) else None
    
    try:
        try:
            result = ai_engine.generate_reply(msg)
        except Exception:
            result = ai_engine.build_fallback_reply(msg)
        
        body = format_auto_reply_body(msg, result.get("reply_body", "").strip(), ai_engine, cfg)
        attachments = build_reply_attachments(ai_engine, result, msg, include_fixed_attachment, extra_attachment)
        MailClient(cfg).reply_mail(msg, body, attachments)
        mark_replied(g.user["id"], msg)
        db().execute("update inbox_messages set status=? where id=?", ("已回复", message_id))
        log_mail(
            g.user["id"],
            msg.sender,
            msg.sender_email,
            "自动回复成功",
            MailClient._build_reply_subject(msg.subject),
            body,
            ", ".join(path.name for path in attachments) if attachments else "",
            result.get("matched_keyword", ""),
        )
        flash("自动回复已发送。", "success")
        if "application/json" in request.headers.get("Accept", ""):
            db().commit()
            return jsonify({"ok": True})
    except Exception as exc:
        db().execute("update inbox_messages set status=? where id=?", ("回复失败", message_id))
        log_mail(g.user["id"], msg.sender, msg.sender_email, "自动回复失败", MailClient._build_reply_subject(msg.subject), "", str(exc))
        flash(f"自动回复失败：{exc}", "error")
        if "application/json" in request.headers.get("Accept", ""):
            db().commit()
            return jsonify({"ok": False, "error": str(exc)}), 500
    db().commit()
    return redirect(url_for("inbox"))


@app.route("/auto-reply-pending", methods=["POST"])
@login_required
def auto_reply_pending():
    """显示待回复邮件列表，询问用户是否要继续"""
    rows = db().execute(
        "select * from inbox_messages where user_id=? and status='待回复' order by id limit 50",
        (g.user["id"],),
    ).fetchall()
    
    if not rows:
        flash("当前没有待回复邮件。", "error")
        return redirect(url_for("inbox"))
    
    cfg = make_app_config(g.user["id"])
    fixed_attachment_name = display_file_name(cfg.attachments.get("fixed_attachment_path", "").strip())
    include_fixed_default = cfg.attachments.get("fixed_attachment_enabled", "false").strip().lower() in {"1", "true", "yes", "on"}

    # 返回待回复邮件列表，让用户确认
    items = []
    for row in rows:
        items.append({
            "id": row["id"],
            "sender": row["sender"],
            "sender_email": row["sender_email"],
            "subject": row["subject"],
            "date": row["date"],
        })
    
    return render_template(
        "confirm_batch_reply.html",
        items=items,
        count=len(items),
        fixed_attachment_name=fixed_attachment_name,
        include_fixed_default=include_fixed_default and bool(fixed_attachment_name),
    )


@app.route("/execute-batch-reply", methods=["POST"])
@login_required
def execute_batch_reply():
    """执行批量回复"""
    rows = db().execute(
        "select * from inbox_messages where user_id=? and status='待回复' order by id limit 50",
        (g.user["id"],),
    ).fetchall()
    
    if not rows:
        flash("当前没有待回复邮件。", "error")
        return redirect(url_for("inbox"))

    ok = failed = 0
    cfg = make_app_config(g.user["id"])
    ai_engine = AIReplyEngine(cfg)
    mailer = MailClient(cfg)
    fixed_attachment_ids = set(request.form.getlist("include_fixed_attachment_ids"))
    
    for row in rows:
        msg = inbox_row_to_message(row)
        row_id_text = str(row["id"])
        include_fixed_attachment = row_id_text in fixed_attachment_ids
        reply_attachment_path = request.form.get(f"reply_attachment_path_{row_id_text}", "").strip()
        uploaded_attachment_path = save_user_upload(g.user["id"], request.files.get(f"reply_attachment_file_{row_id_text}"), f"reply_attachment-{row_id_text}")
        extra_attachment = Path(uploaded_attachment_path or reply_attachment_path) if (uploaded_attachment_path or reply_attachment_path) else None
        try:
            try:
                result = ai_engine.generate_reply(msg)
            except Exception:
                result = ai_engine.build_fallback_reply(msg)
            body = format_auto_reply_body(msg, result.get("reply_body", "").strip(), ai_engine, cfg)
            attachments = build_reply_attachments(ai_engine, result, msg, include_fixed_attachment, extra_attachment)
            mailer.reply_mail(msg, body, attachments)
            mark_replied(g.user["id"], msg)
            db().execute("update inbox_messages set status=? where id=?", ("已回复", row["id"]))
            log_mail(
                g.user["id"],
                msg.sender,
                msg.sender_email,
                "自动回复成功",
                MailClient._build_reply_subject(msg.subject),
                body,
                ", ".join(path.name for path in attachments) if attachments else "",
                result.get("matched_keyword", ""),
            )
            ok += 1
        except Exception as exc:
            failed += 1
            db().execute("update inbox_messages set status=? where id=?", ("回复失败", row["id"]))
            log_mail(g.user["id"], msg.sender, msg.sender_email, "自动回复失败", MailClient._build_reply_subject(msg.subject), "", str(exc))
        db().commit()
    
    flash(f"批量回复完成：成功 {ok}，失败 {failed}。", "success" if ok else "error")
    return redirect(url_for("inbox"))


@app.route("/bounce-scan", methods=["POST"])
@login_required
def bounce_scan():
    try:
        messages = MailClient(make_app_config(g.user["id"])).fetch_inbox_messages(limit=80)
        count = 0
        for msg in messages:
            if not is_bounce(msg.subject, msg.sender_email, msg.body):
                continue
            count += 1
            db().execute(
                "insert into sent_logs(user_id,company,recipient,status,subject,body,business_summary,error,created_at) values(?,?,?,?,?,?,?,?,?)",
                (g.user["id"], msg.sender, msg.sender_email, "退信", msg.subject, msg.body[:3000], "", "系统识别为退信/系统邮件", now()),
            )
        db().commit()
        flash(f"退信扫描完成，识别 {count} 封。", "success")
    except Exception as exc:
        flash(str(exc), "error")
    return redirect(url_for("logs"))


@app.route("/users", methods=["GET", "POST"])
@admin_required
def users():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        is_admin = 1 if request.form.get("is_admin") else 0
        if not username or not password:
            flash("请输入账号和密码。", "error")
        else:
            try:
                db().execute(
                    "insert into users(username,password_hash,is_admin,created_at) values(?,?,?,?)",
                    (username, generate_password_hash(password), is_admin, now()),
                )
                db().commit()
                flash("账号已创建。", "success")
            except sqlite3.IntegrityError:
                flash("账号已存在。", "error")
        return redirect(url_for("users"))
    rows = db().execute("select id,username,is_admin,created_at from users order by id").fetchall()
    return render_template("users.html", rows=rows)


@app.route("/password", methods=["GET", "POST"])
@admin_required
def password():
    if request.method == "POST":
        old = request.form.get("old_password", "")
        new = request.form.get("new_password", "")
        if not check_password_hash(g.user["password_hash"], old):
            flash("原密码错误。", "error")
        elif len(new) < 6:
            flash("新密码至少 6 位。", "error")
        else:
            db().execute("update users set password_hash=? where id=?", (generate_password_hash(new), g.user["id"]))
            db().commit()
            flash("密码已修改。", "success")
        return redirect(url_for("password"))
    return render_template("password.html")


@app.route("/logo/<int:user_id>/<path:filename>")
@login_required
def logo_file(user_id: int, filename: str):
    if user_id != g.user["id"] and not g.user["is_admin"]:
        return Response("forbidden", status=403)
    return send_from_directory(UPLOAD_DIR / str(user_id), filename)


if __name__ == "__main__":
    init_db()
    print(f"网页版外贸邮件系统已启动：http://127.0.0.1:{WEB_PORT}")
    print(f"局域网访问请使用本机 IP：http://本机IP:{WEB_PORT}")
    print(f"工作区：{WORKSPACE_LABEL}")
    print(f"数据目录：{WEB_DATA}")
    print("默认管理员：admin / admin123")
    app.run(host="0.0.0.0", port=WEB_PORT, threaded=True)
