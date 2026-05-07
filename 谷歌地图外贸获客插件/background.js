const AI_CONFIG = {
  endpoint: "https://api.openai.com/v1/chat/completions", // 默认使用 OpenAI 接口，或替换为您自己的代理地址
  apiKey: "YOUR_API_KEY_HERE", // 请在此处填写您的 API 密钥
  model: "gpt-4o-mini"
};

const CRC32_TABLE = (() => {
  const table = new Uint32Array(256);
  for (let i = 0; i < 256; i += 1) {
    let crc = i;
    for (let j = 0; j < 8; j += 1) {
      crc = (crc & 1) ? (0xedb88320 ^ (crc >>> 1)) : (crc >>> 1);
    }
    table[i] = crc >>> 0;
  }
  return table;
})();

const DEFAULT_STATE = {
  running: false,
  status: "待命",
  detail: "请先打开 Google Maps 页面，再启动插件。",
  country: "",
  city: "",
  currentKeyword: "",
  startedAt: null,
  lastUpdatedAt: null,
  results: [],
  plan: {
    plannedCountries: 0,
    remainingCountries: 0,
    plannedCities: 0,
    remainingCities: 0,
    currentCountry: "",
    currentCity: "",
    currentCityKeywordDone: 0,
    currentCityKeywordTotal: 0,
    skippedCities: 0,
    mode: "manual"
  },
  stats: {
    processed: 0,
    total: 0
  }
};

chrome.runtime.onInstalled.addListener(async () => {
  const current = await chrome.storage.local.get(["gmh_state", "gmh_last_results_backup", "gmh_city_run_history", "gmh_completed_cities"]);
  if (!current.gmh_state) {
    await chrome.storage.local.set({ gmh_state: DEFAULT_STATE });
  }
  if (!current.gmh_last_results_backup) {
    await chrome.storage.local.set({ gmh_last_results_backup: null });
  }
  if (!current.gmh_city_run_history) {
    await chrome.storage.local.set({ gmh_city_run_history: [] });
  }
  if (!current.gmh_completed_cities) {
    await chrome.storage.local.set({ gmh_completed_cities: [] });
  }
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message?.type) {
    return false;
  }

  if (message.type === "STATE_PATCH") {
    respondAsync(sendResponse, async () => {
      await updateState(message.patch);
      return { ok: true };
    });
    return true;
  }

  if (message.type === "RESET_STATE") {
    respondAsync(sendResponse, async () => {
      await chrome.storage.local.set({ gmh_state: DEFAULT_STATE });
      return { ok: true };
    });
    return true;
  }

  if (message.type === "ARCHIVE_CURRENT_RESULTS") {
    respondAsync(sendResponse, async () => {
      const backup = await archiveCurrentResults(message.payload);
      return { ok: true, backup };
    });
    return true;
  }

  if (message.type === "RESTORE_LAST_RESULTS") {
    respondAsync(sendResponse, async () => {
      const restoredState = await restoreLastResults();
      return { ok: true, state: restoredState };
    });
    return true;
  }

  if (message.type === "REGISTER_CITY_RUN") {
    respondAsync(sendResponse, async () => {
      const history = await registerCityRun(message.payload);
      return { ok: true, history };
    });
    return true;
  }

  if (message.type === "FINALIZE_CITY_RUN") {
    respondAsync(sendResponse, async () => {
      const history = await finalizeCityRun(message.payload);
      return { ok: true, history };
    });
    return true;
  }

  if (message.type === "REGISTER_COMPLETED_CITY") {
    respondAsync(sendResponse, async () => {
      const completedCities = await registerCompletedCity(message.payload);
      return { ok: true, completedCities };
    });
    return true;
  }

  if (message.type === "SCRAPE_REMOTE_SOURCE") {
    respondAsync(sendResponse, async () => ({
      ok: true,
      result: await scrapeRemoteSource(message.payload)
    }));
    return true;
  }

  if (message.type === "GENERATE_BUSINESS_INTRO") {
    respondAsync(sendResponse, async () => ({
      ok: true,
      result: await generateBusinessIntroduction(message.payload)
    }));
    return true;
  }

  if (message.type === "GENERATE_KEYWORD_VARIANTS") {
    respondAsync(sendResponse, async () => ({
      ok: true,
      result: await generateKeywordVariants(message.payload)
    }));
    return true;
  }

  if (message.type === "EXPORT_DATA") {
    respondAsync(sendResponse, async () => ({
      ok: true,
      filename: await exportDataFile(message.format)
    }));
    return true;
  }

  return false;
});

async function updateState(patch) {
  const current = await chrome.storage.local.get("gmh_state");
  const nextState = mergeDeep(current.gmh_state || DEFAULT_STATE, {
    ...patch,
    lastUpdatedAt: Date.now()
  });
  await chrome.storage.local.set({ gmh_state: nextState });
  return nextState;
}

async function scrapeRemoteSource(payload) {
  const { url, sourceLabel } = payload || {};
  if (!url) {
    throw new Error("缺少待采集页面地址。");
  }

  const tab = await chrome.tabs.create({
    url,
    active: false
  });

  try {
    await waitForTabComplete(tab.id, 15000);
    await sleep(500);
    const response = await chrome.tabs.sendMessage(tab.id, {
      type: "EXTRACT_PAGE_CONTACTS",
      payload: { sourceLabel, url }
    });
    return response || {};
  } finally {
    if (tab.id) {
      await chrome.tabs.remove(tab.id).catch(() => undefined);
    }
  }
}

async function archiveCurrentResults(payload) {
  const current = await chrome.storage.local.get("gmh_state");
  const state = current.gmh_state || DEFAULT_STATE;
  if (!state.results?.length) {
    return null;
  }

  const backup = {
    archivedAt: Date.now(),
    reason: payload?.reason || "pre_run",
    summary: {
      keyword: payload?.keyword || "",
      country: payload?.country || "",
      city: payload?.city || "",
      total: state.results.length
    },
    state: {
      ...state,
      running: false,
      status: state.status || "已备份",
      detail: state.detail || "已自动备份上次采集结果。"
    }
  };

  await chrome.storage.local.set({ gmh_last_results_backup: backup });
  return backup;
}

async function restoreLastResults() {
  const current = await chrome.storage.local.get("gmh_last_results_backup");
  const backup = current.gmh_last_results_backup;
  if (!backup?.state?.results?.length) {
    throw new Error("没有可恢复的上次结果。");
  }

  const restoredState = mergeDeep(DEFAULT_STATE, {
    ...backup.state,
    running: false,
    status: "已恢复",
    detail: `已恢复上次结果，共 ${backup.state.results.length} 条。`,
    lastUpdatedAt: Date.now()
  });
  await chrome.storage.local.set({ gmh_state: restoredState });
  return restoredState;
}

async function registerCityRun(payload) {
  const current = await chrome.storage.local.get("gmh_city_run_history");
  const history = Array.isArray(current.gmh_city_run_history) ? current.gmh_city_run_history : [];
  const runId = String(payload?.runId || "");
  if (!runId) {
    return history;
  }

  const country = String(payload?.country || "").trim();
  const city = String(payload?.city || "").trim();
  const keyword = String(payload?.keyword || "").trim();
  const projectKeyword = String(payload?.projectKeyword || keyword).trim();
  const projectKey = makeHistoryProjectKey(projectKeyword);
  const nextHistory = [...history];
  let run = nextHistory.find((item) => item.runId === runId);
  if (!run) {
    run = {
      runId,
      startedAt: payload?.startedAt || Date.now(),
      finishedAt: null,
      status: "running",
      country,
      projectKeyword,
      projectKey,
      keyword,
      cities: []
    };
    nextHistory.unshift(run);
  }

  const cityKey = makeHistoryCityKey(country, city);
  if (cityKey && !run.cities.some((item) => makeHistoryCityKey(item.country, item.city) === cityKey)) {
    run.cities.push({
      country,
      city,
      projectKeyword,
      projectKey,
      recordedAt: Date.now()
    });
  }

  const limitedHistory = nextHistory.slice(0, 500);
  await chrome.storage.local.set({ gmh_city_run_history: limitedHistory });
  return limitedHistory;
}

async function finalizeCityRun(payload) {
  const current = await chrome.storage.local.get("gmh_city_run_history");
  const history = Array.isArray(current.gmh_city_run_history) ? current.gmh_city_run_history : [];
  const runId = String(payload?.runId || "");
  if (!runId) {
    return history;
  }

  const nextHistory = history.map((item) => {
    if (item.runId !== runId) {
      return item;
    }
    return {
      ...item,
      status: payload?.status || item.status || "completed",
      finishedAt: Date.now()
    };
  });

  const limitedHistory = nextHistory.slice(0, 500);
  await chrome.storage.local.set({ gmh_city_run_history: limitedHistory });
  return limitedHistory;
}

async function registerCompletedCity(payload) {
  const current = await chrome.storage.local.get("gmh_completed_cities");
  const completedCities = Array.isArray(current.gmh_completed_cities) ? current.gmh_completed_cities : [];
  const country = String(payload?.country || "").trim();
  const city = String(payload?.city || "").trim();
  const projectKeyword = String(payload?.projectKeyword || "").trim();
  const projectKey = makeHistoryProjectKey(projectKeyword);
  const cityKey = makeHistoryCityKey(country, city);
  if (!cityKey) {
    return completedCities;
  }

  const next = [...completedCities];
  if (!next.some((item) => makeHistoryCityKey(item.country, item.city) === cityKey)) {
    next.unshift({
      country,
      city,
      projectKeyword,
      projectKey,
      completedAt: Date.now()
    });
  }

  const limited = next.slice(0, 500);
  await chrome.storage.local.set({ gmh_completed_cities: limited });
  return limited;
}

async function exportDataFile(format) {
  const current = await chrome.storage.local.get([
    "gmh_state",
    "gmh_project_keyword_input",
    "gmh_keyword_input",
    "gmh_country_input",
    "gmh_city_input",
    "gmh_city_run_history"
  ]);
  const rows = current.gmh_state?.results || [];
  if (!rows.length) {
    throw new Error("没有可导出的数据。");
  }

  const normalizedRows = rows
    .map(normalizeExportRow)
    .filter((row) => row["邮箱"]);
  if (!normalizedRows.length) {
    throw new Error("没有可导出的邮箱数据。");
  }
  const exportRows = dedupeExportRows(normalizedRows);
  const keyword = current.gmh_project_keyword_input
    || current.gmh_state?.projectKeyword
    || current.gmh_keyword_input
    || current.gmh_state?.currentKeyword
    || "未设置";
  const history = Array.isArray(current.gmh_city_run_history) ? current.gmh_city_run_history : [];
  
  const filenameBase = buildExportFilenameBase({
    rows: exportRows,
    keyword,
    history
  });

  if (format === "csv") {
    const csv = buildCsv(exportRows);
    const filename = `${filenameBase}.csv`;
    await chrome.downloads.download({
      url: `data:text/csv;charset=utf-8,${encodeURIComponent(`\ufeff${csv}`)}`,
      filename,
      saveAs: true
    });
    return filename;
  }

  const workbookBytes = buildXlsxWorkbook(exportRows);
  const filename = `${filenameBase}.xlsx`;
  const dataUrl = buildBinaryDataUrl(
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    workbookBytes
  );
  await chrome.downloads.download({
    url: dataUrl,
    filename,
    saveAs: true
  });
  return filename;
}

async function generateBusinessIntroduction(payload) {
  const { text, url, companyName } = payload || {};
  if (!text || !String(text).trim()) {
    return "";
  }

  const prompt = [
    "你是一名企业信息整理助手。",
    "请根据提供的官网文本，提炼一句中文业务介绍。",
    "要求：",
    "1. 只输出一句中文，不要标题、不要项目符号、不要解释。",
    "2. 长度控制在 40 到 90 个中文字符之间。",
    "3. 聚焦主营产品、服务场景、客户类型或业务定位。",
    "4. 如果信息不足，请尽量保守概括，不要编造联系方式、成立时间、规模等事实。",
    "5. 如果看不出明确业务内容，返回空字符串。",
    "",
    `公司名称：${companyName || "未知"}`,
    `官网地址：${url || "未知"}`,
    "官网文本：",
    String(text).slice(0, 6000)
  ].join("\n");

  const response = await fetch(AI_CONFIG.endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${AI_CONFIG.apiKey}`
    },
    body: JSON.stringify({
      model: AI_CONFIG.model,
      temperature: 0.2,
      messages: [
        {
          role: "system",
          content: "你擅长从网页文本中提炼真实、简洁的企业主营介绍。"
        },
        {
          role: "user",
          content: prompt
        }
      ]
    })
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => "");
    throw new Error(`AI 接口请求失败：${response.status}${errorText ? ` ${errorText.slice(0, 120)}` : ""}`);
  }

  const data = await response.json();
  const content = data?.choices?.[0]?.message?.content;
  return sanitizeAiText(content);
}

async function generateKeywordVariants(payload) {
  const seedKeyword = sanitizeAiText(payload?.keyword || "");
  if (!seedKeyword) {
    return [];
  }

  const prompt = [
    "你是一名 Google Maps B2B 搜索词扩展助手。",
    "请围绕给定核心关键词，生成 8 到 12 个英文搜索关键词变体。",
    "要求：",
    "1. 与原词意思接近，适合同一批潜在客户搜索。",
    "2. 优先使用商业搜索常见表达，如 supplier, company, contractor, installer, wholesaler, distributor, service 等。",
    "3. 不要输出国家、城市、人名、品牌名。",
    "4. 不要偏离原始行业，不要扩展到完全不同产品。",
    "5. 只返回 JSON 数组字符串，例如 [\"a\", \"b\"]。",
    "",
    `核心关键词：${seedKeyword}`
  ].join("\n");

  const response = await fetch(AI_CONFIG.endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${AI_CONFIG.apiKey}`
    },
    body: JSON.stringify({
      model: AI_CONFIG.model,
      temperature: 0.4,
      messages: [
        {
          role: "system",
          content: "你擅长为 Google Maps 和企业获客场景生成高相关英文关键词变体。"
        },
        {
          role: "user",
          content: prompt
        }
      ]
    })
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => "");
    throw new Error(`关键词扩展失败：${response.status}${errorText ? ` ${errorText.slice(0, 120)}` : ""}`);
  }

  const data = await response.json();
  const content = data?.choices?.[0]?.message?.content;
  return parseKeywordVariants(content, seedKeyword);
}

function normalizeExportRow(item) {
  return {
    "公司名称": item.companyName || "",
    "联系电话": item.phone || "",
    "邮箱": validateAndCleanEmail(item.email) || "",
    "官网地址": item.website || "",
    "所在国家": item.country || "",
    "所在城市": item.city || "",
    "搜索关键词": item.keyword || "",
    "业务介绍": item.businessIntroduction || "",
    "社媒链接": (item.socialLinks || []).join(" | "),
    "商家评分": item.rating || ""
  };
}

function dedupeExportRows(rows) {
  const merged = new Map();
  for (const row of rows || []) {
    const key = findExistingExportDedupKey(merged, row) || buildExportDedupKey(row);
    if (!key) {
      continue;
    }

    if (!merged.has(key)) {
      merged.set(key, { ...row });
      continue;
    }

    merged.set(key, mergeExportRows(merged.get(key), row));
  }
  return Array.from(merged.values());
}

function findExistingExportDedupKey(merged, row) {
  const candidateKeys = new Set(buildExportDedupIdentityKeys(row));
  for (const [key, current] of merged.entries()) {
    const currentKeys = buildExportDedupIdentityKeys(current);
    if (currentKeys.some((currentKey) => candidateKeys.has(currentKey))) {
      return key;
    }
  }
  return "";
}

function buildExportDedupKey(row) {
  return buildExportDedupIdentityKeys(row)[0] || "";
}

function buildExportDedupIdentityKeys(row) {
  const keys = [];
  const email = validateAndCleanEmail(row["邮箱"] || "");
  if (email) {
    keys.push(`email:${email}`);
  }

  const websiteHost = normalizeWebsiteHost(row["官网地址"] || "");
  if (websiteHost) {
    keys.push(`website:${websiteHost}`);
  }

  const phone = normalizePhone(row["联系电话"] || "");
  if (phone) {
    keys.push(`phone:${phone}`);
  }

  const companyName = normalizeTextFingerprint(row["公司名称"] || "");
  const city = normalizeTextFingerprint(row["所在城市"] || "");
  if (companyName && city) {
    keys.push(`company-city:${companyName}|${city}`);
  }

  return uniqueValues(keys);
}

function mergeExportRows(current, incoming) {
  return {
    ...current,
    "公司名称": pickLonger(current["公司名称"], incoming["公司名称"]),
    "联系电话": pickLonger(current["联系电话"], incoming["联系电话"]),
    "邮箱": validateAndCleanEmail(current["邮箱"]) || validateAndCleanEmail(incoming["邮箱"]) || "",
    "官网地址": pickLonger(current["官网地址"], incoming["官网地址"]),
    "所在国家": pickLonger(current["所在国家"], incoming["所在国家"]),
    "所在城市": pickLonger(current["所在城市"], incoming["所在城市"]),
    "搜索关键词": mergeTextValues(current["搜索关键词"], incoming["搜索关键词"]),
    "业务介绍": pickLonger(current["业务介绍"], incoming["业务介绍"]),
    "社媒链接": mergeTextValues(current["社媒链接"], incoming["社媒链接"], " | "),
    "商家评分": pickLonger(current["商家评分"], incoming["商家评分"])
  };
}

function validateAndCleanEmail(email) {
  const cleaned = String(email || "")
    .toLowerCase()
    .trim()
    .replace(/\s+/g, "")
    .replace(/^[^a-z0-9._%+-]+/, "")
    .replace(/[^a-z0-9._%+-]+$/, "");
  
  // 验证邮箱格式
  if (!/^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$/.test(cleaned)) {
    return "";
  }
  
  // 检查邮箱长度（RFC 5321）
  if (cleaned.length < 5 || cleaned.length > 254) {
    return "";
  }
  
  // 检查本地部分（@前面）长度
  const atIndex = cleaned.lastIndexOf("@");
  const localPart = cleaned.substring(0, atIndex);
  const domain = cleaned.substring(atIndex + 1);
  
  if (localPart.length > 64 || localPart.length === 0) {
    return "";
  }
  
  // 检查连续的点、开头/结尾的点
  if (/\.\.|\.$|^\./.test(cleaned) || /\.@/.test(cleaned) || /@\./.test(cleaned)) {
    return "";
  }
  
  // 检查域名有效性
  if (!/^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)*$/.test(domain)) {
    return "";
  }
  
  return cleaned;
}

function normalizeWebsiteHost(value) {
  try {
    return new URL(value).hostname.replace(/^www\./, "").toLowerCase();
  } catch (error) {
    return String(value || "").replace(/^https?:\/\//i, "").replace(/^www\./i, "").split("/")[0].toLowerCase();
  }
}

function normalizePhone(value) {
  return String(value || "").replace(/\D/g, "");
}

function normalizeTextFingerprint(value) {
  return String(value || "").toLowerCase().replace(/[^a-z0-9\u4e00-\u9fa5]+/g, "");
}

function mergeTextValues(a, b, separator = " / ") {
  return uniqueValues([a, b].filter(Boolean)).join(separator);
}

function pickLonger(a, b) {
  return String(b || "").length > String(a || "").length ? b : a;
}

function uniqueValues(list) {
  return Array.from(new Set((list || []).map((item) => String(item || "").trim()).filter(Boolean)));
}

function respondAsync(sendResponse, task) {
  Promise.resolve()
    .then(task)
    .then((payload) => sendResponse(payload))
    .catch((error) => sendResponse({
      ok: false,
      error: error?.message || String(error || "未知错误")
    }));
}

function buildExportFilenameBase({ rows, keyword, history }) {
  const now = new Date();
  const year = String(now.getFullYear());
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  const date = `${year}-${month}-${day}`;
  
  // 计算该关键词是第几轮
  const sanitizedKeyword = sanitizeFilenameSegment(keyword);
  const projectKey = makeHistoryProjectKey(keyword);
  const roundNumber = calculateRoundNumber(history, projectKey);
  
  return `${sanitizedKeyword}_${date}_第${roundNumber}轮`;
}

function countExportCities(rows) {
  const cities = new Set();
  for (const row of (rows || [])) {
    const key = `${String(row.country || "").trim().toLowerCase()}|${String(row.city || "").trim().toLowerCase()}`;
    if (key !== "|") {
      cities.add(key);
    }
  }
  return cities.size || 1;
}

function sanitizeFilenameSegment(value) {
  const normalized = String(value || "")
    .replace(/[\\/:*?"<>|]+/g, " ")
    .replace(/\s+/g, " ")
    .replace(/[\r\n,]+/g, " ")
    .trim();

  const compact = normalized || "未设置";
  return compact.slice(0, 60).replace(/\.+$/g, "").trim() || "未设置";
}

function makeHistoryCityKey(country, city) {
  return `${String(country || "").trim().toLowerCase()}|${String(city || "").trim().toLowerCase()}`;
}

function makeHistoryProjectKey(keyword) {
  return String(keyword || "")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim();
}

function calculateRoundNumber(history, projectKey) {
  if (!Array.isArray(history) || !projectKey) {
    return 1;
  }
  
  // 计算该projectKey对应的run数量
  const matchingRuns = history.filter((run) => {
    const runProjectKey = makeHistoryProjectKey(run.projectKeyword || run.keyword || "");
    return runProjectKey === projectKey;
  });
  
  return matchingRuns.length || 1;
}

function buildCsv(rows) {
  const headers = Object.keys(rows[0]);
  const body = rows.map((row) => headers.map((header) => csvEscape(row[header] || "")).join(","));
  return [headers.join(","), ...body].join("\n");
}

function buildXlsxWorkbook(rows) {
  const headers = Object.keys(rows[0]);
  const sheetXml = buildWorksheetXml(headers, rows);
  const files = [
    { name: "[Content_Types].xml", content: buildContentTypesXml() },
    { name: "_rels/.rels", content: buildRootRelsXml() },
    { name: "xl/workbook.xml", content: buildWorkbookXml() },
    { name: "xl/_rels/workbook.xml.rels", content: buildWorkbookRelsXml() },
    { name: "xl/worksheets/sheet1.xml", content: sheetXml },
    { name: "xl/styles.xml", content: buildStylesXml() }
  ];
  return buildZipBytes(files);
}

function csvEscape(value) {
  const normalized = String(value).replace(/\r?\n/g, " ");
  if (/[",]/.test(normalized)) {
    return `"${normalized.replace(/"/g, '""')}"`;
  }
  return normalized;
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function buildWorksheetXml(headers, rows) {
  const allRows = [headers, ...rows.map((row) => headers.map((header) => row[header] || ""))];
  const cells = allRows
    .map((values, rowIndex) => {
      const cellXml = values
        .map((value, columnIndex) => {
          const ref = `${columnNumberToName(columnIndex + 1)}${rowIndex + 1}`;
          const styleIndex = rowIndex === 0 ? 1 : 0;
          return `<c r="${ref}" t="inlineStr" s="${styleIndex}"><is><t xml:space="preserve">${escapeXml(value)}</t></is></c>`;
        })
        .join("");
      return `<row r="${rowIndex + 1}">${cellXml}</row>`;
    })
    .join("");

  const lastCell = `${columnNumberToName(headers.length)}${allRows.length}`;
  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetViews><sheetView workbookViewId="0"/></sheetViews>
  <sheetFormatPr defaultRowHeight="15"/>
  <cols>${headers.map((_, index) => `<col min="${index + 1}" max="${index + 1}" width="${index === 7 || index === 8 ? 36 : 22}" customWidth="1"/>`).join("")}</cols>
  <sheetData>${cells}</sheetData>
  <dimension ref="A1:${lastCell}"/>
</worksheet>`;
}

function buildContentTypesXml() {
  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>`;
}

function buildRootRelsXml() {
  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>`;
}

function buildWorkbookXml() {
  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
          xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Leads" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>`;
}

function buildWorkbookRelsXml() {
  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>`;
}

function buildStylesXml() {
  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="2">
    <font><sz val="11"/><name val="Calibri"/></font>
    <font><b/><sz val="11"/><name val="Calibri"/></font>
  </fonts>
  <fills count="2">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
  </fills>
  <borders count="1">
    <border><left/><right/><top/><bottom/><diagonal/></border>
  </borders>
  <cellStyleXfs count="1">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>
  </cellStyleXfs>
  <cellXfs count="2">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>
  </cellXfs>
  <cellStyles count="1">
    <cellStyle name="Normal" xfId="0" builtinId="0"/>
  </cellStyles>
</styleSheet>`;
}

function buildZipBytes(files) {
  const encoder = new TextEncoder();
  const fileEntries = files.map((file) => {
    const bytes = encoder.encode(file.content);
    return {
      name: file.name,
      bytes,
      crc32: computeCrc32(bytes)
    };
  });

  const localParts = [];
  const centralParts = [];
  let offset = 0;

  for (const entry of fileEntries) {
    const nameBytes = encoder.encode(entry.name);
    const localHeader = createZipHeader(0x04034b50, nameBytes, entry.bytes.length, entry.crc32, offset, false);
    localParts.push(localHeader, nameBytes, entry.bytes);

    const centralHeader = createZipHeader(0x02014b50, nameBytes, entry.bytes.length, entry.crc32, offset, true);
    centralParts.push(centralHeader, nameBytes);

    offset += localHeader.length + nameBytes.length + entry.bytes.length;
  }

  const centralDirectory = new Uint8Array(concatUint8Arrays(centralParts));
  const centralSize = centralDirectory.length;
  const endRecord = createZipEndRecord(fileEntries.length, centralSize, offset);
  return concatUint8Arrays([...localParts, centralDirectory, endRecord]);
}

function createZipHeader(signature, nameBytes, size, crc32, offset, isCentral) {
  const buffer = new ArrayBuffer(isCentral ? 46 : 30);
  const view = new DataView(buffer);
  view.setUint32(0, signature, true);
  if (isCentral) {
    view.setUint16(4, 20, true);
    view.setUint16(6, 20, true);
    view.setUint16(8, 0, true);
    view.setUint16(10, 0, true);
    view.setUint16(12, 0, true);
    view.setUint16(14, 0, true);
    view.setUint32(16, crc32 >>> 0, true);
    view.setUint32(20, size, true);
    view.setUint32(24, size, true);
    view.setUint16(28, nameBytes.length, true);
    view.setUint16(30, 0, true);
    view.setUint16(32, 0, true);
    view.setUint16(34, 0, true);
    view.setUint16(36, 0, true);
    view.setUint32(38, 0, true);
    view.setUint32(42, offset, true);
  } else {
    view.setUint16(4, 20, true);
    view.setUint16(6, 0, true);
    view.setUint16(8, 0, true);
    view.setUint16(10, 0, true);
    view.setUint16(12, 0, true);
    view.setUint32(14, crc32 >>> 0, true);
    view.setUint32(18, size, true);
    view.setUint32(22, size, true);
    view.setUint16(26, nameBytes.length, true);
    view.setUint16(28, 0, true);
  }
  return new Uint8Array(buffer);
}

function createZipEndRecord(fileCount, centralSize, centralOffset) {
  const buffer = new ArrayBuffer(22);
  const view = new DataView(buffer);
  view.setUint32(0, 0x06054b50, true);
  view.setUint16(4, 0, true);
  view.setUint16(6, 0, true);
  view.setUint16(8, fileCount, true);
  view.setUint16(10, fileCount, true);
  view.setUint32(12, centralSize, true);
  view.setUint32(16, centralOffset, true);
  view.setUint16(20, 0, true);
  return new Uint8Array(buffer);
}

function concatUint8Arrays(chunks) {
  const total = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
  const output = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    output.set(chunk, offset);
    offset += chunk.length;
  }
  return output;
}

function computeCrc32(bytes) {
  let crc = 0 ^ -1;
  for (let i = 0; i < bytes.length; i += 1) {
    crc = (crc >>> 8) ^ CRC32_TABLE[(crc ^ bytes[i]) & 0xff];
  }
  return (crc ^ -1) >>> 0;
}

function columnNumberToName(value) {
  let number = value;
  let result = "";
  while (number > 0) {
    const remainder = (number - 1) % 26;
    result = String.fromCharCode(65 + remainder) + result;
    number = Math.floor((number - 1) / 26);
  }
  return result;
}

function escapeXml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

function buildBinaryDataUrl(mimeType, bytes) {
  let binary = "";
  const chunkSize = 0x8000;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    const chunk = bytes.subarray(i, i + chunkSize);
    binary += String.fromCharCode(...chunk);
  }
  return `data:${mimeType};base64,${btoa(binary)}`;
}

function sanitizeAiText(value) {
  return String(value || "")
    .replace(/^[\s"'`]+|[\s"'`]+$/g, "")
    .replace(/^业务介绍[:：]\s*/i, "")
    .replace(/\r?\n+/g, " ")
    .trim();
}

function parseKeywordVariants(value, seedKeyword) {
  const raw = String(value || "").trim();
  let parsed = [];

  try {
    parsed = JSON.parse(raw);
  } catch (error) {
    parsed = raw.split(/\r?\n|,/).map((item) => item.replace(/^[-*\d.\s"]+/, "").replace(/["]+$/g, "").trim());
  }

  const normalized = [seedKeyword, ...parsed]
    .map((item) => sanitizeAiText(item))
    .filter(Boolean)
    .filter((item) => /^[\w\s/&+-]+$/i.test(item))
    .slice(0, 12);

  return Array.from(new Set(normalized));
}

function waitForTabComplete(tabId, timeoutMs = 30000) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      chrome.tabs.onUpdated.removeListener(listener);
      reject(new Error("页面加载超时。"));
    }, timeoutMs);

    const listener = (updatedTabId, info) => {
      if (updatedTabId === tabId && info.status === "complete") {
        clearTimeout(timer);
        chrome.tabs.onUpdated.removeListener(listener);
        resolve();
      }
    };

    chrome.tabs.onUpdated.addListener(listener);
  });
}

function mergeDeep(target, source) {
  const output = Array.isArray(target) ? [...target] : { ...target };
  for (const [key, value] of Object.entries(source || {})) {
    if (Array.isArray(value)) {
      output[key] = [...value];
      continue;
    }

    if (value && typeof value === "object") {
      output[key] = mergeDeep(output[key] || {}, value);
      continue;
    }

    output[key] = value;
  }
  return output;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function pad(value) {
  return String(value).padStart(2, "0");
}
