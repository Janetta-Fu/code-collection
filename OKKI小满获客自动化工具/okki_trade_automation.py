"""
小满 OKKI CRM「智能贸易数据」外贸获客自动化脚本

依赖：
    pip install selenium requests pandas openpyxl

运行：
    python okki_trade_automation.py

说明：
1. 默认启动可视化界面，填写筛选条件后点击“开始采集”。
2. OKKI 页面属于登录态系统，推荐使用 COOKIE_STRING 或浏览器手动登录。
3. OKKI CRM 页面结构可能随版本变化，若元素无法定位，请优先调整 OKKI_SELECTORS。
4. 本脚本只使用公开官网页面文本做联系方式和业务信息提取，请确保使用过程符合平台条款与数据合规要求。
"""

from __future__ import annotations

import json
import os
import queue
import re
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from html import escape as html_escape, unescape as html_unescape
from html.parser import HTMLParser
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import parse_qsl, unquote, urlencode, urljoin, urlparse, urlunparse

import pandas as pd
import requests
from openpyxl import Workbook
from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    JavascriptException,
    NoSuchElementException,
    SessionNotCreatedException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait


# =========================
# 一、可配置参数
# =========================

MIN_AMOUNT_THRESHOLD = 5000.0

OKKI_BASE_URL = "https://crm.okki.com/"

# 智能贸易数据真实页面。登录后脚本会直接打开这个地址。
OKKI_SMART_TRADE_URL = "https://crm.okki.com/new_discovery/ciq-datum"

OKKI_USERNAME = ""
OKKI_PASSWORD = ""

# 支持浏览器复制的 Cookie 字符串，或 JSON Cookie 数组。
COOKIE_STRING = ""

SEARCH_PRODUCT_NAME = ""
SEARCH_HS_CODE = ""
SEARCH_COUNTRY = ""

OUTPUT_BASE_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "采集数据")
OUTPUT_EXCEL_PATH = OUTPUT_BASE_DIR
OUTPUT_HTML_PATH = OUTPUT_BASE_DIR

YUNWU_ENDPOINT = "https://yunwu.ai/v1/chat/completions"
YUNWU_API_KEY = ""  # 请在此处填写您的 API KEY
YUNWU_MODEL = "gpt-4o-mini"

BROWSER = "chrome"  # chrome / edge
HEADLESS = False
USE_EXISTING_CHROME = False
CHROME_DEBUGGER_ADDRESS = "127.0.0.1:9222"
CHROME_USER_DATA_DIR = os.path.abspath("okki_chrome_profile")
PAGE_TIMEOUT = 30
LOGIN_MANUAL_WAIT_SECONDS = 600
DETAIL_WAIT_SECONDS = 12
MAX_PAGES = 0  # 0 表示自动翻到最后一页
MAX_WEBSITE_INTERNAL_PAGES = 5
REQUEST_TIMEOUT = 15
AUTO_EXPORT = False
INCREMENTAL_STATE_PATH = "okki_incremental_state.json"
INCREMENTAL_STOP_OLD_PAGES = 0
INCREMENTAL_MAX_KEYS = 80000

RESULT_COLUMNS = ["公司名称", "联系电话", "邮箱", "官网地址", "所在国家", "贸易记录金额", "搜索关键词", "业务介绍", "社媒链接"]

ENABLE_GUI = True


# =========================
# 二、OKKI 页面选择器
# =========================

OKKI_SELECTORS: Dict[str, List[Tuple[str, str]]] = {
    "login_username": [
        (By.CSS_SELECTOR, "input[placeholder*='请输入登录账号']"),
        (By.CSS_SELECTOR, "input[placeholder*='登录账号']"),
        (By.CSS_SELECTOR, "input[placeholder*='登录帐号']"),
        (By.CSS_SELECTOR, "input[placeholder*='请输入账号']"),
        (By.CSS_SELECTOR, "input[name='username']"),
        (By.CSS_SELECTOR, "input[name='account']"),
        (By.CSS_SELECTOR, "input[name='email']"),
        (By.CSS_SELECTOR, "input[placeholder*='账号']"),
        (By.CSS_SELECTOR, "input[placeholder*='邮箱']"),
        (By.CSS_SELECTOR, "input[placeholder*='手机号']"),
        (By.CSS_SELECTOR, "input[type='text']"),
    ],
    "login_password": [
        (By.CSS_SELECTOR, "input[placeholder*='请输入您的密码']"),
        (By.CSS_SELECTOR, "input[placeholder*='请输入密码']"),
        (By.CSS_SELECTOR, "input[type='password']"),
        (By.CSS_SELECTOR, "input[name='password']"),
        (By.CSS_SELECTOR, "input[placeholder*='密码']"),
    ],
    "login_submit": [
        (By.XPATH, "//*[normalize-space(.)='登录' and (self::button or self::div or self::span or self::a or @role='button')]"),
        (By.XPATH, "//button[contains(normalize-space(.), '登录')]"),
        (By.XPATH, "//button[contains(normalize-space(.), '登錄')]"),
        (By.XPATH, "//button[contains(normalize-space(.), 'Login')]"),
        (By.XPATH, "//button[contains(normalize-space(.), 'Sign in')]"),
        (By.XPATH, "//*[contains(@class,'button') and contains(normalize-space(.), '登录')]"),
        (By.XPATH, "//*[contains(@class,'btn') and contains(normalize-space(.), '登录')]"),
        (By.CSS_SELECTOR, "button[type='submit']"),
    ],
    "account_login_tab": [
        (By.XPATH, "//*[contains(normalize-space(.), '账号登录')]"),
        (By.XPATH, "//*[contains(normalize-space(.), '帐号登录')]"),
        (By.XPATH, "//*[contains(normalize-space(.), '密码登录')]"),
        (By.XPATH, "//*[contains(normalize-space(.), '密码') and contains(normalize-space(.), '登录')]"),
        (By.XPATH, "//*[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'account login')]"),
        (By.XPATH, "//*[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'password login')]"),
    ],
    "login_agreement_checkbox": [
        (By.XPATH, "//input[@type='checkbox' and (contains(../text(), '同意') or contains(ancestor::*[contains(@class,'checkbox') or self::label][1], '同意'))]"),
        (By.XPATH, "//*[contains(normalize-space(.), '同意') and (contains(normalize-space(.), '隐私') or contains(normalize-space(.), '服务合同'))]//input[@type='checkbox']"),
        (By.XPATH, "//*[contains(normalize-space(.), '同意') and (contains(normalize-space(.), '隐私') or contains(normalize-space(.), '服务合同'))]"),
        (By.XPATH, "//input[@type='checkbox']"),
        (By.CSS_SELECTOR, ".ant-checkbox-input"),
        (By.CSS_SELECTOR, ".el-checkbox__original"),
        (By.CSS_SELECTOR, "[role='checkbox']"),
    ],
    "product_input": [
        (By.XPATH, "//*[normalize-space(.)='产品']/following::input[1]"),
        (By.XPATH, "//*[contains(normalize-space(.), '请输入产品名称')]/self::input"),
        (By.CSS_SELECTOR, "input[placeholder*='请输入产品名称']"),
        (By.XPATH, "//input[contains(translate(@placeholder, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'search by product or company')]"),
        (By.XPATH, "//input[contains(translate(@placeholder, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'product') or contains(translate(@placeholder, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'company')]"),
        (By.XPATH, "//textarea[contains(translate(@placeholder, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'product') or contains(translate(@placeholder, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'company')]"),
        (By.XPATH, "//input[contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'product') or contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'company')]"),
        (By.CSS_SELECTOR, "input[placeholder*='产品名称']"),
        (By.CSS_SELECTOR, "input[placeholder*='产品']"),
        (By.CSS_SELECTOR, "textarea[placeholder*='产品']"),
        (By.CSS_SELECTOR, "input[aria-label*='产品']"),
        (By.XPATH, "//*[contains(normalize-space(.), '产品名称')]/following::input[1]"),
        (By.XPATH, "//*[contains(normalize-space(.), '产品')]/following::input[1]"),
    ],
    "hs_input": [
        (By.XPATH, "//*[normalize-space(.)='HS编码']/following::input[1]"),
        (By.XPATH, "//*[contains(normalize-space(.), '请输入数字')]/self::input"),
        (By.CSS_SELECTOR, "input[placeholder*='请输入数字']"),
        (By.XPATH, "//input[contains(translate(@placeholder, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'hs code')]"),
        (By.XPATH, "//input[contains(translate(@placeholder, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'hscode')]"),
        (By.XPATH, "//input[contains(translate(@placeholder, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'hs') and contains(translate(@placeholder, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'code')]"),
        (By.XPATH, "//*[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'hs code')]/following::input[1]"),
        (By.CSS_SELECTOR, "input[placeholder*='HS']"),
        (By.CSS_SELECTOR, "input[placeholder*='hs']"),
        (By.CSS_SELECTOR, "input[placeholder*='编码']"),
        (By.CSS_SELECTOR, "textarea[placeholder*='HS']"),
        (By.CSS_SELECTOR, "textarea[placeholder*='编码']"),
        (By.XPATH, "//*[contains(normalize-space(.), 'HS编码')]/following::input[1]"),
        (By.XPATH, "//*[contains(normalize-space(.), 'HS')]/following::input[1]"),
        (By.XPATH, "//*[contains(normalize-space(.), '编码')]/following::input[1]"),
    ],
    "company_input": [
        (By.XPATH, "//*[normalize-space(.)='公司']/following::input[1]"),
        (By.CSS_SELECTOR, "input[placeholder*='请输入公司名称']"),
        (By.XPATH, "//input[contains(translate(@placeholder, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'company name')]"),
    ],
    "buyer_country_input": [
        (By.XPATH, "//*[normalize-space(.)='采购商国家/地区']/following::input[1]"),
        (By.XPATH, "//*[contains(normalize-space(.), '采购商国家')]/following::input[1]"),
    ],
    "buyer_country_dropdown": [
        (By.XPATH, "//*[normalize-space(.)='采购商国家/地区']/following::*[@role='combobox' or contains(@class,'select') or self::input][1]"),
        (By.XPATH, "//*[contains(normalize-space(.), '采购商国家')]/following::*[@role='combobox' or contains(@class,'select') or self::input][1]"),
    ],
    "country_input": [
        (By.XPATH, "//*[normalize-space(.)='采购商国家/地区']/following::input[1]"),
        (By.XPATH, "//*[contains(normalize-space(.), '采购商国家')]/following::input[1]"),
        (By.XPATH, "//input[contains(translate(@placeholder, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'search by country or region')]"),
        (By.XPATH, "//input[contains(translate(@placeholder, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'country') or contains(translate(@placeholder, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'region')]"),
        (By.XPATH, "//textarea[contains(translate(@placeholder, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'country') or contains(translate(@placeholder, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'region')]"),
        (By.XPATH, "//input[contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'country') or contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'region')]"),
        (By.CSS_SELECTOR, "input[placeholder*='国家']"),
        (By.CSS_SELECTOR, "input[placeholder*='地区']"),
        (By.CSS_SELECTOR, "input[aria-label*='国家']"),
        (By.XPATH, "//*[contains(normalize-space(.), '国家/地区')]/following::input[1]"),
        (By.XPATH, "//*[contains(normalize-space(.), '国家')]/following::input[1]"),
        (By.XPATH, "//*[contains(normalize-space(.), '地区')]/following::input[1]"),
    ],
    "country_dropdown": [
        (By.XPATH, "//*[normalize-space(.)='采购商国家/地区']/following::*[@role='combobox' or contains(@class,'select') or self::input][1]"),
        (By.XPATH, "//*[contains(normalize-space(.), '采购商国家')]/following::*[@role='combobox' or contains(@class,'select') or self::input][1]"),
        (By.XPATH, "//*[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'country or region')]/following::*[self::div or self::span or self::button][1]"),
        (By.XPATH, "//*[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'country')]/following::*[self::div or self::span or self::button][1]"),
        (By.XPATH, "//*[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'region')]/following::*[self::div or self::span or self::button][1]"),
        (By.XPATH, "//*[contains(normalize-space(.), '国家/地区')]/following::*[self::div or self::span or self::button][1]"),
        (By.XPATH, "//*[contains(normalize-space(.), '国家')]/following::*[self::div or self::span or self::button][1]"),
        (By.XPATH, "//*[contains(normalize-space(.), '地区')]/following::*[self::div or self::span or self::button][1]"),
    ],
    "search_button": [
        (By.XPATH, "//*[normalize-space(.)='搜索' and (self::button or self::div or self::span or self::a or @role='button')]"),
        (By.XPATH, "//*[contains(@class,'search') and contains(normalize-space(.), '搜索')]"),
        (By.XPATH, "//*[contains(@class,'btn') and contains(normalize-space(.), '搜索')]"),
        (By.XPATH, "//*[normalize-space(.)='公司']/following::button[1]"),
        (By.XPATH, "//*[normalize-space(.)='公司']/following::*[normalize-space(.)='搜索'][1]"),
        (By.XPATH, "//*[normalize-space(.)='HS编码']/following::button[contains(., '搜索') or contains(@class, 'primary') or contains(@class, 'blue')][1]"),
        (By.XPATH, "//*[normalize-space(.)='HS编码']/following::*[normalize-space(.)='搜索'][1]"),
        (By.XPATH, "//button[normalize-space(.)='搜索']"),
        (By.XPATH, "//button[contains(normalize-space(.), '搜索')]"),
        (By.XPATH, "//button[contains(normalize-space(.), '查询')]"),
        (By.XPATH, "//button[contains(normalize-space(.), 'Search')]"),
        (By.CSS_SELECTOR, ".ant-btn-primary"),
        (By.CSS_SELECTOR, ".el-button--primary"),
        (By.XPATH, "//*[self::button or @role='button'][contains(normalize-space(.), '搜索')]"),
        (By.XPATH, "//*[self::button or @role='button'][contains(normalize-space(.), '查询')]"),
        (By.XPATH, "//*[self::button or @role='button'][contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'search')]"),
    ],
    "result_rows": [
        (By.XPATH, "//table//tbody/tr[.//*[normalize-space()]]"),
        (By.XPATH, "//*[@role='row' and .//*[normalize-space()]]"),
        (By.CSS_SELECTOR, ".ant-table-tbody > tr"),
        (By.CSS_SELECTOR, ".el-table__body-wrapper tbody tr"),
        (By.XPATH, "//*[contains(@class,'table') or contains(@class,'list') or contains(@class,'result')]//*[contains(@class,'row') and .//*[normalize-space()]]"),
    ],
    "next_page": [
        (By.CSS_SELECTOR, ".ant-pagination-next:not(.ant-pagination-disabled) button"),
        (By.CSS_SELECTOR, ".ant-pagination-next:not(.ant-pagination-disabled)"),
        (By.CSS_SELECTOR, ".el-pagination .btn-next:not([disabled])"),
        (By.XPATH, "//*[self::button or @role='button' or self::li][contains(normalize-space(.), '下一页') and not(@disabled)]"),
        (By.XPATH, "//*[self::button or @role='button' or self::li][contains(normalize-space(.), '下一頁') and not(@disabled)]"),
        (By.XPATH, "//*[self::button or @role='button' or self::li][contains(normalize-space(.), 'Next') and not(@disabled)]"),
    ],
    "drawer_close": [
        (By.CSS_SELECTOR, ".ant-drawer-close"),
        (By.CSS_SELECTOR, ".ant-modal-close"),
        (By.CSS_SELECTOR, ".el-drawer__close-btn"),
        (By.CSS_SELECTOR, ".el-dialog__headerbtn"),
        (By.XPATH, "//*[self::button or @role='button'][contains(@aria-label, 'Close')]"),
        (By.XPATH, "//*[self::button or @role='button'][contains(normalize-space(.), '关闭')]"),
        (By.XPATH, "//*[self::button or @role='button'][contains(normalize-space(.), '返回')]"),
    ],
}

SOCIAL_HOSTS = ("facebook.com", "instagram.com", "linkedin.com")
SEARCH_HOST_PATTERNS = (
    r"(^|\.)google\.[a-z.]+$",
    r"(^|\.)bing\.com$",
    r"(^|\.)baidu\.com$",
    r"(^|\.)yahoo\.[a-z.]+$",
    r"(^|\.)duckduckgo\.com$",
    r"(^|\.)sogou\.com$",
    r"(^|\.)so\.com$",
    r"(^|\.)yandex\.[a-z.]+$",
)
NAVIGATION_HOST_PATTERNS = (
    r"(^|\.)googleusercontent\.com$",
    r"(^|\.)goo\.gl$",
    r"(^|\.)maps\.app\.goo\.gl$",
    r"(^|\.)mapquest\.com$",
)
SEARCH_PATH_HINTS = (
    "/search",
    "/maps",
    "/map",
    "/url",
    "/imgres",
    "/aclk",
    "/translate",
)
CONTACT_LINK_WORDS = (
    "contact", "contact us", "contacts", "about", "about us", "company",
    "service", "services", "solutions", "products", "support",
)
CONTACT_PATH_CANDIDATES = (
    "/contact-us",
    "/contact",
    "/contacts",
    "/contactus",
    "/about-us",
    "/about",
    "/support",
)
NOISE_TEXT_PATTERN = re.compile(
    r"\b(copyright|all rights reserved|privacy policy|terms of service|cookie|follow us|learn more|read more|home|about us|contact us)\b",
    re.I,
)
BLOCKED_WEBSITE_PATTERN = re.compile(
    r"\b(access denied|forbidden|permission to access|request blocked|security check|"
    r"captcha|robot check|unusual traffic|service unavailable|temporarily unavailable|"
    r"error\s*4\d{2}|reference\s*#|cloudflare|akamai)\b",
    re.I,
)

COUNTRY_ALIASES: Dict[str, List[str]] = {
    "美国": ["美国", "United States", "USA", "US", "America"],
    "越南": ["越南", "Vietnam", "Viet Nam"],
    "印度": ["印度", "India"],
    "阿根廷": ["阿根廷", "Argentina"],
    "俄罗斯": ["俄罗斯", "Russia", "Russian Federation"],
    "墨西哥": ["墨西哥", "Mexico"],
    "乌克兰": ["乌克兰", "Ukraine"],
    "印尼": ["印尼", "印度尼西亚", "Indonesia"],
    "菲律宾": ["菲律宾", "Philippines"],
    "土耳其": ["土耳其", "Turkey", "Türkiye", "Turkiye"],
    "厄瓜多尔": ["厄瓜多尔", "Ecuador"],
    "乌拉圭": ["乌拉圭", "Uruguay"],
    "巴西": ["巴西", "Brazil"],
    "意大利": ["意大利", "Italy"],
    "德国": ["德国", "Germany"],
    "英国": ["英国", "United Kingdom", "UK", "Britain"],
    "法国": ["法国", "France"],
    "西班牙": ["西班牙", "Spain"],
    "荷兰": ["荷兰", "Netherlands", "Holland"],
    "加拿大": ["加拿大", "Canada"],
    "澳大利亚": ["澳大利亚", "Australia"],
    "日本": ["日本", "Japan"],
    "韩国": ["韩国", "South Korea", "Korea"],
    "泰国": ["泰国", "Thailand"],
    "马来西亚": ["马来西亚", "Malaysia"],
    "新加坡": ["新加坡", "Singapore"],
    "南非": ["南非", "South Africa"],
}


@dataclass
class AppConfig:
    min_amount_threshold: float = MIN_AMOUNT_THRESHOLD
    okki_base_url: str = OKKI_BASE_URL
    okki_smart_trade_url: str = OKKI_SMART_TRADE_URL
    okki_username: str = OKKI_USERNAME
    okki_password: str = OKKI_PASSWORD
    cookie_string: str = COOKIE_STRING
    product_name: str = SEARCH_PRODUCT_NAME
    hs_code: str = SEARCH_HS_CODE
    country: str = SEARCH_COUNTRY
    output_excel_path: str = OUTPUT_EXCEL_PATH
    output_html_path: str = OUTPUT_HTML_PATH
    yunwu_endpoint: str = YUNWU_ENDPOINT
    yunwu_api_key: str = YUNWU_API_KEY
    yunwu_model: str = YUNWU_MODEL
    browser: str = BROWSER
    headless: bool = HEADLESS
    use_existing_chrome: bool = USE_EXISTING_CHROME
    chrome_debugger_address: str = CHROME_DEBUGGER_ADDRESS
    chrome_user_data_dir: str = CHROME_USER_DATA_DIR
    page_timeout: int = PAGE_TIMEOUT
    login_manual_wait_seconds: int = LOGIN_MANUAL_WAIT_SECONDS
    detail_wait_seconds: int = DETAIL_WAIT_SECONDS
    max_pages: int = MAX_PAGES
    max_website_internal_pages: int = MAX_WEBSITE_INTERNAL_PAGES
    request_timeout: int = REQUEST_TIMEOUT
    auto_export: bool = AUTO_EXPORT
    incremental_state_path: str = INCREMENTAL_STATE_PATH
    incremental_stop_old_pages: int = INCREMENTAL_STOP_OLD_PAGES
    incremental_max_keys: int = INCREMENTAL_MAX_KEYS

    @property
    def search_keyword(self) -> str:
        parts = []
        if self.product_name.strip():
            parts.append(self.product_name.strip())
        if self.hs_code.strip():
            parts.append(f"HS:{self.hs_code.strip()}")
        return " / ".join(parts)


@dataclass
class TradeRecord:
    company_name: str = ""
    amount: float = 0.0
    raw_amount: str = ""
    country: str = ""
    city: str = ""
    row_text: str = ""
    row_index: int = 0
    page_index: int = 1


@dataclass
class DetailInfo:
    company_name: str = ""
    website: str = ""
    phone: str = ""
    email: str = ""
    country: str = ""
    city: str = ""
    raw_text: str = ""


@dataclass
class WebsiteProfile:
    company_name: str = ""
    website: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""
    social_links: List[str] = field(default_factory=list)
    text: str = ""
    html: str = ""
    ai_fields: Dict[str, str] = field(default_factory=dict)


class SimpleHTMLTextExtractor(HTMLParser):
    """轻量 HTML 文本提取器，避免引入 BeautifulSoup 等额外依赖。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: List[str] = []
        self.title_parts: List[str] = []
        self.h1_parts: List[str] = []
        self._ignored_depth = 0
        self._current_tag = ""

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        self._current_tag = tag.lower()
        if self._current_tag in {"script", "style", "noscript", "svg"}:
            self._ignored_depth += 1
        if self._current_tag in {"p", "div", "section", "article", "br", "li", "tr", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"} and self._ignored_depth > 0:
            self._ignored_depth -= 1
        if tag.lower() in {"p", "div", "section", "article", "li", "tr", "h1", "h2", "h3", "title"}:
            self.parts.append("\n")
        self._current_tag = ""

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        value = sanitize_text(data)
        if not value:
            return
        if self._current_tag == "title":
            self.title_parts.append(value)
        if self._current_tag == "h1":
            self.h1_parts.append(value)
        self.parts.append(value)
        self.parts.append(" ")

    @property
    def text(self) -> str:
        lines = [sanitize_text(line) for line in "".join(self.parts).splitlines()]
        return "\n".join([line for line in lines if line])

    @property
    def title(self) -> str:
        return sanitize_text(" ".join(self.title_parts))

    @property
    def h1(self) -> str:
        return sanitize_text(" ".join(self.h1_parts))


class SimpleHTMLLinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: List[Tuple[str, str]] = []
        self._current_href = ""
        self._current_text: List[str] = []
        self.meta_values: Dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        attrs_dict = {k.lower(): v or "" for k, v in attrs}
        tag_lower = tag.lower()
        if tag_lower == "a":
            self._current_href = attrs_dict.get("href", "")
            self._current_text = []
        if tag_lower == "meta":
            key = attrs_dict.get("property") or attrs_dict.get("name")
            content = attrs_dict.get("content", "")
            if key and content:
                self.meta_values[key.lower()] = content

    def handle_data(self, data: str) -> None:
        if self._current_href:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._current_href:
            self.links.append((self._current_href, sanitize_text(" ".join(self._current_text))))
            self._current_href = ""
            self._current_text = []


def now_text() -> str:
    return datetime.now().strftime("%H:%M:%S")


def sanitize_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def unique_values(values: Iterable[str]) -> List[str]:
    seen = set()
    result = []
    for value in values:
        item = sanitize_text(value)
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def normalize_url(raw_url: str) -> str:
    value = sanitize_text(raw_url)
    if not value:
        return ""
    value = value.strip(" ,;。)")
    if value.startswith("//"):
        value = "https:" + value
    if not re.match(r"^https?://", value, re.I):
        value = "https://" + value
    parsed = urlparse(value)
    if not parsed.netloc or "." not in parsed.netloc:
        return ""
    return value


def is_valid_website_url(raw_url: str) -> bool:
    url = normalize_url(raw_url)
    if not url:
        return False
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if not host:
        return False
    if any(bad in host for bad in ("okki.com", "xiaoman.cn", "localhost")):
        return False
    if any(host.endswith(social) or social in host for social in SOCIAL_HOSTS):
        return False
    if any(re.search(pattern, host, flags=re.I) for pattern in SEARCH_HOST_PATTERNS):
        return False
    if any(re.search(pattern, host, flags=re.I) for pattern in NAVIGATION_HOST_PATTERNS):
        return False
    path = (parsed.path or "").lower()
    query_keys = {key.lower() for key, _ in parse_qsl(parsed.query or "", keep_blank_values=True)}
    if any(path.startswith(prefix) for prefix in SEARCH_PATH_HINTS):
        return False
    if query_keys.intersection({"q", "query", "wd", "word", "keyword", "oq", "aq", "url", "u", "target", "redirect"}):
        if any(token in host for token in ("google", "bing", "baidu", "yahoo", "duckduckgo", "sogou", "yandex")):
            return False
    return parsed.scheme in {"http", "https"} and "." in host


def normalize_company_name(value: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", value.lower())


def derive_brand_from_url(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower().replace("www.", "")
        return host.split(".")[0].replace("-", " ").replace("_", " ").strip()
    except Exception:
        return ""


def clean_company_name_candidate(value: str) -> str:
    cleaned = sanitize_text(value)
    cleaned = re.sub(r"\s*[|¦·-].*$", "", cleaned)
    cleaned = re.sub(r"\b(home|homepage|welcome|official site|official website)\b", "", cleaned, flags=re.I)
    return sanitize_text(cleaned)


def pick_company_name(candidates: Sequence[str], website: str) -> str:
    host_label = clean_company_name_candidate(derive_brand_from_url(website))
    cleaned = [clean_company_name_candidate(item) for item in candidates]
    cleaned = [item for item in cleaned if item and not re.match(r"^(contact|about|services|products|blog|news)$", item, re.I)]
    for item in cleaned:
        if host_label and normalize_company_name(host_label) in normalize_company_name(item):
            return item
    return cleaned[0] if cleaned else host_label


def parse_amount(text: str) -> Tuple[float, str]:
    """从一行贸易记录文本中解析金额，选择最像交易金额的最大值。"""

    raw = sanitize_text(text)
    if not raw:
        return 0.0, ""
    money_patterns = [
        r"(?:US\$|USD|\$)\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(million|m|k|thousand|万|千)?",
        r"(?:金额|交易额|采购额|成交额|总额|amount|value)[^\d$]{0,20}(?:US\$|USD|\$)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(million|m|k|thousand|万|千)?",
    ]
    values: List[Tuple[float, str]] = []
    for pattern in money_patterns:
        for match in re.finditer(pattern, raw, flags=re.I):
            number = float(match.group(1).replace(",", ""))
            unit = (match.group(2) or "").lower()
            if unit in {"million", "m"}:
                number *= 1_000_000
            elif unit in {"k", "thousand"}:
                number *= 1_000
            elif unit == "万":
                number *= 10_000
            elif unit == "千":
                number *= 1_000
            values.append((number, match.group(0)))
    if not values:
        return 0.0, ""
    return max(values, key=lambda item: item[0])


def normalize_obfuscated_email(value: str) -> str:
    text = value or ""
    for _ in range(2):
        try:
            text = html_unescape(text)
        except Exception:
            break
        try:
            text = unquote(text)
        except Exception:
            break
    text = sanitize_text(text)
    if not text:
        return ""
    text = re.sub(r"^mailto:\s*", "", text, flags=re.I)
    text = text.split("?", 1)[0].split("#", 1)[0]
    text = text.replace("&commat;", "@").replace("&period;", ".")
    text = re.sub(r"\s*(?:\(|\[|\{)?\s*at\s*(?:\)|\]|\})?\s*", "@", text, flags=re.I)
    text = re.sub(r"\s*(?:\(|\[|\{)?\s*dot\s*(?:\)|\]|\})?\s*", ".", text, flags=re.I)
    text = re.sub(r"\s*(?:%40|&#64;)\s*", "@", text, flags=re.I)
    text = re.sub(r"\s*(?:%2e|&#46;)\s*", ".", text, flags=re.I)
    text = re.sub(r"\s*@\s*", "@", text)
    text = re.sub(r"\s*\.\s*", ".", text)
    text = text.replace("；", ";").replace("，", ",")
    text = text.strip(" ;,|\"'<>")
    return text.lower()


def extract_email_candidates(text: str, html: str = "") -> List[str]:
    decoded_text = html_unescape(unquote(text or ""))
    decoded_html = html_unescape(unquote(html or ""))
    payload = "\n".join(
        [
            text or "",
            html or "",
            decoded_text,
            decoded_html,
        ]
    )
    direct = re.findall(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", payload, flags=re.I)
    mailto = re.findall(r"mailto:([^\s\"'<>?#]+)", payload, flags=re.I)
    obfuscated = re.findall(
        r"[A-Z0-9._%+-]+\s*(?:@|%40|&#64;|&commat;|\(at\)|\[at\]|\{at\}|\sat\s)\s*[A-Z0-9.-]+"
        r"\s*(?:\.|%2e|&#46;|&period;|\(dot\)|\[dot\]|\{dot\}|\sdot\s)\s*[A-Z]{2,}"
        r"(?:\s*(?:\.|%2e|&#46;|&period;|\(dot\)|\[dot\]|\{dot\}|\sdot\s)\s*[A-Z]{2,})*",
        payload,
        flags=re.I,
    )
    candidates = []
    for item in [*direct, *mailto, *obfuscated]:
        normalized = normalize_obfuscated_email(item)
        if re.fullmatch(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", normalized, flags=re.I):
            candidates.append(normalized)
    return unique_values(candidates)


def harvest_contacts_from_text(text: str, url: str = "", html: str = "") -> Dict[str, List[str] | str]:
    emails = extract_email_candidates(text or "", html or "")[:12]
    phone_candidates = re.findall(
        r"(?:\+\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{4,}",
        text or "",
    )
    phones = unique_values([item.strip() for item in phone_candidates if len(re.sub(r"\D", "", item)) >= 7])[:10]
    return {
        "emails": emails,
        "phones": phones,
        "addresses": extract_address_candidates(text),
        "website": normalize_url(url) if url else "",
    }


def extract_address_candidates(text: str) -> List[str]:
    lines = [sanitize_text(line) for line in re.split(r"\n+", text or "")]
    candidates = []
    for line in lines:
        if len(line) < 12 or len(line) > 160:
            continue
        has_street_word = re.search(r"\b(st|street|rd|road|ave|avenue|blvd|boulevard|dr|drive|lane|ln|suite|ste|unit|floor)\b", line, re.I)
        has_number = re.search(r"\d", line)
        has_postal = re.search(r"\b[A-Z0-9]{3,10}\b", line)
        if (has_street_word and has_number) or (has_street_word and has_postal):
            candidates.append(line)
    return unique_values(candidates)[:5]


def extract_social_links_from_html(html: str) -> List[str]:
    parser = SimpleHTMLLinkExtractor()
    try:
        parser.feed(html or "")
    except Exception:
        pass
    links = [href for href, _ in parser.links]
    regex_links = re.findall(r"https?://(?:www\.)?(?:facebook|instagram|linkedin)\.com/[^\s\"'<>]+", html or "", flags=re.I)
    return normalize_social_links([*links, *regex_links])


def normalize_social_links(links: Iterable[str]) -> List[str]:
    best_by_platform: Dict[str, str] = {}
    for raw_link in unique_values(links):
        normalized = normalize_social_link(raw_link)
        if not normalized:
            continue
        platform = infer_social_platform(normalized)
        current = best_by_platform.get(platform)
        if not current or score_social_link(normalized) > score_social_link(current):
            best_by_platform[platform] = normalized
    return list(best_by_platform.values())


def normalize_social_link(link: str) -> str:
    try:
        parsed = urlparse(link)
        if not parsed.scheme:
            parsed = urlparse("https://" + link.lstrip("/"))
        hostname = parsed.netloc.lower().replace("www.", "")
        if not any(host in hostname for host in SOCIAL_HOSTS):
            return ""
        pathname = re.sub(r"/+", "/", parsed.path).rstrip("/")
        lower_path = pathname.lower()
        if not pathname or pathname == "/":
            return ""
        if re.search(r"(^|/)(login|recover|checkpoint|share|sharer|dialog|plugins|privacy|policies|help|watch|reel|reels|stories|hashtag|explore|intent|search|accounts|oauth|signup)(/|$)", lower_path):
            return ""
        if "facebook.com" in hostname:
            match = re.match(r"^/(?:pages/)?([^/?#]+)(?:/about)?$", pathname, flags=re.I)
            return f"https://www.facebook.com/{match.group(1)}" if match else ""
        if "instagram.com" in hostname:
            match = re.match(r"^/([^/?#]+)$", pathname, flags=re.I)
            if not match or match.group(1).lower() in {"p", "reel", "stories", "explore"}:
                return ""
            return f"https://www.instagram.com/{match.group(1)}"
        if "linkedin.com" in hostname:
            match = re.match(r"^/(company|in)/([^/?#]+)", pathname, flags=re.I)
            return f"https://www.linkedin.com/{match.group(1)}/{match.group(2)}" if match else ""
        return f"{parsed.scheme}://{parsed.netloc}{pathname}"
    except Exception:
        return ""


def score_social_link(link: str) -> float:
    value = link.lower()
    score = 0.0
    if re.search(r"/(company|in)/", value):
        score += 4
    if "/pages/" in value:
        score += 3
    if value.endswith("/about"):
        score -= 1
    if re.search(r"facebook\.com/[^/]+$", value) or re.search(r"instagram\.com/[^/]+$", value):
        score += 5
    if "linkedin.com/company/" in value:
        score += 5
    return score - len(value) / 1000


def infer_social_platform(url: str) -> str:
    if "facebook.com" in url:
        return "Facebook"
    if "instagram.com" in url:
        return "Instagram"
    if "linkedin.com" in url:
        return "LinkedIn"
    return "社媒"


def safe_json_loads_from_text(value: str) -> Dict[str, str]:
    raw = (value or "").strip()
    if not raw:
        return {}
    raw = re.sub(r"^```(?:json)?", "", raw, flags=re.I).strip()
    raw = re.sub(r"```$", "", raw).strip()
    match = re.search(r"\{.*\}", raw, flags=re.S)
    if match:
        raw = match.group(0)
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return {str(k): sanitize_text(v) for k, v in parsed.items()}
    except json.JSONDecodeError:
        return {}
    return {}


def build_business_intro(ai_fields: Dict[str, str], fallback_text: str = "") -> str:
    scope = sanitize_text(ai_fields.get("主营产品/业务范围", ""))
    application = sanitize_text(ai_fields.get("产品用途/应用场景", ""))
    target = sanitize_text(ai_fields.get("目标客户/合作对象", ""))
    advantage = sanitize_text(ai_fields.get("核心优势/服务能力", ""))
    source = sanitize_text(" ".join([scope, application, target, advantage])) or sanitize_text(fallback_text)
    if not source:
        return ""

    def trim_phrase(value: str, max_len: int) -> str:
        text = sanitize_text(value)
        replacements = [
            (r"\bLED\b", "照明"),
            (r"\bOEM\b", "定制代工"),
            (r"\bODM\b", "定制代工"),
            (r"\bDIY\b", "家庭端"),
            (r"\bB2B\b", "企业客户"),
        ]
        for pattern, repl in replacements:
            text = re.sub(pattern, repl, text, flags=re.I)
        text = re.sub(r"[|/]+", "、", text)
        text = text.strip("，,;；。 ")
        if len(text) > max_len:
            text = text[:max_len].rstrip("，,;；。 ")
        return text

    def has_chinese(value: str) -> bool:
        return bool(re.search(r"[\u4e00-\u9fff]", value or ""))

    def infer_scope_zh(payload: str) -> str:
        lower = payload.lower()
        if re.search(r"\b(led|lighting|luminaire|street light|flood light|high mast|industrial light|lamp)\b", lower):
            return "照明产品及配套灯具"
        if re.search(r"\b(traffic signal|traffic sign|signal lamp|lane control|pedestrian|road sign)\b", lower):
            return "交通信号与道路标识产品"
        if re.search(r"\b(artificial grass|synthetic turf|fake grass|landscape turf|sports turf)\b", lower):
            return "人造草坪及配套材料"
        if re.search(r"\b(simulation|virtual training|training system|defense|military)\b", lower):
            return "仿真训练相关产品与系统"
        if re.search(r"\b(industrial|machinery|equipment|hardware|component|electronics)\b", lower):
            return "工业设备及零部件相关产品"
        if re.search(r"\b(manufacturer|factory|supplier|wholesale|distributor)\b", lower):
            return "产品制造与供应服务"
        return "相关产品与配套服务"

    def infer_target_zh(payload: str) -> str:
        lower = payload.lower()
        if re.search(r"\b(contractor|engineering|project|installer|construction)\b", lower):
            return "工程承包商及项目客户"
        if re.search(r"\b(distributor|wholesale|trader|importer|dealer)\b", lower):
            return "贸易商与分销渠道客户"
        if re.search(r"\b(retail|store|supermarket|ecommerce|consumer)\b", lower):
            return "零售渠道与终端采购客户"
        if re.search(r"\b(government|municipal|public sector|military|army|defense)\b", lower):
            return "政府及公共部门客户"
        if re.search(r"\b(oem|odm|brand)\b", lower):
            return "品牌方与企业采购客户"
        return "企业采购与项目型客户"

    def infer_advantage_zh(payload: str) -> str:
        lower = payload.lower()
        parts: List[str] = []
        if re.search(r"\b(custom|oem|odm|private label|tailor)\b", lower):
            parts.append("支持按需定制与项目配套")
        if re.search(r"\b(quality|iso|ce|ul|rohs|certified|compliance)\b", lower):
            parts.append("质量控制规范")
        if re.search(r"\b(delivery|lead time|stock|warehouse|logistics|shipment)\b", lower):
            parts.append("交付稳定且响应及时")
        if re.search(r"\b(service|support|after[- ]?sales|solution)\b", lower):
            parts.append("售前售后配合完善")
        if not parts:
            return "产品覆盖较全，具备稳定供货与持续服务能力"
        return "，".join(unique_values(parts)[:2])

    if not has_chinese(scope):
        lower = source.lower()
        if re.search(r"\b(led|lighting|luminaire|street light|flood light|high mast|industrial light)\b", lower):
            scope = "照明产品及配套灯具"
        elif re.search(r"\b(traffic signal|traffic sign|signal lamp|lane control|pedestrian)\b", lower):
            scope = "交通信号与道路标识产品"
        elif re.search(r"\b(artificial grass|synthetic turf|fake grass|landscape turf|sports turf)\b", lower):
            scope = "人造草坪及配套产品"
        elif re.search(r"\b(manufacturer|factory|supplier|wholesale|distributor|oem|odm)\b", lower):
            scope = "产品制造与供应服务"
        else:
            scope = infer_scope_zh(source)

    scope_display = trim_phrase(scope, 28) or infer_scope_zh(source)
    target_display = trim_phrase(target, 22) if has_chinese(target) else infer_target_zh(source)
    advantage_display = trim_phrase(advantage, 30) if has_chinese(advantage) else infer_advantage_zh(source)
    if not has_chinese(target_display):
        target_display = infer_target_zh(source)
    if not has_chinese(advantage_display):
        advantage_display = infer_advantage_zh(source)

    intro = sanitize_text(
        f"该采购商经营范围以{scope_display}为主，服务人群主要为{target_display}，核心优势是{advantage_display}。"
    )
    if len(intro) > 120:
        clipped = intro[:120]
        punctuation_points = [clipped.rfind("。"), clipped.rfind("；"), clipped.rfind("，")]
        cut = max(punctuation_points)
        if cut >= 36:
            intro = clipped[: cut + 1]
        else:
            intro = re.sub(r"\s+\S*$", "", clipped).rstrip("，,;；。") + "。"
    return intro


def chrome_debugger_ready(address: str) -> bool:
    try:
        response = requests.get(f"http://{address}/json/version", timeout=1)
        return response.ok
    except requests.RequestException:
        return False


def find_chrome_executable() -> str:
    candidates = [
        os.path.join(os.environ.get("ProgramFiles", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("LocalAppData", ""), "Google", "Chrome", "Application", "chrome.exe"),
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return ""


def ensure_controllable_chrome(config: AppConfig) -> None:
    if chrome_debugger_ready(config.chrome_debugger_address):
        return
    chrome_path = find_chrome_executable()
    if not chrome_path:
        raise RuntimeError("未找到 Chrome，请先安装 Google Chrome。")

    port = config.chrome_debugger_address.rsplit(":", 1)[-1]
    target_url = config.okki_smart_trade_url or config.okki_base_url
    subprocess.Popen(
        [
            chrome_path,
            f"--remote-debugging-port={port}",
            "--remote-allow-origins=*",
            target_url,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )
    for _ in range(20):
        if chrome_debugger_ready(config.chrome_debugger_address):
            return
        time.sleep(0.5)
    raise RuntimeError(
        "已尝试打开可控 Chrome，但没有连上调试端口。"
        "如果普通 Chrome 已经开着，请先关闭所有 Chrome 窗口，再重新点击开始采集。"
    )


def create_webdriver(config: AppConfig) -> WebDriver:
    browser = (config.browser or "chrome").lower()
    if config.use_existing_chrome and browser == "chrome":
        ensure_controllable_chrome(config)
        options = webdriver.ChromeOptions()
        options.add_experimental_option("debuggerAddress", config.chrome_debugger_address)
        try:
            return webdriver.Chrome(options=options)
        except WebDriverException as exc:
            raise RuntimeError(
                "无法连接已登录 Chrome。请关闭所有 Chrome 窗口后重试，或取消勾选“连接已登录Chrome”。"
            ) from exc

    if browser == "edge":
        options = webdriver.EdgeOptions()
        options.page_load_strategy = "eager"
        if config.headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--window-size=1440,1000")
        options.add_argument("--lang=zh-CN")
        return webdriver.Edge(options=options)

    def build_chrome_options(profile_dir: str = "", extra_safe: bool = False) -> webdriver.ChromeOptions:
        options = webdriver.ChromeOptions()
        options.page_load_strategy = "eager"
        chrome_path = find_chrome_executable()
        if chrome_path:
            options.binary_location = chrome_path
        options.add_experimental_option("prefs", {
            "intl.accept_languages": "zh-CN,zh",
        })
        if profile_dir:
            os.makedirs(profile_dir, exist_ok=True)
            options.add_argument(f"--user-data-dir={profile_dir}")
            options.add_argument("--profile-directory=Default")
        if config.headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--remote-debugging-port=0")
        options.add_argument("--remote-allow-origins=*")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--window-size=1440,1000")
        options.add_argument("--lang=zh-CN")
        if extra_safe:
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-background-networking")
            options.add_argument("--disable-sync")
        return options

    configured_profile = os.path.abspath(config.chrome_user_data_dir.strip()) if config.chrome_user_data_dir.strip() else ""
    attempts: List[Tuple[str, str, bool]] = []
    if configured_profile:
        attempts.append(("配置资料目录", configured_profile, False))
    attempts.append(("临时资料目录", tempfile.mkdtemp(prefix="okki_chrome_tmp_"), True))
    attempts.append(("无资料目录", "", True))

    last_error: Optional[BaseException] = None
    for label, profile_dir, extra_safe in attempts:
        options = build_chrome_options(profile_dir=profile_dir, extra_safe=extra_safe)
        try:
            return webdriver.Chrome(options=options)
        except (SessionNotCreatedException, WebDriverException) as exc:
            last_error = exc
            message = str(exc).lower()
            retryable = any(
                hint in message
                for hint in (
                    "devtoolsactiveport",
                    "chrome failed to start",
                    "session not created",
                    "not reachable",
                    "user data directory is already in use",
                )
            )
            if not retryable:
                break
            continue

    raise RuntimeError(
        "Chrome 启动失败：已尝试配置资料目录、临时资料目录和无资料目录三种模式，仍无法创建会话。"
        "请先关闭所有 Chrome/ChromeDriver 进程后重试。"
    ) from last_error


def expand_country_names(country: str) -> List[str]:
    value = sanitize_text(country)
    if not value:
        return []
    result = [value]
    normalized = value.lower()
    for chinese_name, aliases in COUNTRY_ALIASES.items():
        alias_set = [item.lower() for item in aliases]
        if normalized == chinese_name.lower() or normalized in alias_set:
            result.extend([chinese_name, *aliases])
            break
    return unique_values(result)


class OkkiTradeAutomation:
    def __init__(
        self,
        config: AppConfig,
        logger: Optional[Callable[[str], None]] = None,
        stop_event: Optional[threading.Event] = None,
        on_result: Optional[Callable[[Dict[str, str]], None]] = None,
    ) -> None:
        self.config = config
        self.logger = logger or print
        self.stop_event = stop_event or threading.Event()
        self.on_result = on_result
        self.driver: Optional[WebDriver] = None
        self.results: List[Dict[str, str]] = []
        self.business_tables: List[Dict[str, str]] = []
        self.processed_keys: set[str] = set()
        self.last_detail_open_state: str = "none"
        self.incremental_context_key: str = ""
        self.incremental_state_path: str = os.path.abspath(self.config.incremental_state_path or INCREMENTAL_STATE_PATH)
        self.incremental_seen_keys: set[str] = set()
        self.incremental_seen_order: List[str] = []
        self.incremental_dirty: bool = False
        self.incremental_loaded: bool = False
        self.live_excel_path: str = ""
        self.live_workbook: Optional[Workbook] = None
        self.live_worksheet = None
        self.live_export_failed: bool = False
        self.export_excel_path: str = ""
        self.export_html_path: str = ""
        self.current_country_context: str = sanitize_text(self.config.country)

    def log(self, message: str) -> None:
        self.logger(f"[{now_text()}] {message}")

    def check_stop(self) -> None:
        if self.stop_event.is_set():
            raise RuntimeError("用户已停止任务。")

    def build_incremental_context_key(self) -> str:
        payload = {
            "product_name": sanitize_text(self.config.product_name).lower(),
            "hs_code": sanitize_text(self.config.hs_code).lower(),
            "country": sanitize_text(self.config.country).lower(),
            "min_amount_threshold": f"{float(self.config.min_amount_threshold):.2f}",
            "smart_trade_url": sanitize_text(self.config.okki_smart_trade_url).lower(),
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    def incremental_context_label(self) -> str:
        parts = []
        if sanitize_text(self.config.product_name):
            parts.append(f"产品：{sanitize_text(self.config.product_name)}")
        if sanitize_text(self.config.hs_code):
            parts.append(f"HS：{sanitize_text(self.config.hs_code)}")
        if sanitize_text(self.config.country):
            parts.append(f"采购商国家：{sanitize_text(self.config.country)}")
        parts.append(f"最低金额：{float(self.config.min_amount_threshold):.2f}")
        return "；".join(parts)

    def load_incremental_state(self) -> None:
        self.incremental_context_key = self.build_incremental_context_key()
        self.incremental_seen_keys = set()
        self.incremental_seen_order = []
        self.incremental_dirty = False
        max_keep = max(5000, int(self.config.incremental_max_keys or INCREMENTAL_MAX_KEYS))

        if not os.path.exists(self.incremental_state_path):
            self.incremental_loaded = True
            self.log(f"增量状态：当前条件独立历史（{self.incremental_context_label()}），首次运行，未发现历史状态文件。")
            return

        try:
            with open(self.incremental_state_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            contexts = data.get("contexts", {}) if isinstance(data, dict) else {}
            context = contexts.get(self.incremental_context_key, {}) if isinstance(contexts, dict) else {}
            keys = context.get("seen_trade_keys", []) if isinstance(context, dict) else []
            if isinstance(keys, list):
                normalized: List[str] = []
                for key in keys[-max_keep:]:
                    item = sanitize_text(key)
                    if item:
                        normalized.append(item)
                self.incremental_seen_order = unique_values(normalized)
                self.incremental_seen_keys = set(self.incremental_seen_order)
            self.incremental_loaded = True
            self.log(f"增量状态：当前条件独立历史（{self.incremental_context_label()}），已加载历史记录 {len(self.incremental_seen_keys)} 条。")
        except Exception as exc:
            self.incremental_loaded = True
            self.log(f"增量状态加载失败，将按空状态继续：{type(exc).__name__}")

    def save_incremental_state(self, force: bool = False) -> None:
        if not self.incremental_loaded:
            return
        if not self.incremental_dirty and not force:
            return

        max_keep = max(5000, int(self.config.incremental_max_keys or INCREMENTAL_MAX_KEYS))
        keep_keys = self.incremental_seen_order[-max_keep:]
        payload: Dict[str, object]
        if os.path.exists(self.incremental_state_path):
            try:
                with open(self.incremental_state_path, "r", encoding="utf-8") as fh:
                    payload = json.load(fh)
                if not isinstance(payload, dict):
                    payload = {}
            except Exception:
                payload = {}
        else:
            payload = {}

        contexts = payload.get("contexts", {})
        if not isinstance(contexts, dict):
            contexts = {}
        contexts[self.incremental_context_key] = {
            "label": self.incremental_context_label(),
            "seen_trade_keys": keep_keys,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        payload["version"] = 1
        payload["contexts"] = contexts

        os.makedirs(os.path.dirname(self.incremental_state_path) or ".", exist_ok=True)
        tmp_path = self.incremental_state_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False)
        os.replace(tmp_path, self.incremental_state_path)
        self.incremental_dirty = False

    def mark_trade_seen(self, trade_key: str) -> None:
        item = sanitize_text(trade_key)
        if not item or item in self.incremental_seen_keys:
            return
        self.incremental_seen_keys.add(item)
        self.incremental_seen_order.append(item)
        max_keep = max(5000, int(self.config.incremental_max_keys or INCREMENTAL_MAX_KEYS))
        if len(self.incremental_seen_order) > max_keep:
            overflow = len(self.incremental_seen_order) - max_keep
            dropped = self.incremental_seen_order[:overflow]
            self.incremental_seen_order = self.incremental_seen_order[overflow:]
            for key in dropped:
                if key not in self.incremental_seen_order:
                    self.incremental_seen_keys.discard(key)
        self.incremental_dirty = True

    @staticmethod
    def extract_trade_date(row_text: str) -> str:
        text = sanitize_text(row_text)
        if not text:
            return ""
        match = re.search(r"\b20\d{2}[-/]\d{1,2}[-/]\d{1,2}\b", text)
        if not match:
            return ""
        return match.group(0).replace("/", "-")

    def build_trade_key(self, record: TradeRecord) -> str:
        company_key = normalize_company_name(record.company_name or "")
        if not company_key:
            return ""
        trade_date = self.extract_trade_date(record.row_text)
        amount_label = sanitize_text(record.raw_amount)
        if amount_label:
            amount_key = re.sub(r"\s+", "", amount_label).upper()
        else:
            try:
                amount_key = f"{float(record.amount):.2f}"
            except Exception:
                amount_key = sanitize_text(record.amount)
        country_key = normalize_company_name(record.country or "")
        return "|".join(
            [
                sanitize_text(self.config.search_keyword).lower(),
                company_key,
                trade_date,
                amount_key,
                country_key,
            ]
        )

    @staticmethod
    def normalize_country_token(value: str) -> str:
        return re.sub(r"[\s\-_]+", "", sanitize_text(value).lower())

    def resolve_canonical_country(self, value: str) -> str:
        token = self.normalize_country_token(value)
        if not token:
            return ""
        for chinese_name, aliases in COUNTRY_ALIASES.items():
            all_names = [chinese_name, *aliases]
            for item in all_names:
                if token == self.normalize_country_token(item):
                    return chinese_name
        return ""

    def build_country_run_plan(self) -> List[str]:
        all_countries = list(COUNTRY_ALIASES.keys())
        raw = sanitize_text(self.config.country)
        if not raw:
            return all_countries

        parts = [sanitize_text(item) for item in re.split(r"[，,;；|/]+", raw) if sanitize_text(item)]
        if len(parts) > 1:
            plan: List[str] = []
            for part in parts:
                canonical = self.resolve_canonical_country(part)
                plan.append(canonical or part)
            return unique_values(plan)

        canonical = self.resolve_canonical_country(raw)
        return [canonical or raw]

    def record_matches_current_country(self, record: TradeRecord) -> bool:
        target = sanitize_text(self.current_country_context or self.config.country)
        if not target:
            return True
        canonical_target = self.resolve_canonical_country(target) or target
        canonical_record = self.resolve_canonical_country(record.country) or sanitize_text(record.country)
        if not canonical_record:
            return True
        return self.normalize_country_token(canonical_record) == self.normalize_country_token(canonical_target)

    @property
    def wait(self) -> WebDriverWait:
        if not self.driver:
            raise RuntimeError("浏览器尚未启动。")
        return WebDriverWait(self.driver, self.config.page_timeout)

    @staticmethod
    def sanitize_filename_component(value: str, max_len: int = 48) -> str:
        text = sanitize_text(value)
        if not text:
            return "未命名产品"
        text = re.sub(r'[\\/:*?"<>|]+', "_", text)
        text = re.sub(r"\s+", "-", text).strip(" ._-")
        if not text:
            text = "未命名产品"
        return text[:max_len]

    def resolve_export_directory(self) -> str:
        raw = sanitize_text(self.config.output_excel_path or OUTPUT_BASE_DIR) or OUTPUT_BASE_DIR
        target = os.path.abspath(raw)
        _, ext = os.path.splitext(target)
        if ext.lower() in {".xlsx", ".xls", ".html", ".htm"}:
            directory = os.path.dirname(target) or os.path.abspath(OUTPUT_BASE_DIR)
        else:
            directory = target
        os.makedirs(directory, exist_ok=True)
        return directory

    def compute_named_export_paths(self) -> Tuple[str, str]:
        directory = self.resolve_export_directory()
        product_source = sanitize_text(self.config.product_name) or sanitize_text(self.config.hs_code) or "未命名产品"
        product_slug = self.sanitize_filename_component(product_source)
        pattern = re.compile(rf"^{re.escape(product_slug)}-第(\d+)次采集\.xlsx$", re.I)
        max_index = 0
        try:
            for filename in os.listdir(directory):
                match = pattern.match(filename)
                if match:
                    max_index = max(max_index, int(match.group(1)))
        except OSError:
            pass
        next_index = max_index + 1
        base_name = f"{product_slug}-第{next_index}次采集"
        excel_path = os.path.join(directory, base_name + ".xlsx")
        html_path = os.path.join(directory, base_name + ".html")
        return excel_path, html_path

    def get_export_paths(self) -> Tuple[str, str]:
        if self.export_excel_path and self.export_html_path:
            return self.export_excel_path, self.export_html_path
        excel_path, html_path = self.compute_named_export_paths()
        self.export_excel_path = excel_path
        self.export_html_path = html_path
        return excel_path, html_path

    def resolve_excel_output_path(self) -> str:
        excel_path, _ = self.get_export_paths()
        return os.path.abspath(excel_path)

    def initialize_live_export(self) -> None:
        self.live_export_failed = False
        self.live_excel_path, _ = self.get_export_paths()
        try:
            workbook = Workbook()
            worksheet = workbook.active
            worksheet.title = "实时采集"
            worksheet.append(RESULT_COLUMNS)
            workbook.save(self.live_excel_path)
            self.live_workbook = workbook
            self.live_worksheet = worksheet
            self.log(f"实时写入已启用：{self.live_excel_path}")
        except Exception as exc:
            self.live_workbook = None
            self.live_worksheet = None
            self.live_export_failed = True
            self.log(f"实时写入初始化失败，改为仅内存采集：{type(exc).__name__}")

    def close_live_export(self) -> None:
        if self.live_workbook:
            try:
                self.live_workbook.save(self.live_excel_path)
            except Exception:
                pass
            try:
                self.live_workbook.close()
            except Exception:
                pass
        self.live_workbook = None
        self.live_worksheet = None

    def append_live_result(self, row: Dict[str, str]) -> None:
        if self.live_export_failed or not self.live_workbook or self.live_worksheet is None:
            return
        values = [sanitize_text(row.get(column, "")) for column in RESULT_COLUMNS]
        try:
            self.live_worksheet.append(values)
            self.live_workbook.save(self.live_excel_path)
        except PermissionError:
            self.live_export_failed = True
            self.log("实时写入失败：Excel 文件正在被占用，请关闭该文件后重试。")
        except Exception as exc:
            self.live_export_failed = True
            self.log(f"实时写入失败：{type(exc).__name__}")

    def run(self) -> List[Dict[str, str]]:
        if not self.config.product_name.strip() and not self.config.hs_code.strip():
            raise ValueError("产品名称和 HS 编码至少需要填写一个。")

        self.load_incremental_state()
        if self.config.auto_export:
            self.initialize_live_export()
        country_plan = self.build_country_run_plan()
        if not country_plan:
            country_plan = [sanitize_text(self.config.country)]
        self.log(f"国家轮询：本次计划 {len(country_plan)} 个国家/地区。")
        self.log("启动浏览器。")
        self.driver = create_webdriver(self.config)
        self.minimize_browser_after_start()
        self.driver.set_page_load_timeout(self.config.page_timeout)
        self.driver.set_script_timeout(max(20, self.config.page_timeout))
        try:
            self.open_and_login()
            self.close_unwanted_tabs()
            for index, country_name in enumerate(country_plan, start=1):
                self.check_stop()
                self.current_country_context = sanitize_text(country_name)
                country_label = self.current_country_context or "全部国家"
                try:
                    self.log(f"国家轮询：开始处理 {country_label}（{index}/{len(country_plan)}）。")
                    self.open_smart_trade_page()
                    self.close_unwanted_tabs()
                    self.execute_search(country_override=self.current_country_context)
                    self.close_unwanted_tabs()
                    self.process_result_pages()
                    self.log(f"国家轮询：完成 {country_label}（{index}/{len(country_plan)}）。")
                except RuntimeError as exc:
                    if "用户已停止任务" in str(exc):
                        raise
                    self.log(f"国家轮询：{country_label} 处理中断，跳过到下一国家。原因：{type(exc).__name__}")
                except Exception as exc:
                    self.log(f"国家轮询：{country_label} 处理异常，跳过到下一国家。原因：{type(exc).__name__}")
                    try:
                        self.close_unwanted_tabs()
                    except Exception:
                        pass
            self.close_live_export()
            if self.config.auto_export:
                self.export_results()
            else:
                self.log("已完成采集，当前为手动导出模式。请点击界面“手动导出表格”按钮。")
            self.log(f"任务完成，成功采集 {len(self.results)} 条。")
            return self.results
        finally:
            try:
                self.save_incremental_state(force=True)
            except Exception as exc:
                self.log(f"增量状态保存失败：{type(exc).__name__}")
            self.close_live_export()
            if self.driver:
                try:
                    if self.config.use_existing_chrome:
                        self.log("已连接用户 Chrome，任务结束后保留浏览器不关闭。")
                    else:
                        self.driver.quit()
                except WebDriverException:
                    pass

    def minimize_browser_after_start(self) -> None:
        if not self.driver or self.config.headless:
            return
        try:
            self.driver.minimize_window()
            self.log("浏览器已最小化，可从任务栏点开查看采集过程。")
        except WebDriverException:
            pass

    def open_and_login(self) -> None:
        assert self.driver
        entry_url = self.config.okki_smart_trade_url.strip() or self.config.okki_base_url
        self.log(f"打开 OKKI 入口：{entry_url}")
        self.driver.get(entry_url)
        self.wait_document_ready()
        self.wait_for_okki_login_or_app(timeout=18)
        if "login.okki.com" in (self.driver.current_url or "").lower():
            self.log("当前是 OKKI 登录页，登录完成后会自动返回目标页面。")

        if self.config.cookie_string.strip():
            self.log("检测到 Cookie 配置，尝试注入登录态。")
            self.inject_cookies(self.config.cookie_string)
            self.driver.refresh()
            self.wait_document_ready()
            self.wait_for_okki_login_or_app(timeout=12)

        if self.is_logged_in():
            self.ensure_simplified_chinese_ui()
            self.log("已处于登录状态。")
            return

        if self.config.okki_username.strip() and self.config.okki_password.strip():
            self.log("尝试使用账号密码登录。")
            self.try_account_login()
            self.wait_for_okki_login_or_app(timeout=18)
            if self.is_logged_in():
                self.ensure_simplified_chinese_ui()
                self.log("账号密码登录成功。")
                return

        wait_seconds = max(60, int(self.config.login_manual_wait_seconds or LOGIN_MANUAL_WAIT_SECONDS))
        self.log(f"未检测到有效登录态。请在浏览器中手动完成 OKKI 登录，脚本会继续等待 {wait_seconds} 秒。")
        deadline = time.time() + wait_seconds
        next_notice = time.time() + 30
        while time.time() < deadline:
            self.check_stop()
            if self.is_logged_in():
                self.ensure_simplified_chinese_ui()
                self.log("手动登录完成。")
                return
            if time.time() >= next_notice:
                remaining = int(deadline - time.time())
                self.log(f"仍在等待登录完成，剩余约 {max(0, remaining)} 秒。")
                next_notice = time.time() + 30
            time.sleep(2)
        raise TimeoutException("登录等待超时：请检查 Cookie、账号密码或手动登录状态。")

    def inject_cookies(self, cookie_string: str) -> None:
        assert self.driver
        cookies = self.parse_cookie_string(cookie_string)
        if not cookies:
            self.log("Cookie 解析为空，跳过 Cookie 注入。")
            return
        for cookie in cookies:
            try:
                item = {"name": cookie["name"], "value": cookie["value"]}
                if cookie.get("domain"):
                    item["domain"] = cookie["domain"]
                if cookie.get("path"):
                    item["path"] = cookie["path"]
                self.driver.add_cookie(item)
            except WebDriverException as exc:
                self.log(f"Cookie 注入失败：{cookie.get('name', '')}，原因：{exc.msg[:120]}")

    @staticmethod
    def parse_cookie_string(cookie_string: str) -> List[Dict[str, str]]:
        raw = cookie_string.strip()
        if not raw:
            return []
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [
                        {
                            "name": str(item.get("name", "")),
                            "value": str(item.get("value", "")),
                            "domain": str(item.get("domain", "")),
                            "path": str(item.get("path", "/") or "/"),
                        }
                        for item in parsed
                        if item.get("name") and item.get("value") is not None
                    ]
            except json.JSONDecodeError:
                return []
        result = []
        for name, value in parse_qsl(raw.replace("; ", "&").replace(";", "&"), keep_blank_values=True):
            if name:
                result.append({"name": name, "value": value, "path": "/"})
        return result

    def switch_to_login_frame(self) -> None:
        assert self.driver
        try:
            self.driver.switch_to.default_content()
        except WebDriverException:
            return

        if self.login_form_present_in_current_context():
            return

        try:
            frames = self.driver.find_elements(By.CSS_SELECTOR, "iframe,frame")
        except WebDriverException:
            return

        for index, frame in enumerate(frames, start=1):
            try:
                self.driver.switch_to.default_content()
                self.driver.switch_to.frame(frame)
                if self.login_form_present_in_current_context():
                    self.log(f"检测到登录表单位于第 {index} 个 iframe。")
                    return
            except WebDriverException:
                continue

        try:
            self.driver.switch_to.default_content()
        except WebDriverException:
            pass

    def login_form_present_in_current_context(self) -> bool:
        assert self.driver
        try:
            if self.driver.find_elements(By.CSS_SELECTOR, "input[type='password']"):
                return True
            if not self.driver.find_elements(By.CSS_SELECTOR, "input,textarea"):
                return False
            text = self.safe_body_text()
            return ("登录" in text or "Login" in text) and ("密码" in text or "Password" in text)
        except WebDriverException:
            return False

    def login_form_present_anywhere(self) -> bool:
        assert self.driver
        try:
            self.driver.switch_to.default_content()
            if self.login_form_present_in_current_context():
                return True
            frames = self.driver.find_elements(By.CSS_SELECTOR, "iframe,frame")
            for frame in frames:
                try:
                    self.driver.switch_to.default_content()
                    self.driver.switch_to.frame(frame)
                    if self.login_form_present_in_current_context():
                        return True
                except WebDriverException:
                    continue
            return False
        except WebDriverException:
            return False
        finally:
            try:
                self.driver.switch_to.default_content()
            except WebDriverException:
                pass

    @staticmethod
    def is_okki_login_url(url: str) -> bool:
        parsed = urlparse(url or "")
        host = parsed.netloc.lower()
        path = parsed.path.lower()
        return "login.okki.com" in host or "passport" in host or "/login" in path

    def has_authenticated_app_markers(self) -> bool:
        text = self.safe_body_text()
        lower_text = text.lower()
        return any(
            word in text or word.lower() in lower_text
            for word in (
                "智能贸易数据", "智能貿易數據", "渠道获客", "渠道獲客", "海关数据", "海關數據", "工作台", "商机", "商機", "线索", "線索",
                "OKKI Leads", "Smart Prospecting", "Prospecting", "Dashboard",
                "Find company", "Find contact", "International Trade",
                "Product Transaction", "Auto Monitoring", "Trade Data",
            )
        )

    def wait_for_okki_login_or_app(self, timeout: int = 15) -> None:
        assert self.driver
        deadline = time.time() + max(1, timeout)
        while time.time() < deadline:
            self.close_unwanted_tabs(log_closed=False)
            try:
                self.driver.switch_to.default_content()
            except WebDriverException:
                pass
            current_url = (self.driver.current_url or "").lower()
            if self.is_logged_in():
                return
            if self.is_okki_login_url(current_url) or self.login_form_present_anywhere():
                return
            time.sleep(0.5)
        self.log("OKKI 页面仍在跳转或加载，继续尝试识别登录状态。")

    @staticmethod
    def is_okki_work_tab_url(url: str) -> bool:
        parsed = urlparse(url or "")
        host = parsed.netloc.lower()
        scheme = parsed.scheme.lower()
        if (url or "").strip().lower() in {"about:blank", "data:,"}:
            return False
        if scheme == "chrome":
            return True
        return host.endswith("okki.com") or host.endswith("xiaoman.cn")

    def close_unwanted_tabs(self, log_closed: bool = True) -> None:
        assert self.driver
        try:
            handles = list(self.driver.window_handles)
        except WebDriverException:
            return
        if len(handles) <= 1:
            return

        original = None
        try:
            original = self.driver.current_window_handle
        except WebDriverException:
            pass

        keep_handle = None
        closed_urls: List[str] = []
        for handle in handles:
            try:
                self.driver.switch_to.window(handle)
                url = self.driver.current_url or ""
                if self.is_okki_work_tab_url(url):
                    if keep_handle is None or "crm." in urlparse(url).netloc.lower():
                        keep_handle = handle
                    continue
                closed_urls.append(url)
                self.driver.close()
            except WebDriverException:
                continue

        try:
            remaining = list(self.driver.window_handles)
            target = keep_handle if keep_handle in remaining else (original if original in remaining else (remaining[0] if remaining else None))
            if target:
                self.driver.switch_to.window(target)
        except WebDriverException:
            pass

        if log_closed and closed_urls:
            short_urls = [urlparse(url).netloc or url for url in closed_urls[:3]]
            self.log("已关闭多余弹出页：" + " / ".join(short_urls))

    def try_account_login(self) -> None:
        assert self.driver
        self.switch_to_login_frame()
        account_tab = self.find_first("account_login_tab", timeout=3)
        if account_tab:
            try:
                self.safe_click(account_tab)
                time.sleep(1)
            except WebDriverException:
                pass

        if self.fill_and_submit_login_by_js():
            time.sleep(5)
            try:
                self.driver.switch_to.default_content()
            except WebDriverException:
                pass
            self.wait_document_ready()
            if self.is_logged_in():
                return
            self.log_login_diagnostics("页面脚本已提交，但 OKKI 仍停留在登录状态")
            self.switch_to_login_frame()

        username_el = self.find_first("login_username", timeout=8)
        password_el = self.find_first("login_password", timeout=8)
        if not username_el or not password_el:
            self.log("未找到账号或密码输入框，转为手动登录等待。")
            self.log_login_diagnostics("未找到登录输入框")
            return
        self.clear_and_type(username_el, self.config.okki_username)
        self.clear_and_type(password_el, self.config.okki_password)
        self.ensure_login_agreement_checked()
        submit_el = self.find_first("login_submit", timeout=8)
        if submit_el:
            for _ in range(50):
                try:
                    disabled = (
                        bool(submit_el.get_attribute("disabled"))
                        or (submit_el.get_attribute("aria-disabled") or "").lower() == "true"
                        or "disabled" in (submit_el.get_attribute("class") or "").lower()
                    )
                    if not disabled:
                        break
                except WebDriverException:
                    break
                time.sleep(0.2)
            self.safe_click(submit_el)
        else:
            password_el.send_keys(Keys.ENTER)
        time.sleep(5)
        try:
            self.driver.switch_to.default_content()
        except WebDriverException:
            pass
        self.wait_document_ready()
        if not self.is_logged_in():
            self.log_login_diagnostics("Selenium 填写提交后仍未登录")

    def fill_and_submit_login_by_js(self) -> bool:
        assert self.driver
        try:
            result = self.driver.execute_async_script(
                """
                const account = arguments[0];
                const password = arguments[1];
                const done = arguments[arguments.length - 1];
                const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
                const compact = (value) => normalize(value).replace(/\\s+/g, '');
                const visible = (el) => {
                  if (!el) return false;
                  const rect = el.getBoundingClientRect();
                  const style = getComputedStyle(el);
                  return rect.width > 0 && rect.height > 0 && style.display !== 'none'
                    && style.visibility !== 'hidden' && Number(style.opacity || '1') !== 0;
                };
                const textOf = (el) => normalize(el?.innerText || el?.textContent || el?.value || '');
                const markerOf = (el) => normalize([
                  el?.placeholder || '',
                  el?.name || '',
                  el?.id || '',
                  el?.getAttribute?.('aria-label') || '',
                  el?.getAttribute?.('autocomplete') || '',
                  el?.getAttribute?.('data-testid') || '',
                  el?.closest?.('label,div,section,form')?.innerText || ''
                ].join(' '));
                const setValue = (input, value) => {
                  const proto = input instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
                  const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
                  input.focus();
                  if (setter) setter.call(input, value);
                  else input.value = value;
                  try {
                    input.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: value }));
                  } catch (err) {
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                  }
                  input.dispatchEvent(new Event('change', { bubbles: true }));
                  input.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, key: 'a' }));
                  input.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true, key: 'a' }));
                  input.dispatchEvent(new Event('blur', { bubbles: true }));
                };
                const allInputs = Array.from(document.querySelectorAll('input,textarea'));
                const visibleInputs = allInputs.filter(visible);
                const editableInputs = visibleInputs.filter(el => {
                  const type = (el.type || '').toLowerCase();
                  return !['hidden', 'checkbox', 'radio', 'submit', 'button'].includes(type) && !el.disabled && !el.readOnly;
                });
                const accountInput = editableInputs.find(el => /登录账号|登录帐号|账号|帐号|邮箱|手机号|用户名|account|email|phone|mobile|user/i.test(markerOf(el)))
                  || editableInputs.find(el => ['text', 'email', 'tel', ''].includes((el.type || '').toLowerCase()));
                const passwordInput = editableInputs.find(el => (el.type || '').toLowerCase() === 'password')
                  || editableInputs.find(el => /密码|password/i.test(markerOf(el)));
                if (!accountInput || !passwordInput) {
                  done({
                    ok: false,
                    reason: 'input-not-found',
                    inputCount: allInputs.length,
                    visibleInputCount: visibleInputs.length
                  });
                  return;
                }
                setValue(accountInput, account);
                setValue(passwordInput, password);

                const checkboxCandidates = allInputs.filter(el => (el.type || '').toLowerCase() === 'checkbox');
                const checkbox = checkboxCandidates.find(el => {
                  const marker = [
                    el.className || '',
                    el.id || '',
                    el.name || '',
                    el.closest('label,div,span,section,form')?.innerText || ''
                  ].join(' ');
                  return /agree|agreement|同意|隐私|服务|合同/i.test(marker) && !/remember|自动登录/i.test(marker);
                }) || checkboxCandidates.find(el => (el.id || '').toLowerCase() !== 'remember');
                if (checkbox) {
                  if (!checkbox.checked) {
                    const clickable = checkbox.closest('label,.ant-checkbox,.el-checkbox,[role="checkbox"],div,span') || checkbox;
                    if (visible(clickable)) {
                      clickable.scrollIntoView({ block: 'center', inline: 'center' });
                      clickable.click();
                    } else if (visible(checkbox)) {
                      checkbox.scrollIntoView({ block: 'center', inline: 'center' });
                      checkbox.click();
                    }
                  }
                  if (!checkbox.checked) {
                    const checkedSetter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'checked')?.set;
                    if (checkedSetter) checkedSetter.call(checkbox, true);
                    else checkbox.checked = true;
                    checkbox.dispatchEvent(new Event('input', { bubbles: true }));
                    checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                  }
                } else {
                  const agreement = Array.from(document.querySelectorAll('label,div,span,p'))
                    .filter(visible)
                    .find(el => /同意/.test(textOf(el)) && /隐私|服务合同|服务/.test(textOf(el)));
                  if (agreement) agreement.click();
                }

                const isDisabled = (button) => {
                  if (!button) return true;
                  return Boolean(
                    button.disabled ||
                    button.getAttribute('disabled') !== null ||
                    (button.getAttribute('aria-disabled') || '').toLowerCase() === 'true' ||
                    /disabled/i.test(button.className || '')
                  );
                };
                const findLoginButton = () => {
                  const direct = Array.from(document.querySelectorAll('button.login-btn, button[type="submit"], input[type="submit"]'))
                    .find(el => visible(el) && /登录|登錄|login|sign\\s*in/i.test(textOf(el) || el.value || ''));
                  if (visible(direct) && /登录|登錄|login|sign in/i.test(textOf(direct))) return direct;
                  const candidates = Array.from(document.querySelectorAll('button,[role="button"],a,div,span'))
                    .filter(visible)
                    .filter(el => {
                      const text = compact(textOf(el));
                      if (!/^(登录|登錄|login|signin)$/i.test(text)) return false;
                      if (/扫码登录|密码登录|验证码登录|注册|忘记/.test(text)) return false;
                      return true;
                    });
                  return candidates
                    .map(el => el.closest('button,[role="button"],a,[class*="btn"],[class*="button"]') || el)
                    .find(visible);
                };
                const deadline = Date.now() + 10000;
                const tick = () => {
                  const loginButton = findLoginButton();
                  if (!loginButton) {
                    if (passwordInput.form && typeof passwordInput.form.requestSubmit === 'function') {
                      passwordInput.form.requestSubmit();
                      done({
                        ok: true,
                        method: 'requestSubmit',
                        accountFilled: Boolean(accountInput.value),
                        passwordFilled: Boolean(passwordInput.value),
                        agreementChecked: checkbox ? checkbox.checked : null
                      });
                      return;
                    }
                    passwordInput.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, key: 'Enter', code: 'Enter' }));
                    passwordInput.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true, key: 'Enter', code: 'Enter' }));
                    done({ ok: true, method: 'enter' });
                    return;
                  }
                  if (!isDisabled(loginButton)) {
                    loginButton.scrollIntoView({ block: 'center', inline: 'center' });
                    loginButton.click();
                    done({
                      ok: true,
                      method: 'button',
                      buttonText: textOf(loginButton),
                      accountFilled: Boolean(accountInput.value),
                      passwordFilled: Boolean(passwordInput.value),
                      agreementChecked: checkbox ? checkbox.checked : null
                    });
                    return;
                  }
                  if (Date.now() < deadline) {
                    setTimeout(tick, 300);
                    return;
                  }
                  done({
                    ok: false,
                    reason: 'button-disabled',
                    buttonText: textOf(loginButton),
                    accountFilled: Boolean(accountInput.value),
                    passwordFilled: Boolean(passwordInput.value),
                    agreementChecked: checkbox ? checkbox.checked : null
                  });
                };
                setTimeout(tick, 800);
                """,
                self.config.okki_username,
                self.config.okki_password,
            )
            if isinstance(result, dict) and result.get("ok"):
                agreement = result.get("agreementChecked")
                agreement_text = "未找到协议框" if agreement is None else ("已勾选" if agreement else "未勾选")
                self.log(
                    "已通过页面脚本填写账号密码并提交登录："
                    f"{result.get('method', '')}，协议：{agreement_text}"
                )
                return True
            self.log(f"页面脚本登录未成功定位：{result}")
        except WebDriverException as exc:
            self.log(f"页面脚本登录失败：{exc.msg[:160]}")
        return False

    def log_login_diagnostics(self, context: str) -> None:
        assert self.driver
        try:
            self.switch_to_login_frame()
            state = self.driver.execute_script(
                """
                const visible = (el) => {
                  if (!el) return false;
                  const rect = el.getBoundingClientRect();
                  const style = getComputedStyle(el);
                  return rect.width > 0 && rect.height > 0 && style.display !== 'none'
                    && style.visibility !== 'hidden' && Number(style.opacity || '1') !== 0;
                };
                const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
                const clip = (value, size = 80) => {
                  const text = normalize(value);
                  return text.length > size ? text.slice(0, size) + '...' : text;
                };
                const bodyText = normalize(document.body?.innerText || '');
                const inputs = Array.from(document.querySelectorAll('input,textarea'))
                  .filter(el => visible(el) || (el.type || '').toLowerCase() === 'checkbox')
                  .slice(0, 8)
                  .map(el => ({
                    type: el.type || el.tagName.toLowerCase(),
                    placeholder: clip(el.placeholder || ''),
                    name: clip(el.name || ''),
                    disabled: Boolean(el.disabled),
                    checked: (el.type || '').toLowerCase() === 'checkbox' ? Boolean(el.checked) : null
                  }));
                const buttons = Array.from(document.querySelectorAll('button,[role="button"],input[type="submit"],a'))
                  .filter(visible)
                  .map(el => clip(el.innerText || el.textContent || el.value || ''))
                  .filter(Boolean)
                  .slice(0, 10);
                const errors = Array.from(document.querySelectorAll(
                  '[role="alert"],.ant-form-item-explain-error,.el-form-item__error,[class*="error"],[class*="Error"],[class*="message"],[class*="Message"]'
                ))
                  .filter(visible)
                  .map(el => clip(el.innerText || el.textContent || ''))
                  .filter(Boolean)
                  .slice(0, 6);
                return {
                  href: location.href,
                  title: document.title,
                  captcha: /验证码|校验码|滑块|拖动|安全验证|身份验证|行为验证|captcha|verification|verify|human/i.test(bodyText),
                  bodyHint: clip(bodyText, 160),
                  inputs,
                  buttons,
                  errors
                };
                """
            )
        except WebDriverException as exc:
            self.log(f"{context}，且无法读取登录页诊断信息：{exc.msg[:120]}")
            try:
                self.driver.switch_to.default_content()
            except WebDriverException:
                pass
            return
        finally:
            try:
                self.driver.switch_to.default_content()
            except WebDriverException:
                pass

        if not isinstance(state, dict):
            self.log(f"{context}。未拿到页面诊断信息。")
            return

        self.log(f"{context}。当前登录页地址：{state.get('href', '')}")
        if state.get("captcha"):
            self.log("检测到验证码/安全验证提示，这一步不能可靠自动绕过，需要先在浏览器里手动完成验证。")
        errors = [item for item in state.get("errors", []) if item]
        if errors:
            self.log("页面提示：" + " / ".join(errors))
        buttons = [item for item in state.get("buttons", []) if item]
        if buttons:
            self.log("当前可见按钮：" + " / ".join(buttons[:6]))
        inputs = state.get("inputs", [])
        if inputs:
            summary = []
            for item in inputs[:5]:
                if not isinstance(item, dict):
                    continue
                label = item.get("placeholder") or item.get("name") or item.get("type") or "input"
                if item.get("disabled"):
                    label += "(禁用)"
                if item.get("checked") is not None:
                    label += "(已勾选)" if item.get("checked") else "(未勾选)"
                summary.append(label)
            if summary:
                self.log("当前输入框：" + " / ".join(summary))

    def ensure_login_agreement_checked(self) -> None:
        checkbox = self.find_first("login_agreement_checkbox", timeout=5)
        if not checkbox:
            self.log("未找到登录协议复选框，继续尝试登录。")
            return
        try:
            checked = (
                checkbox.is_selected()
                or (checkbox.get_attribute("aria-checked") or "").lower() == "true"
                or "checked" in (checkbox.get_attribute("class") or "").lower()
                or "checked" in (checkbox.get_attribute("outerHTML") or "").lower()
            )
            if checked:
                self.log("登录协议已勾选。")
                return
        except WebDriverException:
            pass
        try:
            self.safe_click(checkbox)
            self.log("已勾选登录协议。")
            time.sleep(0.5)
        except WebDriverException as exc:
            try:
                if self.driver:
                    self.driver.execute_script(
                        """
                        const node = arguments[0];
                        const input = node.matches && node.matches('input[type="checkbox"]')
                          ? node
                          : (node.querySelector && node.querySelector('input[type="checkbox"]'));
                        if (input) {
                          input.checked = true;
                          input.dispatchEvent(new Event('input', { bubbles: true }));
                          input.dispatchEvent(new Event('change', { bubbles: true }));
                          return true;
                        }
                        return false;
                        """,
                        checkbox,
                    )
                    self.log("已通过脚本勾选登录协议。")
            except WebDriverException:
                self.log(f"勾选登录协议失败：{exc.msg[:120]}")

    def is_logged_in(self) -> bool:
        assert self.driver
        try:
            url = (self.driver.current_url or "").lower()
            netloc = urlparse(url).netloc.lower()
            if "crm.okki.com" not in netloc:
                return False
            if self.is_okki_login_url(url):
                return False
            if self.login_form_present_anywhere():
                return False
            text = self.safe_body_text().lower()
            cn_text = self.safe_body_text()
            strong_login_words = any(
                word in text or word in cn_text
                for word in ("登录", "登錄", "login", "sign in", "扫码登录", "密码登录", "验证码登录", "立即登录")
            )
            app_words = self.has_authenticated_app_markers()
            if strong_login_words and not app_words:
                return False
            return app_words
        except WebDriverException:
            return False

    def page_looks_traditional_chinese(self) -> bool:
        text = self.safe_body_text()
        return any(
            token in text
            for token in (
                "請輸入搜索關鍵字",
                "請輸入產品名稱",
                "請輸入數字",
                "請輸入公司名稱",
                "採購商國家/地區",
                "供應商國家/地區",
                "智能貿易數據",
                "採購商信息",
                "供應商信息",
                "進口",
                "出口/過境",
            )
        )

    def current_url_looks_like_smart_trade(self) -> bool:
        assert self.driver
        try:
            parsed = urlparse(self.driver.current_url or "")
        except WebDriverException:
            return False
        path = (parsed.path or "").lower().rstrip("/")
        return any(
            token in path
            for token in (
                "/new_discovery/ciq-datum",
                "/ciq-datum",
                "/international-trade",
                "/product-transaction",
            )
        )

    def ensure_simplified_chinese_ui(self) -> None:
        assert self.driver
        if not self.page_looks_traditional_chinese():
            return
        self.log("检测到 OKKI 页面处于繁体界面，尝试切回简体中文。")
        try:
            switched = bool(
                self.driver.execute_script(
                    """
                    const visible = (el) => {
                      if (!el) return false;
                      const rect = el.getBoundingClientRect();
                      const style = getComputedStyle(el);
                      return rect.width > 0 && rect.height > 0 && style.display !== 'none'
                        && style.visibility !== 'hidden' && Number(style.opacity || '1') !== 0;
                    };
                    const normalize = (value) => String(value || '').replace(/\\s+/g, '').trim();
                    const candidates = Array.from(document.querySelectorAll('button,a,div,span,li,p,[role="button"],[role="menuitem"]'))
                      .filter(visible)
                      .filter((el) => {
                        const text = normalize(el.innerText || el.textContent || el.getAttribute('title') || el.getAttribute('aria-label') || '');
                        return /简体中文|簡體中文|简中|簡中/.test(text);
                      });
                    if (candidates.length) {
                      candidates[0].scrollIntoView({ block: 'center', inline: 'center' });
                      candidates[0].click();
                      return true;
                    }
                    try {
                      localStorage.setItem('locale', 'zh-CN');
                      localStorage.setItem('lang', 'zh-CN');
                      localStorage.setItem('language', 'zh-CN');
                      localStorage.setItem('i18n_locale', 'zh-CN');
                      localStorage.setItem('i18nLanguage', 'zh-CN');
                    } catch (err) {}
                    return false;
                    """
                )
            )
            if switched:
                time.sleep(2)
                self.wait_document_ready()
            if self.page_looks_traditional_chinese():
                try:
                    self.driver.refresh()
                    self.wait_document_ready()
                    time.sleep(2)
                except WebDriverException:
                    pass
            if self.page_looks_traditional_chinese():
                self.log("未找到可用的简体切换入口，当前页面仍可能显示繁体。")
            else:
                self.log("已切回简体中文界面。")
        except WebDriverException:
            pass

    def open_smart_trade_page(self) -> None:
        assert self.driver
        target = self.config.okki_smart_trade_url.strip() or self.config.okki_base_url
        self.log(f"打开智能贸易数据页面：{target}")
        self.driver.get(target)
        self.wait_document_ready()
        time.sleep(2)
        self.ensure_simplified_chinese_ui()

        if self.current_url_looks_like_smart_trade() or (self.is_direct_target_url(target) and self.page_looks_like_smart_trade()):
            self.log("已进入智能贸易数据页面。")
            return

        self.log("未直接识别到智能贸易数据页面，尝试从菜单点击进入。")
        menu_paths = [
            ["渠道获客", "智能贸易数据"],
            ["OKKI Leads", "渠道获客", "智能贸易数据"],
            ["OKKI Leads", "智能贸易数据"],
            ["OKKI Leads", "全网找客", "智能贸易数据"],
            ["OKKI Leads", "全球数据", "智能贸易数据"],
            ["OKKI Leads", "数据查询", "智能贸易数据"],
            ["OKKI Leads", "智能拓客", "智能贸易数据"],
            ["线索", "智能贸易数据"],
            ["线索", "全网找客", "智能贸易数据"],
            ["线索", "全球数据", "智能贸易数据"],
            ["线索", "数据查询", "智能贸易数据"],
            ["International Trade"],
            ["Omnichannel Data", "International Trade"],
            ["OKKI Leads", "International Trade"],
            ["OKKI Leads", "Omnichannel Data", "International Trade"],
            ["Product Transaction"],
            ["Auto Monitoring", "Product Transaction"],
            ["智能贸易数据"],
            ["国际贸易"],
            ["全渠道数据", "国际贸易"],
            ["小栗子", "更多搜索", "智能贸易数据"],
            ["更多搜索", "智能贸易数据"],
            ["客户发掘", "智能贸易数据"],
            ["线索开发", "智能贸易数据"],
            ["海关数据", "智能贸易数据"],
            ["智能贸易数据"],
        ]
        for path in menu_paths:
            try:
                for label in path:
                    self.click_text(label, timeout=6)
                    time.sleep(1)
                self.wait_document_ready()
                self.ensure_simplified_chinese_ui()
                if self.page_looks_like_smart_trade(strict=True):
                    self.log("已通过菜单进入智能贸易数据页面。")
                    return
            except Exception:
                continue
        self.log("菜单自动进入未成功，继续按当前页面尝试搜索。若失败，请把智能贸易数据完整 URL 填入配置。")

    def page_looks_like_smart_trade(self, strict: bool = False) -> bool:
        text = self.safe_body_text()
        lower_text = text.lower()
        try:
            if self.driver and self.is_okki_login_url(self.driver.current_url or ""):
                return False
        except WebDriverException:
            pass
        if self.current_url_looks_like_smart_trade():
            return True
        strong_match = any(
            word in text or word.lower() in lower_text
            for word in (
                "智能贸易数据", "智能貿易數據", "贸易数据", "貿易數據", "海关数据", "海關數據", "HS编码", "HS編碼", "采购商", "採購商", "进口商", "進口商",
                "HS Code", "Buyer", "Importer", "Trade Data", "Trade Records",
                "产品名称", "產品名稱", "采购商名称", "採購商名稱", "供货商", "供貨商", "供应商", "供應商",
                "Search by product", "Search by country", "Search by country or region",
                "整合全球贸易数据", "整合全球貿易數據", "实时关注市场动态", "實時關注市場動態", "覆盖 200+ 国家/地区", "覆蓋 200+ 國家/地區",
                "請輸入搜索關鍵字", "請輸入產品名稱", "請輸入數字", "請輸入公司名稱",
            )
        )
        if strong_match:
            return True
        if strict:
            return False
        return any(word in text or word.lower() in lower_text for word in ("International Trade", "智能贸易", "Smart Trade"))

    def is_direct_target_url(self, target: str) -> bool:
        """默认首页不当作目标页；用户粘贴了具体功能页 URL 时才信任页面识别。"""

        try:
            parsed = urlparse(target)
            base = urlparse(self.config.okki_base_url)
            target_path = parsed.path.rstrip("/")
            base_path = base.path.rstrip("/")
            return bool(target_path and target_path != base_path)
        except Exception:
            return False

    def execute_search(self, country_override: Optional[str] = None) -> None:
        self.check_stop()
        self.log("填写搜索条件。")
        if self.config.product_name.strip():
            if self.fill_field("product_input", self.config.product_name.strip()):
                self.log(f"已填写产品名称：{self.config.product_name.strip()}")
            else:
                self.log("未定位到产品名称输入框，请检查选择器。")

        if self.config.hs_code.strip():
            if self.fill_field("hs_input", self.config.hs_code.strip()):
                self.log(f"已填写 HS 编码：{self.config.hs_code.strip()}")
            elif not self.config.product_name.strip() and self.fill_field("product_input", self.config.hs_code.strip()):
                self.log(f"英文 Smart Prospecting 未找到独立 HS 输入框，已把 HS 编码填入产品/公司搜索框：{self.config.hs_code.strip()}")
            else:
                self.log("未定位到 HS 编码输入框，请检查选择器。")

        country_text = sanitize_text(country_override if country_override is not None else self.current_country_context or self.config.country)
        if country_text:
            selected = self.select_country(country_text)
            if selected:
                self.log(f"已选择采购商国家/地区：{country_text}")
            else:
                self.log(f"当前页面暂未出现采购商国家/地区筛选框，先按产品搜索进入结果页后再选择：{country_text}")
                if not self.click_search_button():
                    raise NoSuchElementException("未找到搜索/查询按钮。")
                self.log("已先执行产品搜索，等待结果页加载。")
                self.wait_for_results_or_empty()
                time.sleep(1.5)
                selected = self.select_country(country_text)
                if selected:
                    self.log(f"已在结果页选择采购商国家/地区：{country_text}")
                    self.wait_for_results_or_empty()
                    return
                raise NoSuchElementException(f"未能在结果页采购商国家/地区筛选框中选择：{country_text}")
        else:
            self.log("未输入国家/地区，默认按全部国家采集。")

        if not self.click_search_button():
            raise NoSuchElementException("未找到搜索/查询按钮。")
        self.log("已执行搜索，等待结果加载。")
        self.wait_for_results_or_empty()

    def click_search_button(self) -> bool:
        self.log("尝试点击搜索按钮。")
        button = self.find_first("search_button", timeout=8)
        if button:
            try:
                self.safe_click(button)
                self.log("已通过元素定位点击搜索按钮。")
                return True
            except WebDriverException:
                pass

        assert self.driver
        try:
            clicked = self.driver.execute_script(
                """
                const visible = (el) => {
                  const rect = el.getBoundingClientRect();
                  const style = getComputedStyle(el);
                  return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
                };
                const textOf = (el) => (el.innerText || el.textContent || el.value || '').trim();
                const clickElement = (el) => {
                  const target = el.closest('button,[role="button"],a,.ant-btn,.el-button,[class*="btn"],[class*="button"]') || el;
                  target.scrollIntoView({block: 'center', inline: 'center'});
                  target.click();
                  return true;
                };

                const directCandidates = Array.from(document.querySelectorAll('button,[role="button"],a,.ant-btn,.el-button,[class*="btn"],[class*="button"],div,span'));
                const exactTarget = directCandidates
                  .filter(visible)
                  .find(el => /^(搜索|查询|search)$/i.test(textOf(el)));
                if (exactTarget) {
                  return clickElement(exactTarget);
                }

                const target = directCandidates.find(el => visible(el) && /搜索|查询|search/i.test(textOf(el)));
                if (target) {
                  return clickElement(target);
                }

                const inputs = Array.from(document.querySelectorAll('input')).filter(visible);
                const anchor = inputs.find(el => /请输入公司名称|company/i.test(el.placeholder || '')) || inputs[inputs.length - 1];
                if (anchor) {
                  const buttons = directCandidates.filter(visible);
                  const rect = anchor.getBoundingClientRect();
                  const nearby = buttons
                    .map(el => ({ el, rect: el.getBoundingClientRect() }))
                    .filter(item => item.rect.left >= rect.left && item.rect.top >= rect.top - 60 && item.rect.top <= rect.top + 100)
                    .sort((a, b) => a.rect.left - b.rect.left)[0];
                  if (nearby) {
                    return clickElement(nearby.el);
                  }
                }

                const viewportRight = document.documentElement.clientWidth || window.innerWidth;
                const formBand = Array.from(document.querySelectorAll('input')).filter(visible).map(el => el.getBoundingClientRect());
                const top = formBand.length ? Math.min(...formBand.map(rect => rect.top)) : 0;
                const bottom = formBand.length ? Math.max(...formBand.map(rect => rect.bottom)) : window.innerHeight;
                const rightSide = directCandidates
                  .filter(visible)
                  .map(el => ({ el, rect: el.getBoundingClientRect(), text: textOf(el), style: getComputedStyle(el) }))
                  .filter(item => item.rect.left > viewportRight * 0.65 && item.rect.top >= top - 60 && item.rect.bottom <= bottom + 80)
                  .sort((a, b) => (b.rect.width * b.rect.height) - (a.rect.width * a.rect.height))[0];
                if (rightSide) {
                  return clickElement(rightSide.el);
                }
                return false;
                """
            )
            if clicked:
                self.log("已通过页面脚本点击搜索按钮。")
                return True
        except WebDriverException:
            pass

        try:
            ActionChains(self.driver).send_keys(Keys.ENTER).perform()
            self.log("未直接定位到按钮，已发送 Enter 作为搜索兜底。")
            return True
        except WebDriverException:
            return False

    def process_result_pages(self) -> None:
        try:
            page_limit = int(self.config.max_pages)
        except Exception:
            page_limit = 0
        unlimited = page_limit <= 0
        safety_limit = 5000
        page_index = 1
        consecutive_old_pages = 0
        stop_old_pages = int(self.config.incremental_stop_old_pages or INCREMENTAL_STOP_OLD_PAGES)
        enable_old_stop = stop_old_pages > 0
        empty_page_streak = 0
        if unlimited:
            self.log("分页策略：全量翻页（直到最后一页）。")
        else:
            self.log(f"分页策略：最多处理 {page_limit} 页。")
        if enable_old_stop:
            self.log(f"增量策略：从第 1 页开始扫描，连续 {stop_old_pages} 页无新增即停止。")
        else:
            self.log("增量策略：已关闭连续无新增提前结束，将按翻页条件完整扫描。")

        while True:
            self.check_stop()
            if page_index > safety_limit:
                self.log(f"分页安全保护触发：超过 {safety_limit} 页，已停止。")
                break
            if not unlimited and page_index > page_limit:
                self.log(f"达到分页上限 {page_limit} 页，停止继续翻页。")
                break

            self.log(f"开始处理第 {page_index} 页结果。")
            self.wait_for_results_or_empty()
            rows = self.get_result_rows()
            if not rows:
                if empty_page_streak == 0 and self.driver:
                    self.log("分页检测：当前页为空，尝试刷新后重读。")
                    try:
                        self.driver.refresh()
                        self.wait_document_ready()
                        self.wait_for_results_or_empty()
                        rows = self.get_result_rows()
                    except Exception:
                        rows = []
                self.log("当前页没有可处理的结果行。")
                empty_page_streak += 1
                page_new_count = 0
                if empty_page_streak >= 2:
                    self.log("分页检测：连续空页，判定该国家已到末页或页面异常，结束该国家采集。")
                    break
            else:
                empty_page_streak = 0
                self.log(f"当前页识别到 {len(rows)} 条贸易记录。")
                page_new_count, page_success_count = self.process_current_page(page_index)
                self.log(f"第 {page_index} 页新增记录 {page_new_count} 条，本页成功采集 {page_success_count} 条。")

            if enable_old_stop:
                if page_new_count <= 0:
                    consecutive_old_pages += 1
                    self.log(f"增量检测：第 {page_index} 页无新增，连续无新增页 {consecutive_old_pages}/{stop_old_pages}。")
                else:
                    consecutive_old_pages = 0

                if consecutive_old_pages >= stop_old_pages:
                    self.log(f"增量检测：连续 {stop_old_pages} 页无新增，提前结束本次采集。")
                    try:
                        self.save_incremental_state()
                    except Exception as exc:
                        self.log(f"增量状态写入失败（已忽略）：{type(exc).__name__}")
                    break

            try:
                self.save_incremental_state()
            except Exception as exc:
                self.log(f"增量状态写入失败（已忽略）：{type(exc).__name__}")
            if not self.go_next_page():
                self.log("没有下一页，结果处理结束。")
                break
            page_index += 1
            time.sleep(2)
            self.wait_for_results_or_empty()

    def process_current_page(self, page_index: int) -> Tuple[int, int]:
        row_count = len(self.get_result_rows())
        page_new_count = 0
        page_success_count = 0
        for row_index in range(row_count):
            self.check_stop()
            trade_key = ""
            try:
                rows = self.get_result_rows()
                if row_index >= len(rows):
                    break
                row = rows[row_index]
                record = self.parse_trade_record(row, row_index=row_index + 1, page_index=page_index)
                company_label = record.company_name or f"第{page_index}页第{row_index + 1}行"
                trade_key = self.build_trade_key(record)
                if trade_key and trade_key in self.incremental_seen_keys:
                    self.log(f"增量跳过：{company_label}，历史已处理。")
                    continue
                if trade_key:
                    page_new_count += 1

                if self._is_bad_buyer_line(record.company_name):
                    self.log(f"跳过：第{page_index}页第{row_index + 1}行，采购商名称为空或无效。")
                    if trade_key:
                        self.mark_trade_seen(trade_key)
                    continue
                if not self.record_matches_current_country(record):
                    country_label = sanitize_text(record.country) or "未知国家"
                    target_country = sanitize_text(self.current_country_context or self.config.country)
                    self.log(f"跳过：{company_label}，所在国家 {country_label} 不匹配筛选国家 {target_country}。")
                    continue
                amount_label = sanitize_text(record.raw_amount)
                if not amount_label:
                    try:
                        amount_label = f"{float(record.amount):.2f}"
                    except Exception:
                        amount_label = sanitize_text(record.amount)

                if record.amount < self.config.min_amount_threshold:
                    self.log(f"跳过：{company_label}，金额 {amount_label} 低于阈值 {self.config.min_amount_threshold:.2f}。")
                    if trade_key:
                        self.mark_trade_seen(trade_key)
                    continue

                if not self.row_has_contact_badge(row):
                    self.log(f"跳过：{company_label}，未标记有联系人。")
                    if trade_key:
                        self.mark_trade_seen(trade_key)
                    continue

                rough_key = normalize_company_name(record.company_name)
                if rough_key and rough_key in self.processed_keys:
                    self.log(f"跳过：{record.company_name} 已处理过。")
                    if trade_key:
                        self.mark_trade_seen(trade_key)
                    continue

                self.log(f"处理采购商：{company_label}，金额 {amount_label}。")
                if not self.open_record_detail(row, buyer_name=record.company_name):
                    self.log(f"跳过：{company_label}，无法进入详情页。")
                    if rough_key:
                        self.processed_keys.add(rough_key)
                    if trade_key:
                        self.mark_trade_seen(trade_key)
                    continue

                detail_info = self.extract_detail_info(record)
                self.return_to_results()

                website = normalize_url(detail_info.website)
                if not is_valid_website_url(website):
                    self.log(f"跳过：{detail_info.company_name or company_label}，官网 URL 为空或无效。")
                    if rough_key:
                        self.processed_keys.add(rough_key)
                    if trade_key:
                        self.mark_trade_seen(trade_key)
                    continue
                final_key = normalize_company_name(detail_info.company_name or record.company_name or website)
                if final_key and final_key in self.processed_keys:
                    self.log(f"跳过：{detail_info.company_name or record.company_name} 已处理过。")
                    if rough_key:
                        self.processed_keys.add(rough_key)
                    if trade_key:
                        self.mark_trade_seen(trade_key)
                    continue

                profile = self.collect_website_profile(website, detail_info.company_name or record.company_name)
                useful, reason = self.evaluate_website_profile(profile)
                if not useful:
                    self.log(f"跳过：{detail_info.company_name or record.company_name or company_label}，{reason}。")
                    if rough_key:
                        self.processed_keys.add(rough_key)
                    if final_key:
                        self.processed_keys.add(final_key)
                    if trade_key:
                        self.mark_trade_seen(trade_key)
                    continue
                result = self.build_result_row(record, detail_info, profile)
                self.results.append(result)
                self.business_tables.append(self.build_business_table(record, detail_info, profile))
                self.append_live_result(result)
                if self.on_result:
                    try:
                        self.on_result(dict(result))
                    except Exception:
                        pass
                if rough_key:
                    self.processed_keys.add(rough_key)
                if final_key:
                    self.processed_keys.add(final_key)
                if trade_key:
                    self.mark_trade_seen(trade_key)
                page_success_count += 1
                self.log(f"采集成功：{result['公司名称']}，当前累计 {len(self.results)} 条。")
            except Exception as exc:
                self.log(f"本行处理失败，已跳过。原因：{type(exc).__name__}: {str(exc)[:180]}")
                try:
                    self.return_to_results()
                except Exception:
                    pass
                # 异常行不记入历史，留给下次重试
        return page_new_count, page_success_count

    def parse_trade_record(self, row: WebElement, row_index: int, page_index: int) -> TradeRecord:
        row_text = sanitize_text(row.text)
        table_data = self.extract_row_cells_with_headers(row)
        company_name = self.pick_company_from_row(row, table_data, row_text)
        amount, raw_amount = parse_amount(row_text)
        buyer_country = self.extract_buyer_country(row, table_data, row_text)
        country = buyer_country or self.pick_cell_by_keywords(table_data, ("国家", "地区", "country", "region")) or self.current_country_context or self.config.country
        city = self.pick_cell_by_keywords(table_data, ("城市", "city"))
        return TradeRecord(
            company_name=company_name,
            amount=amount,
            raw_amount=raw_amount,
            country=country,
            city=city,
            row_text=row_text,
            row_index=row_index,
            page_index=page_index,
        )

    def extract_row_cells_with_headers(self, row: WebElement) -> Dict[str, str]:
        try:
            script = """
                const row = arguments[0];
                const table = row.closest('table');
                const cells = Array.from(row.querySelectorAll('td,[role="cell"]')).map(c => (c.innerText || c.textContent || '').trim());
                let headers = [];
                if (table) {
                  headers = Array.from(table.querySelectorAll('thead th,[role="columnheader"]')).map(h => (h.innerText || h.textContent || '').trim());
                }
                const out = {};
                cells.forEach((cell, idx) => {
                  const key = headers[idx] || `列${idx + 1}`;
                  out[key] = cell;
                });
                return out;
            """
            data = self.driver.execute_script(script, row) if self.driver else {}
            if isinstance(data, dict):
                return {sanitize_text(k): sanitize_text(v) for k, v in data.items()}
        except (JavascriptException, StaleElementReferenceException):
            pass
        return {}

    @staticmethod
    def pick_cell_by_keywords(data: Dict[str, str], keywords: Sequence[str]) -> str:
        for key, value in data.items():
            if any(word.lower() in key.lower() for word in keywords):
                return sanitize_text(value)
        return ""

    @staticmethod
    def normalize_country_display(value: str) -> str:
        text = sanitize_text(value)
        if not text:
            return ""
        text = re.sub(r"[\U0001F1E6-\U0001F1FF]{2,}", " ", text)
        text = re.sub(r"(有联系人|同事客户|联系人|未知国家|unknown country|unknown)", " ", text, flags=re.I)
        text = sanitize_text(text)
        if not text:
            return ""

        lower = text.lower()
        for chinese_name, aliases in COUNTRY_ALIASES.items():
            for alias in [chinese_name, *aliases]:
                alias_lower = alias.lower()
                if not alias_lower:
                    continue
                if lower == alias_lower:
                    return chinese_name
                if re.search(rf"\b{re.escape(alias_lower)}\b", lower):
                    return chinese_name
                if alias in text:
                    return chinese_name

        zh_match = re.search(r"[\u4e00-\u9fff]{2,8}", text)
        if zh_match:
            candidate = zh_match.group(0)
            if candidate not in {"采购商", "供应商", "联系人", "有联系人"}:
                return candidate
        return ""

    def extract_buyer_country(self, row: WebElement, table_data: Dict[str, str], row_text: str) -> str:
        dom_country = self.extract_buyer_country_from_dom(row)
        if dom_country:
            return dom_country

        buyer_cell = self.pick_cell_by_keywords(table_data, ("采购商", "买家", "进口商", "buyer", "importer"))
        candidates: List[str] = []
        if buyer_cell:
            candidates.extend(re.split(r"\n+", buyer_cell))

        for item in candidates:
            country = self.normalize_country_display(item)
            if country:
                return country
        return ""

    def extract_buyer_country_from_dom(self, row: WebElement) -> str:
        assert self.driver
        try:
            value = self.driver.execute_script(
                """
                const row = arguments[0];
                const visible = (el) => {
                  if (!el) return false;
                  const rect = el.getBoundingClientRect();
                  const style = getComputedStyle(el);
                  return rect.width > 0 && rect.height > 0 && style.display !== 'none'
                    && style.visibility !== 'hidden' && Number(style.opacity || '1') !== 0;
                };
                const norm = (v) => String(v || '').replace(/\\s+/g, ' ').trim();
                const table = row.closest('table');
                const headers = table
                  ? Array.from(table.querySelectorAll('thead th,[role="columnheader"]')).map((h) => norm(h.innerText || h.textContent || ''))
                  : [];
                const cells = Array.from(row.querySelectorAll('td,[role="cell"]'));
                const buyerIndex = headers.findIndex((h) => /采购商|採購商|买家|買家|进口商|進口商|buyer|importer/i.test(h));
                const buyerCell = buyerIndex >= 0 && cells[buyerIndex] ? cells[buyerIndex] : null;
                if (!buyerCell || !visible(buyerCell)) return '';

                const countryNodes = Array.from(buyerCell.querySelectorAll('span,div,p,em,strong,b'))
                  .filter(visible)
                  .map((el) => norm(el.innerText || el.textContent || ''))
                  .filter(Boolean)
                  .filter((text) => !/有联系人|有聯繫人|同事客户|联系人|未知国家|unknown/i.test(text));
                for (const text of countryNodes) {
                  if (/加拿大|canada/i.test(text)) return text;
                  if (/美国|美國|united states|usa|u\\.s\\.|u\\.s\\.a\\./i.test(text)) return text;
                  if (/英国|英國|united kingdom|uk|澳大利亚|澳洲|australia|德国|德國|germany|法国|法國|france|荷兰|荷蘭|netherlands/i.test(text)) return text;
                }
                const text = norm(buyerCell.innerText || buyerCell.textContent || '');
                return text;
                """,
                row,
            )
            return self.normalize_country_display(sanitize_text(value))
        except (JavascriptException, StaleElementReferenceException, WebDriverException):
            return ""

    def row_has_contact_badge(self, row: WebElement) -> bool:
        try:
            return bool(
                self.driver.execute_script(
                    """
                    const row = arguments[0];
                    const visible = (el) => {
                      if (!el) return false;
                      const rect = el.getBoundingClientRect();
                      const style = getComputedStyle(el);
                      return rect.width > 0 && rect.height > 0 && style.display !== 'none'
                        && style.visibility !== 'hidden' && Number(style.opacity || '1') !== 0;
                    };
                    const nodes = Array.from(row.querySelectorAll('span,div,a,button,em,i,strong,b'))
                      .filter(visible);
                    return nodes.some((el) => {
                      const text = String(el.innerText || el.textContent || '').replace(/\\s+/g, '').trim();
                      return text === '有联系人' || text === '有聯繫人';
                    });
                    """,
                    row,
                )
            )
        except (JavascriptException, StaleElementReferenceException, WebDriverException):
            try:
                return bool(re.search(r"有\s*联系人|有\s*聯繫人", sanitize_text(row.text)))
            except (StaleElementReferenceException, WebDriverException):
                return False

    def pick_company_from_row(self, row: WebElement, table_data: Dict[str, str], row_text: str) -> str:
        value = self.pick_cell_by_keywords(table_data, ("采购商", "买家", "进口商", "客户", "公司", "buyer", "importer", "company"))
        if value:
            return sanitize_text(value.split("\n")[0])
        try:
            clickable_texts = []
            for element in row.find_elements(By.XPATH, ".//a|.//button|.//*[@role='button']"):
                text = sanitize_text(element.text)
                if text and len(text) > 2 and not re.search(r"详情|查看|more|detail", text, re.I):
                    clickable_texts.append(text)
            if clickable_texts:
                return clickable_texts[0]
        except StaleElementReferenceException:
            pass
        return sanitize_text((row_text or "").split(" ")[0])[:120]

    @staticmethod
    def _is_bad_buyer_line(value: str) -> bool:
        text = sanitize_text(value)
        if not text:
            return True
        if text in {"--", "-", "—", "未知国家", "Unknown", "UNKNOWN"}:
            return True
        if re.search(r"^(有联系人|同事客户|联系人)$", text, flags=re.I):
            return True
        if re.fullmatch(r"(美国|中国大陆|中国香港|中国澳门|中国台湾|未知国家)", text):
            return True
        return False

    def get_buyer_name_click_targets(self, row: WebElement, buyer_name: str = "") -> List[WebElement]:
        assert self.driver
        targets: List[Tuple[int, WebElement]] = []
        expected_name = sanitize_text(buyer_name)
        expected_norm = normalize_company_name(expected_name)
        if not expected_norm or self._is_bad_buyer_line(expected_name):
            return []
        try:
            script = """
                const row = arguments[0];
                const expectedName = (arguments[1] || '').replace(/\\s+/g, ' ').trim();
                const normalizeKey = (v) => (v || '').toLowerCase().replace(/[^a-z0-9\\u4e00-\\u9fff]+/g, '');
                const visible = (el) => {
                  if (!el) return false;
                  const rect = el.getBoundingClientRect();
                  const style = getComputedStyle(el);
                  return rect.width > 0 && rect.height > 0 && style.display !== 'none'
                    && style.visibility !== 'hidden' && Number(style.opacity || '1') !== 0;
                };
                const norm = (v) => (v || '').replace(/\\s+/g, ' ').trim();
                const badLine = /^(--|-|—|未知国家|unknown|有联系人|同事客户|联系人|美国|中国大陆|中国香港|中国澳门|中国台湾)$/i;
                const isBadLine = (text) => !text || badLine.test(text);
                const isBadBlob = (text) => /删除|加入|收藏|下载|导出|联系|营销|whatsapp|邮件|email|icon|search|zoom|loupe|放大镜/.test(text);

                const table = row.closest('table');
                const headers = table
                  ? Array.from(table.querySelectorAll('thead th,[role="columnheader"]')).map((h) => norm(h.innerText || h.textContent || ''))
                  : [];
                const cells = Array.from(row.querySelectorAll('td,[role="cell"]'));
                const buyerIndex = headers.findIndex((h) => /采购商|买家|进口商|buyer|importer|company/i.test(h));
                const buyerCell = buyerIndex >= 0 && cells[buyerIndex] ? cells[buyerIndex] : (cells.length >= 4 ? cells[3] : cells[0] || null);
                if (!buyerCell || !visible(buyerCell)) return [];

                const lines = (buyerCell.innerText || buyerCell.textContent || '')
                  .split(/\\n+/)
                  .map(norm)
                  .filter(Boolean);
                let buyerName = expectedName;
                if (!buyerName) {
                  for (const line of lines) {
                    if (!isBadLine(line) && /[a-zA-Z\\u4e00-\\u9fff]/.test(line)) {
                      buyerName = line;
                      break;
                    }
                  }
                }
                if (!buyerName) return [];
                const buyerNameKey = normalizeKey(buyerName);
                if (!buyerNameKey) return [];

                const candidates = [];
                const push = (el, score, rawText='') => {
                  if (!el || !visible(el)) return;
                  const exists = candidates.find((item) => item.el === el);
                  if (exists) {
                    exists.score = Math.max(exists.score, score);
                    return;
                  }
                  candidates.push({ el, score, rawText });
                };

                const elements = Array.from(buyerCell.querySelectorAll("a,button,[role='button'],span,div,p,strong,b"));
                for (const el of elements) {
                  const text = norm(el.innerText || el.textContent || '');
                  if (isBadLine(text)) continue;
                  const blob = `${text} ${String(el.className || '')} ${String(el.getAttribute('aria-label') || '')} ${String(el.getAttribute('title') || '')}`.toLowerCase();
                  if (isBadBlob(blob)) continue;
                  const first = text.split(/\\n+/).map(norm).find((line) => !isBadLine(line)) || '';
                  const firstKey = normalizeKey(first);
                  const textKey = normalizeKey(text);
                  if (!firstKey && !textKey) continue;
                  if (firstKey !== buyerNameKey && textKey !== buyerNameKey) continue;

                  const clickable = el.closest("a,button,[role='button']") || el;
                  if (!visible(clickable)) continue;
                  const clickableBlob = `${String(clickable.className || '')} ${String(clickable.getAttribute('aria-label') || '')} ${String(clickable.getAttribute('title') || '')}`.toLowerCase();
                  if (isBadBlob(clickableBlob)) continue;

                  let score = 100;
                  if (text === buyerName) score += 30;
                  if (first === buyerName) score += 20;
                  if (clickable === el) score += 10;
                  if (clickable.tagName && clickable.tagName.toLowerCase() === 'a') score += 8;
                  push(el, score + 12, text);
                  if (clickable !== el) {
                    push(clickable, score, text);
                  }
                }

                if ((buyerCell.innerText || buyerCell.textContent || '').includes(buyerName)) {
                  const iconLike = Array.from(buyerCell.querySelectorAll("a,button,[role='button'],svg,use,i,span,div"))
                    .map((el) => {
                      const rect = el.getBoundingClientRect();
                      const blob = [
                        String(el.className || ''),
                        String(el.getAttribute('aria-label') || ''),
                        String(el.getAttribute('title') || ''),
                        String(el.getAttribute('data-icon') || ''),
                        String(el.getAttribute('href') || ''),
                        String(el.innerText || el.textContent || '')
                      ].join(' ').toLowerCase();
                      return { el, rect, blob };
                    })
                    .filter((item) => {
                      if (!visible(item.el)) return false;
                      const smallEnough = item.rect.width <= 44 && item.rect.height <= 44;
                      const isSearchIcon = /search|zoom|loupe|magnifier|fangda|放大|查看|详情|detail/.test(item.blob);
                      return smallEnough && isSearchIcon;
                    });
                  for (const item of iconLike) {
                    const clickable = item.el.closest("a,button,[role='button']") || item.el;
                    push(clickable, 108, '采购商详情图标');
                  }
                }

                candidates.sort((a, b) => b.score - a.score);
                return candidates.slice(0, 4).map((item) => item.el);
            """
            picked = self.driver.execute_script(script, row, expected_name)
            if isinstance(picked, list):
                for item in picked:
                    if isinstance(item, WebElement):
                        targets.append((220, item))
        except (JavascriptException, StaleElementReferenceException, WebDriverException):
            pass

        try:
            fallback_elements = row.find_elements(By.XPATH, ".//a|.//button|.//*[@role='button']|.//span|.//div")
            for element in fallback_elements:
                try:
                    text = sanitize_text(element.text)
                    if not text or self._is_bad_buyer_line(text):
                        continue
                    first_line = ""
                    for line in re.split(r"\n+", text):
                        line_value = sanitize_text(line)
                        if line_value and not self._is_bad_buyer_line(line_value):
                            first_line = line_value
                            break
                    text_norm = normalize_company_name(text)
                    first_norm = normalize_company_name(first_line)
                    if first_norm != expected_norm and text_norm != expected_norm:
                        continue
                    blob = " ".join(
                        [
                            text.lower(),
                            sanitize_text(element.get_attribute("class")).lower(),
                            sanitize_text(element.get_attribute("aria-label")).lower(),
                            sanitize_text(element.get_attribute("title")).lower(),
                        ]
                    )
                    if re.search(r"icon|search|zoom|loupe|放大镜|删除|下载|导出|营销|email|whatsapp", blob, flags=re.I):
                        continue
                    if element.is_displayed():
                        score = 126
                        if first_norm == expected_norm:
                            score += 30
                        if text_norm == expected_norm:
                            score += 25
                        if sanitize_text(element.tag_name).lower() == "a":
                            score += 8
                        targets.append((score, element))

                    tag_name = sanitize_text(element.tag_name).lower()
                    if tag_name not in {"a", "button"} and element.get_attribute("role") != "button":
                        try:
                            clickable_parent = element.find_element(By.XPATH, "./ancestor::*[self::a or self::button or @role='button'][1]")
                            if clickable_parent.is_displayed():
                                parent_score = 112
                                if first_norm == expected_norm:
                                    parent_score += 24
                                if text_norm == expected_norm:
                                    parent_score += 20
                                if sanitize_text(clickable_parent.tag_name).lower() == "a":
                                    parent_score += 8
                                targets.append((parent_score, clickable_parent))
                        except WebDriverException:
                            pass
                except WebDriverException:
                    continue
        except StaleElementReferenceException:
            return []

        dedup: Dict[str, WebElement] = {}
        targets.sort(key=lambda item: item[0], reverse=True)
        ordered: List[WebElement] = []
        for idx, (_, element) in enumerate(targets):
            try:
                key = element.id
            except Exception:
                key = f"fallback-{idx}"
            if key in dedup:
                continue
            dedup[key] = element
            ordered.append(element)
        return ordered

    def detect_detail_state(self, before_url: str, before_handles: set[str]) -> str:
        assert self.driver
        try:
            if set(self.driver.window_handles) - before_handles:
                return "window"
        except WebDriverException:
            pass
        try:
            if self.detail_panel_visible():
                return "panel"
        except WebDriverException:
            pass
        try:
            if self.driver.current_url != before_url:
                return "navigate"
        except WebDriverException:
            pass
        return "none"

    def wait_detail_state(self, before_url: str, before_handles: set[str], timeout: float) -> str:
        deadline = time.time() + max(timeout, 1)
        while time.time() < deadline:
            state = self.detect_detail_state(before_url, before_handles)
            if state != "none":
                return state
            time.sleep(0.25)
        return "none"

    def open_record_detail(self, row: WebElement, buyer_name: str = "") -> bool:
        assert self.driver
        before_handles = set(self.driver.window_handles)
        before_url = self.driver.current_url
        self.last_detail_open_state = "none"
        try:
            targets = self.get_buyer_name_click_targets(row, buyer_name=buyer_name)
        except StaleElementReferenceException:
            return False

        if not targets:
            self.log("详情打开失败：未定位到可点击的采购商名称元素。")
            return False

        max_attempts = max(1, min(len(targets), 2))
        for index, target in enumerate(targets[:max_attempts], start=1):
            clicked = False
            target_label = ""
            try:
                target_label = sanitize_text(target.text).split("\n")[0]
            except Exception:
                target_label = ""
            self.log(f"详情打开：尝试点击采购商名称文本 [{target_label or buyer_name}]（{index}/{max_attempts}）。")
            try:
                self.safe_click(target)
                clicked = True
            except Exception:
                try:
                    ActionChains(self.driver).move_to_element(target).click().perform()
                    clicked = True
                except Exception:
                    try:
                        self.driver.execute_script("arguments[0].click();", target)
                        clicked = True
                    except Exception:
                        clicked = False
            if not clicked:
                continue

            state = self.wait_detail_state(
                before_url,
                before_handles,
                timeout=max(2.0, min(float(self.config.detail_wait_seconds), 4.5)),
            )
            if state == "none":
                continue

            self.last_detail_open_state = state
            if state == "window":
                try:
                    new_handles = list(set(self.driver.window_handles) - before_handles)
                    if new_handles:
                        self.driver.switch_to.window(new_handles[0])
                        self.wait_document_ready()
                except WebDriverException:
                    pass
            elif state == "navigate":
                self.wait_document_ready()
            self.log(f"详情打开成功（状态：{state}，采购商名称点击 {index}/{max_attempts}）。")
            return True

        self.last_detail_open_state = "none"
        return False

    def detail_panel_visible(self) -> bool:
        assert self.driver
        selectors = [".ant-drawer", ".ant-modal", ".el-drawer", ".el-dialog", "[class*='detail']", "[class*='Detail']"]
        for selector in selectors:
            try:
                for element in self.driver.find_elements(By.CSS_SELECTOR, selector):
                    if element.is_displayed() and sanitize_text(element.text):
                        return True
            except WebDriverException:
                continue
        return False

    def extract_detail_info(self, record: TradeRecord) -> DetailInfo:
        time.sleep(1)
        text = self.safe_body_text()
        contacts = harvest_contacts_from_text(text)
        website = self.extract_website_from_detail_card() or self.extract_website_from_detail(text)
        company = self.extract_labeled_value(text, ("采购商", "买家", "进口商", "公司名称", "公司", "Buyer", "Importer", "Company")) or record.company_name
        country = self.extract_labeled_value(text, ("国家", "地区", "Country", "Region")) or record.country
        city = self.extract_labeled_value(text, ("城市", "City")) or record.city
        phones = contacts.get("phones") if isinstance(contacts.get("phones"), list) else []
        emails = contacts.get("emails") if isinstance(contacts.get("emails"), list) else []
        return DetailInfo(
            company_name=company,
            website=website,
            phone=phones[0] if phones else "",
            email=emails[0] if emails else "",
            country=country,
            city=city,
            raw_text=text[:5000],
        )

    def extract_website_from_detail_card(self) -> str:
        assert self.driver
        try:
            candidate = self.driver.execute_script(
                """
                const visible = (el) => {
                  if (!el) return false;
                  const rect = el.getBoundingClientRect();
                  const style = getComputedStyle(el);
                  return rect.width > 0 && rect.height > 0 && style.display !== 'none'
                    && style.visibility !== 'hidden' && Number(style.opacity || '1') !== 0;
                };
                const norm = (v) => (v || '').replace(/\\s+/g, ' ').trim();
                const roots = Array.from(document.querySelectorAll('.ant-drawer,.ant-modal,.el-drawer,.el-dialog,[class*="detail"],[class*="Detail"]'))
                  .filter(visible);
                const root = roots[0] || document.body;
                const top = root.getBoundingClientRect().top;
                const anchors = Array.from(root.querySelectorAll('a[href],a'))
                  .filter(visible)
                  .map((el) => {
                    const href = norm(el.getAttribute('href') || '');
                    const text = norm(el.innerText || el.textContent || '');
                    const rect = el.getBoundingClientRect();
                    const cls = String(el.className || '');
                    const aria = String(el.getAttribute('aria-label') || '');
                    const title = String(el.getAttribute('title') || '');
                    return { href, text, cls, aria, title, top: rect.top };
                  })
                  .filter((item) => item.top <= top + 320);
                const urlLike = /(?:https?:\\/\\/)?(?:www\\.)?[a-z0-9][a-z0-9.-]+\\.[a-z]{2,}(?:\\/[^\\s]*)?/i;
                const bad = /facebook|instagram|linkedin|youtube|twitter|pinterest|google|bing|baidu|map|search|zoom|loupe|放大镜/i;
                const out = [];
                for (const item of anchors) {
                  const blob = `${item.href} ${item.text} ${item.cls} ${item.aria} ${item.title}`.toLowerCase();
                  if (bad.test(blob)) continue;
                  if (urlLike.test(item.href)) out.push(item.href);
                  else if (urlLike.test(item.text)) out.push(item.text);
                }
                return out.length ? out[0] : '';
                """
            )
            if isinstance(candidate, str) and is_valid_website_url(candidate):
                return normalize_url(candidate)
        except WebDriverException:
            pass
        return ""

    def extract_website_from_detail(self, text: str) -> str:
        assert self.driver
        candidates: List[Tuple[str, str, int]] = []
        seen_urls: set[str] = set()

        def add_candidate(raw_url: str, context: str = "", bonus: int = 0) -> None:
            normalized = normalize_url(raw_url)
            if not normalized or normalized in seen_urls:
                return
            if not is_valid_website_url(normalized):
                return
            seen_urls.add(normalized)
            candidates.append((normalized, sanitize_text(context), bonus))

        def score_candidate(url: str, context: str, bonus: int) -> int:
            parsed = urlparse(url)
            host = (parsed.hostname or "").lower()
            path = (parsed.path or "").lower()
            context_lower = sanitize_text(context).lower()
            score = 100 + bonus
            if path in {"", "/"}:
                score += 12
            if parsed.query:
                score -= 10
            if re.search(r"官网|官方网站|website|official|homepage|主页", context_lower):
                score += 36
            if re.search(r"google|bing|baidu|yahoo|duckduckgo|sogou|yandex|谷歌|百度|地图|search|map", context_lower):
                score -= 80
            if re.search(r"linkedin|facebook|instagram|youtube|twitter|wechat|whatsapp|社媒", context_lower):
                score -= 50
            if re.search(r"/(search|maps?|url|imgres|translate)", path):
                score -= 80
            if len(host.split(".")[0]) <= 2:
                score -= 8
            return score

        label_xpaths = [
            "//*[contains(normalize-space(.), '官网URL')]/following::a[@href][1]",
            "//*[contains(normalize-space(.), '官网')]/following::a[@href][1]",
            "//*[contains(normalize-space(.), '官方网站')]/following::a[@href][1]",
            "//*[contains(normalize-space(.), 'Website')]/following::a[@href][1]",
            "//*[contains(normalize-space(.), '网站')]/following::a[@href][1]",
        ]
        for xpath in label_xpaths:
            try:
                element = self.driver.find_element(By.XPATH, xpath)
                href = element.get_attribute("href") or ""
                text_value = element.text or ""
                title_value = element.get_attribute("title") or ""
                aria_value = element.get_attribute("aria-label") or ""
                context = " ".join([text_value, title_value, aria_value])
                add_candidate(href, context, bonus=45)
                add_candidate(text_value, context, bonus=30)
            except NoSuchElementException:
                continue

        try:
            detail_roots: List[WebElement] = []
            for selector in (".ant-drawer", ".ant-modal", ".el-drawer", ".el-dialog", "[class*='detail']", "[class*='Detail']"):
                for root in self.driver.find_elements(By.CSS_SELECTOR, selector):
                    if root.is_displayed():
                        detail_roots.append(root)
            if not detail_roots:
                detail_roots.append(self.driver.find_element(By.TAG_NAME, "body"))
            for root in detail_roots[:2]:
                for anchor in root.find_elements(By.XPATH, ".//a[@href]")[:120]:
                    href = anchor.get_attribute("href") or ""
                    text_value = sanitize_text(anchor.text)
                    title_value = sanitize_text(anchor.get_attribute("title"))
                    aria_value = sanitize_text(anchor.get_attribute("aria-label"))
                    parent_text = ""
                    try:
                        parent = anchor.find_element(By.XPATH, "./ancestor::*[self::div or self::li or self::p][1]")
                        parent_text = sanitize_text(parent.text)[:220]
                    except WebDriverException:
                        pass
                    context = " ".join([text_value, title_value, aria_value, parent_text])
                    bonus = 20 if re.search(r"官网|官方网站|website|official|主页", context, re.I) else 0
                    add_candidate(href, context, bonus=bonus)
                    add_candidate(text_value, context, bonus=bonus - 4)
        except WebDriverException:
            pass

        for match in re.finditer(r"(?:https?://)?(?:www\.)?[a-z0-9][a-z0-9.-]+\.[a-z]{2,}(?:/[^\s，。；;]*)?", text or "", flags=re.I):
            value = match.group(0)
            start = max(0, match.start() - 26)
            end = min(len(text or ""), match.end() + 26)
            context = (text or "")[start:end]
            bonus = 20 if re.search(r"官网|官方网站|website|official|主页", context, re.I) else 8
            add_candidate(value, context, bonus=bonus)

        if candidates:
            ranked = sorted(
                ((score_candidate(url, context, bonus), url) for url, context, bonus in candidates),
                key=lambda item: item[0],
                reverse=True,
            )
            if ranked and ranked[0][0] > 0:
                return ranked[0][1]
        return ""

    @staticmethod
    def extract_labeled_value(text: str, labels: Sequence[str]) -> str:
        for label in labels:
            pattern = rf"{re.escape(label)}\s*[:：]\s*([^\n\r|，,;；]{{2,120}})"
            match = re.search(pattern, text or "", flags=re.I)
            if match:
                return sanitize_text(match.group(1))
        return ""

    def return_to_results(self) -> None:
        assert self.driver
        state = self.last_detail_open_state
        self.last_detail_open_state = "none"

        if len(self.driver.window_handles) > 1:
            current = self.driver.current_window_handle
            self.driver.close()
            for handle in self.driver.window_handles:
                if handle != current:
                    self.driver.switch_to.window(handle)
                    break
            time.sleep(1)
            return

        if state == "panel" or self.detail_panel_visible():
            close = self.find_first("drawer_close", timeout=3)
            if close:
                try:
                    self.safe_click(close)
                    time.sleep(1)
                    return
                except Exception:
                    pass
            try:
                ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                time.sleep(1)
                if self.get_result_rows():
                    return
            except Exception:
                pass

        if state != "navigate":
            return

        try:
            self.driver.back()
            time.sleep(2)
            self.wait_document_ready()
        except WebDriverException:
            pass

    def enter_official_website(self, website: str) -> str:
        if not is_valid_website_url(website) or not self.driver:
            return website
        assert self.driver
        base_url = normalize_url(website) or website
        base_handle = self.driver.current_window_handle
        before_handles = set(self.driver.window_handles)
        final_url = base_url
        try:
            self.driver.execute_script("window.open(arguments[0], '_blank');", base_url)
            WebDriverWait(self.driver, 8).until(lambda d: len(d.window_handles) > len(before_handles))
            new_handles = list(set(self.driver.window_handles) - before_handles)
            if not new_handles:
                self.log(f"官网进入失败：{base_url}，未创建新标签页。")
                return base_url
            self.driver.switch_to.window(new_handles[0])
            self.wait_document_ready()
            time.sleep(1)
            resolved = normalize_url(self.driver.current_url)
            if is_valid_website_url(resolved):
                final_url = resolved
            self.log(f"已进入官网：{final_url}")
            return final_url
        except Exception as exc:
            self.log(f"官网进入失败，改用原始官网抓取：{base_url}，原因：{type(exc).__name__}")
            return base_url
        finally:
            try:
                current = self.driver.current_window_handle
                if current != base_handle and current in self.driver.window_handles:
                    self.driver.close()
            except WebDriverException:
                pass
            try:
                if base_handle in self.driver.window_handles:
                    self.driver.switch_to.window(base_handle)
                    self.wait_document_ready()
            except WebDriverException:
                pass

    def fetch_url_with_browser(self, url: str) -> Tuple[str, str, str, List[Tuple[str, str]]]:
        if not self.driver:
            return "", "", normalize_url(url) or url, []
        assert self.driver
        base_url = normalize_url(url) or url
        if not is_valid_website_url(base_url):
            return "", "", base_url, []

        base_handle = self.driver.current_window_handle
        before_handles = set(self.driver.window_handles)
        final_url = base_url
        html = ""
        text = ""
        links: List[Tuple[str, str]] = []
        browser_page_timeout = max(6, min(int(self.config.page_timeout or PAGE_TIMEOUT), 14))
        try:
            self.driver.execute_script("window.open('about:blank', '_blank');")
            WebDriverWait(self.driver, 8).until(lambda d: len(d.window_handles) > len(before_handles))
            new_handles = list(set(self.driver.window_handles) - before_handles)
            if not new_handles:
                return "", "", final_url, []
            self.driver.switch_to.window(new_handles[0])
            self.driver.set_page_load_timeout(browser_page_timeout)
            self.driver.get(base_url)
            self.wait_document_ready()
            time.sleep(1)
            try:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.6)
            except WebDriverException:
                pass
            resolved = normalize_url(self.driver.current_url)
            if is_valid_website_url(resolved):
                final_url = resolved
            html = self.driver.page_source or ""
            parsed_text, _, _, _, parsed_links = self.parse_html(html, final_url)
            visible_text = self.safe_body_text()
            merged_lines = [
                sanitize_text(line)
                for line in re.split(r"\n+", f"{parsed_text}\n{visible_text}")
                if sanitize_text(line)
            ]
            text = "\n".join(merged_lines)
            links = parsed_links
            return html, text, final_url, links
        except TimeoutException:
            self.log(f"浏览器抓取超时：{base_url}，>{browser_page_timeout} 秒。")
            return "", "", final_url, []
        except Exception as exc:
            self.log(f"浏览器兜底抓取失败：{base_url}，原因：{type(exc).__name__}")
            return "", "", final_url, []
        finally:
            try:
                for handle in list(self.driver.window_handles):
                    if handle not in before_handles:
                        try:
                            self.driver.switch_to.window(handle)
                            self.driver.close()
                        except WebDriverException:
                            pass
            except WebDriverException:
                pass
            try:
                if base_handle in self.driver.window_handles:
                    self.driver.switch_to.window(base_handle)
                    self.driver.set_page_load_timeout(max(10, int(self.config.page_timeout or PAGE_TIMEOUT)))
                    self.wait_document_ready()
                elif self.driver.window_handles:
                    self.driver.switch_to.window(self.driver.window_handles[0])
                    self.driver.set_page_load_timeout(max(10, int(self.config.page_timeout or PAGE_TIMEOUT)))
                    self.wait_document_ready()
            except WebDriverException:
                pass

    def collect_website_profile(self, website: str, fallback_company_name: str) -> WebsiteProfile:
        self.log(f"抓取官网：{website}")
        stage_start = time.time()
        stage_budget = max(35, min(95, int(self.config.request_timeout or REQUEST_TIMEOUT) * 5))
        http_timeout = max(6, min(int(self.config.request_timeout or REQUEST_TIMEOUT), 12))
        next_heartbeat = stage_start + 12

        def stage_guard(step: str) -> bool:
            nonlocal next_heartbeat
            now = time.time()
            elapsed = int(now - stage_start)
            if now >= next_heartbeat:
                self.log(f"官网抓取进行中：{step}，已耗时 {elapsed} 秒。")
                next_heartbeat = now + 12
            if now - stage_start > stage_budget:
                self.log(f"官网抓取超时：{website}，已耗时 {elapsed} 秒，跳过当前采购商官网。")
                return False
            return True

        if not stage_guard("主站抓取前"):
            return WebsiteProfile(company_name=fallback_company_name, website=website)

        text = ""
        title = ""
        h1 = ""
        meta: Dict[str, str] = {}
        links: List[Tuple[str, str]] = []
        html = ""
        final_url = normalize_url(website) or website

        if not stage_guard("requests主站抓取前"):
            return WebsiteProfile(company_name=fallback_company_name, website=final_url or website)
        html, final_url = self.fetch_url(final_url or website, timeout_override=http_timeout)
        if not stage_guard("requests主站抓取后"):
            return WebsiteProfile(company_name=fallback_company_name, website=final_url or website)
        if html:
            text, title, h1, meta, links = self.parse_html(html, final_url)

        # requests 抓不到内容时才用浏览器兜底，减少自动化窗口抢前台。
        if not html and not text and self.driver:
            if not stage_guard("浏览器兜底抓取前"):
                return WebsiteProfile(company_name=fallback_company_name, website=final_url or website)
            browser_html, browser_text, browser_url, browser_links = self.fetch_url_with_browser(final_url or website)
            if browser_html or browser_text:
                parsed_text = ""
                parsed_title = ""
                parsed_h1 = ""
                parsed_meta: Dict[str, str] = {}
                parsed_links: List[Tuple[str, str]] = []
                if browser_html:
                    html = browser_html
                    parsed_text, parsed_title, parsed_h1, parsed_meta, parsed_links = self.parse_html(browser_html, browser_url or final_url)
                if browser_text and len(browser_text) >= len(text):
                    text = browser_text
                elif parsed_text and not text:
                    text = parsed_text
                title = title or parsed_title
                h1 = h1 or parsed_h1
                if parsed_meta:
                    meta = parsed_meta
                if browser_links:
                    links = browser_links
                elif parsed_links:
                    links = parsed_links
                if is_valid_website_url(browser_url):
                    final_url = browser_url

        if not html and not text:
            self.log(f"官网请求失败：{website}")
            return WebsiteProfile(company_name=fallback_company_name, website=website)

        aggregate_text = text or ""
        aggregate_html = html or ""
        social_links = extract_social_links_from_html(aggregate_html)
        visited_links: set[str] = set()
        internal_limit = min(max(int(self.config.max_website_internal_pages or MAX_WEBSITE_INTERNAL_PAGES), 1), 3)
        internal_links = self.find_internal_links(final_url, links)[:internal_limit]
        for link in internal_links:
            self.check_stop()
            if not stage_guard(f"站内补抓 {len(visited_links) + 1}/{len(internal_links)}"):
                break
            normalized_link = normalize_url(link) or link
            if normalized_link in visited_links:
                continue
            visited_links.add(normalized_link)

            extra_text = ""
            extra_html = ""
            extra_final_url = normalize_url(link) or link
            extra_html, extra_final_url = self.fetch_url(link, timeout_override=http_timeout)
            if extra_html:
                extra_text, _, _, _, _ = self.parse_html(extra_html, extra_final_url or link)
            if not stage_guard(f"站内补抓完成 {len(visited_links)}/{len(internal_links)}"):
                break

            if extra_text:
                aggregate_text += "\n" + extra_text
            if extra_html:
                aggregate_html += "\n" + extra_html
                social_links = normalize_social_links([*social_links, *extract_social_links_from_html(extra_html)])

        contacts = harvest_contacts_from_text(aggregate_text, final_url, aggregate_html)
        emails_preview = contacts.get("emails") if isinstance(contacts.get("emails"), list) else []
        if not emails_preview:
            for link in self.guess_contact_page_urls(final_url):
                self.check_stop()
                normalized_link = normalize_url(link) or link
                if normalized_link in visited_links:
                    continue
                visited_links.add(normalized_link)
                if not stage_guard("常见联系页补抓"):
                    break
                extra_html, extra_final_url = self.fetch_url(normalized_link, timeout_override=http_timeout)
                if not extra_html:
                    continue
                extra_text, _, _, _, _ = self.parse_html(extra_html, extra_final_url or normalized_link)
                aggregate_text += "\n" + extra_text
                aggregate_html += "\n" + extra_html
                social_links = normalize_social_links([*social_links, *extract_social_links_from_html(extra_html)])
                contacts = harvest_contacts_from_text(aggregate_text, final_url, aggregate_html)
                emails_preview = contacts.get("emails") if isinstance(contacts.get("emails"), list) else []
                if emails_preview:
                    self.log(f"已从联系页提取邮箱：{extra_final_url or normalized_link}")
                    break
        if not emails_preview:
            self.log("官网邮箱未命中，按规则快速跳过，不执行二次浏览器兜底。")

        company_candidates = [meta.get("og:site_name", ""), meta.get("application-name", ""), h1, title, fallback_company_name]
        company_name = pick_company_name(company_candidates, final_url) or fallback_company_name
        ai_fields: Dict[str, str] = {}
        if stage_guard("业务信息解析前"):
            ai_fields = self.extract_ai_business_fields(aggregate_text, final_url, company_name)
        if not ai_fields and stage_guard("业务信息本地兜底前"):
            ai_fields = self.fallback_business_fields(aggregate_text, final_url, company_name)

        phones = contacts.get("phones") if isinstance(contacts.get("phones"), list) else []
        emails = contacts.get("emails") if isinstance(contacts.get("emails"), list) else []
        addresses = contacts.get("addresses") if isinstance(contacts.get("addresses"), list) else []
        return WebsiteProfile(
            company_name=ai_fields.get("采购商公司名称") or company_name,
            website=final_url,
            phone=phones[0] if phones else "",
            email=emails[0] if emails else "",
            address=addresses[0] if addresses else "",
            social_links=social_links,
            text=aggregate_text[:12000],
            html=aggregate_html[:12000],
            ai_fields=ai_fields,
        )

    def evaluate_website_profile(self, profile: WebsiteProfile) -> Tuple[bool, str]:
        website = normalize_url(profile.website) or sanitize_text(profile.website)
        host = ""
        if website:
            try:
                host = (urlparse(website).hostname or "").lower()
            except Exception:
                host = ""

        if any(
            key in host
            for key in ("edgesuite.net", "akamaized.net", "akamai", "cloudflare", "captcha")
        ):
            return False, "官网页面被拦截或重定向到安全校验页"

        text_probe = sanitize_text(
            " ".join(
                [
                    profile.text[:2500],
                    profile.html[:1500],
                    " ".join((profile.ai_fields or {}).values())[:800],
                ]
            )
        )
        if BLOCKED_WEBSITE_PATTERN.search(text_probe) and not (
            sanitize_text(profile.phone) or sanitize_text(profile.email)
        ):
            return False, "官网页面被拦截/拒绝访问，未获得有效内容"

        has_email = bool(sanitize_text(profile.email))
        if not has_email:
            return False, "官网未提取到邮箱，按规则过滤。"
        return True, ""

    def fetch_url(self, url: str, timeout_override: Optional[int] = None) -> Tuple[str, str]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/123 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.8,zh-CN;q=0.7,zh;q=0.6",
        }
        request_timeout = max(4, int(timeout_override or self.config.request_timeout or REQUEST_TIMEOUT))
        connect_timeout = min(6, max(3, request_timeout // 2))
        normalized = normalize_url(url)
        candidates = [normalized]
        if normalized.startswith("https://"):
            candidates.append("http://" + normalized[8:])
        elif normalized.startswith("http://"):
            candidates.append("https://" + normalized[7:])

        for candidate in unique_values(candidates):
            try:
                with requests.Session() as session:
                    session.max_redirects = 8
                    response = session.get(
                        candidate,
                        headers=headers,
                        timeout=(connect_timeout, request_timeout),
                        allow_redirects=True,
                    )
                content_type = response.headers.get("content-type", "")
                if response.ok and ("text/html" in content_type or "application/xhtml" in content_type or not content_type):
                    return response.text, response.url
                if response.ok and response.text:
                    return response.text, response.url
                self.log(f"官网响应异常：{candidate}，HTTP {response.status_code}")
            except requests.Timeout:
                self.log(f"官网请求超时：{candidate}，>{request_timeout} 秒。")
            except requests.TooManyRedirects:
                self.log(f"官网重定向过多：{candidate}，已跳过。")
            except requests.RequestException as exc:
                self.log(f"官网请求异常：{candidate}，{str(exc)[:120]}")
        return "", normalized

    @staticmethod
    def parse_html(html: str, base_url: str) -> Tuple[str, str, str, Dict[str, str], List[Tuple[str, str]]]:
        text_parser = SimpleHTMLTextExtractor()
        link_parser = SimpleHTMLLinkExtractor()
        try:
            text_parser.feed(html or "")
        except Exception:
            pass
        try:
            link_parser.feed(html or "")
        except Exception:
            pass
        links = [(urljoin(base_url, href), label) for href, label in link_parser.links]
        return text_parser.text, text_parser.title, text_parser.h1, link_parser.meta_values, links

    @staticmethod
    def find_internal_links(base_url: str, links: Sequence[Tuple[str, str]]) -> List[str]:
        base = urlparse(base_url)
        result = []
        for href, label in links:
            parsed = urlparse(href)
            if parsed.netloc.lower().replace("www.", "") != base.netloc.lower().replace("www.", ""):
                continue
            marker = f"{label} {href}".lower()
            if any(word in marker for word in CONTACT_LINK_WORDS):
                result.append(href)
        return unique_values(result)

    def guess_contact_page_urls(self, base_url: str) -> List[str]:
        normalized = normalize_url(base_url)
        if not normalized:
            return []
        parsed = urlparse(normalized)
        root = f"{parsed.scheme}://{parsed.netloc}"
        return unique_values([urljoin(root, path) for path in CONTACT_PATH_CANDIDATES])

    def extract_ai_business_fields(self, text: str, website: str, company_name: str) -> Dict[str, str]:
        if not self.config.yunwu_api_key.strip():
            self.log("未配置 YUNWU_API_KEY，跳过 GPT 解析，使用本地文本规则兜底。")
            return {}

        prompt = "\n".join(
            [
                "你是一名外贸获客信息整理助手。",
                "请从采购商官网文本中提取真实业务信息，只能依据文本，不要编造。",
                "请只输出 JSON 对象，不要 Markdown，不要解释。",
                "字段必须包含：采购商公司名称、官网URL、主营产品/业务范围、产品用途/应用场景、目标客户/合作对象、核心优势/服务能力、相关产品关键词。",
                "如果某项信息不足，请填空字符串。",
                "",
                f"已知公司名称：{company_name or '未知'}",
                f"官网URL：{website}",
                "官网文本：",
                text[:9000],
            ]
        )
        try:
            response = requests.post(
                self.config.yunwu_endpoint,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.config.yunwu_api_key.strip()}",
                },
                json={
                    "model": self.config.yunwu_model,
                    "temperature": 0.2,
                    "messages": [
                        {"role": "system", "content": "你擅长从企业官网文本中提取结构化外贸开发信息。"},
                        {"role": "user", "content": prompt},
                    ],
                },
                timeout=self.config.request_timeout,
            )
            if not response.ok:
                self.log(f"GPT 接口请求失败：HTTP {response.status_code} {response.text[:120]}")
                return {}
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            fields = safe_json_loads_from_text(content)
            if fields:
                fields.setdefault("官网URL", website)
                fields.setdefault("采购商公司名称", company_name)
            return fields
        except (requests.RequestException, ValueError, KeyError, IndexError) as exc:
            self.log(f"GPT 解析异常：{type(exc).__name__}: {str(exc)[:160]}")
            return {}

    @staticmethod
    def fallback_business_fields(text: str, website: str, company_name: str) -> Dict[str, str]:
        lines = [sanitize_text(line) for line in re.split(r"\n+", text or "")]
        lines = [line for line in lines if 20 <= len(line) <= 260 and not NOISE_TEXT_PATTERN.search(line)]
        keyword_lines = [
            line for line in lines
            if re.search(r"\b(product|products|service|services|solution|solutions|manufacturer|supplier|wholesale|distributor|factory|custom|oem|odm|application|industry)\b", line, re.I)
        ]
        selected = keyword_lines[:3] or lines[:3]
        keywords = unique_values(re.findall(r"\b[A-Za-z][A-Za-z0-9+&/-]{2,}(?:\s+[A-Za-z][A-Za-z0-9+&/-]{2,}){0,2}\b", " ".join(selected)))[:12]
        return {
            "采购商公司名称": company_name,
            "官网URL": website,
            "主营产品/业务范围": " ".join(selected)[:500],
            "产品用途/应用场景": "",
            "目标客户/合作对象": "",
            "核心优势/服务能力": "",
            "相关产品关键词": ", ".join(keywords),
        }

    def build_result_row(self, record: TradeRecord, detail: DetailInfo, profile: WebsiteProfile) -> Dict[str, str]:
        ai_fields = profile.ai_fields or {}
        amount_value = sanitize_text(record.raw_amount)
        if not amount_value:
            try:
                amount_value = f"{float(record.amount):.2f}"
            except Exception:
                amount_value = sanitize_text(record.amount)
        return {
            "公司名称": sanitize_text(profile.company_name or detail.company_name or record.company_name),
            "联系电话": sanitize_text(profile.phone or detail.phone),
            "邮箱": sanitize_text(profile.email or detail.email),
            "官网地址": profile.website or detail.website,
            "所在国家": sanitize_text(record.country or detail.country or self.current_country_context or self.config.country),
            "贸易记录金额": amount_value,
            "搜索关键词": self.config.search_keyword,
            "业务介绍": build_business_intro(ai_fields, profile.text),
            "社媒链接": " | ".join(profile.social_links),
        }

    def build_business_table(self, record: TradeRecord, detail: DetailInfo, profile: WebsiteProfile) -> Dict[str, str]:
        ai_fields = profile.ai_fields or {}
        return {
            "公司名称": profile.company_name or detail.company_name or record.company_name,
            "官网URL": ai_fields.get("官网URL") or profile.website or detail.website,
            "主营产品/业务范围": ai_fields.get("主营产品/业务范围", ""),
            "产品用途/应用场景": ai_fields.get("产品用途/应用场景", ""),
            "目标客户/合作对象": ai_fields.get("目标客户/合作对象", ""),
            "核心优势/服务能力": ai_fields.get("核心优势/服务能力", ""),
            "相关产品关键词": ai_fields.get("相关产品关键词", ""),
            "联系电话": profile.phone or detail.phone,
            "邮箱": profile.email or detail.email,
            "社媒链接": " | ".join(profile.social_links),
            "贸易记录金额": record.raw_amount or f"{record.amount:.2f}",
            "搜索关键词": self.config.search_keyword,
        }

    def export_results(self) -> None:
        if not self.results:
            self.log("没有采集成功的数据，跳过文件输出。")
            return
        excel_path, _ = self.get_export_paths()

        excel_dir = os.path.dirname(excel_path)
        if excel_dir:
            os.makedirs(excel_dir, exist_ok=True)

        df = pd.DataFrame(
            self.results,
            columns=RESULT_COLUMNS,
        )
        before_count = len(df)
        if not df.empty:
            company_keys = df["公司名称"].fillna("").map(normalize_company_name)
            website_keys = df["官网地址"].fillna("").map(lambda value: normalize_company_name(urlparse(normalize_url(value) or value).netloc or value))
            dedupe_keys = [
                company_key or website_key or f"row-{index}"
                for index, (company_key, website_key) in enumerate(zip(company_keys, website_keys))
            ]
            df = df.assign(_dedupe_key=dedupe_keys).drop_duplicates(subset=["_dedupe_key"], keep="first").drop(columns=["_dedupe_key"])
        removed_count = before_count - len(df)
        df.to_excel(excel_path, index=False, engine="openpyxl")
        self.log(f"Excel 已生成：{os.path.abspath(excel_path)}")
        if removed_count > 0:
            self.log(f"导出前已自动去重 {removed_count} 条重复公司记录。")
        self.log("已按设置仅导出 Excel。")

    @staticmethod
    def render_business_html(tables: Sequence[Dict[str, str]]) -> str:
        sections = []
        for index, table in enumerate(tables, start=1):
            title = html_escape(table.get("公司名称") or f"采购商 {index}")
            rows = []
            for key, value in table.items():
                rows.append(
                    "<tr>"
                    f"<th>{html_escape(str(key))}</th>"
                    f"<td>{html_escape(str(value or ''))}</td>"
                    "</tr>"
                )
            sections.append(f"<section><h2>{index}. {title}</h2><table>{''.join(rows)}</table></section>")
        return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>OKKI 智能贸易数据业务信息表</title>
  <style>
    body {{ margin: 24px; font-family: Arial, "Microsoft YaHei", sans-serif; color: #1f2937; background: #f7f8fb; }}
    h1 {{ font-size: 22px; margin: 0 0 18px; }}
    h2 {{ font-size: 16px; margin: 24px 0 10px; }}
    section {{ max-width: 980px; margin-bottom: 20px; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #d8dee9; }}
    th, td {{ border: 1px solid #d8dee9; padding: 10px 12px; vertical-align: top; line-height: 1.55; }}
    th {{ width: 210px; background: #eef2f7; text-align: left; }}
  </style>
</head>
<body>
  <h1>OKKI 智能贸易数据业务信息表</h1>
  {''.join(sections)}
</body>
</html>
"""

    def wait_document_ready(self) -> None:
        assert self.driver
        try:
            WebDriverWait(self.driver, self.config.page_timeout).until(
                lambda d: d.execute_script("return document.readyState") in {"interactive", "complete"}
            )
        except TimeoutException:
            self.log("页面加载等待超时，继续尝试后续操作。")

    def wait_for_results_or_empty(self) -> None:
        try:
            WebDriverWait(self.driver, self.config.page_timeout).until(
                lambda d: len(self.get_result_rows()) > 0 or self.page_has_empty_result_state()
            )
        except TimeoutException:
            self.log("搜索结果加载超时，后续将尝试读取当前页面。")

    def page_has_empty_result_state(self) -> bool:
        text = self.safe_body_text()
        if any(word in text for word in ("为你找到", "条数据", "10000+", "贸易产品信息", "Trade Records")):
            return False
        return any(word in text for word in ("暂无数据", "无数据", "没有数据", "暂无搜索结果", "No data", "No results"))

    def get_result_rows(self) -> List[WebElement]:
        assert self.driver
        seen: set[str] = set()
        for by, selector in OKKI_SELECTORS["result_rows"]:
            try:
                rows = []
                for row in self.driver.find_elements(by, selector):
                    if not row.is_displayed():
                        continue
                    text = sanitize_text(row.text)
                    if not text or text in seen:
                        continue
                    if not self.looks_like_trade_result_row(row):
                        continue
                    seen.add(text)
                    rows.append(row)
                if rows:
                    return rows
            except WebDriverException:
                continue
        try:
            rows = self.driver.execute_script(
                """
                const visible = (el) => {
                  if (!el) return false;
                  const rect = el.getBoundingClientRect();
                  const style = getComputedStyle(el);
                  return rect.width > 0 && rect.height > 0 && style.display !== 'none'
                    && style.visibility !== 'hidden' && Number(style.opacity || '1') !== 0;
                };
                const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
                const candidates = Array.from(document.querySelectorAll(
                  'table tbody tr, [role="row"], .ant-table-row, .el-table__row, [class*="table-row"], [class*="TableRow"]'
                ));
                return candidates.filter((row) => {
                  if (!visible(row)) return false;
                  const text = normalize(row.innerText || row.textContent || '');
                  if (!text || /暂无|无数据|no data|no results/i.test(text)) return false;
                  if (/日期.*金额|金额.*采购商|贸易产品信息.*HS/i.test(text)) return false;
                  const cells = Array.from(row.querySelectorAll('td,[role="cell"],[class*="cell"],[class*="Cell"]'))
                    .filter(visible)
                    .map((cell) => normalize(cell.innerText || cell.textContent || ''))
                    .filter(Boolean);
                  const hasMoney = /(?:US\\$|USD|\\$)\\s*[0-9]/i.test(text);
                  const hasDate = /\\b20\\d{2}[-/]\\d{1,2}[-/]\\d{1,2}\\b/.test(text);
                  const hasHs = /\\b\\d{4,10}\\b/.test(text);
                  return cells.length >= 4 && (hasMoney || (hasDate && hasHs));
                });
                """
            )
            if isinstance(rows, list):
                filtered = []
                for row in rows:
                    try:
                        text = sanitize_text(row.text)
                        if text and text not in seen and self.looks_like_trade_result_row(row):
                            seen.add(text)
                            filtered.append(row)
                    except WebDriverException:
                        continue
                if filtered:
                    return filtered
        except WebDriverException:
            pass
        return []

    def looks_like_trade_result_row(self, row: WebElement) -> bool:
        try:
            text = sanitize_text(row.text)
            if not text:
                return False
            if re.search(r"暂无|无数据|没有数据|no data|no results", text, flags=re.I):
                return False
            if re.search(r"日期.*金额|金额.*采购商|采购商.*金额|Buyer.*Amount|Importer.*Value|贸易产品信息.*HS", text, flags=re.I):
                return False
            amount, _ = parse_amount(text)
            if amount > 0:
                return True
            table_data = self.extract_row_cells_with_headers(row)
            non_empty_cells = [value for value in table_data.values() if sanitize_text(value)]
            if len(non_empty_cells) >= 4 and (
                re.search(r"\b20\d{2}[-/]\d{1,2}[-/]\d{1,2}\b", text)
                or re.search(r"\b\d{4,10}\b", text)
            ):
                return True
            return False
        except (StaleElementReferenceException, WebDriverException):
            return False

    def get_active_page_number(self) -> Optional[int]:
        assert self.driver
        try:
            value = self.driver.execute_script(
                """
                const visible = (el) => {
                  if (!el) return false;
                  const rect = el.getBoundingClientRect();
                  const style = getComputedStyle(el);
                  return rect.width > 0 && rect.height > 0 && style.display !== 'none'
                    && style.visibility !== 'hidden' && Number(style.opacity || '1') !== 0;
                };
                const pagers = Array.from(document.querySelectorAll('.ant-pagination,.el-pagination,[class*="pagination"],[class*="Pagination"]'))
                  .filter(visible);
                if (!pagers.length) return null;
                const pager = pagers.sort((a, b) => (b.getBoundingClientRect().width * b.getBoundingClientRect().height) - (a.getBoundingClientRect().width * a.getBoundingClientRect().height))[0];
                const active = pager.querySelector('.ant-pagination-item-active,.is-active,[aria-current="page"],li.active');
                if (!active) return null;
                const text = (active.innerText || active.textContent || '').replace(/\\s+/g, '').trim();
                const number = parseInt(text, 10);
                return Number.isFinite(number) ? number : null;
                """
            )
            if isinstance(value, (int, float)):
                return int(value)
        except WebDriverException:
            pass
        return None

    def get_last_page_number(self) -> Optional[int]:
        assert self.driver
        try:
            value = self.driver.execute_script(
                """
                const visible = (el) => {
                  if (!el) return false;
                  const rect = el.getBoundingClientRect();
                  const style = getComputedStyle(el);
                  return rect.width > 0 && rect.height > 0 && style.display !== 'none'
                    && style.visibility !== 'hidden' && Number(style.opacity || '1') !== 0;
                };
                const pagers = Array.from(document.querySelectorAll('.ant-pagination,.el-pagination,[class*="pagination"],[class*="Pagination"]'))
                  .filter(visible);
                if (!pagers.length) return null;
                const pager = pagers.sort((a, b) => (b.getBoundingClientRect().width * b.getBoundingClientRect().height) - (a.getBoundingClientRect().width * a.getBoundingClientRect().height))[0];
                const values = Array.from(pager.querySelectorAll('li,a,button,span'))
                  .filter(visible)
                  .map((el) => parseInt((el.innerText || el.textContent || '').replace(/\\s+/g, ''), 10))
                  .filter((n) => Number.isFinite(n) && n > 0 && n < 100000);
                if (!values.length) return null;
                return Math.max(...values);
                """
            )
            if isinstance(value, (int, float)):
                return int(value)
        except WebDriverException:
            pass
        return None

    def get_url_page_number(self) -> Optional[int]:
        assert self.driver
        try:
            parsed = urlparse(self.driver.current_url)
            params = dict(parse_qsl(parsed.query or "", keep_blank_values=True))
            for key in ("page", "pageNo", "pageNum", "current", "p", "search_page"):
                raw = sanitize_text(params.get(key))
                if raw and re.fullmatch(r"-?\d+", raw):
                    return int(raw)
        except Exception:
            return None
        return None

    def build_next_page_url(self) -> Optional[str]:
        assert self.driver
        current_url = self.driver.current_url
        parsed = urlparse(current_url)
        query_pairs = parse_qsl(parsed.query or "", keep_blank_values=True)
        if not query_pairs:
            return None

        updated: List[Tuple[str, str]] = []
        changed = False
        for key, value in query_pairs:
            key_lower = key.lower()
            raw = sanitize_text(value)
            if key_lower in {"page", "p", "pageno", "page_no", "pageindex", "page_index"} and re.fullmatch(r"-?\d+", raw):
                updated.append((key, str(int(raw) + 1)))
                changed = True
                continue
            if key_lower in {"search_page", "offset_page"} and re.fullmatch(r"-?\d+", raw):
                updated.append((key, str(int(raw) + 1)))
                changed = True
                continue
            updated.append((key, value))

        if not changed:
            active_page = self.get_active_page_number()
            if active_page is None:
                return None
            updated.append(("page", str(active_page + 1)))

        new_query = urlencode(updated, doseq=True)
        next_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
        if next_url == current_url:
            return None
        return next_url

    def go_next_page_by_url(self) -> bool:
        assert self.driver
        next_url = self.build_next_page_url()
        if not next_url:
            return False
        try:
            self.log(f"分页：尝试 URL 翻页 -> {next_url}")
            self.driver.get(next_url)
            self.wait_document_ready()
            return True
        except WebDriverException:
            return False

    def click_next_page_with_script(self) -> bool:
        assert self.driver
        try:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.2)
            clicked = self.driver.execute_script(
                """
                const visible = (el) => {
                  if (!el) return false;
                  const rect = el.getBoundingClientRect();
                  const style = getComputedStyle(el);
                  return rect.width > 0 && rect.height > 0 && style.display !== 'none'
                    && style.visibility !== 'hidden' && Number(style.opacity || '1') !== 0;
                };
                const disabled = (el) => {
                  if (!el) return true;
                  const cls = String(el.className || '').toLowerCase();
                  const aria = String(el.getAttribute('aria-disabled') || '').toLowerCase();
                  const dis = String(el.getAttribute('disabled') || '').toLowerCase();
                  return aria === 'true' || dis === 'true' || dis === 'disabled' || cls.includes('disabled');
                };
                const clickElement = (el) => {
                  if (!el || !visible(el) || disabled(el)) return false;
                  const target = el.tagName && el.tagName.toLowerCase() === 'li'
                    ? (el.querySelector('button,a,span') || el)
                    : el;
                  if (!visible(target) || disabled(target)) return false;
                  target.scrollIntoView({ block: 'center', inline: 'center' });
                  target.click();
                  return true;
                };
                const pagers = Array.from(document.querySelectorAll('.ant-pagination,.el-pagination,[class*="pagination"],[class*="Pagination"]'))
                  .filter(visible);
                if (!pagers.length) return false;
                const pager = pagers.sort((a, b) => (b.getBoundingClientRect().width * b.getBoundingClientRect().height) - (a.getBoundingClientRect().width * a.getBoundingClientRect().height))[0];

                const antNext = pager.querySelector('.ant-pagination-next:not(.ant-pagination-disabled)');
                if (clickElement(antNext)) return true;

                const btnNext = pager.querySelector('.btn-next:not(.is-disabled):not([disabled])');
                if (clickElement(btnNext)) return true;

                const active = pager.querySelector('.ant-pagination-item-active,.is-active,[aria-current="page"],li.active');
                if (active) {
                  const activeNum = parseInt((active.innerText || active.textContent || '').replace(/\\s+/g, ''), 10);
                  if (Number.isFinite(activeNum)) {
                    const targetNum = String(activeNum + 1);
                    const numItems = Array.from(pager.querySelectorAll('li,a,button,span'))
                      .filter(visible)
                      .find((el) => (el.innerText || el.textContent || '').replace(/\\s+/g, '').trim() === targetNum);
                    if (clickElement(numItems)) return true;
                  }
                }

                const textButtons = Array.from(pager.querySelectorAll('button,a,li,span,[role="button"]'))
                  .filter(visible)
                  .find((el) => /下一页|下一頁|next|>$/.test((el.innerText || el.textContent || '').trim().toLowerCase()));
                if (clickElement(textButtons)) return true;
                return false;
                """
            )
            return bool(clicked)
        except WebDriverException:
            return False

    def page_has_advanced(
        self,
        previous_first: str,
        previous_page: Optional[int],
        previous_url: str,
        previous_url_page: Optional[int],
    ) -> bool:
        current_page = self.get_active_page_number()
        if previous_page and current_page and current_page != previous_page:
            return True
        current_url_page = self.get_url_page_number()
        if previous_url_page is not None and current_url_page is not None and current_url_page != previous_url_page:
            return True
        try:
            if previous_url and self.driver and self.driver.current_url != previous_url:
                before_path = urlparse(previous_url).path
                after_path = urlparse(self.driver.current_url).path
                if before_path == after_path:
                    return True
        except Exception:
            pass
        rows = self.get_result_rows()
        if rows:
            current_first = sanitize_text(rows[0].text)
            if previous_first and current_first and current_first != previous_first:
                return True
        return False

    def wait_page_advanced(
        self,
        previous_first: str,
        previous_page: Optional[int],
        previous_url: str,
        previous_url_page: Optional[int],
        timeout: float,
    ) -> bool:
        assert self.driver
        deadline = time.time() + max(timeout, 1.0)
        while time.time() < deadline:
            if self.page_has_advanced(previous_first, previous_page, previous_url, previous_url_page):
                return True
            time.sleep(0.3)
        return self.page_has_advanced(previous_first, previous_page, previous_url, previous_url_page)

    def click_next_page_with_locator(self) -> bool:
        assert self.driver
        next_button = self.find_first("next_page", timeout=4)
        if not next_button:
            return False
        try:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.2)
            aria_disabled = sanitize_text(next_button.get_attribute("aria-disabled")).lower()
            disabled_attr = sanitize_text(next_button.get_attribute("disabled")).lower()
            class_name = sanitize_text(next_button.get_attribute("class")).lower()
            is_disabled = (
                aria_disabled in {"true", "1"}
                or disabled_attr in {"true", "1", "disabled"}
                or "disabled" in class_name
            )
            if is_disabled:
                return False
            self.safe_click(next_button)
            return True
        except Exception:
            return False

    def go_next_page(self) -> bool:
        rows = self.get_result_rows()
        current_first = sanitize_text(rows[0].text) if rows else ""
        current_page = self.get_active_page_number()
        current_url_page = self.get_url_page_number()
        current_url = self.driver.current_url if self.driver else ""
        last_page = self.get_last_page_number()
        if current_page and last_page and current_page >= last_page:
            self.log(f"分页：当前已是最后一页（{current_page}/{last_page}）。")
            return False

        attempts: List[Tuple[str, Callable[[], bool]]] = [
            ("脚本点击", self.click_next_page_with_script),
            ("选择器点击", self.click_next_page_with_locator),
            ("URL 翻页", self.go_next_page_by_url),
            ("脚本点击重试", self.click_next_page_with_script),
        ]
        for name, clicker in attempts:
            self.check_stop()
            clicked = False
            try:
                clicked = bool(clicker())
            except Exception:
                clicked = False
            if not clicked:
                self.log(f"分页：{name} 未命中可点击下一页。")
                continue

            if self.wait_page_advanced(
                current_first,
                current_page,
                current_url,
                current_url_page,
                timeout=min(max(float(self.config.page_timeout), 6.0), 15.0),
            ):
                self.log(f"分页：已进入下一页（{name}）。")
                return True
            self.log(f"分页：{name} 已点击，但未检测到页码变化，继续重试。")

        self.log("分页：点击后未检测到页码变化，判定没有下一页或翻页失败。")
        return False

    def find_first(self, selector_key: str, timeout: int = 10) -> Optional[WebElement]:
        assert self.driver
        deadline = time.time() + timeout
        while time.time() < deadline:
            for by, selector in OKKI_SELECTORS.get(selector_key, []):
                try:
                    for element in self.driver.find_elements(by, selector):
                        if element.is_displayed():
                            return element
                except WebDriverException:
                    continue
            time.sleep(0.2)
        return None

    def fill_field(self, selector_key: str, value: str) -> bool:
        element = self.find_first(selector_key, timeout=8)
        if not element:
            return False
        self.clear_and_type(element, value)
        return True

    def click_country_hotspot(self, country: str) -> bool:
        assert self.driver
        candidates = expand_country_names(country)
        for candidate in candidates:
            try:
                clicked = self.driver.execute_script(
                    """
                    const target = (arguments[0] || '').trim().toLowerCase();
                    if (!target) return false;
                    const visible = (el) => {
                      if (!el) return false;
                      const rect = el.getBoundingClientRect();
                      const style = getComputedStyle(el);
                      return rect.width > 0 && rect.height > 0 && style.display !== 'none'
                        && style.visibility !== 'hidden' && Number(style.opacity || '1') !== 0;
                    };
                    const normalize = (v) => (v || '').replace(/\\s+/g, ' ').trim();
                    const inCountryZone = (el) => {
                      const zone = el.closest('section,div,ul,article,[class*=\"country\"],[class*=\"region\"],[class*=\"area\"]');
                      if (!zone) return false;
                      const text = normalize(zone.innerText || zone.textContent || '').toLowerCase();
                      return /国家|地区|country|region|熱門|热门/.test(text);
                    };
                    const nodes = Array.from(document.querySelectorAll('a,button,div,span,li,p'))
                      .filter(visible)
                      .map((el) => {
                        const text = normalize(el.innerText || el.textContent || '');
                        if (!text || text.length > 24) return null;
                        const lower = text.toLowerCase();
                        if (!(lower === target || lower.includes(target))) return null;
                        const rect = el.getBoundingClientRect();
                        let score = 0;
                        if (lower === target) score += 10;
                        if (lower.includes(target)) score += 4;
                        if (inCountryZone(el)) score += 8;
                        const cls = String(el.className || '').toLowerCase();
                        if (/country|region|area|hot|tab/.test(cls)) score += 2;
                        if (rect.top >= 120 && rect.top <= window.innerHeight + 520) score += 2;
                        if (text.length <= 8) score += 1;
                        return { el, score };
                      })
                      .filter(Boolean)
                      .sort((a, b) => b.score - a.score);
                    if (!nodes.length) return false;
                    const node = nodes[0].el;
                    const targetEl = node.closest('a,button,[role=\"button\"],li,div,span') || node;
                    targetEl.scrollIntoView({ block: 'center', inline: 'center' });
                    targetEl.click();
                    return true;
                    """,
                    candidate,
                )
                if clicked:
                    return True
            except WebDriverException:
                continue
        return False

    def select_country(self, country: str) -> bool:
        candidates = expand_country_names(country)
        if self.select_buyer_country_like_user(country, candidates):
            self.log(f"已选择采购商国家/地区：{country}")
            return True

        buyer_filter = self.find_buyer_country_filter()
        if buyer_filter:
            self.safe_click(buyer_filter)
            try:
                buyer_filter.send_keys(Keys.CONTROL, "a")
                buyer_filter.send_keys(Keys.BACKSPACE)
                buyer_filter.send_keys(country)
            except WebDriverException:
                try:
                    self.driver.execute_script(
                        """
                        const el = arguments[0];
                        const value = arguments[1];
                        el.focus();
                        el.value = value;
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                        """,
                        buyer_filter,
                        country,
                    )
                except WebDriverException:
                    pass
            time.sleep(1)
            for candidate in candidates:
                if self.click_country_dropdown_option(candidate, timeout=5):
                    self.log(f"已从采购商国家/地区列表点击：{candidate}")
                    return True
            if self.country_filter_has_selection(candidates):
                self.log(f"检测到采购商国家/地区已选中：{country}")
                return True
            self.log(f"采购商国家/地区输入框已输入 {country}，但没有匹配到可点击的下拉选项。")
            return False

        dropdown = self.find_first("buyer_country_dropdown", timeout=5)
        if dropdown:
            self.safe_click(dropdown)
            time.sleep(1)
            for candidate in candidates:
                if self.click_country_dropdown_option(candidate, timeout=5):
                    self.log(f"已从采购商国家/地区列表点击：{candidate}")
                    return True
            if self.country_filter_has_selection(candidates):
                self.log(f"检测到采购商国家/地区已选中：{country}")
                return True
            return False

        return False

    def select_buyer_country_like_user(self, country: str, candidates: Sequence[str]) -> bool:
        assert self.driver
        if self.country_filter_has_selection(candidates):
            return True
        for candidate in candidates:
            try:
                opened = bool(
                    self.driver.execute_script(
                        """
                        const value = String(arguments[0] || '').trim();
                        const visible = (el) => {
                          if (!el) return false;
                          const rect = el.getBoundingClientRect();
                          const style = getComputedStyle(el);
                          return rect.width > 0 && rect.height > 0 && style.display !== 'none'
                            && style.visibility !== 'hidden' && Number(style.opacity || '1') !== 0;
                        };
                        const textOf = (el) => String(el?.innerText || el?.textContent || '').replace(/\\s+/g, ' ').trim();
                        const labels = Array.from(document.querySelectorAll('label,div,span,p'))
                          .filter(visible)
                          .filter((el) => {
                            const text = textOf(el);
                            return text.length <= 30 && /采购商\\s*国家\\s*\\/\\s*地区|采购商国家|採購商\\s*國家\\s*\\/\\s*地區|採購商國家/.test(text);
                          });
                        const roots = [];
                        for (const label of labels) {
                          const labelRect = label.getBoundingClientRect();
                          const nodes = Array.from(document.querySelectorAll('.ant-select,.ant-select-selector,.el-select,.el-input,[role="combobox"],input'))
                            .filter(visible)
                            .map((el) => ({ el, rect: el.getBoundingClientRect() }))
                            .filter((item) => {
                              const below = item.rect.top >= labelRect.bottom - 12 && item.rect.top <= labelRect.bottom + 80;
                              const sameColumn = item.rect.left >= labelRect.left - 16 && item.rect.left <= labelRect.left + 560;
                              const notHeaderSearch = item.rect.top > 220;
                              return below && sameColumn && notHeaderSearch;
                            })
                            .sort((a, b) => {
                              const ad = Math.abs(a.rect.left - labelRect.left) + Math.abs(a.rect.top - labelRect.bottom);
                              const bd = Math.abs(b.rect.left - labelRect.left) + Math.abs(b.rect.top - labelRect.bottom);
                              return ad - bd;
                            });
                          if (nodes.length) roots.push(nodes[0].el);
                        }
                        const root = roots[0];
                        if (!root) return false;
                        const selectRoot = root.closest('.ant-select,.el-select,[role="combobox"]') || root;
                        const selector = selectRoot.querySelector('.ant-select-selector,.el-input__inner,input') || root;
                        selector.scrollIntoView({ block: 'center', inline: 'center' });
                        selector.click();
                        const input = selectRoot.querySelector('input') || (selector.matches?.('input') ? selector : null) || document.activeElement;
                        if (input && 'value' in input) {
                          const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;
                          input.focus();
                          if (setter) setter.call(input, value);
                          else input.value = value;
                          input.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: value }));
                          input.dispatchEvent(new Event('change', { bubbles: true }));
                          input.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, key: value.slice(-1) || 'a' }));
                          input.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true, key: value.slice(-1) || 'a' }));
                        }
                        return true;
                        """,
                        candidate,
                    )
                )
                if not opened:
                    continue
                time.sleep(1.2)
                if self.click_country_dropdown_option(candidate, timeout=4):
                    time.sleep(0.5)
                    if self.country_filter_has_selection(candidates):
                        return True
                    return True
                try:
                    ActionChains(self.driver).send_keys(Keys.ENTER).perform()
                    time.sleep(0.6)
                    if self.country_filter_has_selection(candidates):
                        return True
                except WebDriverException:
                    pass
            except WebDriverException:
                continue
        return False

    def country_filter_has_selection(self, candidates: Sequence[str]) -> bool:
        assert self.driver
        try:
            return bool(
                self.driver.execute_script(
                    """
                    const aliases = Array.from(arguments[0] || []).map(v => String(v || '').replace(/\\s+/g, '').trim().toLowerCase()).filter(Boolean);
                    const visible = (el) => {
                      if (!el) return false;
                      const rect = el.getBoundingClientRect();
                      const style = getComputedStyle(el);
                      return rect.width > 0 && rect.height > 0 && style.display !== 'none'
                        && style.visibility !== 'hidden' && Number(style.opacity || '1') !== 0;
                    };
                    const matches = (text) => {
                      const token = String(text || '').replace(/\\s+/g, '').trim().toLowerCase();
                      return token && aliases.some(alias => token.includes(alias) || alias.includes(token));
                    };
                    const labels = Array.from(document.querySelectorAll('label,div,span,p'))
                      .filter(visible)
                      .filter((el) => {
                        const text = String(el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim();
                        return text.length <= 30 && /采购商\\s*国家\\s*\\/\\s*地区|采购商国家|採購商\\s*國家\\s*\\/\\s*地區|採購商國家/.test(text);
                      });
                    for (const label of labels) {
                      const labelRect = label.getBoundingClientRect();
                      const nodes = Array.from(document.querySelectorAll('.ant-select,.ant-select-selector,.el-select,.el-input,[role="combobox"],input'))
                        .filter(visible)
                        .map((el) => ({ el, rect: el.getBoundingClientRect() }))
                        .filter((item) => {
                          const below = item.rect.top >= labelRect.bottom - 12 && item.rect.top <= labelRect.bottom + 80;
                          const sameColumn = item.rect.left >= labelRect.left - 16 && item.rect.left <= labelRect.left + 560;
                          return below && sameColumn && item.rect.top > 220;
                        });
                      for (const item of nodes) {
                        const root = item.el.closest('.ant-select,.el-select,[role="combobox"],.el-input,div') || item.el;
                        const text = `${root.innerText || root.textContent || ''} ${item.el.value || ''}`;
                        if (matches(text)) return true;
                      }
                    }
                    return false;
                    """,
                    list(candidates),
                )
            )
        except WebDriverException:
            return False

    def find_buyer_country_filter(self) -> Optional[WebElement]:
        assert self.driver
        try:
            element = self.driver.execute_script(
                """
                const visible = (el) => {
                  if (!el) return false;
                  const rect = el.getBoundingClientRect();
                  const style = getComputedStyle(el);
                  return rect.width > 0 && rect.height > 0 && style.display !== 'none'
                    && style.visibility !== 'hidden' && Number(style.opacity || '1') !== 0;
                };
                const textOf = (el) => (el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim();
                const labels = Array.from(document.querySelectorAll('label,div,span,p'))
                  .filter(visible)
                  .filter((el) => {
                    const text = textOf(el);
                    return text.length <= 24 && /采购商\\s*国家\\s*\\/\\s*地区|采购商国家/.test(text);
                  });
                for (const label of labels) {
                  const labelRect = label.getBoundingClientRect();
                  const candidates = Array.from(document.querySelectorAll('input,[role="combobox"],.ant-select-selector,.el-select,.el-input,.ant-select'))
                    .filter(visible)
                    .map((el) => ({ el, rect: el.getBoundingClientRect() }))
                    .filter((item) => {
                      const nearBelow = item.rect.top >= labelRect.bottom - 4 && item.rect.top <= labelRect.bottom + 52;
                      const nearSameColumn = item.rect.left >= labelRect.left - 8 && item.rect.left <= labelRect.left + 460;
                      const notTopSearch = item.rect.top > 280;
                      return nearBelow && nearSameColumn && notTopSearch;
                    })
                    .sort((a, b) => {
                      const ad = Math.abs(a.rect.left - labelRect.left) + Math.abs(a.rect.top - labelRect.bottom);
                      const bd = Math.abs(b.rect.left - labelRect.left) + Math.abs(b.rect.top - labelRect.bottom);
                      return ad - bd;
                    });
                  if (candidates.length) {
                    const input = candidates[0].el.querySelector?.('input') || candidates[0].el;
                    return input;
                  }
                }
                return null;
                """
            )
            if element:
                return element
        except WebDriverException:
            pass
        return self.find_first("buyer_country_input", timeout=3)

    def click_country_dropdown_option(self, text: str, timeout: int = 5) -> bool:
        assert self.driver
        escaped = self.xpath_literal(text)
        escaped_lower = self.xpath_literal(text.lower())
        xpaths = [
            f"//*[@role='option' and normalize-space(.)={escaped}]",
            f"//*[@role='option' and contains(normalize-space(.), {escaped})]",
            f"//*[self::li or contains(@class,'select-item') or contains(@class,'option')][normalize-space(.)={escaped}]",
            f"//*[self::li or contains(@class,'select-item') or contains(@class,'option')][contains(normalize-space(.), {escaped})]",
            f"//*[@role='option' and translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')={escaped_lower}]",
            f"//*[self::li or contains(@class,'select-item') or contains(@class,'option')][contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), {escaped_lower})]",
        ]
        deadline = time.time() + timeout
        while time.time() < deadline:
            for xpath in xpaths:
                try:
                    for element in self.driver.find_elements(By.XPATH, xpath):
                        if element.is_displayed():
                            self.safe_click(element)
                            return True
                except WebDriverException:
                    continue
            time.sleep(0.2)
        return False

    def select_country_anywhere(self, country: str) -> bool:
        candidates = expand_country_names(country)
        for candidate in candidates:
            if self.click_option_text(candidate, timeout=2):
                self.log(f"已从国家/地区列表点击：{candidate}")
                return True

        if self.fill_field("country_input", country):
            try:
                ActionChains(self.driver).send_keys(Keys.ENTER).perform()
                time.sleep(1)
            except WebDriverException:
                pass
            for candidate in candidates:
                if self.click_option_text(candidate, timeout=3):
                    return True
            return True
        dropdown = self.find_first("country_dropdown", timeout=5)
        if dropdown:
            self.safe_click(dropdown)
            time.sleep(1)
            for candidate in candidates:
                if self.click_option_text(candidate, timeout=5):
                    return True
        return False

    def click_option_text(self, text: str, timeout: int = 5) -> bool:
        assert self.driver
        escaped = self.xpath_literal(text)
        escaped_lower = self.xpath_literal(text.lower())
        xpaths = [
            f"//*[self::li or self::div or self::span or @role='option'][normalize-space(.)={escaped}]",
            f"//*[self::li or self::div or self::span or @role='option'][contains(normalize-space(.), {escaped})]",
            f"//*[self::li or self::div or self::span or @role='option'][translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')={escaped_lower}]",
            f"//*[self::li or self::div or self::span or @role='option'][contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), {escaped_lower})]",
        ]
        deadline = time.time() + timeout
        while time.time() < deadline:
            for xpath in xpaths:
                try:
                    for element in self.driver.find_elements(By.XPATH, xpath):
                        if element.is_displayed():
                            self.safe_click(element)
                            return True
                except WebDriverException:
                    continue
            time.sleep(0.2)
        return False

    def click_text(self, text: str, timeout: int = 8) -> None:
        assert self.driver
        escaped = self.xpath_literal(text)
        escaped_lower = self.xpath_literal(text.lower())
        xpaths = [
            f"//*[self::button or self::a or @role='button' or @role='menuitem'][contains(normalize-space(.), {escaped})]",
            f"//*[self::button or self::a or @role='button' or @role='menuitem'][contains(normalize-space(@title), {escaped}) or contains(normalize-space(@aria-label), {escaped})]",
            f"//*[contains(normalize-space(.), {escaped})]",
            f"//*[contains(normalize-space(@title), {escaped}) or contains(normalize-space(@aria-label), {escaped})]",
            f"//*[self::button or self::a or @role='button' or @role='menuitem'][contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), {escaped_lower})]",
            f"//*[self::button or self::a or @role='button' or @role='menuitem'][contains(translate(normalize-space(@title), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), {escaped_lower}) or contains(translate(normalize-space(@aria-label), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), {escaped_lower})]",
            f"//*[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), {escaped_lower})]",
            f"//*[contains(translate(normalize-space(@title), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), {escaped_lower}) or contains(translate(normalize-space(@aria-label), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), {escaped_lower})]",
        ]
        deadline = time.time() + timeout
        while time.time() < deadline:
            for xpath in xpaths:
                try:
                    for element in self.driver.find_elements(By.XPATH, xpath):
                        if element.is_displayed():
                            self.safe_click(element)
                            return
                except WebDriverException:
                    continue
            time.sleep(0.2)
        raise NoSuchElementException(f"未找到文本：{text}")

    @staticmethod
    def xpath_literal(value: str) -> str:
        if "'" not in value:
            return f"'{value}'"
        if '"' not in value:
            return f'"{value}"'
        parts = value.split("'")
        return "concat(" + ', "\"\'\"", '.join([f"'{part}'" for part in parts]) + ")"

    def clear_and_type(self, element: WebElement, value: str) -> None:
        assert self.driver
        self.safe_click(element)
        try:
            element.send_keys(Keys.CONTROL, "a")
            element.send_keys(Keys.BACKSPACE)
            element.send_keys(value)
        except WebDriverException:
            self.driver.execute_script(
                """
                const el = arguments[0];
                const value = arguments[1];
                el.focus();
                el.value = value;
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
                """,
                element,
                value,
            )

    def safe_click(self, element: WebElement) -> None:
        assert self.driver
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", element)
            time.sleep(0.2)
            element.click()
        except (ElementClickInterceptedException, WebDriverException):
            self.driver.execute_script("arguments[0].click();", element)

    def safe_body_text(self) -> str:
        assert self.driver
        try:
            return self.driver.find_element(By.TAG_NAME, "body").text
        except WebDriverException:
            return ""


class TkLogBridge:
    def __init__(self, log_queue: "queue.Queue[str]") -> None:
        self.log_queue = log_queue

    def __call__(self, message: str) -> None:
        print(message)
        self.log_queue.put(message)


class OkkiAutomationGUI:
    def __init__(self) -> None:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk

        self.tk = tk
        self.ttk = ttk
        self.filedialog = filedialog
        self.messagebox = messagebox

        self.root = tk.Tk()
        self.root.title("OKKI 智能贸易数据自动化获客")
        self.root.geometry("980x760")
        self.root.minsize(880, 680)

        self.log_queue: "queue.Queue[str]" = queue.Queue()
        self.stop_event = threading.Event()
        self.worker: Optional[threading.Thread] = None
        self.vars: Dict[str, object] = {}
        self.latest_results: List[Dict[str, str]] = []
        self.latest_business_tables: List[Dict[str, str]] = []
        self.latest_config: Optional[AppConfig] = None
        self._log_line_count = 0
        self._max_log_lines = 1500
        self._max_logs_per_flush = 160
        self._preview_max_rows = 500
        self.run_popup = None
        self.run_popup_status_var = None

        self.build_ui()
        self.bring_main_window_front()
        self.root.after(200, self.flush_logs)

    def build_ui(self) -> None:
        tk = self.tk
        ttk = self.ttk
        outer = ttk.Frame(self.root, padding=14)
        outer.pack(fill=tk.BOTH, expand=True)

        ttk.Label(outer, text="OKKI 智能贸易数据自动化获客", font=("Microsoft YaHei", 16, "bold")).pack(anchor=tk.W)
        ttk.Label(outer, text="先填写产品名称 / HS 编码；国家留空=按预置国家自动轮询。默认手动导出，且不影响你当前打开的浏览器。").pack(anchor=tk.W, pady=(4, 12))

        form = ttk.Frame(outer)
        form.pack(fill=tk.X)
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        self.add_entry(form, 0, 0, "最低金额阈值", "min_amount_threshold", str(MIN_AMOUNT_THRESHOLD))
        self.add_entry(form, 0, 2, "浏览器", "browser", BROWSER)
        self.add_check(form, 0, 4, "无头模式", "headless", HEADLESS)
        self.add_check(form, 1, 0, "连接调试Chrome", "use_existing_chrome", USE_EXISTING_CHROME)
        ttk.Label(form, text="导出方式：手动导出").grid(row=1, column=4, sticky=tk.W, padx=(0, 12), pady=5)
        self.add_entry(form, 1, 2, "Chrome调试端口", "chrome_debugger_address", CHROME_DEBUGGER_ADDRESS)
        self.add_entry(form, 2, 0, "OKKI专用资料目录", "chrome_user_data_dir", CHROME_USER_DATA_DIR)
        self.add_entry(form, 3, 0, "OKKI 首页", "okki_base_url", OKKI_BASE_URL)
        self.add_entry(form, 4, 0, "智能贸易数据 URL", "okki_smart_trade_url", OKKI_SMART_TRADE_URL)
        self.add_entry(form, 5, 0, "OKKI 账号", "okki_username", OKKI_USERNAME)
        self.add_entry(form, 5, 2, "OKKI 密码", "okki_password", OKKI_PASSWORD, show="*")
        self.add_text(form, 6, 0, "Cookie", "cookie_string", COOKIE_STRING, height=3)
        self.add_entry(form, 7, 0, "产品名称", "product_name", SEARCH_PRODUCT_NAME)
        self.add_entry(form, 7, 2, "HS 编码", "hs_code", SEARCH_HS_CODE)
        self.add_entry(form, 8, 0, "国家/地区", "country", SEARCH_COUNTRY)
        self.add_entry(form, 8, 2, "最大翻页数(0=全部)", "max_pages", str(MAX_PAGES))
        self.add_entry(form, 9, 0, "yunwu Endpoint", "yunwu_endpoint", YUNWU_ENDPOINT)
        self.add_entry(form, 10, 0, "yunwu API Key（已内置）", "yunwu_api_key", YUNWU_API_KEY, show="*", readonly=True)
        self.add_entry(form, 10, 2, "模型", "yunwu_model", YUNWU_MODEL)
        self.add_file_entry(form, 11, 0, "导出目录", "output_excel_path", OUTPUT_EXCEL_PATH, [("All files", "*.*")], select_dir=True)

        actions = ttk.Frame(outer)
        actions.pack(fill=tk.X, pady=12)
        self.start_button = ttk.Button(actions, text="开始采集", command=self.start)
        self.start_button.pack(side=tk.LEFT)
        self.stop_button = ttk.Button(actions, text="停止", command=self.stop, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=8)
        self.export_button = ttk.Button(actions, text="手动导出表格", command=self.manual_export, state=tk.DISABLED)
        self.export_button.pack(side=tk.LEFT, padx=8)
        self.status_var = tk.StringVar(value="待命")
        ttk.Label(actions, textvariable=self.status_var).pack(side=tk.LEFT, padx=16)

        preview_frame = ttk.LabelFrame(outer, text="实时采集结果（最新在下方）")
        preview_frame.pack(fill=tk.BOTH, pady=(0, 8))
        self.preview_table = ttk.Treeview(preview_frame, columns=RESULT_COLUMNS, show="headings", height=8)
        for column in RESULT_COLUMNS:
            self.preview_table.heading(column, text=column)
        column_widths = {
            "公司名称": 180,
            "联系电话": 120,
            "邮箱": 180,
            "官网地址": 220,
            "所在国家": 90,
            "贸易记录金额": 110,
            "搜索关键词": 100,
            "业务介绍": 300,
            "社媒链接": 180,
        }
        for column in RESULT_COLUMNS:
            self.preview_table.column(column, width=column_widths.get(column, 120), anchor=tk.W)
        preview_y_scroll = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.preview_table.yview)
        preview_x_scroll = ttk.Scrollbar(preview_frame, orient=tk.HORIZONTAL, command=self.preview_table.xview)
        self.preview_table.configure(yscrollcommand=preview_y_scroll.set, xscrollcommand=preview_x_scroll.set)
        self.preview_table.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        preview_y_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        preview_x_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        log_frame = ttk.LabelFrame(outer, text="运行日志")
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.log_text = tk.Text(log_frame, wrap=tk.WORD, height=20)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def bring_main_window_front(self) -> None:
        try:
            self.root.update_idletasks()
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
            self.root.attributes("-topmost", True)
            self.root.after(800, lambda: self.root.attributes("-topmost", False))
        except Exception:
            pass

    def show_run_popup(self) -> None:
        tk = self.tk
        ttk = self.ttk
        self.bring_main_window_front()
        if self.run_popup and self.run_popup.winfo_exists():
            try:
                self.run_popup.deiconify()
                self.run_popup.lift()
                self.run_popup.focus_force()
            except Exception:
                pass
            return
        popup = tk.Toplevel(self.root)
        popup.title("运行中")
        popup.geometry("360x150")
        popup.resizable(False, False)
        popup.transient(self.root)
        try:
            popup.attributes("-topmost", True)
        except Exception:
            pass
        frame = ttk.Frame(popup, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="任务正在运行中，请勿关闭浏览器。").pack(anchor=tk.W)
        self.run_popup_status_var = tk.StringVar(value="状态：运行中")
        ttk.Label(frame, textvariable=self.run_popup_status_var).pack(anchor=tk.W, pady=(8, 10))
        ttk.Button(frame, text="显示主窗口", command=self.bring_main_window_front).pack(anchor=tk.W)
        self.run_popup = popup

    def close_run_popup(self) -> None:
        if self.run_popup and self.run_popup.winfo_exists():
            try:
                self.run_popup.destroy()
            except Exception:
                pass
        self.run_popup = None
        self.run_popup_status_var = None

    def add_entry(
        self,
        parent,
        row: int,
        col: int,
        label: str,
        key: str,
        default: str,
        show: Optional[str] = None,
        readonly: bool = False,
    ) -> None:
        tk = self.tk
        ttk = self.ttk
        var = tk.StringVar(value=default)
        self.vars[key] = var
        ttk.Label(parent, text=label).grid(row=row, column=col, sticky=tk.W, padx=(0, 8), pady=5)
        entry = ttk.Entry(parent, textvariable=var, show=show)
        if readonly:
            entry.configure(state="readonly")
        entry.grid(row=row, column=col + 1, sticky=tk.EW, padx=(0, 12), pady=5)

    def add_check(self, parent, row: int, col: int, label: str, key: str, default: bool) -> None:
        tk = self.tk
        ttk = self.ttk
        var = tk.BooleanVar(value=default)
        self.vars[key] = var
        ttk.Checkbutton(parent, text=label, variable=var).grid(row=row, column=col, sticky=tk.W, padx=(0, 12), pady=5)

    def add_text(self, parent, row: int, col: int, label: str, key: str, default: str, height: int = 3) -> None:
        tk = self.tk
        ttk = self.ttk
        var = tk.StringVar(value=default)
        self.vars[key] = var
        ttk.Label(parent, text=label).grid(row=row, column=col, sticky=tk.NW, padx=(0, 8), pady=5)
        text = tk.Text(parent, height=height, wrap=tk.WORD)
        text.insert("1.0", default)
        text.grid(row=row, column=col + 1, columnspan=3, sticky=tk.EW, padx=(0, 12), pady=5)

        def sync_var(_event=None) -> None:
            var.set(text.get("1.0", tk.END).strip())

        text.bind("<KeyRelease>", sync_var)
        text.bind("<FocusOut>", sync_var)

    def add_file_entry(self, parent, row: int, col: int, label: str, key: str, default: str, filetypes, select_dir: bool = False) -> None:
        tk = self.tk
        ttk = self.ttk
        var = tk.StringVar(value=default)
        self.vars[key] = var
        ttk.Label(parent, text=label).grid(row=row, column=col, sticky=tk.W, padx=(0, 8), pady=5)
        ttk.Entry(parent, textvariable=var).grid(row=row, column=col + 1, columnspan=2, sticky=tk.EW, padx=(0, 8), pady=5)
        ttk.Button(parent, text="选择", command=lambda: self.choose_file(var, filetypes, select_dir=select_dir)).grid(row=row, column=col + 3, sticky=tk.W, padx=(0, 12), pady=5)

    def choose_file(self, var, filetypes, select_dir: bool = False) -> None:
        if select_dir:
            path = self.filedialog.askdirectory()
        else:
            path = self.filedialog.asksaveasfilename(filetypes=filetypes)
        if path:
            var.set(path)

    def build_config(self) -> AppConfig:
        def get_str(key: str) -> str:
            var = self.vars.get(key)
            if var is None:
                return ""
            return str(var.get()).strip()

        try:
            threshold = float(get_str("min_amount_threshold") or "0")
        except ValueError as exc:
            raise ValueError("最低金额阈值必须是数字。") from exc
        try:
            page_limit = int(float(get_str("max_pages") or str(MAX_PAGES)))
            if page_limit < 0:
                raise ValueError("最大翻页数不能小于 0。")
        except ValueError as exc:
            raise ValueError("最大翻页数必须是数字，0 表示翻完全部分页。") from exc

        return AppConfig(
            min_amount_threshold=threshold,
            okki_base_url=get_str("okki_base_url") or OKKI_BASE_URL,
            okki_smart_trade_url=get_str("okki_smart_trade_url") or OKKI_SMART_TRADE_URL,
            okki_username=get_str("okki_username"),
            okki_password=get_str("okki_password"),
            cookie_string=get_str("cookie_string"),
            product_name=get_str("product_name"),
            hs_code=get_str("hs_code"),
            country=get_str("country"),
            output_excel_path=get_str("output_excel_path") or OUTPUT_EXCEL_PATH,
            output_html_path=get_str("output_excel_path") or OUTPUT_HTML_PATH,
            yunwu_endpoint=get_str("yunwu_endpoint") or YUNWU_ENDPOINT,
            yunwu_api_key=YUNWU_API_KEY,
            yunwu_model=get_str("yunwu_model") or YUNWU_MODEL,
            browser=get_str("browser") or BROWSER,
            headless=bool(self.vars["headless"].get()),
            use_existing_chrome=bool(self.vars["use_existing_chrome"].get()),
            auto_export=False,
            chrome_debugger_address=get_str("chrome_debugger_address") or CHROME_DEBUGGER_ADDRESS,
            chrome_user_data_dir=get_str("chrome_user_data_dir") or CHROME_USER_DATA_DIR,
            max_pages=page_limit,
        )

    def start(self) -> None:
        if self.worker and self.worker.is_alive():
            return
        try:
            config = self.build_config()
            if not config.product_name and not config.hs_code:
                self.messagebox.showwarning("缺少搜索条件", "产品名称和 HS 编码至少填写一个。")
                return
        except Exception as exc:
            self.messagebox.showerror("配置错误", str(exc))
            return

        self.stop_event.clear()
        self.latest_results = []
        self.latest_business_tables = []
        self.latest_config = None
        self.start_button.configure(state=self.tk.DISABLED)
        self.stop_button.configure(state=self.tk.NORMAL)
        self.export_button.configure(state=self.tk.DISABLED)
        self.status_var.set("运行中")
        self.log_text.delete("1.0", self.tk.END)
        self._log_line_count = 0
        for item in self.preview_table.get_children():
            self.preview_table.delete(item)

        def worker() -> None:
            automation: Optional[OkkiTradeAutomation] = None
            try:
                def on_result_row(row: Dict[str, str]) -> None:
                    self.log_queue.put("__RESULT__" + json.dumps(row, ensure_ascii=False))

                automation = OkkiTradeAutomation(
                    config,
                    logger=TkLogBridge(self.log_queue),
                    stop_event=self.stop_event,
                    on_result=on_result_row,
                )
                automation.run()
                self.latest_results = list(automation.results)
                self.latest_business_tables = list(automation.business_tables)
                self.latest_config = config
                if self.latest_results:
                    self.log_queue.put("__CAN_EXPORT__1")
                else:
                    self.log_queue.put("__CAN_EXPORT__0")
                self.log_queue.put("__STATUS__任务完成")
            except Exception as exc:
                if automation and automation.results:
                    self.latest_results = list(automation.results)
                    self.latest_business_tables = list(automation.business_tables)
                    self.latest_config = config
                    self.log_queue.put("__CAN_EXPORT__1")
                    if isinstance(exc, RuntimeError) and "用户已停止任务" in str(exc):
                        self.log_queue.put("__STATUS__任务已停止（可导出已采集数据）")
                    else:
                        self.log_queue.put("__STATUS__任务失败（可导出已采集数据）")
                else:
                    self.log_queue.put("__CAN_EXPORT__0")
                    self.log_queue.put("__STATUS__任务失败")
                self.log_queue.put(f"[{now_text()}] 任务失败：{type(exc).__name__}: {str(exc)}")
            finally:
                self.log_queue.put("__DONE__")

        self.worker = threading.Thread(target=worker, daemon=True)
        self.worker.start()
        self.show_run_popup()

    def stop(self) -> None:
        self.stop_event.set()
        self.status_var.set("正在停止")
        self.log_queue.put(f"[{now_text()}] 已请求停止，当前步骤结束后退出。")
        if self.run_popup_status_var is not None:
            try:
                self.run_popup_status_var.set("状态：正在停止")
            except Exception:
                pass

    def manual_export(self) -> None:
        if not self.latest_results:
            self.messagebox.showwarning("无可导出数据", "当前没有可导出的采集结果，请先运行采集任务。")
            return
        try:
            config = self.build_config()
        except Exception as exc:
            self.messagebox.showerror("导出配置错误", str(exc))
            return
        try:
            exporter = OkkiTradeAutomation(config, logger=TkLogBridge(self.log_queue))
            exporter.results = list(self.latest_results)
            exporter.business_tables = list(self.latest_business_tables)
            exporter.export_results()
            self.status_var.set("导出完成")
        except Exception as exc:
            self.messagebox.showerror("导出失败", f"{type(exc).__name__}: {str(exc)}")

    def flush_logs(self) -> None:
        processed = 0
        normal_lines: List[str] = []
        while processed < self._max_logs_per_flush:
            try:
                message = self.log_queue.get_nowait()
            except queue.Empty:
                break
            processed += 1
            if message == "__DONE__":
                self.start_button.configure(state=self.tk.NORMAL)
                self.stop_button.configure(state=self.tk.DISABLED)
                self.close_run_popup()
                continue
            if message.startswith("__CAN_EXPORT__"):
                enable = message.endswith("1")
                self.export_button.configure(state=self.tk.NORMAL if enable else self.tk.DISABLED)
                continue
            if message.startswith("__STATUS__"):
                self.status_var.set(message.replace("__STATUS__", "", 1))
                continue
            if message.startswith("__RESULT__"):
                payload = message.replace("__RESULT__", "", 1)
                try:
                    row = json.loads(payload)
                    if isinstance(row, dict):
                        self.append_preview_row(row)
                except Exception:
                    pass
                continue
            normal_lines.append(message)

        if normal_lines:
            chunk = "\n".join(normal_lines) + "\n"
            self.log_text.insert(self.tk.END, chunk)
            self._log_line_count += len(normal_lines)
            if self._log_line_count > self._max_log_lines:
                overflow = self._log_line_count - self._max_log_lines
                if overflow > 0:
                    self.log_text.delete("1.0", f"{overflow + 1}.0")
                    self._log_line_count -= overflow
            self.log_text.see(self.tk.END)
        self.root.after(200, self.flush_logs)

    def append_preview_row(self, row: Dict[str, str]) -> None:
        values = [sanitize_text(row.get(column, "")) for column in RESULT_COLUMNS]
        self.preview_table.insert("", self.tk.END, values=values)
        children = self.preview_table.get_children()
        if len(children) > self._preview_max_rows:
            overflow = len(children) - self._preview_max_rows
            for item in children[:overflow]:
                self.preview_table.delete(item)
        self.preview_table.yview_moveto(1.0)

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    if ENABLE_GUI:
        OkkiAutomationGUI().run()
        return
    config = AppConfig()
    OkkiTradeAutomation(config).run()


if __name__ == "__main__":
    main()
