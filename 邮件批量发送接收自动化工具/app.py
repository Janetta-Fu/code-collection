import configparser
import csv
import hashlib
import imaplib
import json
import mimetypes
import os
import posixpath
import queue
import random
import re
import smtplib
import ssl
import threading
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from email.utils import formataddr, make_msgid, parsedate_to_datetime, parseaddr
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.parser import BytesParser
from email.policy import default
from pathlib import Path
from tkinter import END, LEFT, RIGHT, BOTH, X, Y, BooleanVar, PhotoImage, filedialog, messagebox, scrolledtext, StringVar, Text, Tk
from tkinter import ttk
from tkinter import colorchooser
from xml.etree import ElementTree as ET


BASE_DIR = Path(__file__).resolve().parent
APP_DATA_DIR = Path(os.environ.get("MAIL_APP_DATA_DIR", str(BASE_DIR))).resolve()
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_PATH = Path(os.environ.get("MAIL_CONFIG_PATH", str(APP_DATA_DIR / "config.ini"))).resolve()
SENT_LOG_PATH = APP_DATA_DIR / "sent_log.csv"
SENT_EMAILS_PATH = APP_DATA_DIR / "sent_emails.txt"
REPLIED_EMAILS_PATH = APP_DATA_DIR / "replied_emails.txt"
REPLY_HISTORY_PATH = APP_DATA_DIR / "reply_history.csv"
DEFAULT_BUSINESS_DESC = "related products and services"
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DEFAULT_TEMPLATE_COLORS = {
    "header_line_color": "#79c600",
    "footer_background_color": "#79c600",
    "footer_text_color": "#ffffff",
}
EMAIL_FORMAT_OPTIONS = {
    "HTML+纯文本": "both",
    "仅HTML": "html",
    "仅纯文本": "plain",
}


def decode_mime(value: str) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


@dataclass
class CustomerRecord:
    company_name: str
    email: str
    business_intro: str
    phone: str = ""
    website: str = ""
    country: str = ""
    city: str = ""
    search_keyword: str = ""


@dataclass
class InboxMessage:
    uid: str
    message_id: str
    sender: str
    sender_email: str
    subject: str
    date: str
    body: str
    references: str = ""


def _message_date_timestamp(message: InboxMessage) -> float:
    try:
        parsed = parsedate_to_datetime(message.date or "")
        return parsed.timestamp()
    except Exception:
        return 0.0


class AppConfig:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.parser = configparser.ConfigParser()

    def load(self) -> None:
        if not self.path.exists():
            raise FileNotFoundError(
                f"未找到配置文件：{self.path}\n请先复制 config.ini.example 为 config.ini 并填写邮箱信息。"
            )
        self.parser.read(self.path, encoding="utf-8")

    def save(self) -> None:
        with self.path.open("w", encoding="utf-8") as file:
            self.parser.write(file)

    @property
    def project(self) -> configparser.SectionProxy:
        if "project" not in self.parser:
            self.parser["project"] = {}
        return self.parser["project"]

    @property
    def mail(self) -> configparser.SectionProxy:
        return self.parser["mail"]

    @property
    def runtime(self) -> configparser.SectionProxy:
        return self.parser["runtime"]

    @property
    def templates(self) -> configparser.SectionProxy:
        return self.parser["templates"]

    @property
    def email_template(self) -> configparser.SectionProxy:
        if "email_template" not in self.parser:
            self.parser["email_template"] = {}
        return self.parser["email_template"]

    @property
    def ai(self) -> configparser.SectionProxy:
        if "ai" not in self.parser:
            self.parser["ai"] = {}
        return self.parser["ai"]

    @property
    def attachments(self) -> configparser.SectionProxy:
        if "attachments" not in self.parser:
            self.parser["attachments"] = {}
        return self.parser["attachments"]


class ExcelLoader:
    COLUMN_ALIASES = {
        "company_name": ["公司名称", "company", "company name", "客户名称"],
        "email": ["邮箱", "email", "邮箱地址", "mail"],
        "business_intro": ["业务介绍", "business intro", "description", "产品介绍"],
        "phone": ["联系电话", "电话", "phone"],
        "website": ["官网地址", "website", "url"],
        "country": ["所在国家", "country"],
        "city": ["所在城市", "city"],
        "search_keyword": ["搜索关键词", "关键词", "search keyword", "keyword", "keywords"],
    }

    def __init__(self, default_business_intro: str) -> None:
        self.default_business_intro = default_business_intro

    def load_records(self, file_path: str) -> list[CustomerRecord]:
        if not file_path.lower().endswith(".xlsx"):
            raise ValueError("当前版本仅支持 .xlsx 文件，请先将 Excel 另存为 .xlsx 格式。")

        rows = self._read_xlsx_rows(file_path)

        if not rows:
            return []

        headers = [self._safe_text(cell) for cell in rows[0]]
        column_map = self._match_columns(headers)
        if "company_name" not in column_map or "email" not in column_map:
            raise ValueError("Excel 中至少需要包含“公司名称”和“邮箱”两列。")

        index_map = {name: idx for idx, name in enumerate(headers)}
        records: list[CustomerRecord] = []
        for row in rows[1:]:
            company_name = self._get_cell(row, index_map, column_map["company_name"])
            email = self._get_cell(row, index_map, column_map["email"]).lower()
            business_intro = self._get_cell(row, index_map, column_map.get("business_intro"))
            if not company_name:
                continue
            records.append(
                CustomerRecord(
                    company_name=company_name,
                    email=email,
                    business_intro=business_intro or self.default_business_intro,
                    phone=self._get_cell(row, index_map, column_map.get("phone")),
                    website=self._get_cell(row, index_map, column_map.get("website")),
                    country=self._get_cell(row, index_map, column_map.get("country")),
                    city=self._get_cell(row, index_map, column_map.get("city")),
                    search_keyword=self._get_cell(row, index_map, column_map.get("search_keyword")),
                )
            )
        return records

    def _match_columns(self, columns: list[str]) -> dict[str, str]:
        normalized = {self._normalize_text(col): col for col in columns}
        result: dict[str, str] = {}
        for field, aliases in self.COLUMN_ALIASES.items():
            for alias in aliases:
                matched = normalized.get(self._normalize_text(alias))
                if matched:
                    result[field] = matched
                    break
        return result

    @staticmethod
    def _normalize_text(value: str) -> str:
        return re.sub(r"\s+", "", str(value).strip().lower())

    @staticmethod
    def _safe_text(value) -> str:
        if value is None:
            return ""
        return str(value).strip()

    def _get_cell(self, row: tuple, index_map: dict[str, int], column_name: str | None) -> str:
        if not column_name:
            return ""
        index = index_map.get(column_name)
        if index is None or index >= len(row):
            return ""
        return self._safe_text(row[index])

    def _read_xlsx_rows(self, file_path: str) -> list[tuple]:
        namespace = {
            "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
            "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
        }

        with zipfile.ZipFile(file_path, "r") as archive:
            shared_strings = self._read_shared_strings(archive, namespace)
            first_sheet_path = self._find_first_sheet_path(archive, namespace)
            if not first_sheet_path:
                raise ValueError("未找到 Excel 工作表内容。")

            sheet_root = ET.fromstring(archive.read(first_sheet_path))
            rows_with_index: list[tuple[int, tuple]] = []
            for row_elem in sheet_root.findall(".//main:sheetData/main:row", namespace):
                cells: dict[int, str] = {}
                max_index = -1
                for cell in row_elem.findall("main:c", namespace):
                    ref = cell.attrib.get("r", "")
                    column_index = self._column_ref_to_index(ref)
                    max_index = max(max_index, column_index)
                    cell_type = cell.attrib.get("t", "")
                    value = self._read_cell_value(cell, cell_type, shared_strings, namespace)
                    cells[column_index] = value

                if max_index < 0:
                    continue
                row_index = self._row_ref_to_index(row_elem.attrib.get("r", ""))
                rows_with_index.append((row_index, tuple(cells.get(i, "") for i in range(max_index + 1))))
            return [row for _, row in sorted(rows_with_index, key=lambda item: item[0])]

    def _read_shared_strings(self, archive: zipfile.ZipFile, namespace: dict[str, str]) -> list[str]:
        if "xl/sharedStrings.xml" not in archive.namelist():
            return []

        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        strings: list[str] = []
        for item in root.findall("main:si", namespace):
            parts = [node.text or "" for node in item.findall(".//main:t", namespace)]
            strings.append("".join(parts))
        return strings

    def _find_first_sheet_path(self, archive: zipfile.ZipFile, namespace: dict[str, str]) -> str | None:
        workbook_root = ET.fromstring(archive.read("xl/workbook.xml"))
        relations_root = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))

        first_sheet = workbook_root.find("main:sheets/main:sheet", namespace)
        if first_sheet is None:
            return None

        relation_id = first_sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        if not relation_id:
            return None

        for rel in relations_root.findall("rel:Relationship", namespace):
            if rel.attrib.get("Id") == relation_id:
                target = rel.attrib.get("Target", "")
                sheet_path = self._normalize_workbook_relation_target(target)
                return sheet_path if sheet_path in archive.namelist() else None
        return None

    @staticmethod
    def _normalize_workbook_relation_target(target: str) -> str:
        normalized_target = target.replace("\\", "/").strip()
        if not normalized_target:
            return ""

        if normalized_target.startswith("/"):
            normalized_target = normalized_target.lstrip("/")
        elif not normalized_target.startswith("xl/"):
            normalized_target = posixpath.join("xl", normalized_target)

        return posixpath.normpath(normalized_target)

    def _read_cell_value(
        self,
        cell: ET.Element,
        cell_type: str,
        shared_strings: list[str],
        namespace: dict[str, str],
    ) -> str:
        if cell_type == "inlineStr":
            parts = [node.text or "" for node in cell.findall(".//main:t", namespace)]
            return "".join(parts).strip()

        value_node = cell.find("main:v", namespace)
        if value_node is None or value_node.text is None:
            return ""

        raw_value = value_node.text
        if cell_type == "s":
            try:
                return shared_strings[int(raw_value)].strip()
            except Exception:
                return raw_value.strip()
        return raw_value.strip()

    @staticmethod
    def _column_ref_to_index(reference: str) -> int:
        letters = "".join(ch for ch in reference if ch.isalpha()).upper()
        result = 0
        for char in letters:
            result = result * 26 + (ord(char) - ord("A") + 1)
        return max(result - 1, 0)

    @staticmethod
    def _row_ref_to_index(reference: str) -> int:
        match = re.search(r"\d+", reference or "")
        if not match:
            return 0
        return max(int(match.group()) - 1, 0)


class TemplateEngine:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def build_subject(self, record: CustomerRecord) -> str:
        cleaned_business = self.summarize_business_intro(record.business_intro)
        return f"Quick note on your {cleaned_business}"

    def build_body(self, record: CustomerRecord) -> str:
        cleaned_business = self.summarize_business_intro(record.business_intro)
        project = self.config.project
        company_name = project.get("project_name", "").strip() or "our company"
        website = project.get("project_website", "").strip()
        contact_name = project.get("contact_name", "").strip() or company_name
        website_text = website or "our website"

        return (
            f"Hi {record.company_name} team,\n\n"
            f"I noticed from your company profile that {record.company_name} is connected with {cleaned_business}. "
            f"That kind of work usually requires steady product support, clear communication, and partners who understand "
            f"how different projects and markets can vary, so I wanted to introduce ourselves in a respectful way.\n\n"
            f"I am writing from {company_name}. We support overseas partners with practical cooperation, stable follow-up, "
            f"and solutions that can be discussed according to each market's needs. You can also learn more here: {website_text}\n\n"
            f"If there is ever a suitable opportunity in the future, we would be glad to exchange more details and see "
            f"whether our work could be useful for your business. No pressure at all, just keeping the door open for possible cooperation.\n\n"
            f"Best regards,\n"
            f"{contact_name}\n"
            f"{company_name}\n"
            f"{website_text}"
        )

    def summarize_business_intro(self, text: str) -> str:
        raw = (text or "").strip()
        if not raw:
            return DEFAULT_BUSINESS_DESC

        cleaned = raw.replace("\r", " ").replace("\n", " ")
        cleaned = re.sub(r"[;；|]+", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.;:")
        lowered = cleaned.lower()
        keyword_phrases = self._extract_business_keyword_phrases(lowered)

        replacements = {
            "核心业务提炼": "",
            "核心业务": "",
            "主营": "",
            "提供": "",
            "服务": "services",
            "产品": "products",
            "人工草坪": "artificial grass",
            "人造草坪": "artificial grass",
            "草坪": "artificial grass",
            "地毯": "carpet",
            "地板": "flooring",
            "硬质地板": "hard surface flooring",
            "经销商": "distributors",
            "质量控制": "quality control",
            "生产设施": "production facilities",
            "安装": "installation",
            "批发": "wholesale",
            "供应": "supply",
            "景观": "landscaping",
            "庭院": "residential landscaping",
            "运动场": "sports landscaping",
            "工程": "contract projects",
            "覆盖": "",
            "客户群体": "",
            "应用场景": "",
            "业务方向": "",
            "及": " and ",
            "、": ", ",
            "，": ", ",
            "。": ". ",
            ":": " ",
        }
        for source, target in replacements.items():
            cleaned = cleaned.replace(source, target)

        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = re.sub(r"\s*,\s*", ", ", cleaned).strip(" ,.;:")

        if re.search(r"[\u4e00-\u9fff]", raw):
            keywords = list(keyword_phrases)
            keyword_map = [
                ("artificial grass", ["人工草", "人造草"]),
                ("artificial grass installation", ["安装"]),
                ("artificial grass supply", ["供应"]),
                ("artificial grass wholesale", ["批发"]),
                ("carpet and flooring products", ["地毯", "地板", "硬质地板"]),
                ("flooring distribution", ["地板经销商", "经销商"]),
                ("quality-focused production", ["质量控制", "生产设施", "高质量"]),
                ("landscaping solutions", ["景观", "庭院"]),
                ("sports landscaping", ["运动场"]),
                ("contract projects", ["工程"]),
            ]
            for english, tokens in keyword_map:
                if any(token in raw for token in tokens) and english not in keywords:
                    keywords.append(english)
            if not keywords:
                return "the business described in your company profile"
            return self._join_keywords(keywords)

        if keyword_phrases and len(cleaned.split()) <= 10:
            return self._join_keywords(keyword_phrases)

        fragments = [part.strip(" ,.;:") for part in re.split(r"[,.]", cleaned) if part.strip(" ,.;:")]
        filtered: list[str] = []
        for phrase in keyword_phrases:
            if phrase not in filtered:
                filtered.append(phrase)
        stop_phrases = {
            "core business",
            "core business summary",
            "customer groups",
            "application scenarios",
            "business direction",
        }
        for part in fragments:
            part_lower = part.lower()
            if part_lower in stop_phrases:
                continue
            if len(part_lower) < 4:
                continue
            if part_lower not in filtered:
                filtered.append(part_lower)

        if not filtered:
            return DEFAULT_BUSINESS_DESC
        return self._join_keywords(filtered[:3])

    @staticmethod
    def _join_keywords(items: list[str]) -> str:
        normalized = []
        for item in items:
            value = re.sub(r"\s+", " ", item).strip(" ,.;:")
            if value and value not in normalized:
                normalized.append(value)
        if not normalized:
            return DEFAULT_BUSINESS_DESC
        if len(normalized) == 1:
            return normalized[0]
        if len(normalized) == 2:
            return f"{normalized[0]} and {normalized[1]}"
        return f"{normalized[0]}, {normalized[1]}, and {normalized[2]}"

    @staticmethod
    def _extract_business_keyword_phrases(text: str) -> list[str]:
        phrases: list[str] = []

        def add(value: str) -> None:
            if value not in phrases:
                phrases.append(value)

        if any(term in text for term in ["artificial grass", "synthetic grass", "synthetic turf", "artificial turf"]):
            add("artificial grass")
        if any(term in text for term in ["install", "installation", "installer", "contractor", "contract project"]):
            add("artificial grass installation")
        if any(term in text for term in ["supplier", "supply", "supplies"]):
            add("artificial grass supply")
        if any(term in text for term in ["wholesale", "wholesaler", "distributor", "distribution"]):
            add("artificial grass wholesale")
        if any(term in text for term in ["landscape", "landscaping", "lawn care", "garden"]):
            add("landscaping solutions")
        if any(term in text for term in ["sports field", "playground", "putting green"]):
            add("sports landscaping")
        return phrases


class MailClient:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    @staticmethod
    def _create_legacy_ssl_context() -> ssl.SSLContext:
        context = ssl.create_default_context()
        try:
            context.set_ciphers("DEFAULT@SECLEVEL=1")
        except Exception:
            pass
        return context

    def test_smtp_connection(self) -> list[str]:
        host = self.config.mail.get("smtp_host", "")
        port = self.config.mail.getint("smtp_port_ssl", fallback=465)
        starttls_port = self.config.mail.getint("smtp_port_starttls", fallback=25)
        username = self.config.mail.get("username", "")
        password = self.config.mail.get("password", "")

        if not host or not username or not password:
            raise ValueError("SMTP 配置不完整，请检查 config.ini。")

        results: list[str] = []
        ssl_error = None
        starttls_error = None

        try:
            context = self._create_legacy_ssl_context()
            with smtplib.SMTP_SSL(host, port, context=context, timeout=60) as server:
                server.login(username, password)
            results.append(f"465 SSL 登录成功：{host}:{port}")
        except Exception as exc:
            ssl_error = exc
            results.append(f"465 SSL 登录失败：{exc}")

        try:
            with smtplib.SMTP(host, starttls_port, timeout=30) as server:
                server.ehlo()
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
                server.login(username, password)
            results.append(f"25 STARTTLS 登录成功：{host}:{starttls_port}")
        except Exception as exc:
            starttls_error = exc
            results.append(f"25 STARTTLS 登录失败：{exc}")

        if ssl_error and starttls_error:
            raise ValueError("\n".join(results))
        return results

    def send_mail(self, recipient: str, subject: str, body: str, attachments: list[Path] | None = None) -> None:
        host = self.config.mail.get("smtp_host", "")
        port = self.config.mail.getint("smtp_port_ssl", fallback=465)
        username = self.config.mail.get("username", "")
        password = self.config.mail.get("password", "")
        sender_name = self._clean_header_value(self.config.project.get("project_name", ""))
        clean_recipient = self._clean_header_value(recipient)
        clean_subject = self._clean_header_value(subject)

        if not host or not username or not password:
            raise ValueError("SMTP 配置不完整，请检查 config.ini。")

        message = EmailMessage()
        message["From"] = formataddr((sender_name, username)) if sender_name else username
        message["To"] = clean_recipient
        message["Subject"] = clean_subject
        normalized_body = normalize_links_in_text(body)
        email_format = get_email_format(self.config)
        if email_format == "html":
            message.set_content(normalized_body)
            self._attach_html_alternative(message, normalized_body)
        elif email_format == "plain":
            message.set_content(normalized_body)
        else:
            message.set_content(normalized_body)
            self._attach_html_alternative(message, normalized_body)

        self._attach_files(message, attachments or [])

        context = self._create_legacy_ssl_context()
        with smtplib.SMTP_SSL(host, port, context=context, timeout=30) as server:
            server.login(username, password)
            server.send_message(message, from_addr=username, to_addrs=[clean_recipient])

    def reply_mail(
        self,
        original_message: InboxMessage,
        body: str,
        attachments: list[Path] | None = None,
    ) -> None:
        host = self.config.mail.get("smtp_host", "")
        port = self.config.mail.getint("smtp_port_ssl", fallback=465)
        username = self.config.mail.get("username", "")
        password = self.config.mail.get("password", "")
        sender_name = self._clean_header_value(self.config.project.get("project_name", ""))
        clean_recipient = self._clean_header_value(original_message.sender_email)

        if not host or not username or not password:
            raise ValueError("SMTP 配置不完整，请检查 config.ini。")

        message = EmailMessage()
        message["From"] = formataddr((sender_name, username)) if sender_name else username
        message["To"] = clean_recipient
        message["Subject"] = self._build_reply_subject(original_message.subject)
        if original_message.message_id:
            message_id = self._clean_header_value(original_message.message_id)
            message["In-Reply-To"] = message_id
            refs = self._clean_header_value(original_message.references)
            message["References"] = f"{refs} {message_id}".strip() if refs else message_id
        message["Message-ID"] = make_msgid()
        normalized_body = normalize_links_in_text(body)
        email_format = get_email_format(self.config)
        if email_format == "plain":
            message.set_content(normalized_body)
        else:
            message.set_content(normalized_body)
            self._attach_html_alternative(message, normalized_body)

        self._attach_files(message, attachments or [])

        context = self._create_legacy_ssl_context()
        with smtplib.SMTP_SSL(host, port, context=context, timeout=30) as server:
            server.login(username, password)
            server.send_message(message, from_addr=username, to_addrs=[clean_recipient])

    def _attach_files(self, message: EmailMessage, attachments: list[Path]) -> None:
        for file_path in attachments:
            if not file_path.exists() or not file_path.is_file():
                raise ValueError(f"附件文件不存在或无法读取：{file_path}")
            mime_type, _ = mimetypes.guess_type(str(file_path))
            maintype, subtype = ("application", "octet-stream")
            if mime_type:
                maintype, subtype = mime_type.split("/", 1)
            with file_path.open("rb") as file:
                message.add_attachment(
                    file.read(),
                    maintype=maintype,
                    subtype=subtype,
                    filename=file_path.name,
                )

    def _build_html_content(self, body: str) -> str:
        return build_email_template_html(body, self.config)

    def _attach_html_alternative(self, message: EmailMessage, body: str) -> None:
        logo_path_text = get_logo_path(self.config)
        logo_cid = ""
        logo_file = self._resolve_logo_file(logo_path_text)
        if logo_file and logo_file.exists() and logo_file.is_file():
            logo_cid = make_msgid(domain="mail-template-logo")[1:-1]

        html_body = build_email_template_html(body, self.config, f"cid:{logo_cid}" if logo_cid else "")
        message.add_alternative(html_body, subtype="html")

        if not logo_path_text or re.match(r"^https?://", logo_path_text.strip(), flags=re.IGNORECASE):
            return
        if not logo_cid or not logo_file:
            raise ValueError(f"邮件 LOGO 文件不存在或无法读取：{logo_path_text}")
        if not logo_file.exists() or not logo_file.is_file():
            raise ValueError(f"邮件 LOGO 文件不存在或无法读取：{logo_path_text}")

        mime_type, _ = mimetypes.guess_type(str(logo_file))
        if not mime_type or not mime_type.startswith("image/"):
            raise ValueError(f"邮件 LOGO 不是有效图片文件：{logo_file}")

        maintype, subtype = mime_type.split("/", 1)
        with logo_file.open("rb") as file:
            message.get_payload()[-1].add_related(
                file.read(),
                maintype=maintype,
                subtype=subtype,
                cid=f"<{logo_cid}>",
                filename=logo_file.name,
                disposition="inline",
            )

    @staticmethod
    def _resolve_logo_file(path_text: str) -> Path | None:
        value = (path_text or "").strip()
        if not value:
            return None
        if value.lower().startswith("file://"):
            parsed_path = urllib.parse.urlparse(value).path
            if os.name == "nt" and re.match(r"^/[a-zA-Z]:/", parsed_path):
                parsed_path = parsed_path[1:]
            return Path(urllib.parse.unquote(parsed_path))
        if re.match(r"^(https?://|data:|cid:)", value, flags=re.IGNORECASE):
            return None

        logo_file = Path(value)
        if logo_file.exists():
            return logo_file
        candidate = BASE_DIR / logo_file
        if candidate.exists():
            return candidate
        return logo_file
      
    def fetch_recent_inbox(self, limit: int = 20) -> list[dict[str, str]]:
        results: list[dict[str, str]] = []
        client = self._open_imap_client()
        try:
            client.select("INBOX")
            status, data = client.uid("search", None, "ALL")
            if status != "OK":
                return results

            ids = data[0].split()
            for uid in reversed(ids[-limit:]):
                status, msg_data = client.uid("fetch", uid, "(BODY.PEEK[])")
                if status != "OK" or not msg_data or not msg_data[0]:
                    continue
                raw = msg_data[0][1]
                message = BytesParser(policy=default).parsebytes(raw)
                body = self._extract_body(message)
                results.append(
                    {
                        "from": decode_mime(message.get("From", "")),
                        "subject": decode_mime(message.get("Subject", "")),
                        "date": message.get("Date", ""),
                        "body": body[:500].strip(),
                    }
                )
        finally:
            self._close_imap_client(client)
        return results

    def fetch_inbox_messages(
        self,
        limit: int = 20,
        unread_only: bool = False,
        recent_days: int | None = None,
        min_uid: int | None = None,
    ) -> list[InboxMessage]:
        results: list[InboxMessage] = []
        client = self._open_imap_client()
        try:
            client.select("INBOX")
            criteria = ["UNSEEN" if unread_only else "ALL"]
            if min_uid and min_uid > 0:
                criteria.extend(["UID", f"{min_uid + 1}:*"])
            if recent_days:
                since_timestamp = time.time() - max(1, recent_days) * 86400
                criteria.extend(["SINCE", time.strftime("%d-%b-%Y", time.localtime(since_timestamp))])
            status, data = client.uid("search", None, *criteria)
            if status != "OK":
                return results

            ids = data[0].split()
            for uid in reversed(ids[-limit:]):
                status, msg_data = client.uid("fetch", uid, "(BODY.PEEK[])")
                if status != "OK" or not msg_data or not msg_data[0]:
                    continue
                raw = msg_data[0][1]
                message = BytesParser(policy=default).parsebytes(raw)
                sender = decode_mime(message.get("From", ""))
                sender_email = parseaddr(sender)[1].strip().lower()
                subject = decode_mime(message.get("Subject", ""))
                body = self._extract_body(message)
                msg_id = (message.get("Message-ID", "") or "").strip()
                if not msg_id:
                    msg_id = self._build_fallback_message_id(sender_email, subject, message.get("Date", ""), body, uid.decode(errors="ignore"))
                results.append(
                    InboxMessage(
                        uid=uid.decode(errors="ignore"),
                        message_id=msg_id,
                        sender=sender,
                        sender_email=sender_email,
                        subject=subject,
                        date=message.get("Date", ""),
                        body=body.strip(),
                        references=(message.get("References", "") or "").strip(),
                    )
                )
        finally:
            self._close_imap_client(client)
        return sorted(results, key=lambda item: _message_date_timestamp(item), reverse=True)

    def _open_imap_client(self):
        host = self.config.mail.get("imap_host", "")
        ssl_port = self.config.mail.getint("imap_port_ssl", fallback=993)
        starttls_port = self.config.mail.getint("imap_port_starttls", fallback=143)
        username = self.config.mail.get("username", "")
        password = self.config.mail.get("password", "")
        if not host or not username or not password:
            raise ValueError("IMAP 配置不完整，请检查 config.ini。")

        context = self._create_legacy_ssl_context()
        errors: list[str] = []

        try:
            client = imaplib.IMAP4_SSL(host, ssl_port, ssl_context=context)
            try:
                client.login(username, password)
                return client
            except Exception:
                self._close_imap_client(client)
                raise
        except Exception as exc:
            errors.append(f"SSL {host}:{ssl_port} 失败：{exc}")

        try:
            client = imaplib.IMAP4(host, starttls_port)
            try:
                client.starttls(ssl_context=context)
                client.login(username, password)
                return client
            except Exception:
                self._close_imap_client(client)
                raise
        except Exception as exc:
            errors.append(f"STARTTLS {host}:{starttls_port} 失败：{exc}")

        raise ValueError("IMAP 收信登录失败：" + "；".join(errors))

    @staticmethod
    def _close_imap_client(client) -> None:
        try:
            client.logout()
        except Exception:
            try:
                client.shutdown()
            except Exception:
                pass

    def _extract_body(self, message) -> str:
        if message.is_multipart():
            html_body = ""
            for part in message.walk():
                content_type = part.get_content_type()
                disposition = str(part.get("Content-Disposition", ""))
                if content_type == "text/plain" and "attachment" not in disposition.lower():
                    try:
                        return part.get_content()
                    except Exception:
                        continue
                if content_type == "text/html" and "attachment" not in disposition.lower() and not html_body:
                    try:
                        html_body = part.get_content()
                    except Exception:
                        continue
            return self._strip_html(html_body)
        try:
            content = message.get_content()
            if message.get_content_type() == "text/html":
                return self._strip_html(content)
            return content
        except Exception:
            return ""

    @staticmethod
    def _strip_html(html: str) -> str:
        if not html:
            return ""
        text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
        text = re.sub(r"(?i)<br\s*/?>", "\n", text)
        text = re.sub(r"(?i)</p>|</div>|</li>|</tr>|</table>", "\n", text)
        text = re.sub(r"(?s)<.*?>", " ", text)
        text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        text = re.sub(r"\r", "", text)
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()

    @staticmethod
    def _build_reply_subject(subject: str) -> str:
        clean_subject = MailClient._clean_header_value(subject)
        if clean_subject.lower().startswith("re:"):
            return clean_subject
        return f"Re: {clean_subject}" if clean_subject else "Re:"

    @staticmethod
    def _clean_header_value(value: str) -> str:
        text = str(value or "").replace("\r", " ").replace("\n", " ")
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _build_fallback_message_id(sender_email: str, subject: str, date: str, body: str, uid: str = "") -> str:
        raw = f"{uid}|{sender_email}|{subject}|{date}|{body[:500]}"
        return hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()


def extract_clean_reply_body(body: str) -> str:
    text = (body or "").strip()
    if not text:
        return ""

    split_patterns = [
        r"\n[- ]{2,}\s*回复的原邮件\s*[- ]{2,}",
        r"\n[- ]{2,}\s*Original Message\s*[- ]{2,}",
        r"\nOn .+?wrote:",
        r"\n发件人[:：]",
    ]
    for pattern in split_patterns:
        parts = re.split(pattern, text, maxsplit=1, flags=re.IGNORECASE | re.DOTALL)
        if len(parts) > 1:
            text = parts[0].strip()
            break

    return text.strip()


def extract_customer_display_name(sender: str, sender_email: str) -> str:
    display_name = decode_mime(parseaddr(sender or "")[0]).strip()
    if display_name:
        cleaned = re.sub(r"[<>\"']", "", display_name).strip()
        if cleaned:
            return cleaned

    local_part = (sender_email or "").split("@", 1)[0].strip()
    local_part = re.sub(r"[._\-]+", " ", local_part)
    local_part = re.sub(r"\d+", " ", local_part)
    local_part = re.sub(r"\s+", " ", local_part).strip()
    if local_part:
        words = [word.capitalize() if word.isascii() else word for word in local_part.split()]
        return " ".join(words)
    return "there"


def normalize_links_in_text(text: str) -> str:
    value = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"(?i)(here|download|website|link|catalogue|catalog)\s*:\s*(https?://)", r"\1: \2", value)
    value = re.sub(r"(?<!\s)(https?://)", r" \1", value)
    value = re.sub(r"\s+\n", "\n", value)
    return value.strip()


def text_to_basic_html(text: str) -> str:
    safe = html_escape(normalize_links_in_text(text))
    safe = re.sub(
        r"(https?://[^\s<]+)",
        lambda match: f'<a href="{match.group(1)}">{match.group(1)}</a>',
        safe,
    )
    safe = safe.replace("\n", "<br>")
    return f"<html><body style=\"font-family:Arial, sans-serif; font-size:14px; line-height:1.6;\">{safe}</body></html>"


def html_escape(text: str) -> str:
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def normalize_color(value: str, default: str) -> str:
    color = (value or "").strip()
    if re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        return color.lower()
    rgb_match = re.fullmatch(r"rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)", color, flags=re.IGNORECASE)
    if rgb_match:
        values = [max(0, min(255, int(part))) for part in rgb_match.groups()]
        return "#{:02x}{:02x}{:02x}".format(*values)
    comma_match = re.fullmatch(r"\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*", color)
    if comma_match:
        values = [max(0, min(255, int(part))) for part in comma_match.groups()]
        return "#{:02x}{:02x}{:02x}".format(*values)
    return default


def get_email_format(config: AppConfig) -> str:
    value = config.email_template.get("email_format", "both").strip().lower()
    return value if value in {"both", "html", "plain"} else "both"


def get_logo_path(config: AppConfig) -> str:
    return config.email_template.get("logo_path", "").strip() or config.project.get("logo_path", "").strip()


def get_logo_src_for_html(config: AppConfig, logo_src: str = "") -> str:
    if logo_src:
        return logo_src

    logo_path = get_logo_path(config)
    if not logo_path:
        return ""
    if re.match(r"^(https?://|cid:|data:|file://)", logo_path, flags=re.IGNORECASE):
        return logo_path

    logo_file = Path(logo_path)
    if logo_file.exists() and logo_file.is_file():
        return logo_file.resolve().as_uri()

    return ""


def get_template_color(config: AppConfig, key: str) -> str:
    return normalize_color(config.email_template.get(key, ""), DEFAULT_TEMPLATE_COLORS[key])


def get_footer_lines(config: AppConfig) -> list[str]:
    project = config.project
    contact_phone = project.get("contact_phone", "").strip()
    contact_email = project.get("contact_email", "").strip() or config.mail.get("username", "").strip()
    office_address = project.get("office_address", "").strip()
    factory_address = project.get("factory_address", "").strip()
    copyright_text = project.get("copyright_text", "").strip()
    project_name = project.get("project_name", "").strip()
    if not copyright_text and project_name:
        copyright_text = f"Copyright {project_name}"

    lines = []
    if contact_phone or contact_email:
        parts = []
        if contact_phone:
            parts.append(f"Phone: {contact_phone}")
        if contact_email:
            parts.append(f"Email: {contact_email}")
        lines.append("  ".join(parts))
    if office_address:
        lines.append(f"Office Address: {office_address}")
    if factory_address:
        lines.append(f"Factory Address: {factory_address}")
    if copyright_text:
        lines.append(copyright_text)
    return lines


def _linkify_html_text(text: str) -> str:
    safe = html_escape(normalize_links_in_text(text))
    return re.sub(
        r"(https?://[^\s<]+)",
        lambda match: f'<a href="{match.group(1)}" style="color:#1a73e8; text-decoration:underline;">{match.group(1)}</a>',
        safe,
    )


def _format_footer_address(address: str) -> str:
    safe = html_escape(address)
    return re.sub(
        r",\s*(China\(Mainland\))$",
        r",<br>\1",
        safe,
        flags=re.IGNORECASE,
    )


def build_footer_html(config: AppConfig) -> str:
    project = config.project
    contact_phone = project.get("contact_phone", "").strip()
    contact_email = project.get("contact_email", "").strip() or config.mail.get("username", "").strip()
    office_address = project.get("office_address", "").strip()
    factory_address = project.get("factory_address", "").strip()
    copyright_text = project.get("copyright_text", "").strip()
    project_name = project.get("project_name", "").strip()
    if not copyright_text and project_name:
        copyright_text = f"Copyright {project_name}"

    rows = []
    contact_parts = []
    if contact_phone:
        contact_parts.append(f"<strong>Phone:</strong> {html_escape(contact_phone)}")
    if contact_email:
        safe_email = html_escape(contact_email)
        contact_parts.append(
            f'<strong>Email:</strong> <a href="mailto:{safe_email}" '
            'style="color:#0000ee; text-decoration:underline;">'
            f"{safe_email}</a>"
        )
    if contact_parts:
        rows.append(" ".join(contact_parts))
    if office_address:
        rows.append(f"<strong>Office Address:</strong> {_format_footer_address(office_address)}")
    if factory_address:
        rows.append(f"<strong>Factory Address:</strong> {_format_footer_address(factory_address)}")
    if copyright_text:
        rows.append(html_escape(copyright_text))
    return "<br>".join(rows) or "&nbsp;"


def split_email_template_sections(text: str, config: AppConfig) -> tuple[str, str, str, str]:
    normalized_text = normalize_links_in_text(text)
    lines = [line.strip() for line in normalized_text.splitlines()]
    non_empty_lines = [line for line in lines if line]

    greeting_line = "Dear"
    if non_empty_lines and re.match(r"^(dear|hi|hello)\b", non_empty_lines[0], flags=re.IGNORECASE):
        greeting_line = non_empty_lines.pop(0)

    closing_index = None
    for index, line in enumerate(non_empty_lines):
        if re.match(r"^(best regards|kind regards|regards|sincerely)\b", line, flags=re.IGNORECASE):
            closing_index = index
            break

    project = config.project
    contact_name = project.get("contact_name", "").strip() or project.get("project_name", "").strip() or "Our team"
    closing_line = "Best regards,"
    sender_line = contact_name

    if closing_index is not None:
        closing_line = non_empty_lines[closing_index]
        content_lines = non_empty_lines[:closing_index]
    else:
        content_lines = non_empty_lines

    content_text = "\n".join(content_lines).strip()
    return greeting_line, content_text, closing_line, sender_line


def build_email_template_preview_text(text: str, config: AppConfig) -> str:
    greeting_line, content_text, closing_line, sender_line = split_email_template_sections(text, config)
    project = config.project
    project_name = project.get("project_name", "").strip()
    project_website = project.get("project_website", "").strip()
    today = time.strftime("%Y-%m-%d")
    footer_lines = get_footer_lines(config)

    parts = [
        f"Date:{today}",
        project_name,
        "",
        greeting_line,
        "",
        content_text or "-",
        "",
        closing_line,
        sender_line,
        "",
    ]
    parts.extend(footer_lines)
    if project_website:
        parts.append(project_website)
    return "\n".join(parts).strip()


def build_email_template_html(text: str, config: AppConfig, logo_src: str = "") -> str:
    greeting_line, content_text, closing_line, sender_line = split_email_template_sections(text, config)
    content_html = _linkify_html_text(content_text).replace("\n", "<br>") or "&nbsp;"

    project = config.project
    project_name = project.get("project_name", "").strip()
    header_line_color = get_template_color(config, "header_line_color")
    footer_background_color = get_template_color(config, "footer_background_color")
    footer_text_color = get_template_color(config, "footer_text_color")
    footer_html = build_footer_html(config)
    logo_path = get_logo_src_for_html(config, logo_src)
    logo_html = ""
    if logo_path:
        logo_html = (
            '<table border="0" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">'
            '<tr>'
            '<td style="vertical-align:middle; padding-right:12px;">'
            f'<img src="{html_escape(logo_path)}" alt="{html_escape(project_name)}" '
            'style="max-height:78px; max-width:120px; vertical-align:middle;">'
            '</td>'
            f'<td style="vertical-align:middle; font-family: Microsoft Yahei, Arial, sans-serif; font-size:24px; font-weight:bold; color:#222;">{html_escape(project_name)}</td>'
            '</tr>'
            '</table>'
        )
    company_html = html_escape(project_name) if project_name else "&nbsp;"
    today = time.strftime("%Y-%m-%d")

    return f"""<html>
<body>
<table border="0" width="100%" cellpadding="0" cellspacing="0">
  <tbody>
    <tr>
      <td style="padding: 10px 0 30px 0;">
        <table style="border: 1px solid #cccccc; border-collapse: collapse;" align="center" border="0" width="700" cellpadding="0" cellspacing="0">
          <tbody>
            <tr>
              <td style="height:90px; padding: 0 25px; background:#ffffff;">
                <table border="0" width="100%" cellpadding="0" cellspacing="0">
                  <tr>
                    <td style="height:90px; vertical-align:middle; font-family: Microsoft Yahei, Arial, sans-serif; font-size:24px; font-weight:bold; color:#222;">
                      {logo_html or company_html}
                    </td>
                    <td align="right" style="height:90px; vertical-align:middle; font-family: Microsoft Yahei, Arial, sans-serif; font-size: 14px; color:#111;">
                      <b>Date</b>:{html_escape(today)}
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="width:100%; height:5px; background:{html_escape(header_line_color)};"></td>
            </tr>
            <tr>
              <td style="padding: 30px;">
                <table border="0" width="100%" cellpadding="0" cellspacing="0">
                  <tbody>
                    <tr>
                      <td style="color: #333; font-family: Microsoft Yahei, Arial, sans-serif; font-size: 14px;">{html_escape(greeting_line)}</td>
                    </tr>
                    <tr>
                      <td style="padding: 25px 0px; color: #333; font-family: Microsoft Yahei, Arial, sans-serif; font-size: 14px; line-height: 30px;">{content_html}</td>
                    </tr>
                    <tr>
                      <td style="padding: 25px 0px; color: #333; font-family: Microsoft Yahei, Arial, sans-serif; font-size: 14px; line-height: 30px;">{html_escape(closing_line)}<br>{html_escape(sender_line)}</td>
                    </tr>
                  </tbody>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding: 18px 10px; background: {html_escape(footer_background_color)};">
                <table border="0" width="100%" cellpadding="0" cellspacing="0">
                  <tbody>
                    <tr>
                      <td style="color: {html_escape(footer_text_color)}; font-family: Microsoft Yahei, Arial, sans-serif; font-size: 12px; line-height: 16px; text-align:center;" width="100%" align="center">
                        {footer_html}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </td>
            </tr>
          </tbody>
        </table>
      </td>
    </tr>
  </tbody>
</table>
</body>
</html>"""


class AIReplyEngine:
    INTENT_KEYWORDS = {
        "catalog": ["catalog", "catalogue", "brochure", "leaflet"],
        "quotation": ["quotation", "quote", "price", "pricing", "cost", "offer"],
        "certificate": ["certificate", "certification", "certified", "compliance", "report"],
        "delivery": ["lead time", "delivery", "shipping", "ship", "etd", "eta"],
        "payment": ["payment", "pay", "tt", "t t", "lc", "l c", "terms"],
        "sample": ["sample", "sampling"],
        "moq": ["moq", "minimum order", "minimum quantity"],
        "warranty": ["warranty", "guarantee"],
        "installation": ["install", "installation"],
    }

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.local_rules = self._load_local_rules()
        self.local_rules_load_note = self._build_local_rules_note()

    def generate_reply(self, message: InboxMessage) -> dict:
        local_matches = self._find_local_rule_matches(message)
        if len(local_matches) >= 2:
            try:
                merged = self._generate_multi_question_reply(message, local_matches)
                merged["source"] = "local_docx_api"
                merged["matched_keyword"] = " | ".join(match["matched_keyword"] for match in local_matches)
                return merged
            except Exception:
                combined_reply = "\n\n".join(
                    self._normalize_reply_paragraphs(match["reply_body"])
                    for match in local_matches
                )
                return {
                    "reply_body": combined_reply,
                    "attach_quote": False,
                    "attach_catalog": False,
                    "attach_certificate": False,
                    "source": "local_docx_multi",
                    "matched_keyword": " | ".join(match["matched_keyword"] for match in local_matches),
                }

        local_match = local_matches[0] if local_matches else None
        if local_match:
            return {
                "reply_body": self._normalize_reply_paragraphs(local_match["reply_body"]),
                "attach_quote": False,
                "attach_catalog": False,
                "attach_certificate": False,
                "source": "local_docx",
                "matched_keyword": local_match["matched_keyword"],
            }

        prompt = self._build_prompt(message)
        payload = {
            "model": self.config.ai.get("model", "gpt-4o-mini"),
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an experienced B2B foreign trade sales assistant. "
                        "Write concise, professional, natural English email replies. "
                        "Never sound exaggerated, spammy, or pushy. "
                        "Reply in a sincere and concise B2B style. "
                        "Return JSON only with keys: reply_body, attach_quote, attach_catalog, attach_certificate. "
                        "reply_body must contain the main response content only. "
                        "Do not include greeting, customer name, signature, or website."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        }

        parsed = self._call_ai_json(payload)

        return {
            "reply_body": self._normalize_reply_paragraphs((parsed.get("reply_body", "") or "").strip()),
            "attach_quote": bool(parsed.get("attach_quote")),
            "attach_catalog": bool(parsed.get("attach_catalog")),
            "attach_certificate": bool(parsed.get("attach_certificate")),
            "source": "api",
            "matched_keyword": "",
        }

    def _generate_multi_question_reply(self, message: InboxMessage, local_matches: list[dict]) -> dict:
        sender_name = self.config.project.get("project_name", "").strip() or "Our team"
        website = self.config.project.get("project_website", "").strip() or "-"
        snippets = []
        for index, match in enumerate(local_matches, start=1):
            snippets.append(
                f"Question {index}: {match['matched_keyword']}\n"
                f"Answer {index}: {self._normalize_reply_paragraphs(match['reply_body'])}"
            )
        prompt = (
            "Write one coherent English reply body for a B2B foreign trade email.\n"
            "The customer asked multiple questions. You must answer all of them clearly and naturally.\n"
            "Use the provided local approved answers as the factual basis.\n"
            "Do not ignore any question. Do not add unsupported claims.\n"
            "Do not include greeting or signature.\n"
            "Keep the reply concise, professional, and natural with clean paragraph breaks.\n\n"
            f"Our company name: {sender_name}\n"
            f"Our website: {website}\n\n"
            f"Customer subject: {message.subject}\n"
            f"Customer email body:\n{message.body}\n\n"
            "Approved local answers:\n"
            + "\n\n".join(snippets)
        )
        payload = {
            "model": self.config.ai.get("model", "gpt-4o-mini"),
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an experienced B2B foreign trade sales assistant. "
                        "Return JSON only with keys: reply_body, attach_quote, attach_catalog, attach_certificate. "
                        "reply_body must answer all customer questions using the approved local answers only. "
                        "Do not include greeting or signature."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        }
        parsed = self._call_ai_json(payload)
        return {
            "reply_body": self._normalize_reply_paragraphs((parsed.get("reply_body", "") or "").strip()),
            "attach_quote": bool(parsed.get("attach_quote")),
            "attach_catalog": bool(parsed.get("attach_catalog")),
            "attach_certificate": bool(parsed.get("attach_certificate")),
        }

    def _call_ai_json(self, payload: dict) -> dict:
        base_url = self.config.ai.get("base_url", "https://api.openai.com")
        api_key = self.config.ai.get("api_key", "").strip()
        if not api_key:
            raise ValueError("AI 配置不完整，请在 config.ini 中填写 ai.api_key。")

        endpoint = base_url.rstrip("/") + "/v1/chat/completions"
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise ValueError(f"AI 接口调用失败：HTTP {exc.code} {detail}") from exc
        except Exception as exc:
            raise ValueError(f"AI 接口调用失败：{exc}") from exc

        try:
            data = json.loads(raw)
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)
        except Exception as exc:
            raise ValueError(f"AI 返回结果解析失败：{exc}") from exc

    def build_attachment_list(self, ai_result: dict, message: InboxMessage) -> list[Path]:
        attachments: list[Path] = []
        requested = self._detect_attachment_intent(message)

        if self._fixed_attachment_enabled():
            fixed_path = self.config.attachments.get("fixed_attachment_path", "").strip()
            if fixed_path:
                attachments.append(Path(fixed_path))

        if ai_result.get("attach_quote") or requested["quote"]:
            quote_path = self.config.attachments.get("quote_path", "").strip()
            if quote_path:
                attachments.append(Path(quote_path))
        if ai_result.get("attach_catalog") or requested["catalog"]:
            catalog_path = self.config.attachments.get("catalog_path", "").strip()
            if catalog_path:
                attachments.append(Path(catalog_path))
        if ai_result.get("attach_certificate") or requested["certificate"]:
            certificate_path = self.config.attachments.get("certificate_path", "").strip()
            if certificate_path:
                attachments.append(Path(certificate_path))

        unique: list[Path] = []
        seen: set[str] = set()
        for item in attachments:
            key = str(item).lower()
            if key not in seen:
                unique.append(item)
                seen.add(key)
        return unique

    def build_fallback_reply(self, message: InboxMessage) -> dict:
        lowered = f"{message.subject}\n{message.body}".lower()

        if any(keyword in lowered for keyword in ["price", "quotation", "quote", "cost", "pricing"]):
            reply_body = (
                "Thank you for your message.\n\n"
                "I have attached our quotation for your reference. "
                "If you would like, you can share a few more details about your requirement and we can follow up accordingly."
            )
            return {"reply_body": reply_body, "attach_quote": True, "attach_catalog": False, "attach_certificate": False, "source": "fallback", "matched_keyword": ""}

        if any(keyword in lowered for keyword in ["product", "catalog", "spec", "details", "brochure"]):
            reply_body = (
                "Thank you for your inquiry.\n\n"
                "I have attached our catalog for your reference. "
                "If there is anything specific you would like us to focus on, please feel free to let us know."
            )
            return {"reply_body": reply_body, "attach_quote": False, "attach_catalog": True, "attach_certificate": False, "source": "fallback", "matched_keyword": ""}

        if any(keyword in lowered for keyword in ["certificate", "certification", "test report", "compliance"]):
            reply_body = (
                "Thank you for your email.\n\n"
                "I have attached the relevant certificate file for your reference.\n\n"
                "Please let me know if you need any additional information."
            )
            return {"reply_body": reply_body, "attach_quote": False, "attach_catalog": False, "attach_certificate": True, "source": "fallback", "matched_keyword": ""}

        reply_body = (
            "Thank you for your message.\n\n"
            "We appreciate your note and are glad to stay in touch. "
            "If there is anything you would like to discuss further, please feel free to let us know."
        )
        return {"reply_body": reply_body, "attach_quote": False, "attach_catalog": False, "attach_certificate": False, "source": "fallback", "matched_keyword": ""}

    def _build_prompt(self, message: InboxMessage) -> str:
        sender_name = self.config.project.get("project_name", "").strip() or "Our team"
        website = self.config.project.get("project_website", "").strip() or "-"
        return (
            "Write a reply email in English for a B2B foreign trade conversation.\n"
            "Requirements:\n"
            "- Professional, concise, natural, and polite.\n"
            "- No exaggerated claims, no spammy marketing tone.\n"
            "- Do not hard sell. Keep it sincere, brief, and professional.\n"
            "- If the customer asks about price, respond appropriately and indicate attach_quote=true.\n"
            "- If the customer asks about product details or catalog, indicate attach_catalog=true.\n"
            "- If the customer asks for certification/compliance documents, indicate attach_certificate=true.\n"
            "- If the customer only greets or writes briefly, reply shortly and politely.\n"
            "- Output the response body only, without greeting or signature.\n"
            "- Keep natural paragraph breaks when helpful.\n\n"
            f"Our company name: {sender_name}\n"
            f"Our website: {website}\n\n"
            f"Customer sender: {message.sender}\n"
            f"Customer subject: {message.subject}\n"
            f"Customer email body:\n{message.body}\n"
        )

    def _load_local_rules(self) -> list[dict[str, str]]:
        path_value = self.config.ai.get("local_reply_docx_path", "").strip()
        if not path_value:
            return []
        file_path = Path(path_value)
        if not file_path.exists():
            return []

        try:
            with zipfile.ZipFile(file_path, "r") as archive:
                xml_data = archive.read("word/document.xml")
        except Exception:
            return []

        namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        try:
            root = ET.fromstring(xml_data)
        except Exception:
            return []

        paragraphs: list[str] = []
        for paragraph in root.findall(".//w:p", namespace):
            texts = [node.text or "" for node in paragraph.findall(".//w:t", namespace)]
            line = "".join(texts).strip()
            if line:
                paragraphs.append(line)

        faq_rules = self._parse_faq_docx_rules(paragraphs)
        if faq_rules:
            return faq_rules
        return self._parse_inline_docx_rules(paragraphs)

    def _parse_faq_docx_rules(self, paragraphs: list[str]) -> list[dict[str, str]]:
        rules: list[dict[str, str]] = []
        question_text = ""
        answer_lines: list[str] = []

        def flush_rule() -> None:
            nonlocal question_text, answer_lines
            question = question_text.strip()
            answer_parts = [line.strip() for line in answer_lines if line.strip()]
            answer = self._normalize_reply_paragraphs("\n\n".join(answer_parts))
            if question and answer:
                rules.append({
                    "keyword": question,
                    "reply_body": answer,
                    "intent": self._detect_intent_from_text(question),
                    "tokens": self._extract_keyword_tokens(question),
                })
            question_text = ""
            answer_lines = []

        for raw_line in paragraphs:
            line = (raw_line or "").strip()
            if not line:
                continue
            if self._is_docx_question_line(line):
                flush_rule()
                question_text = self._clean_docx_question_line(line)
                continue
            if question_text:
                answer_lines.append(line)

        flush_rule()
        return rules

    def _parse_inline_docx_rules(self, paragraphs: list[str]) -> list[dict[str, str]]:
        rules: list[dict[str, str]] = []
        for line in paragraphs:
            if "," not in line:
                continue
            keyword_part, reply_part = line.split(",", 1)
            keyword = keyword_part.strip()
            reply = self._normalize_reply_paragraphs(reply_part.strip())
            if keyword and reply:
                rules.append({
                    "keyword": keyword,
                    "reply_body": reply,
                    "intent": self._detect_intent_from_text(keyword),
                    "tokens": self._extract_keyword_tokens(keyword),
                })
        return rules

    @staticmethod
    def _is_docx_question_line(line: str) -> bool:
        return bool(re.match(r"^\d+[\.\)]\s*.+", (line or "").strip()))

    @staticmethod
    def _clean_docx_question_line(line: str) -> str:
        return re.sub(r"^\d+[\.\)]\s*", "", (line or "").strip()).strip()

    def _build_local_rules_note(self) -> str:
        path_value = self.config.ai.get("local_reply_docx_path", "").strip()
        if not path_value:
            return "未选择本地话术文件。"
        if not Path(path_value).exists():
            return f"本地话术文件不存在：{path_value}"
        if not self.local_rules:
            return f"已读取文件，但未提取到有效话术：{path_value}"
        return f"已加载本地话术 {len(self.local_rules)} 条。"

    def _find_local_rule_matches(self, message: InboxMessage) -> list[dict]:
        customer_text = self._extract_customer_question_text(message)
        segments = self._split_customer_question_segments(customer_text)
        if not segments:
            segments = [customer_text]

        unique_matches: list[dict] = []
        seen_keywords: set[str] = set()
        for segment in segments:
            best_match = self._find_best_local_rule_for_text(segment)
            if not best_match:
                continue
            key = best_match["matched_keyword"].strip().lower()
            if key in seen_keywords:
                continue
            unique_matches.append(best_match)
            seen_keywords.add(key)

        if unique_matches:
            return unique_matches[:3]

        fallback_match = self._find_best_local_rule_for_text(customer_text)
        return [fallback_match] if fallback_match else []

    def _find_best_local_rule_for_text(self, customer_text: str) -> dict | None:
        haystack = self._normalize_match_text(customer_text)
        haystack_tokens = set(self._extract_keyword_tokens(customer_text))
        message_intent = self._detect_intent_from_text(customer_text)
        scored_matches: list[tuple[float, dict]] = []

        for rule in self.local_rules:
            keyword = (rule.get("keyword", "") or "").strip()
            if not keyword:
                continue
            rule_intent = (rule.get("intent", "") or "").strip()
            if message_intent and rule_intent and rule_intent != message_intent:
                continue
            normalized_keyword = self._normalize_match_text(keyword)
            if normalized_keyword and normalized_keyword in haystack:
                scored_matches.append((1.0, {"matched_keyword": keyword, "reply_body": rule["reply_body"]}))
                continue

            keyword_tokens = rule.get("tokens") or self._extract_keyword_tokens(keyword)
            if not keyword_tokens or not haystack_tokens:
                continue
            if not haystack_tokens.intersection(keyword_tokens):
                continue

            overlap = self._keyword_match_score(keyword_tokens, haystack_tokens)
            reverse_overlap = self._keyword_match_score(list(haystack_tokens), set(keyword_tokens))
            phrase_bonus = self._phrase_similarity_bonus(keyword, customer_text)
            score = (overlap * 0.55) + (reverse_overlap * 0.25) + phrase_bonus
            scored_matches.append((score, {"matched_keyword": keyword, "reply_body": rule["reply_body"]}))

        threshold = 0.5 if message_intent else 0.72
        filtered = [item for item in scored_matches if item[0] >= threshold]
        filtered.sort(key=lambda item: item[0], reverse=True)
        return filtered[0][1] if filtered else None

    def _split_customer_question_segments(self, text: str) -> list[str]:
        value = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
        if not value:
            return []
        value = re.sub(r"\s+and\s+i\s+would\s+like\s+to\s+", "\nI would like to ", value, flags=re.IGNORECASE)
        value = re.sub(r"\s+and\s+please\s+", "\nPlease ", value, flags=re.IGNORECASE)
        value = re.sub(r"\?\s*", "?\n", value)
        segments = re.split(r"[\n;]+", value)
        result = []
        for segment in segments:
            cleaned = segment.strip(" ,.")
            if cleaned:
                result.append(cleaned)
        return result[:5]

    def _phrase_similarity_bonus(self, rule_keyword: str, customer_text: str) -> float:
        rule_text = self._normalize_match_text(rule_keyword)
        customer = self._normalize_match_text(customer_text)
        comparable_pairs = [
            ("installation", ["installation time", "how long", "take", "takes", "days", "duration", "working days"]),
            ("lead time", ["lead time", "delivery time", "shipping time", "eta", "etd"]),
            ("catalog", ["catalog", "catalogue", "brochure", "product list"]),
            ("quotation", ["quotation", "quote", "price", "cost", "how much"]),
            ("sample", ["sample", "samples"]),
            ("warranty", ["warranty", "guarantee", "years"]),
        ]
        for anchor, phrases in comparable_pairs:
            rule_hit = anchor in rule_text or any(phrase in rule_text for phrase in phrases)
            customer_hit = anchor in customer or any(phrase in customer for phrase in phrases)
            if rule_hit and customer_hit:
                return 0.25
        return 0.0

    def _extract_customer_question_text(self, message: InboxMessage) -> str:
        clean_body = extract_clean_reply_body(message.body)
        lines = [line.strip() for line in clean_body.splitlines() if line.strip()]
        if lines:
            return "\n".join(lines[:6])
        return f"{message.subject}\n{clean_body}".strip()

    @staticmethod
    def _normalize_reply_paragraphs(text: str) -> str:
        value = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
        value = re.sub(r"^\s*(dear|hi|hello)\b[^\n]*,?\s*", "", value, count=1, flags=re.IGNORECASE)
        value = re.split(r"\n\s*(best regards|kind regards|regards|sincerely)[\s,]*\n?", value, maxsplit=1, flags=re.IGNORECASE)[0]
        lines = [line.rstrip() for line in value.split("\n")]
        normalized: list[str] = []
        blank_pending = False
        for line in lines:
            if not line.strip():
                blank_pending = True
                continue
            if blank_pending and normalized:
                normalized.append("")
            normalized.append(line.strip())
            blank_pending = False
        return normalize_links_in_text("\n".join(normalized).strip())

    def _fixed_attachment_enabled(self) -> bool:
        value = self.config.attachments.get("fixed_attachment_enabled", "false").strip().lower()
        return value in {"1", "true", "yes", "on"}

    @staticmethod
    def _normalize_match_text(text: str) -> str:
        value = (text or "").lower()
        value = re.sub(r"https?://\S+", " ", value)
        value = re.sub(r"[^a-z0-9\s]", " ", value)
        value = re.sub(r"\s+", " ", value)
        return value.strip()

    def _extract_keyword_tokens(self, text: str) -> list[str]:
        synonym_map = {
            "catalogue": "catalog",
            "brochure": "catalog",
            "catalogs": "catalog",
            "catalogues": "catalog",
            "booklet": "catalog",
            "price": "quotation",
            "prices": "quotation",
            "quote": "quotation",
            "quotes": "quotation",
            "pricing": "quotation",
            "cost": "quotation",
            "costs": "quotation",
            "amount": "quotation",
            "spec": "specification",
            "specs": "specification",
            "detail": "information",
            "details": "information",
            "info": "information",
            "product": "products",
            "products": "products",
            "certification": "certificate",
            "certifications": "certificate",
            "installing": "installation",
            "installed": "installation",
            "setup": "installation",
            "duration": "time",
            "timeline": "time",
            "days": "time",
            "day": "time",
            "takes": "time",
            "take": "time",
            "long": "time",
            "timing": "time",
        }
        stopwords = {
            "a", "an", "the", "to", "for", "of", "in", "on", "with", "and", "or",
            "is", "are", "do", "you", "your", "can", "could", "would", "please",
            "me", "i", "we", "our", "it", "this", "that", "have", "has", "what"
        }
        normalized = self._normalize_match_text(text)
        tokens = []
        for raw_token in normalized.split():
            if len(raw_token) < 3 or raw_token in stopwords:
                continue
            token = synonym_map.get(raw_token, raw_token)
            tokens.append(token)
        deduped: list[str] = []
        for token in tokens:
            if token not in deduped:
                deduped.append(token)
        return deduped

    @staticmethod
    def _keyword_match_score(tokens: list[str], haystack_tokens: set[str]) -> float:
        if not tokens:
            return 0.0
        matched = sum(1 for token in tokens if token in haystack_tokens)
        return matched / len(tokens)

    def _detect_intent_from_text(self, text: str) -> str:
        normalized = self._normalize_match_text(text)
        for intent, keywords in self.INTENT_KEYWORDS.items():
            for keyword in keywords:
                keyword_tokens = self._extract_keyword_tokens(keyword)
                if not keyword_tokens:
                    continue
                if all(token in normalized.split() for token in keyword_tokens):
                    return intent
                if keyword in normalized:
                    return intent
        return ""

    @staticmethod
    def _detect_attachment_intent(message: InboxMessage) -> dict[str, bool]:
        text = f"{message.subject}\n{message.body}".lower()
        return {
            "quote": any(keyword in text for keyword in ["price", "quotation", "quote", "cost", "pricing"]),
            "catalog": any(keyword in text for keyword in ["product", "catalog", "brochure", "details", "spec"]),
            "certificate": any(keyword in text for keyword in ["certificate", "certification", "compliance", "test report"]),
        }


class MailAutomationApp:
    BUSINESS_KEYWORDS = [
        "catalog", "catalogue", "brochure", "product list", "price", "quote", "quotation",
        "sample", "samples", "install", "installation", "cost", "how much", "warranty",
        "guarantee", "years", "safe", "pet", "kids", "children", "non-toxic", "eco-friendly",
        "drain", "drainage", "water", "rain", "fade", "sun", "uv", "resistant", "color",
        "turf", "grass", "artificial", "synthetic", "lawn", "garden", "project", "order",
        "wholesale", "dealer", "distributor", "need", "want", "looking for", "send me",
        "provide", "produce", "production", "where", "how", "when", "size", "height", "density", "quality",
        "lead time", "shipping", "delivery", "factory", "manufacturer", "manufacture", "manufacturing", "yarn",
    ]
    SYSTEM_SENDER_KEYWORDS = [
        "mailer-daemon", "postmaster", "daemon", "no-reply", "noreply", "auto", "notification",
    ]
    SYSTEM_SUBJECT_KEYWORDS = [
        "undeliverable", "delivery status notification", "failure notice", "returned mail",
        "auto reply", "automatic reply", "out of office", "vacation", "away from office",
        "delivery failure", "mail delivery subsystem",
    ]
    AUTO_REPLY_BODY_KEYWORDS = [
        "automatic reply", "auto reply", "out of office", "away from the office",
        "i am currently out", "thank you for your email", "this is an automated response",
        "i will be back", "on leave", "vacation responder",
    ]
    SIGNATURE_KEYWORDS = [
        "certified", "hubl", "hub", "mbe", "wbe", "dbe", "minority business", "signature",
        "best regards", "kind regards", "regards", "thanks and regards", "sincerely",
        "phone", "tel", "mobile", "email", "website", "www.", "http://", "https://",
    ]
    MEANINGLESS_SHORT_PHRASES = {
        "thanks", "thank you", "ok", "okay", "noted", "received", "got it", "sure",
        "fine", "great", "good", "hello", "hi", "test", "welcome",
    }

    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title("外贸邮件自动化发送系统")
        self.root.geometry("1180x760")

        self.config = AppConfig(CONFIG_PATH)
        self.log_queue: queue.Queue = queue.Queue()
        self.records: list[CustomerRecord] = []
        self.record_statuses: list[str] = []
        self.sent_log_items: list[dict[str, str]] = []
        self.sent_emails: set[str] = set()
        self.replied_email_ids: set[str] = set()
        self.reply_history: dict[str, dict[str, str]] = {}
        self.is_sending = False
        self.stop_requested = False
        self.suppress_customer_select_event = False
        self.is_auto_replying = False
        self.selected_file = StringVar()
        self.current_project = StringVar(value="未加载")
        self.progress_text = StringVar(value="等待开始")
        self.company_name_var = StringVar()
        self.website_var = StringVar()
        self.local_reply_docx_var = StringVar()
        self.fixed_attachment_path_var = StringVar()
        self.fixed_attachment_enabled_var = BooleanVar(value=False)
        self.logo_path_var = StringVar()
        self.header_line_color_var = StringVar(value=DEFAULT_TEMPLATE_COLORS["header_line_color"])
        self.footer_background_color_var = StringVar(value=DEFAULT_TEMPLATE_COLORS["footer_background_color"])
        self.footer_text_color_var = StringVar(value=DEFAULT_TEMPLATE_COLORS["footer_text_color"])
        self.contact_name_var = StringVar()
        self.contact_phone_var = StringVar()
        self.contact_email_var = StringVar()
        self.office_address_var = StringVar()
        self.factory_address_var = StringVar()
        self.copyright_text_var = StringVar()
        self.email_format_label_var = StringVar(value="HTML+纯文本")
        self.template_preview_logo_image = None

        self._load_config()
        self.template_engine = TemplateEngine(self.config)
        self.mail_client = MailClient(self.config)
        self.ai_reply_engine = AIReplyEngine(self.config)
        self.excel_loader = ExcelLoader(DEFAULT_BUSINESS_DESC)

        self._build_ui()
        self._load_replied_email_ids()
        self._load_reply_history()
        self._poll_log_queue()

    def _load_config(self) -> None:
        self.config.load()
        company_name = self.config.project.get("project_name", "").strip()
        website = self.config.project.get("project_website", "").strip()
        self.company_name_var.set(company_name)
        self.website_var.set(website)
        self.local_reply_docx_var.set(self.config.ai.get("local_reply_docx_path", "").strip())
        self.fixed_attachment_path_var.set(self.config.attachments.get("fixed_attachment_path", "").strip())
        self.fixed_attachment_enabled_var.set(
            self.config.attachments.get("fixed_attachment_enabled", "false").strip().lower() in {"1", "true", "yes", "on"}
        )
        email_template = self.config.email_template
        self.logo_path_var.set(email_template.get("logo_path", "").strip() or self.config.project.get("logo_path", "").strip())
        self.header_line_color_var.set(get_template_color(self.config, "header_line_color"))
        self.footer_background_color_var.set(get_template_color(self.config, "footer_background_color"))
        self.footer_text_color_var.set(get_template_color(self.config, "footer_text_color"))
        self.contact_name_var.set(self.config.project.get("contact_name", "").strip())
        self.contact_phone_var.set(self.config.project.get("contact_phone", "").strip())
        self.contact_email_var.set(self.config.project.get("contact_email", "").strip())
        self.office_address_var.set(self.config.project.get("office_address", "").strip())
        self.factory_address_var.set(self.config.project.get("factory_address", "").strip())
        self.copyright_text_var.set(self.config.project.get("copyright_text", "").strip())
        format_value = get_email_format(self.config)
        format_label = next((label for label, value in EMAIL_FORMAT_OPTIONS.items() if value == format_value), "HTML+纯文本")
        self.email_format_label_var.set(format_label)
        self.current_project.set(company_name or "未设置")

    def _build_ui(self) -> None:
        top_frame = ttk.Frame(self.root, padding=12)
        top_frame.pack(fill=X)

        ttk.Label(top_frame, text="我方公司名称：").pack(side=LEFT)
        ttk.Entry(top_frame, textvariable=self.company_name_var, width=28).pack(side=LEFT, padx=(0, 12))
        ttk.Label(top_frame, text="我方官网：").pack(side=LEFT)
        ttk.Entry(top_frame, textvariable=self.website_var, width=34).pack(side=LEFT, padx=(0, 12))
        ttk.Button(top_frame, text="保存我方信息", command=self.save_sender_info).pack(side=LEFT)
        ttk.Button(top_frame, text="打开配置文件", command=self.open_config_file).pack(side=LEFT, padx=8)
        ttk.Button(top_frame, text="重新加载配置", command=self.reload_config).pack(side=LEFT, padx=8)
        ttk.Button(top_frame, text="测试邮箱配置", command=self.test_mail_config).pack(side=LEFT)

        reply_frame = ttk.Frame(self.root, padding=(12, 0, 12, 12))
        reply_frame.pack(fill=X)

        ttk.Label(reply_frame, text="话术 Word：").pack(side=LEFT)
        ttk.Entry(reply_frame, textvariable=self.local_reply_docx_var, width=34).pack(side=LEFT, padx=(0, 8))
        ttk.Button(reply_frame, text="选择话术文件", command=self.select_local_reply_docx).pack(side=LEFT)
        ttk.Checkbutton(
            reply_frame,
            text="附带固定附件",
            variable=self.fixed_attachment_enabled_var,
        ).pack(side=LEFT, padx=(14, 6))
        ttk.Entry(reply_frame, textvariable=self.fixed_attachment_path_var, width=28).pack(side=LEFT, padx=(0, 8))
        ttk.Button(reply_frame, text="选择附件", command=self.select_fixed_attachment).pack(side=LEFT)
        ttk.Button(reply_frame, text="保存回复配置", command=self.save_reply_settings).pack(side=LEFT, padx=8)

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=BOTH, expand=True, padx=12, pady=(0, 12))

        send_tab = ttk.Frame(notebook, padding=12)
        template_tab = ttk.Frame(notebook, padding=12)
        inbox_tab = ttk.Frame(notebook, padding=12)
        sent_tab = ttk.Frame(notebook, padding=12)
        notebook.add(send_tab, text="批量发送")
        notebook.add(template_tab, text="邮件模板配置")
        notebook.add(inbox_tab, text="收件箱")
        notebook.add(sent_tab, text="发件记录")

        self._build_send_tab(send_tab)
        self._build_template_tab(template_tab)
        self._build_inbox_tab(inbox_tab)
        self._build_sent_tab(sent_tab)
        self._load_sent_emails()
        self._load_sent_log()

    def _build_send_tab(self, parent: ttk.Frame) -> None:
        file_frame = ttk.LabelFrame(parent, text="客户数据", padding=10)
        file_frame.pack(fill=X)

        ttk.Entry(file_frame, textvariable=self.selected_file).pack(side=LEFT, fill=X, expand=True)
        ttk.Button(file_frame, text="选择 Excel", command=self.select_excel).pack(side=LEFT, padx=8)
        ttk.Button(file_frame, text="加载数据", command=self.load_excel).pack(side=LEFT)

        info_frame = ttk.Frame(parent, padding=(0, 12))
        info_frame.pack(fill=X)

        self.stats_label = ttk.Label(info_frame, text="未加载客户数据")
        self.stats_label.pack(side=LEFT)
        ttk.Label(info_frame, textvariable=self.progress_text).pack(side=RIGHT)

        self.progress = ttk.Progressbar(parent, mode="determinate")
        self.progress.pack(fill=X)

        control_frame = ttk.Frame(parent, padding=(0, 12))
        control_frame.pack(fill=X)
        ttk.Button(control_frame, text="预览首封邮件", command=self.preview_first_mail).pack(side=LEFT)
        ttk.Button(control_frame, text="开始发送", command=self.start_sending).pack(side=LEFT, padx=8)
        ttk.Button(control_frame, text="停止发送", command=self.stop_sending).pack(side=LEFT)

        middle_pane = ttk.Panedwindow(parent, orient="horizontal")
        middle_pane.pack(fill=BOTH, expand=True)

        customer_frame = ttk.LabelFrame(middle_pane, text="客户列表", padding=10)
        preview_frame = ttk.LabelFrame(middle_pane, text="邮件预览", padding=10)
        middle_pane.add(customer_frame, weight=3)
        middle_pane.add(preview_frame, weight=4)

        customer_columns = ("company", "email", "business_intro", "status")
        self.customer_tree = ttk.Treeview(
            customer_frame,
            columns=customer_columns,
            show="headings",
            height=12,
        )
        self.customer_tree.heading("company", text="公司名称")
        self.customer_tree.heading("email", text="邮箱")
        self.customer_tree.heading("business_intro", text="业务介绍")
        self.customer_tree.heading("status", text="状态")
        self.customer_tree.column("company", width=240)
        self.customer_tree.column("email", width=220)
        self.customer_tree.column("business_intro", width=360)
        self.customer_tree.column("status", width=100, anchor="center")
        self.customer_tree.pack(fill=BOTH, expand=True)
        self.customer_tree.bind("<<TreeviewSelect>>", self.on_customer_selected)

        self.preview_text = scrolledtext.ScrolledText(preview_frame, wrap="word", height=20)
        self.preview_text.pack(fill=BOTH, expand=True)

        content_pane = ttk.Panedwindow(parent, orient="horizontal")
        content_pane.pack(fill=BOTH, expand=True)

        left_frame = ttk.LabelFrame(content_pane, text="日志", padding=10)
        right_frame = ttk.LabelFrame(content_pane, text="发送详情", padding=10)
        content_pane.add(left_frame, weight=3)
        content_pane.add(right_frame, weight=2)

        self.log_text = scrolledtext.ScrolledText(left_frame, wrap="word", height=20)
        self.log_text.pack(fill=BOTH, expand=True)

        self.detail_text = scrolledtext.ScrolledText(right_frame, wrap="word", height=20)
        self.detail_text.pack(fill=BOTH, expand=True)

    def _build_template_tab(self, parent: ttk.Frame) -> None:
        pane = ttk.Panedwindow(parent, orient="horizontal")
        pane.pack(fill=BOTH, expand=True)

        form_frame = ttk.LabelFrame(pane, text="邮件模板配置", padding=10)
        preview_frame = ttk.LabelFrame(pane, text="实时预览", padding=10)
        pane.add(form_frame, weight=3)
        pane.add(preview_frame, weight=4)

        for index in range(3):
            form_frame.columnconfigure(index, weight=1 if index == 1 else 0)

        row = 0
        ttk.Label(form_frame, text="公司LOGO：").grid(row=row, column=0, sticky="w", pady=4)
        logo_entry = ttk.Entry(form_frame, textvariable=self.logo_path_var)
        logo_entry.grid(row=row, column=1, sticky="ew", pady=4, padx=(0, 8))
        ttk.Button(form_frame, text="上传LOGO", command=self.select_template_logo).grid(row=row, column=2, sticky="ew", pady=4)
        logo_entry.bind("<KeyRelease>", self._on_template_config_changed)

        row += 1
        self._add_template_entry(form_frame, row, "邮件格式：", self.email_format_label_var, widget_type="combo")
        row += 1
        self._add_template_entry(form_frame, row, "公司名称：", self.company_name_var)
        row += 1
        self._add_template_entry(form_frame, row, "官网链接：", self.website_var)
        row += 1
        self._add_template_entry(form_frame, row, "发件人姓名：", self.contact_name_var)
        row += 1
        self._add_template_entry(form_frame, row, "电话：", self.contact_phone_var)
        row += 1
        self._add_template_entry(form_frame, row, "邮箱：", self.contact_email_var)
        row += 1
        self._add_template_entry(form_frame, row, "办公地址：", self.office_address_var)
        row += 1
        self._add_template_entry(form_frame, row, "工厂地址：", self.factory_address_var)
        row += 1
        self._add_template_entry(form_frame, row, "版权文字：", self.copyright_text_var)
        row += 1
        self._add_template_entry(form_frame, row, "顶部分割线颜色：", self.header_line_color_var, color_key="header_line_color")
        row += 1
        self._add_template_entry(form_frame, row, "底部背景色：", self.footer_background_color_var, color_key="footer_background_color")
        row += 1
        self._add_template_entry(form_frame, row, "底部文字颜色：", self.footer_text_color_var, color_key="footer_text_color")

        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=row + 1, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        ttk.Button(button_frame, text="保存配置", command=self.save_template_config).pack(side=LEFT)
        ttk.Button(button_frame, text="重置", command=self.reset_template_config).pack(side=LEFT, padx=8)
        ttk.Button(button_frame, text="刷新预览", command=self.refresh_template_preview).pack(side=LEFT)

        self.template_preview_text = Text(preview_frame, wrap="word", height=28)
        self.template_preview_text.pack(fill=BOTH, expand=True)
        self.template_preview_text.tag_configure("header_line", background=self.header_line_color_var.get())
        self.template_preview_text.tag_configure(
            "footer",
            background=self.footer_background_color_var.get(),
            foreground=self.footer_text_color_var.get(),
            justify="center",
        )
        self.template_preview_text.tag_configure("company", font=("Arial", 16, "bold"))
        self.template_preview_text.tag_configure("date", justify="right")
        self.refresh_template_preview()

    def _add_template_entry(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: StringVar,
        widget_type: str = "entry",
        color_key: str = "",
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4)
        if widget_type == "combo":
            widget = ttk.Combobox(parent, textvariable=variable, values=list(EMAIL_FORMAT_OPTIONS.keys()), state="readonly")
            widget.bind("<<ComboboxSelected>>", self._on_template_config_changed)
        else:
            widget = ttk.Entry(parent, textvariable=variable)
            widget.bind("<KeyRelease>", self._on_template_config_changed)
        widget.grid(row=row, column=1, sticky="ew", pady=4, padx=(0, 8))
        if color_key:
            ttk.Button(parent, text="选择颜色", command=lambda key=color_key, var=variable: self.choose_template_color(key, var)).grid(
                row=row, column=2, sticky="ew", pady=4
            )
        else:
            ttk.Label(parent, text="").grid(row=row, column=2, sticky="ew", pady=4)

    def _build_inbox_tab(self, parent: ttk.Frame) -> None:
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=X)

        ttk.Button(toolbar, text="刷新收件箱", command=self.refresh_inbox).pack(side=LEFT)
        self.auto_reply_button = ttk.Button(toolbar, text="自动回复最近未读", command=self.auto_reply_unread)
        self.auto_reply_button.pack(side=LEFT, padx=8)

        inbox_pane = ttk.Panedwindow(parent, orient="horizontal")
        inbox_pane.pack(fill=BOTH, expand=True, pady=(12, 0))

        list_frame = ttk.LabelFrame(inbox_pane, text="最近邮件", padding=10)
        detail_frame = ttk.LabelFrame(inbox_pane, text="邮件内容", padding=10)
        inbox_pane.add(list_frame, weight=2)
        inbox_pane.add(detail_frame, weight=3)

        columns = ("from", "subject", "date")
        self.inbox_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=18)
        self.inbox_tree.heading("from", text="发件人")
        self.inbox_tree.heading("subject", text="主题")
        self.inbox_tree.heading("date", text="日期")
        self.inbox_tree.column("from", width=220)
        self.inbox_tree.column("subject", width=320)
        self.inbox_tree.column("date", width=180)
        self.inbox_tree.pack(fill=BOTH, expand=True)
        self.inbox_tree.bind("<<TreeviewSelect>>", self.show_selected_mail)

        self.inbox_conversation = scrolledtext.ScrolledText(
            detail_frame,
            wrap="word",
            font=("Segoe Print", 11),
            bg="#f4f6f8",
            relief="flat",
            padx=14,
            pady=14,
        )
        self.inbox_conversation.pack(fill=BOTH, expand=True)
        self.inbox_conversation.tag_configure(
            "incoming_meta",
            foreground="#6b7280",
            justify="right",
            spacing1=8,
            spacing3=2,
        )
        self.inbox_conversation.tag_configure(
            "incoming_body",
            background="#d9ecff",
            foreground="#1f2937",
            lmargin1=180,
            lmargin2=180,
            rmargin=20,
            spacing1=2,
            spacing3=16,
        )
        self.inbox_conversation.tag_configure(
            "outgoing_meta",
            foreground="#6b7280",
            justify="left",
            spacing1=8,
            spacing3=2,
        )
        self.inbox_conversation.tag_configure(
            "outgoing_body",
            background="#ffffff",
            foreground="#111827",
            lmargin1=20,
            lmargin2=20,
            rmargin=180,
            spacing1=2,
            spacing3=18,
        )
        self.inbox_conversation.tag_configure(
            "empty_state",
            foreground="#6b7280",
            justify="center",
            spacing1=30,
        )
        self.inbox_conversation.config(state="disabled")

        self.inbox_items: list[dict[str, str]] = []
        self.inbox_messages: list[InboxMessage] = []

    def _build_sent_tab(self, parent: ttk.Frame) -> None:
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=X)
        ttk.Button(toolbar, text="刷新记录", command=self.refresh_sent_log).pack(side=LEFT)

        sent_pane = ttk.Panedwindow(parent, orient="horizontal")
        sent_pane.pack(fill=BOTH, expand=True, pady=(12, 0))

        list_frame = ttk.LabelFrame(sent_pane, text="发件记录", padding=10)
        detail_frame = ttk.LabelFrame(sent_pane, text="记录详情", padding=10)
        sent_pane.add(list_frame, weight=3)
        sent_pane.add(detail_frame, weight=2)

        columns = ("time", "company", "recipient", "status")
        self.sent_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=18)
        self.sent_tree.heading("time", text="时间")
        self.sent_tree.heading("company", text="公司")
        self.sent_tree.heading("recipient", text="收件人")
        self.sent_tree.heading("status", text="状态")
        self.sent_tree.column("time", width=160)
        self.sent_tree.column("company", width=260)
        self.sent_tree.column("recipient", width=260)
        self.sent_tree.column("status", width=120, anchor="center")
        self.sent_tree.pack(fill=BOTH, expand=True)
        self.sent_tree.bind("<<TreeviewSelect>>", self.show_selected_sent_log)

        self.sent_detail = Text(detail_frame, wrap="word")
        self.sent_detail.pack(fill=BOTH, expand=True)

    def open_config_file(self) -> None:
        if not CONFIG_PATH.exists():
            messagebox.showwarning("提示", f"未找到配置文件：{CONFIG_PATH}")
            return
        os.startfile(CONFIG_PATH)

    def reload_config(self) -> None:
        try:
            self._load_config()
            self.template_engine = TemplateEngine(self.config)
            self.mail_client = MailClient(self.config)
            self.ai_reply_engine = AIReplyEngine(self.config)
            self.refresh_template_preview()
            self.log("已重新加载配置文件。")
        except Exception as exc:
            messagebox.showerror("配置错误", str(exc))

    def save_sender_info(self) -> None:
        self._sync_sender_info_to_config(save_to_file=True)
        self.template_engine = TemplateEngine(self.config)
        self.mail_client = MailClient(self.config)
        self.ai_reply_engine = AIReplyEngine(self.config)
        if self.records:
            selection = self.customer_tree.selection()
            if selection:
                self._render_mail_preview(int(selection[0]), keep_selection=False)
        self.log("已保存我方公司名称和官网。")

    def save_template_config(self) -> None:
        self._sync_template_config_to_config(save_to_file=True)
        self.template_engine = TemplateEngine(self.config)
        self.mail_client = MailClient(self.config)
        self.ai_reply_engine = AIReplyEngine(self.config)
        self.refresh_template_preview()
        if self.records:
            selection = self.customer_tree.selection()
            if selection:
                self._render_mail_preview(int(selection[0]), keep_selection=False)
        self.log("已保存邮件模板配置。")

    def reset_template_config(self) -> None:
        self.logo_path_var.set("")
        self.header_line_color_var.set(DEFAULT_TEMPLATE_COLORS["header_line_color"])
        self.footer_background_color_var.set(DEFAULT_TEMPLATE_COLORS["footer_background_color"])
        self.footer_text_color_var.set(DEFAULT_TEMPLATE_COLORS["footer_text_color"])
        self.company_name_var.set("")
        self.website_var.set("")
        self.contact_name_var.set("")
        self.contact_phone_var.set("")
        self.contact_email_var.set("")
        self.office_address_var.set("")
        self.factory_address_var.set("")
        self.copyright_text_var.set("")
        self.email_format_label_var.set("HTML+纯文本")
        self.save_template_config()

    def select_template_logo(self) -> None:
        file_path = filedialog.askopenfilename(
            title="选择公司LOGO",
            filetypes=[
                ("图片文件", "*.png;*.gif;*.jpg;*.jpeg;*.bmp"),
                ("所有文件", "*.*"),
            ],
        )
        if not file_path:
            return
        self.logo_path_var.set(file_path)
        self.refresh_template_preview()

    def choose_template_color(self, key: str, variable: StringVar) -> None:
        current = normalize_color(variable.get(), DEFAULT_TEMPLATE_COLORS.get(key, "#79c600"))
        result = colorchooser.askcolor(color=current, title="选择颜色")
        if result and result[1]:
            variable.set(result[1])
            self.refresh_template_preview()

    def _on_template_config_changed(self, _event=None) -> None:
        self.refresh_template_preview()

    def refresh_template_preview(self) -> None:
        if not hasattr(self, "template_preview_text"):
            return
        self._sync_template_config_to_config(save_to_file=False)
        self.template_preview_text.config(state="normal")
        self.template_preview_text.delete("1.0", END)
        self.template_preview_text.tag_configure("header_line", background=self.header_line_color_var.get())
        self.template_preview_text.tag_configure(
            "footer",
            background=self.footer_background_color_var.get(),
            foreground=self.footer_text_color_var.get(),
            justify="center",
        )

        logo_path = self.logo_path_var.get().strip()
        logo_inserted = False
        if logo_path:
            try:
                self.template_preview_logo_image = PhotoImage(file=logo_path)
                self.template_preview_text.image_create(END, image=self.template_preview_logo_image)
                self.template_preview_text.insert(END, "\n")
                logo_inserted = True
            except Exception:
                self.template_preview_logo_image = None
        if not logo_inserted:
            self.template_preview_text.insert(END, (self.company_name_var.get().strip() or "Company Name") + "\n", "company")

        self.template_preview_text.insert(END, f"Date:{time.strftime('%Y-%m-%d')}\n", "date")
        self.template_preview_text.insert(END, " " * 100 + "\n", "header_line")

        sample_record = self.records[0] if self.records else CustomerRecord(
            company_name="Sample Customer",
            email="customer@example.com",
            business_intro="customized products and project services",
        )
        sample_body = TemplateEngine(self.config).build_body(sample_record)
        greeting_line, content_text, closing_line, sender_line = split_email_template_sections(sample_body, self.config)
        self.template_preview_text.insert(END, "\n")
        self.template_preview_text.insert(END, greeting_line + "\n\n")
        self.template_preview_text.insert(END, content_text + "\n\n")
        self.template_preview_text.insert(END, closing_line + "\n")
        self.template_preview_text.insert(END, sender_line + "\n\n")

        footer_text = "\n".join(get_footer_lines(self.config))
        self.template_preview_text.insert(END, "\n" + (footer_text or "Footer information") + "\n", "footer")
        self.template_preview_text.config(state="disabled")

    def save_reply_settings(self) -> None:
        self._sync_reply_settings_to_config(save_to_file=True)
        self.ai_reply_engine = AIReplyEngine(self.config)
        self.log(f"已保存智能回复配置。{self.ai_reply_engine.local_rules_load_note}")
        messagebox.showinfo("回复配置", self.ai_reply_engine.local_rules_load_note)

    def _sync_sender_info_to_config(self, save_to_file: bool = False) -> None:
        company_name = self.company_name_var.get().strip()
        website = self.website_var.get().strip()
        self.config.project["project_name"] = company_name
        self.config.project["project_website"] = website
        if "product_advantages" in self.config.project:
            self.config.project["product_advantages"] = ""
        self.current_project.set(company_name or "未设置")
        if save_to_file:
            self.config.save()

    def _sync_template_config_to_config(self, save_to_file: bool = False) -> None:
        self._sync_sender_info_to_config(save_to_file=False)
        project = self.config.project
        project["contact_name"] = self.contact_name_var.get().strip()
        project["contact_phone"] = self.contact_phone_var.get().strip()
        project["contact_email"] = self.contact_email_var.get().strip()
        project["office_address"] = self.office_address_var.get().strip()
        project["factory_address"] = self.factory_address_var.get().strip()
        project["copyright_text"] = self.copyright_text_var.get().strip()

        email_template = self.config.email_template
        email_template["logo_path"] = self.logo_path_var.get().strip()
        email_template["header_line_color"] = normalize_color(
            self.header_line_color_var.get(), DEFAULT_TEMPLATE_COLORS["header_line_color"]
        )
        email_template["footer_background_color"] = normalize_color(
            self.footer_background_color_var.get(), DEFAULT_TEMPLATE_COLORS["footer_background_color"]
        )
        email_template["footer_text_color"] = normalize_color(
            self.footer_text_color_var.get(), DEFAULT_TEMPLATE_COLORS["footer_text_color"]
        )
        email_template["email_format"] = EMAIL_FORMAT_OPTIONS.get(self.email_format_label_var.get(), "both")
        self.header_line_color_var.set(email_template["header_line_color"])
        self.footer_background_color_var.set(email_template["footer_background_color"])
        self.footer_text_color_var.set(email_template["footer_text_color"])
        self.current_project.set(project.get("project_name", "").strip() or "未设置")
        if save_to_file:
            self.config.save()

    def _sync_reply_settings_to_config(self, save_to_file: bool = False) -> None:
        self.config.ai["local_reply_docx_path"] = self.local_reply_docx_var.get().strip()
        self.config.attachments["fixed_attachment_enabled"] = "true" if self.fixed_attachment_enabled_var.get() else "false"
        self.config.attachments["fixed_attachment_path"] = self.fixed_attachment_path_var.get().strip()
        if save_to_file:
            self.config.save()

    def select_local_reply_docx(self) -> None:
        file_path = filedialog.askopenfilename(
            title="选择本地 Word 话术文件",
            filetypes=[("Word 文件", "*.docx")],
        )
        if file_path:
            self.local_reply_docx_var.set(file_path)

    def select_fixed_attachment(self) -> None:
        file_path = filedialog.askopenfilename(
            title="选择固定附件",
            filetypes=[("所有文件", "*.*"), ("PDF 文件", "*.pdf")],
        )
        if file_path:
            self.fixed_attachment_path_var.set(file_path)

    def select_excel(self) -> None:
        file_path = filedialog.askopenfilename(
            title="选择客户 Excel 文件",
            filetypes=[("Excel 文件", "*.xlsx *.xls")],
        )
        if file_path:
            self.selected_file.set(file_path)

    def load_excel(self) -> None:
        file_path = self.selected_file.get().strip()
        if not file_path:
            messagebox.showwarning("提示", "请先选择 Excel 文件。")
            return
        if not os.path.exists(file_path):
            messagebox.showerror("读取失败", f"文件不存在：{file_path}")
            return

        self.progress_text.set("正在加载数据...")
        self.stats_label.config(text="正在读取客户数据，请稍候...")
        self.log(f"开始读取 Excel：{file_path}")
        threading.Thread(target=self._load_excel_worker, args=(file_path,), daemon=True).start()

    def _load_excel_worker(self, file_path: str) -> None:
        try:
            records = self.excel_loader.load_records(file_path)
            statuses: list[str] = []
            valid_count = sum(1 for item in records if self._can_send_record(item))
            skipped_count = len(records) - valid_count
            for item in records:
                statuses.append(self._get_record_status(item))

            self.log_queue.put(
                ("loaded", records, statuses, valid_count, skipped_count, file_path)
            )
        except Exception as exc:
            self.log_queue.put(("load_error", str(exc), file_path))

    def preview_first_mail(self) -> None:
        self._sync_template_config_to_config()
        if not self.records:
            messagebox.showwarning("提示", "请先导入并加载客户 Excel。")
            return
        first_valid = next((item for item in self.records if self._can_send_record(item)), None)
        if not first_valid:
            messagebox.showwarning("提示", "当前数据中没有可发送的客户记录。")
            return
        subject = self.template_engine.build_subject(first_valid)
        body = self.template_engine.build_body(first_valid)
        index = self.records.index(first_valid)
        self._render_mail_preview(index)
        self.log(f"已生成预览：{first_valid.company_name}")

    def start_sending(self) -> None:
        if not self._confirm_action("开始发送", "确定要开始批量发送邮件吗？"):
            return
        self._sync_template_config_to_config()
        if self.is_sending:
            messagebox.showinfo("提示", "发送任务已在进行中。")
            return
        if not self.records:
            messagebox.showwarning("提示", "请先加载客户数据。")
            return
        self.stop_requested = False
        self.is_sending = True
        self.progress["value"] = 0
        threading.Thread(target=self._send_worker, daemon=True).start()

    def stop_sending(self) -> None:
        if not self._confirm_action("停止发送", "确定要停止当前发送任务吗？"):
            return
        self.stop_requested = True
        self.log("已请求停止，当前邮件处理完成后会终止任务。")

    def _send_worker(self) -> None:
        success_count = 0
        fail_count = 0
        skip_count = 0
        min_delay = self.config.runtime.getint("min_delay_seconds", fallback=10)
        max_delay = self.config.runtime.getint("max_delay_seconds", fallback=15)

        for index, record in enumerate(self.records, start=1):
            if self.stop_requested:
                self.log("发送任务已手动停止。")
                break

            if not self._can_send_record(record):
                skip_count += 1
                reason = self._get_skip_reason(record)
                self.record_statuses[index - 1] = f"跳过: {reason}"
                if reason == "已发送过":
                    self.log(f"[已跳过（已发送过）] {record.company_name} -> {record.email}")
                else:
                    self.log(f"[跳过] {record.company_name}：{reason}")
                self.log_queue.put(("status", index - 1, f"跳过: {reason}"))
                self.log_queue.put(("progress", index, len(self.records)))
                continue

            try:
                subject = self.template_engine.build_subject(record)
                body = self.template_engine.build_body(record)
                self.mail_client.send_mail(record.email, subject, body)
                success_count += 1
                self.record_statuses[index - 1] = "已发送"
                self._mark_email_sent(record.email)
                self.log(f"[成功] {record.company_name} -> {record.email}")
                self.log_queue.put(("preview", index - 1, record.email, subject, body))
                self.log_queue.put(("status", index - 1, "已发送"))
                self._append_sent_log(record, subject, body, "发送成功", "")
            except Exception as exc:
                fail_count += 1
                self.record_statuses[index - 1] = "失败"
                self.log(f"[失败] {record.company_name} -> {record.email}，原因：{exc}")
                self.log_queue.put(("status", index - 1, "失败"))
                self._append_sent_log(record, "", "", "发送失败", str(exc))

            self.log_queue.put(("progress", index, len(self.records)))
            if index < len(self.records) and not self.stop_requested:
                delay = random.randint(min_delay, max_delay)
                self.log(f"等待 {delay} 秒后继续发送下一封。")
                time.sleep(delay)

        self.is_sending = False
        self.log(
            f"任务结束：成功 {success_count}，失败 {fail_count}，跳过 {skip_count}。"
        )

    def refresh_inbox(self) -> None:
        threading.Thread(target=self._fetch_inbox_worker, daemon=True).start()

    def auto_reply_unread(self) -> None:
        if not self._confirm_action("自动回复最近未读", "确定要自动回复最近未读邮件吗？"):
            return
        if self.is_auto_replying:
            messagebox.showinfo("自动回复", "自动回复任务正在进行中。")
            return
        self._sync_sender_info_to_config()
        self._sync_reply_settings_to_config()
        if not self.local_reply_docx_var.get().strip():
            continue_api = messagebox.askyesno(
                "API 回复提醒",
                "当前未选择本地话术文件，本次将直接使用 AI 准确回复。\n确定继续吗？",
            )
            if not continue_api:
                return
        else:
            self.ai_reply_engine = AIReplyEngine(self.config)
            self.log(self.ai_reply_engine.local_rules_load_note)
            if not self.ai_reply_engine.local_rules:
                continue_without_rules = messagebox.askyesno(
                    "本地话术未加载",
                    self.ai_reply_engine.local_rules_load_note + "\n\n本次将直接使用 AI 准确回复，确定继续吗？",
                )
                if not continue_without_rules:
                    return
        reply_candidates = list(self.inbox_messages)

        if not reply_candidates:
            messagebox.showinfo("自动回复", "当前列表中没有需要自动回复的客户邮件，请先刷新收件箱。")
            self.log("自动回复预检查完成：当前列表中没有需要自动回复的客户邮件。")
            return

        preview_lines = []
        for idx, message in enumerate(reply_candidates, start=1):
            preview_lines.append(f"{idx}. {message.sender_email} | {message.subject}")
        preview_text = "本次准备自动回复以下邮件：\n\n" + "\n".join(preview_lines)
        if not messagebox.askyesno("自动回复确认清单", preview_text + "\n\n确定继续吗？"):
            self.log("自动回复已取消：用户在清单确认步骤中取消。")
            return
        self.ai_reply_engine = AIReplyEngine(self.config)
        self.is_auto_replying = True
        if hasattr(self, "auto_reply_button"):
            self.auto_reply_button.config(state="disabled")
        self.log("开始自动处理最近未读回信。")
        self.progress_text.set("正在自动回复未读邮件...")
        threading.Thread(target=self._auto_reply_worker, daemon=True).start()

    def test_mail_config(self) -> None:
        self.log("开始测试 SMTP 邮箱配置。")
        self.progress_text.set("正在测试邮箱配置...")
        threading.Thread(target=self._test_mail_config_worker, daemon=True).start()

    def _test_mail_config_worker(self) -> None:
        try:
            results = self.mail_client.test_smtp_connection()
            summary = "\n".join(results)
            self.log_queue.put(("smtp_test", True, summary))
        except Exception as exc:
            self.log_queue.put(("smtp_test", False, f"SMTP 登录失败：{exc}"))

    def _fetch_inbox_worker(self) -> None:
        try:
            raw_items = self.mail_client.fetch_inbox_messages(limit=20, unread_only=False)
            filtered_items = self._get_pending_reply_messages(raw_items)
            items = [
                {
                    "from": item.sender,
                    "subject": item.subject,
                    "date": item.date,
                    "body": item.body[:500].strip(),
                }
                for item in filtered_items
            ]
            self.log_queue.put(("inbox", items, filtered_items))
            self.log(f"已刷新收件箱，仅显示待回复客户邮件，共 {len(filtered_items)} 封。")
        except Exception as exc:
            self.log(f"收件箱刷新失败：{exc}")

    def _auto_reply_worker(self) -> None:
        try:
            candidates = list(self.inbox_messages)
            processed = 0
            skipped = 0
            failed = 0

            for message in candidates:
                try:
                    ai_result = self.ai_reply_engine.generate_reply(message)
                except Exception as exc:
                    self.log(f"[AI 失败] {message.sender_email} | {message.subject}，原因：{exc}")
                    ai_result = self.ai_reply_engine.build_fallback_reply(message)

                reply_core_body = (ai_result.get("reply_body", "") or "").strip()
                if not reply_core_body:
                    ai_result = self.ai_reply_engine.build_fallback_reply(message)
                    reply_core_body = ai_result["reply_body"]

                reply_body = self._format_auto_reply_body(message, reply_core_body)

                try:
                    attachments = self.ai_reply_engine.build_attachment_list(ai_result, message)
                    self.mail_client.reply_mail(message, reply_body, attachments)
                    self._mark_replied_message(message.uid or message.message_id)
                    self._append_reply_log(
                        message,
                        reply_body,
                        attachments,
                        ai_result.get("source", ""),
                        ai_result.get("matched_keyword", ""),
                    )
                    processed += 1
                    attachment_text = ", ".join(path.name for path in attachments) if attachments else "无附件"
                    source_text = ai_result.get("source", "unknown")
                    keyword_text = ai_result.get("matched_keyword", "")
                    keyword_suffix = f" | 关键词：{keyword_text}" if keyword_text else ""
                    self.log(f"[自动回复成功] {message.sender_email} | {message.subject} | {source_text}{keyword_suffix} | {attachment_text}")
                except Exception as exc:
                    failed += 1
                    self.log(f"[自动回复失败] {message.sender_email} | {message.subject}，原因：{exc}")

            self.log_queue.put(("auto_reply_done", processed, skipped, failed))
        except Exception as exc:
            self.log_queue.put(("auto_reply_error", str(exc)))

    def show_selected_mail(self, _event=None) -> None:
        selection = self.inbox_tree.selection()
        if not selection:
            return
        index = int(selection[0])
        item = self.inbox_items[index]
        customer_meta = f"{item['from']}    {item['date']}"
        customer_body = item["body"]
        reply_meta = f"{self.config.project.get('project_name', '').strip() or '我方'}"
        reply_body = "暂无自动回复内容"
        if index < len(self.inbox_messages):
            message = self.inbox_messages[index]
            reply_info = self.reply_history.get(message.uid) or self.reply_history.get(message.message_id)
            if reply_info:
                attachments = reply_info.get("attachments", "").strip() or "无附件"
                source = reply_info.get("source", "").strip() or "-"
                matched_keyword = reply_info.get("matched_keyword", "").strip() or "-"
                reply_meta = (
                    f"{self.config.project.get('project_name', '').strip() or '我方'}    "
                    f"{reply_info.get('time', '')}\n"
                    f"主题：{reply_info.get('reply_subject', '')}\n"
                    f"来源：{source} | 关键词：{matched_keyword} | 附件：{attachments}"
                )
                reply_body = extract_clean_reply_body(reply_info.get("reply_body", "")) or "暂无自动回复内容"

        self.inbox_conversation.config(state="normal")
        self.inbox_conversation.delete("1.0", END)
        self.inbox_conversation.insert(END, customer_meta + "\n", "incoming_meta")
        self.inbox_conversation.insert(END, customer_body + "\n\n", "incoming_body")
        self.inbox_conversation.insert(END, reply_meta + "\n", "outgoing_meta")
        self.inbox_conversation.insert(END, reply_body + "\n", "outgoing_body")
        self.inbox_conversation.config(state="disabled")
        self.inbox_conversation.see("end")

    def _poll_log_queue(self) -> None:
        while True:
            try:
                item = self.log_queue.get_nowait()
            except queue.Empty:
                break

            action = item[0]
            if action == "log":
                self.log_text.insert(END, item[1] + "\n")
                self.log_text.see(END)
            elif action == "progress":
                current, total = item[1], item[2]
                self.progress["maximum"] = max(total, 1)
                self.progress["value"] = current
                percent = int((current / max(total, 1)) * 100)
                self.progress_text.set(f"进度：{current}/{total} ({percent}%)")
            elif action == "preview":
                _, record_index, recipient, subject, body = item
                self._set_tree_selection(record_index)
                self._fill_preview_text(recipient, subject, body)
                self._fill_detail_text(record_index)
            elif action == "status":
                _, record_index, status = item
                self._update_customer_status(record_index, status)
            elif action == "inbox":
                _, inbox_items, inbox_messages = item
                self._update_inbox(inbox_items, inbox_messages)
            elif action == "loaded":
                _, records, statuses, valid_count, skipped_count, file_path = item
                self.records = records
                self.record_statuses = statuses
                self.stats_label.config(
                    text=f"已加载 {len(self.records)} 条客户数据，可发送 {valid_count} 条，待跳过 {skipped_count} 条"
                )
                self.progress["value"] = 0
                self.progress["maximum"] = max(len(self.records), 1)
                self.progress_text.set("数据已加载")
                self._refresh_customer_tree()
                if self.records:
                    self._render_mail_preview(0)
                else:
                    self.preview_text.delete("1.0", END)
                    self.detail_text.delete("1.0", END)
                self.log(f"成功读取客户数据，共 {len(self.records)} 条：{file_path}")
            elif action == "load_error":
                _, error_message, file_path = item
                self.stats_label.config(text="未加载客户数据")
                self.progress_text.set("加载失败")
                self.log(f"读取失败：{file_path}，原因：{error_message}")
                messagebox.showerror("读取失败", error_message)
            elif action == "sent_log_added":
                self.sent_log_items.insert(0, item[1])
                self._refresh_sent_log_tree()
            elif action == "smtp_test":
                _, success, message = item
                self.progress_text.set("等待开始")
                self.log(message)
                if success:
                    messagebox.showinfo("邮箱配置测试", message)
                else:
                    messagebox.showerror("邮箱配置测试", message)
            elif action == "auto_reply_done":
                _, processed, skipped, failed = item
                self.is_auto_replying = False
                if hasattr(self, "auto_reply_button"):
                    self.auto_reply_button.config(state="normal")
                self.progress_text.set("等待开始")
                self.log(f"自动回复完成：成功 {processed}，跳过 {skipped}，失败 {failed}。")
                messagebox.showinfo("自动回复", f"自动回复完成。\n成功：{processed}\n跳过：{skipped}\n失败：{failed}")
            elif action == "auto_reply_error":
                self.is_auto_replying = False
                if hasattr(self, "auto_reply_button"):
                    self.auto_reply_button.config(state="normal")
                self.progress_text.set("等待开始")
                self.log(f"自动回复任务失败：{item[1]}")
                messagebox.showerror("自动回复", item[1])

        self.root.after(200, self._poll_log_queue)

    def _update_inbox(self, items: list[dict[str, str]], messages: list[InboxMessage]) -> None:
        self.inbox_items = items
        self.inbox_messages = messages
        for row in self.inbox_tree.get_children():
            self.inbox_tree.delete(row)
        for index, item in enumerate(items):
            self.inbox_tree.insert(
                "",
                END,
                iid=str(index),
                values=(item["from"], item["subject"], item["date"]),
            )
        self.inbox_conversation.config(state="normal")
        self.inbox_conversation.delete("1.0", END)
        if not items:
            self.inbox_conversation.insert(END, "暂无可显示的客户邮件", "empty_state")
        self.inbox_conversation.config(state="disabled")
        if items:
            first_id = "0"
            self.inbox_tree.selection_set(first_id)
            self.inbox_tree.focus(first_id)
            self.inbox_tree.see(first_id)
            self.show_selected_mail()

    def log(self, message: str) -> None:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.log_queue.put(("log", f"[{timestamp}] {message}"))

    def refresh_sent_log(self) -> None:
        self._refresh_sent_log_tree()

    def _append_sent_log(
        self,
        record: CustomerRecord,
        subject: str,
        body: str,
        status: str,
        error_message: str,
    ) -> None:
        item = {
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "company": record.company_name,
            "recipient": record.email,
            "status": status,
            "subject": subject,
            "body": body,
            "business_summary": self.template_engine.summarize_business_intro(record.business_intro),
            "error": error_message,
        }
        self._write_sent_log_row(item)
        self.log_queue.put(("sent_log_added", item))

    def _append_reply_log(
        self,
        message: InboxMessage,
        body: str,
        attachments: list[Path],
        source: str,
        matched_keyword: str,
    ) -> None:
        item = {
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "company": message.sender,
            "recipient": message.sender_email,
            "status": "自动回复成功",
            "subject": MailClient._build_reply_subject(message.subject),
            "body": extract_clean_reply_body(body),
            "business_summary": "auto reply",
            "error": ",".join(path.name for path in attachments) if attachments else "",
        }
        self._write_sent_log_row(item)
        self._write_reply_history_row(
            {
                "uid": message.uid,
                "message_id": message.message_id,
                "time": item["time"],
                "recipient": message.sender_email,
                "original_subject": message.subject,
                "reply_subject": item["subject"],
                "reply_body": extract_clean_reply_body(body),
                "attachments": item["error"],
                "source": source,
                "matched_keyword": matched_keyword,
            }
        )
        self.log_queue.put(("sent_log_added", item))

    def _write_sent_log_row(self, item: dict[str, str]) -> None:
        file_exists = SENT_LOG_PATH.exists()
        with SENT_LOG_PATH.open("a", encoding="utf-8-sig", newline="") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=["time", "company", "recipient", "status", "subject", "body", "business_summary", "error"],
            )
            if not file_exists:
                writer.writeheader()
            writer.writerow(item)

    def _load_sent_log(self) -> None:
        if not SENT_LOG_PATH.exists():
            self.sent_log_items = []
            return
        items: list[dict[str, str]] = []
        with SENT_LOG_PATH.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            for row in reader:
                items.append(dict(row))
        self.sent_log_items = list(reversed(items))
        self._refresh_sent_log_tree()

    def _refresh_sent_log_tree(self) -> None:
        if not hasattr(self, "sent_tree"):
            return
        for row in self.sent_tree.get_children():
            self.sent_tree.delete(row)
        for index, item in enumerate(self.sent_log_items):
            self.sent_tree.insert(
                "",
                END,
                iid=str(index),
                values=(item.get("time", ""), item.get("company", ""), item.get("recipient", ""), item.get("status", "")),
            )
        self.sent_detail.delete("1.0", END)

    def show_selected_sent_log(self, _event=None) -> None:
        selection = self.sent_tree.selection()
        if not selection:
            return
        index = int(selection[0])
        item = self.sent_log_items[index]
        preview_body = build_email_template_preview_text(item.get("body", "") or "", self.config)
        detail = (
            f"时间：{item.get('time', '')}\n"
            f"公司：{item.get('company', '')}\n"
            f"收件人：{item.get('recipient', '')}\n"
            f"状态：{item.get('status', '')}\n"
            f"业务短语：{item.get('business_summary', '')}\n"
            f"主题：{item.get('subject', '') or '-'}\n"
            f"错误信息：{item.get('error', '') or '-'}\n\n"
            f"{preview_body}"
        )
        self.sent_detail.delete("1.0", END)
        self.sent_detail.insert(END, detail)

    def _load_sent_emails(self) -> None:
        if not SENT_EMAILS_PATH.exists():
            self.sent_emails = set()
            return
        emails: set[str] = set()
        with SENT_EMAILS_PATH.open("r", encoding="utf-8") as file:
            for line in file:
                email = line.strip().lower()
                if email:
                    emails.add(email)
        self.sent_emails = emails

    def _mark_email_sent(self, email: str) -> None:
        normalized = (email or "").strip().lower()
        if not normalized or normalized in self.sent_emails:
            return
        self.sent_emails.add(normalized)
        with SENT_EMAILS_PATH.open("a", encoding="utf-8") as file:
            file.write(normalized + "\n")

    def _load_replied_email_ids(self) -> None:
        if not REPLIED_EMAILS_PATH.exists():
            self.replied_email_ids = set()
            return
        ids: set[str] = set()
        with REPLIED_EMAILS_PATH.open("r", encoding="utf-8") as file:
            for line in file:
                value = line.strip()
                if value:
                    ids.add(value)
        self.replied_email_ids = ids

    def _mark_replied_message(self, message_id: str) -> None:
        normalized = (message_id or "").strip()
        if not normalized or normalized in self.replied_email_ids:
            return
        self.replied_email_ids.add(normalized)
        with REPLIED_EMAILS_PATH.open("a", encoding="utf-8") as file:
            file.write(normalized + "\n")

    def _has_replied_to_message(self, message_id: str) -> bool:
        normalized = (message_id or "").strip()
        return bool(normalized and normalized in self.replied_email_ids)

    def _write_reply_history_row(self, item: dict[str, str]) -> None:
        uid = (item.get("uid", "") or "").strip()
        message_id = (item.get("message_id", "") or "").strip()
        if uid:
            self.reply_history[uid] = item
        if message_id:
            self.reply_history[message_id] = item
        file_exists = REPLY_HISTORY_PATH.exists()
        with REPLY_HISTORY_PATH.open("a", encoding="utf-8-sig", newline="") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "uid",
                    "message_id",
                    "time",
                    "recipient",
                    "original_subject",
                    "reply_subject",
                    "reply_body",
                    "attachments",
                    "source",
                    "matched_keyword",
                ],
            )
            if not file_exists:
                writer.writeheader()
            writer.writerow(item)

    def _load_reply_history(self) -> None:
        if not REPLY_HISTORY_PATH.exists():
            self.reply_history = {}
            return
        history: dict[str, dict[str, str]] = {}
        with REPLY_HISTORY_PATH.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            for row in reader:
                uid = (row.get("uid", "") or "").strip()
                message_id = (row.get("message_id", "") or "").strip()
                if uid:
                    history[uid] = dict(row)
                if message_id:
                    history[message_id] = dict(row)
        self.reply_history = history

    def on_customer_selected(self, _event=None) -> None:
        self._sync_sender_info_to_config()
        if self.suppress_customer_select_event:
            return
        selection = self.customer_tree.selection()
        if not selection:
            return
        record_index = int(selection[0])
        self._render_mail_preview(record_index, keep_selection=False)

    def _refresh_customer_tree(self) -> None:
        for row in self.customer_tree.get_children():
            self.customer_tree.delete(row)
        for index, record in enumerate(self.records):
            business_summary = self.template_engine.summarize_business_intro(record.business_intro)
            self.customer_tree.insert(
                "",
                END,
                iid=str(index),
                values=(
                    record.company_name,
                    record.email,
                    business_summary,
                    self.record_statuses[index] if index < len(self.record_statuses) else "",
                ),
            )

    def _render_mail_preview(self, record_index: int, keep_selection: bool = True) -> None:
        self._sync_sender_info_to_config()
        if record_index < 0 or record_index >= len(self.records):
            return
        record = self.records[record_index]
        subject = self.template_engine.build_subject(record)
        body = self.template_engine.build_body(record)
        if keep_selection:
            self._set_tree_selection(record_index)
        self._fill_preview_text(record.email, subject, body)
        self._fill_detail_text(record_index)

    def _fill_preview_text(self, recipient: str, subject: str, body: str) -> None:
        self.preview_text.delete("1.0", END)
        preview_body = build_email_template_preview_text(body, self.config)
        self.preview_text.insert(END, f"To: {recipient}\nSubject: {subject}\n\n{preview_body}")

    def _fill_detail_text(self, record_index: int) -> None:
        record = self.records[record_index]
        status = self.record_statuses[record_index] if record_index < len(self.record_statuses) else ""
        business_summary = self.template_engine.summarize_business_intro(record.business_intro)
        can_send = self._can_send_record(record)
        skip_reason = self._get_skip_reason(record) if not can_send else "-"
        subject = self.template_engine.build_subject(record) if can_send else "-"
        sender_name = self.config.project.get("project_name", "").strip() or "-"
        sender_website = self.config.project.get("project_website", "").strip() or "-"
        detail = (
            f"公司名称：{record.company_name}\n"
            f"发送资格：{'可发送' if can_send else '不发送'}\n"
            f"当前状态：{status or '-'}\n"
            f"不发送原因：{skip_reason}\n"
            f"\n"
            f"邮箱：{record.email or '-'}\n"
            f"联系电话：{record.phone or '-'}\n"
            f"官网地址：{record.website or '-'}\n"
            f"国家 / 城市：{record.country or '-'} / {record.city or '-'}\n"
            f"\n"
            f"原始业务介绍：{record.business_intro or '-'}\n"
            f"清洗后业务短语：{business_summary}\n"
            f"预计邮件主题：{subject}\n"
            f"我方公司名称：{sender_name}\n"
            f"我方官网：{sender_website}"
        )
        self.detail_text.delete("1.0", END)
        self.detail_text.insert(END, detail)

    def _update_customer_status(self, record_index: int, status: str) -> None:
        if record_index < 0 or record_index >= len(self.records):
            return
        values = self.customer_tree.item(str(record_index), "values")
        if values:
            self.customer_tree.item(
                str(record_index),
                values=(values[0], values[1], values[2], status),
            )
        current_selection = self.customer_tree.selection()
        if current_selection and current_selection[0] == str(record_index):
            self._fill_detail_text(record_index)

    def _set_tree_selection(self, record_index: int) -> None:
        row_id = str(record_index)
        if row_id in self.customer_tree.get_children():
            self.suppress_customer_select_event = True
            try:
                self.customer_tree.selection_set(row_id)
                self.customer_tree.focus(row_id)
                self.customer_tree.see(row_id)
            finally:
                self.suppress_customer_select_event = False

    @staticmethod
    def _is_valid_email(value: str) -> bool:
        return bool(value and EMAIL_PATTERN.match(value))

    def _has_meaningful_business_intro(self, record: CustomerRecord) -> bool:
        raw = (record.business_intro or "").strip()
        if not raw:
            return False
        summary = self.template_engine.summarize_business_intro(raw)
        return summary != DEFAULT_BUSINESS_DESC

    def _can_send_record(self, record: CustomerRecord) -> bool:
        return (
            self._is_valid_email(record.email)
            and self._has_meaningful_business_intro(record)
            and not self._has_already_sent(record.email)
        )

    def _get_skip_reason(self, record: CustomerRecord) -> str:
        missing_email = not self._is_valid_email(record.email)
        missing_business = not self._has_meaningful_business_intro(record)
        already_sent = self._has_already_sent(record.email)
        if already_sent:
            return "已发送过"
        if missing_email and missing_business:
            return "缺少有效邮箱和可用业务信息"
        if missing_email:
            return "缺少有效邮箱"
        if missing_business:
            return "缺少可用业务信息"
        return "-"

    def _get_record_status(self, record: CustomerRecord) -> str:
        if self._can_send_record(record):
            return "待发送"
        return f"不发送: {self._get_skip_reason(record)}"

    def _has_already_sent(self, email: str) -> bool:
        normalized = (email or "").strip().lower()
        return bool(normalized and normalized in self.sent_emails)

    @staticmethod
    def _confirm_action(title: str, message: str) -> bool:
        return messagebox.askyesno(title, message)

    def _format_auto_reply_body(self, message: InboxMessage, body_text: str) -> str:
        customer_name = extract_customer_display_name(message.sender, message.sender_email)
        company_name = self.config.project.get("project_name", "").strip() or "Our Team"
        website = self.config.project.get("project_website", "").strip()
        core_body = self.ai_reply_engine._normalize_reply_paragraphs(body_text)
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

    @staticmethod
    def _normalize_subject(subject: str) -> str:
        value = (subject or "").strip().lower()
        while True:
            updated = re.sub(r"^(re|fw|fwd|回复|转发)\s*[:：]\s*", "", value, flags=re.IGNORECASE)
            if updated == value:
                break
            value = updated.strip()
        value = re.sub(r"\s+", " ", value)
        return value.strip()

    @staticmethod
    def _extract_email_domain(email: str) -> str:
        normalized = (email or "").strip().lower()
        if "@" not in normalized:
            return ""
        return normalized.split("@", 1)[1]

    def _is_reply_to_sent_mail(self, message: InboxMessage) -> bool:
        sender_email = (message.sender_email or "").strip().lower()
        if not sender_email:
            return False

        subject = (message.subject or "").strip()
        normalized_subject = self._normalize_subject(subject)
        if not normalized_subject:
            return False

        has_reply_prefix = bool(re.match(r"^\s*(re|回复)\s*[:：]", subject, flags=re.IGNORECASE))
        if not has_reply_prefix and not message.references:
            return False

        sender_domain = self._extract_email_domain(sender_email)
        for item in self.sent_log_items:
            if item.get("status") != "发送成功":
                continue
            recipient_email = (item.get("recipient", "") or "").strip().lower()
            recipient_domain = self._extract_email_domain(recipient_email)
            sent_subject = self._normalize_subject(item.get("subject", ""))
            same_recipient = bool(recipient_email and recipient_email == sender_email)
            same_domain = bool(sender_domain and recipient_domain and sender_domain == recipient_domain)
            if sent_subject and sent_subject == normalized_subject and (same_recipient or same_domain):
                return True
        return False

    def _get_auto_reply_candidates(self, messages: list[InboxMessage]) -> list[InboxMessage]:
        own_email = self.config.mail.get("username", "").strip().lower()
        candidates: list[InboxMessage] = []
        for message in messages:
            if not message.sender_email or message.sender_email == own_email:
                continue
            if not self._is_reply_to_sent_mail(message):
                continue
            if self._has_replied_to_message(message.uid or message.message_id):
                continue
            if not self._should_auto_reply_message(message):
                continue
            candidates.append(message)
        return candidates

    def _get_pending_reply_messages(self, messages: list[InboxMessage]) -> list[InboxMessage]:
        return self._get_auto_reply_candidates(messages)

    def _should_auto_reply_message(self, message: InboxMessage) -> bool:
        if self._is_system_or_bounce_mail(message):
            return False

        customer_text = self._extract_effective_customer_text(message)
        if not customer_text:
            return False
        if self._is_meaningful_business_question(customer_text):
            return True
        if self._is_signature_only_text(customer_text):
            return False
        if self._is_meaningless_short_text(customer_text):
            return False
        if self._contains_business_keyword(customer_text):
            return True
        return self._effective_text_length(customer_text) > 25

    def _extract_effective_customer_text(self, message: InboxMessage) -> str:
        text = extract_clean_reply_body(message.body)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = [line.strip() for line in text.splitlines()]
        meaningful_lines: list[str] = []
        for line in lines:
            if not line:
                continue
            lowered = line.lower()
            if lowered.startswith("from:") or lowered.startswith("sent:") or lowered.startswith("to:"):
                continue
            if lowered.startswith("subject:") or lowered.startswith("cc:") or lowered.startswith("bcc:"):
                continue
            meaningful_lines.append(line)
        return "\n".join(meaningful_lines).strip()

    def _is_system_or_bounce_mail(self, message: InboxMessage) -> bool:
        sender_combo = f"{message.sender} {message.sender_email}".lower()
        subject = (message.subject or "").lower()
        body = (message.body or "").lower()

        if any(keyword in sender_combo for keyword in self.SYSTEM_SENDER_KEYWORDS):
            return True
        if any(keyword in subject for keyword in self.SYSTEM_SUBJECT_KEYWORDS):
            return True
        if any(keyword in body for keyword in self.AUTO_REPLY_BODY_KEYWORDS):
            return True
        return False

    def _contains_business_keyword(self, text: str) -> bool:
        haystack = " " + self._normalize_keyword_text(text) + " "
        for keyword in self.BUSINESS_KEYWORDS:
            normalized_keyword = self._normalize_keyword_text(keyword)
            if not normalized_keyword:
                continue
            if f" {normalized_keyword} " in haystack:
                return True
        return False

    def _is_meaningful_business_question(self, text: str) -> bool:
        normalized = self._normalize_keyword_text(text)
        if not normalized:
            return False
        if not self._contains_business_keyword(normalized):
            return False

        question_starters = (
            "what ", "how ", "when ", "where ", "which ", "can ", "could ",
            "would ", "do ", "does ", "is ", "are ", "please ", "need ",
            "want ", "looking for ", "send me ", "provide ",
        )
        if normalized.startswith(question_starters):
            return True
        if "?" in (text or ""):
            return True
        request_phrases = (
            "lead time", "how much", "send me", "provide", "looking for",
            "need ", "want ", "quote", "quotation", "price", "sample",
            "catalog", "catalogue", "brochure", "delivery", "shipping",
            "installation", "warranty", "guarantee", "factory", "manufacturer",
            "manufacture", "produce", "production", "yarn",
        )
        if any(phrase in normalized for phrase in request_phrases):
            return True
        return False

    @staticmethod
    def _normalize_keyword_text(text: str) -> str:
        value = (text or "").lower()
        value = value.replace("-", " ")
        value = re.sub(r"[^a-z0-9\s]", " ", value)
        value = re.sub(r"\s+", " ", value)
        return value.strip()

    def _is_signature_only_text(self, text: str) -> bool:
        lowered = text.lower().strip()
        if not lowered:
            return True
        if self._is_meaningful_business_question(text):
            return False

        lines = [line.strip() for line in lowered.splitlines() if line.strip()]
        if not lines:
            return True
        if len(lines) > 6:
            return False

        company_like_count = 0
        signature_like_lines = 0
        for line in lines:
            if any(keyword in line for keyword in self.SIGNATURE_KEYWORDS):
                signature_like_lines += 1
                continue
            if "&" in line or " inc" in line or " llc" in line or " ltd" in line or " co." in line or " company" in line:
                company_like_count += 1
                signature_like_lines += 1
                continue
            if re.fullmatch(r"[a-z .,&/()-]{2,40}", line) and len(line.split()) <= 5:
                company_like_count += 1
                signature_like_lines += 1
                continue
            if re.fullmatch(r".{0,40}certified.*", line):
                signature_like_lines += 1
                continue

        if signature_like_lines == len(lines):
            return True
        if len(lines) <= 3 and company_like_count >= 1 and signature_like_lines >= len(lines) - 1:
            return True
        return False

    def _is_meaningless_short_text(self, text: str) -> bool:
        normalized = self._normalize_keyword_text(text)
        if not normalized:
            return True
        if normalized in self.MEANINGLESS_SHORT_PHRASES:
            return True
        words = normalized.split()
        if len(words) <= 4 and normalized in self.MEANINGLESS_SHORT_PHRASES:
            return True
        if len(words) <= 4 and all(word in {"thanks", "thank", "you", "ok", "okay", "noted", "received", "sure", "hi", "hello"} for word in words):
            return True
        return False

    @staticmethod
    def _effective_text_length(text: str) -> int:
        normalized = re.sub(r"\s+", "", text or "")
        return len(normalized)


def main() -> None:
    try:
        root = Tk()
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
        app = MailAutomationApp(root)
        root.mainloop()
    except Exception as exc:
        error_message = f"{exc}\n\n{traceback.format_exc()}"
        try:
            root = Tk()
            root.withdraw()
            messagebox.showerror("程序启动失败", error_message)
            root.destroy()
        except Exception:
            pass
        print(error_message)


if __name__ == "__main__":
    main()
