const DEFAULT_KEYWORDS = [
  "Restaurant",
  "Coffee Shop",
  "Hotel",
  "Gym"
];

const PROJECT_CITY_BLOCKLIST = [
  {
    keywords: [],
    country: "Country Name",
    cities: ["City 1", "City 2"]
  }
];

const COUNTRY_ALIASES = {
  usa: "美国",
  "u.s.a.": "美国",
  us: "美国",
  "u.s.": "美国",
  "united states": "美国",
  america: "美国",
  canada: "加拿大",
  mexico: "墨西哥",
  brazil: "巴西",
  argentina: "阿根廷",
  chile: "智利",
  colombia: "哥伦比亚",
  peru: "秘鲁",
  uk: "英国",
  "u.k.": "英国",
  "united kingdom": "英国",
  england: "英国",
  ireland: "爱尔兰",
  france: "法国",
  french: "法国",
  frensh: "法国",
  germany: "德国",
  italy: "意大利",
  spain: "西班牙",
  portugal: "葡萄牙",
  netherlands: "荷兰",
  belgium: "比利时",
  switzerland: "瑞士",
  austria: "奥地利",
  poland: "波兰",
  sweden: "瑞典",
  norway: "挪威",
  denmark: "丹麦",
  finland: "芬兰",
  greece: "希腊",
  romania: "罗马尼亚",
  "czech republic": "捷克",
  turkey: "土耳其",
  australia: "澳大利亚",
  "united arab emirates": "阿联酋",
  uae: "阿联酋",
  "saudi arabia": "沙特阿拉伯",
  "new zealand": "新西兰",
  "south africa": "南非",
  japan: "日本",
  korea: "韩国",
  "south korea": "韩国",
  india: "印度",
  pakistan: "巴基斯坦",
  bangladesh: "孟加拉国",
  thailand: "泰国",
  vietnam: "越南",
  indonesia: "印度尼西亚",
  philippines: "菲律宾",
  china: "中国",
  "hong kong": "中国香港",
  taiwan: "中国台湾",
  singapore: "新加坡",
  malaysia: "马来西亚"
};

const TARGET_MARKETS = [
  {
    countryLabel: "美国",
    aliases: ["美国", "usa", "us", "united states", "america"],
    cities: [
      "New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio", "San Diego",
      "Dallas", "Jacksonville", "Austin", "Fort Worth", "San Jose", "Columbus", "Charlotte", "Indianapolis",
      "San Francisco", "Seattle", "Denver", "Washington", "Boston", "Nashville", "Baltimore", "Oklahoma City",
      "Louisville", "Portland", "Las Vegas", "Milwaukee", "Albuquerque", "Tucson", "Fresno", "Sacramento",
      "Mesa", "Kansas City", "Atlanta", "Omaha", "Raleigh", "Miami", "Long Beach", "Virginia Beach",
      "Oakland", "Minneapolis", "Tulsa", "Arlington", "Tampa", "New Orleans", "Wichita", "Cleveland",
      "Bakersfield", "Aurora"
    ]
  },
  {
    countryLabel: "加拿大",
    aliases: ["加拿大", "canada"],
    cities: ["Toronto", "Montreal", "Vancouver", "Calgary", "Edmonton", "Ottawa", "Winnipeg", "Quebec City", "Hamilton", "Kitchener"]
  },
  {
    countryLabel: "英国",
    aliases: ["英国", "uk", "u.k.", "united kingdom", "england"],
    cities: ["London", "Birmingham", "Manchester", "Glasgow", "Liverpool", "Leeds", "Bristol", "Sheffield", "Edinburgh", "Leicester"]
  },
  {
    countryLabel: "法国",
    aliases: ["法国", "france", "french", "frensh"],
    cities: ["Paris", "Marseille", "Lyon", "Toulouse", "Nice", "Nantes", "Montpellier", "Strasbourg", "Bordeaux", "Lille"]
  },
  {
    countryLabel: "澳大利亚",
    aliases: ["澳大利亚", "australia"],
    cities: ["Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide", "Gold Coast", "Canberra", "Newcastle", "Wollongong", "Geelong"]
  },
  {
    countryLabel: "阿联酋",
    aliases: ["阿联酋", "uae", "united arab emirates"],
    cities: ["Dubai", "Abu Dhabi", "Sharjah", "Ajman", "Ras Al Khaimah", "Fujairah", "Al Ain", "Umm Al Quwain", "Khor Fakkan", "Dibba Al Fujairah"]
  },
  {
    countryLabel: "沙特阿拉伯",
    aliases: ["沙特阿拉伯", "saudi arabia"],
    cities: ["Riyadh", "Jeddah", "Mecca", "Medina", "Dammam", "Khobar", "Tabuk", "Abha", "Taif", "Jubail"]
  },
  {
    countryLabel: "新西兰",
    aliases: ["新西兰", "new zealand"],
    cities: ["Auckland", "Wellington", "Christchurch", "Hamilton", "Tauranga", "Dunedin", "Palmerston North", "Napier", "Nelson", "Rotorua"]
  },
  {
    countryLabel: "南非",
    aliases: ["南非", "south africa"],
    cities: ["Johannesburg", "Cape Town", "Durban", "Pretoria", "Port Elizabeth", "Bloemfontein", "East London", "Nelspruit", "Polokwane", "Pietermaritzburg"]
  },
  {
    countryLabel: "日本",
    aliases: ["日本", "japan"],
    cities: ["Tokyo", "Yokohama", "Osaka", "Nagoya", "Sapporo", "Fukuoka", "Kobe", "Kyoto", "Kawasaki", "Saitama"]
  },
  {
    countryLabel: "新加坡",
    aliases: ["新加坡", "singapore"],
    cities: ["Singapore"]
  },
  {
    countryLabel: "马来西亚",
    aliases: ["马来西亚", "malaysia"],
    cities: ["Kuala Lumpur", "Johor Bahru", "George Town", "Ipoh", "Shah Alam", "Petaling Jaya", "Kota Kinabalu", "Kuching", "Malacca City", "Penang"]
  }
];

const stateEls = {
  countryInput: document.getElementById("countryInput"),
  cityInput: document.getElementById("cityInput"),
  cityBatchSizeInput: document.getElementById("cityBatchSizeInput"),
  manualSkipCitiesInput: document.getElementById("manualSkipCitiesInput"),
  keywordInput: document.getElementById("keywordInput"),
  expandKeywordsInput: document.getElementById("expandKeywordsInput"),
  skipVisitedInput: document.getElementById("skipVisitedInput"),
  restartCitiesInput: document.getElementById("restartCitiesInput"),
  cityPlanPreview: document.getElementById("cityPlanPreview"),
  citySkipPreview: document.getElementById("citySkipPreview"),
  keywordHints: document.getElementById("keywordHints"),
  startBtn: document.getElementById("startBtn"),
  exportCsvBtn: document.getElementById("exportCsvBtn"),
  exportExcelBtn: document.getElementById("exportExcelBtn"),
  restoreBtn: document.getElementById("restoreBtn"),
  clearBtn: document.getElementById("clearBtn"),
  dedupeBtn: document.getElementById("dedupeBtn"),
  filterInput: document.getElementById("filterInput"),
  sourceFilter: document.getElementById("sourceFilter"),
  filterSummary: document.getElementById("filterSummary"),
  statusText: document.getElementById("statusText"),
  progressText: document.getElementById("progressText"),
  progressBar: document.getElementById("progressBar"),
  detailText: document.getElementById("detailText"),
  resultCount: document.getElementById("resultCount"),
  completedCityCountText: document.getElementById("completedCityCountText"),
  plannedCountriesText: document.getElementById("plannedCountriesText"),
  remainingCountriesText: document.getElementById("remainingCountriesText"),
  plannedCitiesText: document.getElementById("plannedCitiesText"),
  remainingCitiesText: document.getElementById("remainingCitiesText"),
  countryText: document.getElementById("countryText"),
  cityText: document.getElementById("cityText"),
  cityKeywordProgressText: document.getElementById("cityKeywordProgressText"),
  keywordText: document.getElementById("keywordText"),
  resultsList: document.getElementById("resultsList"),
  resultsTableBody: document.getElementById("resultsTableBody"),
  cityRunHistory: document.getElementById("cityRunHistory")
};

let latestState = null;
let latestCityRunHistory = [];
let latestBackupResults = [];
let latestCompletedCities = [];
let pendingStart = false;
let pendingStopRequested = false;
let lastCountryCompletionNoticeId = "";

boot();

async function boot() {
  renderKeywordHints();
  attachEvents();
  stateEls.countryInput.value = await getStorageValue("gmh_country_input", "");
  stateEls.cityInput.value = await getStorageValue("gmh_city_input", "");
  stateEls.cityBatchSizeInput.value = await getStorageValue("gmh_city_batch_size_input", "");
  stateEls.manualSkipCitiesInput.value = await getStorageValue("gmh_manual_skip_cities_input", "");
  stateEls.keywordInput.value = await getStorageValue("gmh_keyword_input", "");
  stateEls.expandKeywordsInput.checked = await getStorageValue("gmh_expand_keywords_input", false);
  stateEls.skipVisitedInput.checked = await getStorageValue("gmh_skip_visited_input", true);
  stateEls.restartCitiesInput.checked = await getStorageValue("gmh_restart_cities_input", false);
  latestState = await getState();
  latestCityRunHistory = await getStorageValue("gmh_city_run_history", []);
  latestBackupResults = await getBackupResults();
  latestCompletedCities = await getStorageValue("gmh_completed_cities", []);
  lastCountryCompletionNoticeId = latestState?.countryCompletionNotice?.id || "";
  renderState(latestState);
  renderCityRunHistory(latestCityRunHistory);
  renderCityPlanPreview();
  chrome.storage.onChanged.addListener(handleStorageChange);
}

function renderKeywordHints() {
  stateEls.keywordHints.innerHTML = DEFAULT_KEYWORDS
    .map((keyword) => `<span class="keyword-chip">${escapeHtml(keyword)}</span>`)
    .join("");
}

function attachEvents() {
  stateEls.startBtn.addEventListener("click", handleStartStop);
  stateEls.exportCsvBtn.addEventListener("click", () => exportData("csv"));
  stateEls.exportExcelBtn.addEventListener("click", () => exportData("excel"));
  stateEls.restoreBtn.addEventListener("click", restoreLastResults);
  stateEls.clearBtn.addEventListener("click", clearData);
  stateEls.dedupeBtn.addEventListener("click", dedupeData);
  stateEls.filterInput.addEventListener("input", () => renderState(latestState));
  stateEls.sourceFilter.addEventListener("change", () => renderState(latestState));
  stateEls.countryInput.addEventListener("input", async (event) => {
    await chrome.storage.local.set({ gmh_country_input: event.target.value.trim() });
    renderCityPlanPreview();
  });
  stateEls.cityInput.addEventListener("input", async (event) => {
    await chrome.storage.local.set({ gmh_city_input: event.target.value.trim() });
    renderCityPlanPreview();
  });
  stateEls.cityBatchSizeInput.addEventListener("input", async (event) => {
    await chrome.storage.local.set({ gmh_city_batch_size_input: event.target.value.trim() });
    renderCityPlanPreview();
  });
  stateEls.manualSkipCitiesInput.addEventListener("input", async (event) => {
    await chrome.storage.local.set({ gmh_manual_skip_cities_input: event.target.value.trim() });
    renderCityPlanPreview();
  });
  stateEls.keywordInput.addEventListener("input", async (event) => {
    await chrome.storage.local.set({ gmh_keyword_input: event.target.value.trim() });
    renderCityPlanPreview();
  });
  stateEls.expandKeywordsInput.addEventListener("change", async (event) => {
    await chrome.storage.local.set({ gmh_expand_keywords_input: Boolean(event.target.checked) });
  });
  stateEls.skipVisitedInput.addEventListener("change", async (event) => {
    await chrome.storage.local.set({ gmh_skip_visited_input: Boolean(event.target.checked) });
    renderCityPlanPreview();
  });
  stateEls.restartCitiesInput.addEventListener("change", async (event) => {
    await chrome.storage.local.set({ gmh_restart_cities_input: Boolean(event.target.checked) });
    renderCityPlanPreview();
  });
}

async function handleStartStop() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id || !isMapsUrl(tab.url)) {
    renderTip("请先在当前标签页打开 Google Maps，然后再点击开始采集。");
    return;
  }

  latestState = await getState();
  const rawKeywordInput = stateEls.keywordInput.value.trim();
  const manualKeywords = splitKeywords(rawKeywordInput);

  if (!manualKeywords.length) {
    renderTip("请先填写关键词，再开始采集。");
    stateEls.keywordInput.focus();
    return;
  }

  const locationValidation = validateManualCityInput(
    stateEls.countryInput.value.trim(),
    stateEls.cityInput.value.trim()
  );
  if (!locationValidation.ok) {
    showLocationInputWarning(locationValidation.message);
    renderCityPlanPreview();
    (locationValidation.field === "country" ? stateEls.countryInput : stateEls.cityInput).focus();
    return;
  }

  if (latestState?.running || pendingStart) {
    pendingStopRequested = true;
    const stopped = await dispatchCommandToTab(tab.id, {
      type: "STOP_SCRAPE"
    });
    if (!stopped.ok) {
      if (pendingStart) {
        renderTip("已取消本次启动。");
      } else {
        renderTip(stopped.error || "停止指令发送失败，请刷新地图页面后重试。");
      }
    }
    if (pendingStart) {
      pendingStart = false;
      renderState(latestState);
    }
    return;
  }

  pendingStart = true;
  pendingStopRequested = false;
  renderState({
    ...(latestState || getDefaultState()),
    running: true,
    status: "启动中",
    detail: "正在准备采集任务..."
  });

  let keywordInputForRun = rawKeywordInput;

  if (stateEls.expandKeywordsInput.checked && manualKeywords.length === 1 && !pendingStopRequested) {
    renderTip(`正在围绕关键词 “${manualKeywords[0]}” 自动扩展同义搜索词...`);
    const expandedKeywords = await expandKeywordVariants(manualKeywords[0]);
    if (expandedKeywords.length > 1) {
      keywordInputForRun = uniqueValues([manualKeywords[0], ...expandedKeywords]).join(", ");
      stateEls.keywordInput.value = keywordInputForRun;
      await chrome.storage.local.set({ gmh_keyword_input: keywordInputForRun });
      renderTip(`已自动扩展为 ${expandedKeywords.length} 个关键词，将按扩展结果执行采集。`);
    }
  } else if (!stateEls.expandKeywordsInput.checked) {
    renderTip(`将只按输入关键词搜索：${manualKeywords.join(", ")}`);
  }

  if (pendingStopRequested) {
    pendingStart = false;
    pendingStopRequested = false;
    latestState = await getState();
    renderState(latestState);
    renderTip("已取消本次启动。");
    return;
  }

  const parsed = parseInputs({
    country: stateEls.countryInput.value.trim(),
    city: stateEls.cityInput.value.trim(),
    cityBatchSize: stateEls.cityBatchSizeInput.value.trim(),
    manualSkipCities: stateEls.manualSkipCitiesInput.value.trim(),
    projectKeyword: manualKeywords[0],
    keywords: keywordInputForRun,
    skipVisitedCities: stateEls.skipVisitedInput.checked,
    restartCities: stateEls.restartCitiesInput.checked,
    seedResults: collectSeedResultsForRun({
      results: dedupeResults([...(latestState?.results || []), ...latestBackupResults]),
      country: stateEls.countryInput.value.trim(),
      city: stateEls.cityInput.value.trim()
    }),
    existingKeywordRecords: collectExistingKeywordRecords([...(latestState?.results || []), ...latestBackupResults]),
    completedCities: [
      ...latestCompletedCities,
      ...collectCompletedCitiesFromRunHistory(latestCityRunHistory, latestState),
      ...collectCompletedCitiesFromResults([...(latestState?.results || []), ...latestBackupResults], latestState),
      ...collectCurrentStateCompletedCities(latestState, manualKeywords[0])
    ]
  });

  await chrome.storage.local.set({
    gmh_country_input: stateEls.countryInput.value.trim(),
    gmh_city_input: stateEls.cityInput.value.trim(),
    gmh_city_batch_size_input: stateEls.cityBatchSizeInput.value.trim(),
    gmh_manual_skip_cities_input: stateEls.manualSkipCitiesInput.value.trim(),
    gmh_project_keyword_input: manualKeywords[0],
    gmh_keyword_input: stateEls.keywordInput.value.trim(),
    gmh_expand_keywords_input: stateEls.expandKeywordsInput.checked,
    gmh_skip_visited_input: stateEls.skipVisitedInput.checked,
    gmh_restart_cities_input: stateEls.restartCitiesInput.checked
  });

  const sent = await dispatchCommandToTab(tab.id, {
    type: "START_SCRAPE",
    payload: parsed
  });
  pendingStart = false;

  if (!sent?.ok) {
    renderTip(sent?.error || "无法连接到地图页面脚本，请刷新 Google Maps 页面后重试。");
    latestState = await getState();
    renderState(latestState);
    pendingStopRequested = false;
    return;
  }

  if (pendingStopRequested) {
    pendingStopRequested = false;
    await dispatchCommandToTab(tab.id, {
      type: "STOP_SCRAPE"
    });
    renderTip("停止指令已发送。");
  }
}

async function exportData(format) {
  const state = await getState();
  if (!state.results?.length) {
    renderTip("当前还没有可导出的数据。");
    return;
  }

  const response = await chrome.runtime.sendMessage({
    type: "EXPORT_DATA",
    format
  });

  if (!response?.ok) {
    renderTip(response?.error || "导出失败，请稍后重试。");
  }
}

async function dispatchCommandToTab(tabId, command) {
  try {
    await chrome.scripting.executeScript({
      target: { tabId },
      files: ["content.js"]
    });
    await wait(200);
    await chrome.tabs.sendMessage(tabId, command);
    return { ok: true };
  } catch (error) {
    return {
      ok: false,
      error: error?.message || "消息发送失败"
    };
  }
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function clearData() {
  await chrome.runtime.sendMessage({ type: "RESET_STATE" });
}

async function restoreLastResults() {
  const response = await chrome.runtime.sendMessage({ type: "RESTORE_LAST_RESULTS" });
  if (!response?.ok) {
    renderTip(response?.error || "没有可恢复的上次结果。");
    return;
  }
  latestState = response.state || await getState();
  renderState(latestState);
}

async function dedupeData() {
  const state = await getState();
  const deduped = dedupeResults(state.results || []);
  await chrome.runtime.sendMessage({
    type: "STATE_PATCH",
    patch: {
      results: deduped,
      detail: `去重完成，保留 ${deduped.length} 条结果。`,
      stats: {
        processed: deduped.length,
        total: deduped.length
      }
    }
  });
}

function handleStorageChange(changes, areaName) {
  if (areaName !== "local") {
    return;
  }
  if (changes.gmh_state) {
    latestState = changes.gmh_state.newValue;
    renderState(latestState);
    showCountryCompletionNotice(latestState);
  }
  if (changes.gmh_city_run_history) {
    latestCityRunHistory = changes.gmh_city_run_history.newValue || [];
    renderCityRunHistory(latestCityRunHistory);
  }
  if (changes.gmh_last_results_backup) {
    latestBackupResults = changes.gmh_last_results_backup.newValue?.state?.results || [];
  }
  if (changes.gmh_completed_cities) {
    latestCompletedCities = changes.gmh_completed_cities.newValue || [];
  }
  renderCityPlanPreview();
}

function renderState(state) {
  const safeState = state || getDefaultState();
  const isRunning = Boolean(safeState.running || pendingStart);
  const total = safeState.stats?.total || 0;
  const processed = safeState.stats?.processed || 0;
  const progress = total ? Math.min(100, Math.round((processed / total) * 100)) : 0;
  const currentKeyword = safeState.currentKeyword || "-";
  const plan = safeState.plan || {};
  const emailResults = (safeState.results || []).filter(hasValidEmail);
  const filteredResults = applyFilters(emailResults);

  stateEls.statusText.textContent = pendingStart ? "启动中" : (isRunning ? "运行中" : (safeState.status || "待命"));
  stateEls.progressText.textContent = `${processed} / ${total}`;
  stateEls.progressBar.style.width = `${progress}%`;
  stateEls.detailText.textContent = safeState.detail || "请先打开 Google Maps 页面，再启动插件。";
  stateEls.resultCount.textContent = String(emailResults.length);
  stateEls.completedCityCountText.textContent = String(countUniqueCompletedCities([
    ...latestCompletedCities,
    ...collectCompletedCitiesFromRunHistory(latestCityRunHistory, safeState),
    ...collectCompletedCitiesFromResults([...(safeState.results || []), ...latestBackupResults], safeState)
  ]));
  stateEls.plannedCountriesText.textContent = formatMetric(plan.plannedCountries);
  stateEls.remainingCountriesText.textContent = formatMetric(plan.remainingCountries);
  stateEls.plannedCitiesText.textContent = formatMetric(plan.plannedCities);
  stateEls.remainingCitiesText.textContent = formatMetric(plan.remainingCities);
  stateEls.countryText.textContent = plan.currentCountry || safeState.country || "-";
  stateEls.cityText.textContent = plan.currentCity || safeState.city || "-";
  stateEls.cityKeywordProgressText.textContent = formatCityKeywordProgress(plan);
  stateEls.keywordText.textContent = currentKeyword;
  stateEls.startBtn.textContent = isRunning ? "停止采集" : "开始采集";
  stateEls.filterSummary.textContent = `当前显示 ${filteredResults.length} / ${emailResults.length} 条结果。`;
  renderResults(filteredResults);
  renderTable(filteredResults);
}

function renderCityRunHistory(history) {
  const allRows = Array.isArray(history) ? history : [];
  const rows = allRows.slice(0, 3);
  if (!rows.length) {
    stateEls.cityRunHistory.innerHTML = `<div class="empty">最近三次跑过的城市会显示在这里。</div>`;
    return;
  }

  stateEls.cityRunHistory.innerHTML = rows
    .map((run) => {
      const projectKeyword = getRunProjectKeyword(run);
      const roundNumber = getProjectRunRoundNumber(allRows, run);
      const cities = (run.cities || []).map((item) => item.city).filter(Boolean);
      const summary = cities.length ? cities.join(" / ") : "暂无城市记录";
      return `
        <article class="result-card">
          <h3>第 ${roundNumber} 次：${escapeHtml(run.country || "-")} / ${escapeHtml(run.status || "running")}</h3>
          <div class="result-meta">
            <div>关键词：${escapeHtml(projectKeyword || "-")}</div>
            <div>城市数：${escapeHtml(String(cities.length || 0))}</div>
            <div>城市：${escapeHtml(shorten(summary, 180))}</div>
          </div>
        </article>
      `;
    })
    .join("");
}

function getRunProjectKeyword(run) {
  return String(run?.projectKeyword || run?.keyword || "").trim();
}

function getProjectRunRoundNumber(history, targetRun) {
  const targetProjectKey = makeProjectKeyPreview(getRunProjectKeyword(targetRun));
  if (!targetProjectKey) {
    return 1;
  }

  const matchingRuns = (history || [])
    .filter((run) => makeProjectKeyPreview(getRunProjectKeyword(run)) === targetProjectKey)
    .sort((left, right) => Number(left.startedAt || 0) - Number(right.startedAt || 0));
  const targetIndex = matchingRuns.findIndex((run) => run === targetRun || (run.runId && run.runId === targetRun.runId));
  return targetIndex >= 0 ? targetIndex + 1 : matchingRuns.length || 1;
}

function renderCityPlanPreview() {
  const countryInput = stateEls.countryInput.value.trim();
  const cityInput = stateEls.cityInput.value.trim();
  const batchSize = normalizeCityBatchSize(stateEls.cityBatchSizeInput.value.trim());
  const skipVisited = stateEls.skipVisitedInput.checked;
  const restartCities = stateEls.restartCitiesInput.checked;
  const previewKeywords = splitKeywords(stateEls.keywordInput.value.trim());
  const projectKeyword = previewKeywords[0] || "";
  const projectBlockedKeys = buildProjectBlockedCityKeySetPreview(previewKeywords);
  const market = findTargetMarketPreview(countryInput);
  const completedCities = [
    ...latestCompletedCities,
    ...collectCompletedCitiesFromRunHistory(latestCityRunHistory, latestState),
    ...collectCompletedCitiesFromResults([...(latestState?.results || []), ...latestBackupResults], latestState),
    ...collectCurrentStateCompletedCities(latestState, projectKeyword)
  ];
  const completedCount = restartCities ? 0 : countUniqueCompletedCities(completedCities, market?.countryLabel || countryInput, projectKeyword);

  stateEls.citySkipPreview.textContent = restartCities
    ? "已启用“从头跑”，本轮不会参考历史已采集城市。"
    : `当前已记录 ${completedCount} 个已采集城市；重启插件后也会继续跳过这些城市。`;

  if (cityInput) {
    const locationValidation = validateManualCityInput(countryInput, cityInput);
    if (!locationValidation.ok) {
      stateEls.cityPlanPreview.textContent = locationValidation.message;
      return;
    }
    const currentCityKey = makeLocationKeyPreview(
      market?.countryLabel || countryInput,
      cityInput
    );
    const currentCityOnlyKey = makeLocationKeyPreview("", cityInput);
    const currentCompletedCities = restartCities ? new Set() : buildCompletedCityKeySetPreview(
      completedCities,
      market?.countryLabel || countryInput,
      projectKeyword
    );
    if (skipVisited && (currentCompletedCities.has(currentCityKey) || currentCompletedCities.has(currentCityOnlyKey))) {
      stateEls.cityPlanPreview.textContent = `已手动指定城市 ${cityInput}，该城市已在历史记录中出现过；本轮会自动跳过。`;
      return;
    }
    stateEls.cityPlanPreview.textContent = `已手动指定城市 ${cityInput}，本轮将只跑这个城市。`;
    return;
  }
  const manualSkipKeys = buildManualSkipCityKeySet(stateEls.manualSkipCitiesInput.value.trim(), market?.countryLabel || "");
  if (!market) {
    stateEls.cityPlanPreview.textContent = countryInput
      ? "当前国家可手动搜索；清空城市时不会使用自动城市轮询。"
      : "留空国家时会按预设国家自动轮询，当前预览仅对单个预设国家显示。";
    return;
  }

  const completedKeys = restartCities ? new Set() : buildCompletedCityKeySetPreview(
    completedCities,
    market.countryLabel,
    projectKeyword
  );
  const skipped = [];
  const runnable = [];

  for (const cityName of market.cities) {
    const key = makeLocationKeyPreview(market.countryLabel, cityName);
    const cityOnlyKey = makeLocationKeyPreview("", cityName);
    if (manualSkipKeys.has(key) || projectBlockedKeys.has(key) || (skipVisited && (completedKeys.has(key) || completedKeys.has(cityOnlyKey)))) {
      skipped.push(cityName);
      continue;
    }
    runnable.push(cityName);
  }

  const selected = runnable.slice(0, batchSize || 10);
  const skippedText = skipped.length ? skipped.slice(0, 12).join(" / ") : "无";
  const selectedText = selected.length ? selected.join(" / ") : "无可执行城市";
  stateEls.cityPlanPreview.textContent = `本轮预计跑 ${selected.length} 个城市：${selectedText}。预计跳过 ${skipped.length} 个城市：${skippedText}${skipped.length > 12 ? " ..." : ""}`;
  if (!restartCities && skipped.length) {
    stateEls.citySkipPreview.textContent = `已采集城市 ${completedCount} 个。本轮将跳过这些城市中的 ${skipped.length} 个：${skippedText}${skipped.length > 12 ? " ..." : ""}`;
  }
}

function renderResults(results) {
  if (!results.length) {
    stateEls.resultsList.innerHTML = `<div class="empty">采集结果会实时显示在这里。</div>`;
    return;
  }

  const recent = [...results].slice(-8).reverse();
  stateEls.resultsList.innerHTML = recent
    .map((item) => {
      const website = item.website
        ? `<div>官网：<a href="${escapeAttribute(item.website)}" target="_blank">${escapeHtml(item.website)}</a></div>`
        : "<div>官网：-</div>";
      const social = item.socialLinks?.length
        ? `<div>社媒：${item.socialLinks.map((link) => `<a href="${escapeAttribute(link)}" target="_blank">${escapeHtml(new URL(link).hostname)}</a>`).join(" / ")}</div>`
        : "<div>社媒：-</div>";
      return `
        <article class="result-card">
          <h3>${escapeHtml(item.companyName || "未命名商家")}</h3>
          <div class="result-meta">
            <div>电话：${escapeHtml(item.phone || "-")}</div>
            <div>邮箱：${escapeHtml(item.email || "-")}</div>
            <div>国家 / 城市：${escapeHtml(item.country || "-")} / ${escapeHtml(item.city || "-")}</div>
            <div>关键词：${escapeHtml(item.keyword || "-")}</div>
            <div>来源：${escapeHtml(item.source || "-")}</div>
            ${website}
            ${social}
          </div>
        </article>
      `;
    })
    .join("");
}

function renderTable(results) {
  if (!results.length) {
    stateEls.resultsTableBody.innerHTML = `<tr><td colspan="10" class="empty">当前筛选条件下暂无结果。</td></tr>`;
    return;
  }

  stateEls.resultsTableBody.innerHTML = results
    .slice()
    .reverse()
    .map((item) => `
      <tr>
        <td>${escapeHtml(item.companyName || "-")}</td>
        <td>${escapeHtml(item.phone || "-")}</td>
        <td>${escapeHtml(item.email || "-")}</td>
        <td>${item.website ? `<a href="${escapeAttribute(item.website)}" target="_blank">${escapeHtml(shorten(item.website, 40))}</a>` : "-"}</td>
        <td>${escapeHtml(item.country || "-")}</td>
        <td>${escapeHtml(item.city || "-")}</td>
        <td>${escapeHtml(item.keyword || "-")}</td>
        <td>${escapeHtml(item.businessIntroduction || "-")}</td>
        <td>${escapeHtml((item.socialLinks || []).join(" | ") || "-")}</td>
        <td>${escapeHtml(item.rating || "-")}</td>
      </tr>
    `)
    .join("");
}

function renderTip(text) {
  stateEls.detailText.textContent = text;
}

function showLocationInputWarning(message) {
  renderTip(message);
  window.alert(message);
}

function showCountryCompletionNotice(state) {
  const notice = state?.countryCompletionNotice;
  if (!notice?.id || notice.id === lastCountryCompletionNoticeId) {
    return;
  }
  lastCountryCompletionNoticeId = notice.id;
  renderTip(notice.message);
  window.alert(notice.message);
}

function applyFilters(results) {
  const textFilter = stateEls.filterInput.value.trim().toLowerCase();
  const sourceFilter = stateEls.sourceFilter.value.trim();

  return results.filter((item) => {
    const haystack = [
      item.companyName,
      item.phone,
      item.email,
      item.city,
      item.country,
      item.keyword,
      item.businessIntroduction,
      item.source,
      item.website,
      item.address
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();

    const textMatched = !textFilter || haystack.includes(textFilter);
    const sourceMatched = !sourceFilter || String(item.source || "").includes(sourceFilter);
    return textMatched && sourceMatched;
  });
}

function hasValidEmail(item) {
  return Boolean(validateAndCleanEmail(item?.email || ""));
}

function dedupeResults(results) {
  const merged = new Map();
  for (const item of results) {
    const key = findExistingDedupKey(merged, item) || buildDedupKey(item);
    if (!merged.has(key)) {
      merged.set(key, { ...item });
      continue;
    }

    const current = merged.get(key);
    merged.set(key, {
      ...current,
      companyName: pickCanonicalCompanyName(current, item),
      phone: pickLonger(current.phone, item.phone),
      email: pickLonger(current.email, item.email),
      address: pickLonger(current.address, item.address),
      website: pickLonger(current.website, item.website),
      city: pickLonger(current.city, item.city),
      country: pickLonger(current.country, item.country),
      keyword: mergeTextValues(current.keyword, item.keyword),
      businessIntroduction: pickLonger(current.businessIntroduction, item.businessIntroduction),
      source: mergeTextValues(current.source, item.source),
      socialLinks: normalizeSocialLinks([...(current.socialLinks || []), ...(item.socialLinks || [])]),
      rating: pickLonger(current.rating, item.rating),
      hours: pickLonger(current.hours, item.hours),
      category: pickLonger(current.category, item.category),
      contactPerson: pickLonger(current.contactPerson, item.contactPerson),
      procurementInfo: mergeTextValues(current.procurementInfo, item.procurementInfo)
    });
  }
  return Array.from(merged.values());
}

function buildDedupKey(item) {
  return buildDedupIdentityKeys(item)[0] || "";
}

function findExistingDedupKey(merged, item) {
  const candidateKeys = new Set(buildDedupIdentityKeys(item));
  for (const [key, current] of merged.entries()) {
    const currentKeys = buildDedupIdentityKeys(current);
    if (currentKeys.some((currentKey) => candidateKeys.has(currentKey))) {
      return key;
    }
  }
  return "";
}

function buildDedupIdentityKeys(item) {
  const keys = [];
  const websiteHost = normalizeWebsiteHost(item.website || "");
  if (websiteHost) {
    keys.push(`website:${websiteHost}`);
  }

  const email = validateAndCleanEmail(item.email || "");
  if (email) {
    keys.push(`email:${email}`);
  }

  const phone = normalizePhone(item.phone || "");
  if (phone) {
    keys.push(`phone:${phone}`);
  }

  const normalizedName = normalizeCompanyName(item.companyName || "");
  const normalizedAddress = normalizeTextFingerprint(item.address || "");
  const normalizedCity = normalizeTextFingerprint(item.city || "");
  if (normalizedName && normalizedAddress) {
    keys.push(`name-address:${normalizedName}|${normalizedAddress}`);
  }
  if (normalizedName && normalizedCity) {
    keys.push(`name-city:${normalizedName}|${normalizedCity}`);
  }
  if (normalizedName) {
    keys.push(`name:${normalizedName}`);
  }

  return uniqueValues(keys);
}

function pickCanonicalCompanyName(current, incoming) {
  const incomingSources = String(incoming.source || "");
  if (incomingSources.includes("官网") && incoming.companyName) {
    return incoming.companyName;
  }
  if (String(current.source || "").includes("官网") && current.companyName) {
    return current.companyName;
  }
  return pickLonger(current.companyName, incoming.companyName);
}

function normalizeUrl(value) {
  try {
    const url = new URL(value);
    return `${url.hostname}${url.pathname}`.replace(/\/+$/, "").toLowerCase();
  } catch (error) {
    return String(value || "").trim().toLowerCase();
  }
}

function mergeTextValues(a, b) {
  return uniqueValues([a, b].filter(Boolean)).join(" / ");
}

function pickLonger(a, b) {
  return String(b || "").length > String(a || "").length ? (b || "") : (a || "");
}

function uniqueValues(list) {
  return Array.from(new Set((list || []).filter(Boolean)));
}

function normalizeSocialLinks(links) {
  const bestByPlatform = new Map();
  for (const rawLink of uniqueValues(links || [])) {
    const normalized = normalizeSocialLink(rawLink);
    if (!normalized) {
      continue;
    }
    const platform = inferSocialPlatform(normalized);
    const current = bestByPlatform.get(platform);
    if (!current || scoreSocialLink(normalized) > scoreSocialLink(current)) {
      bestByPlatform.set(platform, normalized);
    }
  }
  return Array.from(bestByPlatform.values());
}

function normalizeSocialLink(link) {
  try {
    const url = new URL(link);
    const hostname = url.hostname.replace(/^www\./i, "").toLowerCase();
    const pathname = url.pathname.replace(/\/+/g, "/").replace(/\/$/, "");
    const lowerPath = pathname.toLowerCase();
    if (!pathname || !(hostname.includes("facebook.com") || hostname.includes("instagram.com") || hostname.includes("linkedin.com"))) {
      return "";
    }
    if (/(^|\/)(login|recover|checkpoint|share|sharer|dialog|plugins|privacy|policies|help|watch|reel|reels|stories|hashtag|explore|intent|search|accounts|oauth|signup)(\/|$)/i.test(lowerPath)) {
      return "";
    }
    if (hostname.includes("facebook.com")) {
      const match = pathname.match(/^\/(?:pages\/)?([^/?#]+)(?:\/about)?$/i);
      return match?.[1] ? `https://www.facebook.com/${match[1]}` : "";
    }
    if (hostname.includes("instagram.com")) {
      const match = pathname.match(/^\/([^/?#]+)$/i);
      return match?.[1] && !/^(p|reel|stories|explore)$/i.test(match[1]) ? `https://www.instagram.com/${match[1]}` : "";
    }
    if (hostname.includes("linkedin.com")) {
      const match = pathname.match(/^\/(company|in)\/([^/?#]+)/i);
      return match?.[1] && match?.[2] ? `https://www.linkedin.com/${match[1]}/${match[2]}` : "";
    }
    return "";
  } catch (error) {
    return "";
  }
}

function inferSocialPlatform(url) {
  if (url.includes("facebook.com")) {
    return "Facebook";
  }
  if (url.includes("instagram.com")) {
    return "Instagram";
  }
  if (url.includes("linkedin.com")) {
    return "LinkedIn";
  }
  return "社媒";
}

function scoreSocialLink(link) {
  const value = String(link || "").toLowerCase();
  let score = 0;
  if (/\/(company|in)\//.test(value)) {
    score += 4;
  }
  if (/\/pages\//.test(value)) {
    score += 3;
  }
  if (/facebook\.com\/[^/]+$/.test(value) || /instagram\.com\/[^/]+$/.test(value) || /linkedin\.com\/company\//.test(value)) {
    score += 5;
  }
  return score - value.length / 1000;
}

function shorten(text, maxLength) {
  const value = String(text || "");
  return value.length > maxLength ? `${value.slice(0, maxLength - 3)}...` : value;
}

function parseInputs({ country, city, cityBatchSize, manualSkipCities, projectKeyword, keywords, skipVisitedCities, restartCities, seedResults, existingKeywordRecords, completedCities }) {
  return {
    country: String(country || "").trim(),
    city: String(city || "").trim(),
    cityBatchSize: normalizeCityBatchSize(cityBatchSize),
    manualSkipCities: splitManualSkipCities(manualSkipCities),
    projectKeyword: String(projectKeyword || "").trim(),
    keywords: splitKeywords(keywords),
    skipVisitedCities: Boolean(skipVisitedCities),
    restartCities: Boolean(restartCities),
    seedResults: Array.isArray(seedResults) ? seedResults : [],
    existingKeywordRecords: Array.isArray(existingKeywordRecords) ? existingKeywordRecords : [],
    completedCities: Array.isArray(completedCities) ? completedCities : []
  };
}

function normalizeCityBatchSize(value) {
  const normalized = Number.parseInt(String(value || "").trim(), 10);
  return Number.isFinite(normalized) && normalized > 0 ? normalized : 10;
}

function splitManualSkipCities(value) {
  return String(value || "")
    .split(/[,\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function collectExistingKeywordRecords(results) {
  return (results || [])
    .map((item) => ({
      country: String(item.country || "").trim(),
      city: String(item.city || "").trim(),
      keyword: String(item.keyword || "").trim()
    }))
    .filter((item) => item.country || item.city || item.keyword);
}

function collectCompletedCitiesFromResults(results, state = null) {
  const seen = new Set();
  const cities = [];
  const incompleteCityKey = getIncompleteCurrentCityKey(state);
  const stateProjectKeyword = String(state?.projectKeyword || "").trim();
  for (const item of (results || [])) {
    const key = makeLocationKeyPreview(item.country || "", item.city || "");
    if (!key || key === incompleteCityKey || seen.has(key)) {
      continue;
    }
    seen.add(key);
    cities.push({
      country: String(item.country || "").trim(),
      city: String(item.city || "").trim(),
      projectKeyword: String(item.projectKeyword || stateProjectKeyword).trim(),
      completedAt: Date.now()
    });
  }
  return cities;
}

function collectCompletedCitiesFromRunHistory(history, state = null) {
  const seen = new Set();
  const cities = [];
  const incompleteCityKey = getIncompleteCurrentCityKey(state);
  for (const run of (history || [])) {
    const runStatus = String(run?.status || "").toLowerCase();
    if (!runStatus || runStatus === "running") {
      continue;
    }
    for (const item of (run.cities || [])) {
      const key = makeLocationKeyPreview(item.country || run.country || "", item.city || "");
      if (!key || key === incompleteCityKey || seen.has(key)) {
        continue;
      }
      seen.add(key);
      cities.push({
        country: String(item.country || run.country || "").trim(),
        city: String(item.city || "").trim(),
        projectKeyword: String(item.projectKeyword || run.projectKeyword || run.keyword || "").trim(),
        completedAt: item.recordedAt || run.finishedAt || run.startedAt || Date.now()
      });
    }
  }
  return cities;
}

function getIncompleteCurrentCityKey(state) {
  const plan = state?.plan || {};
  const done = Number(plan.currentCityKeywordDone || 0);
  const total = Number(plan.currentCityKeywordTotal || 0);
  if (!plan.currentCountry || !plan.currentCity || !total || done >= total) {
    return "";
  }
  return makeLocationKeyPreview(plan.currentCountry, plan.currentCity);
}

function countUniqueCompletedCities(completedCities, country = "", projectKeyword = "") {
  return buildCompletedCityKeySetPreview(completedCities, country, projectKeyword).size;
}

function collectSeedResultsForRun({ results, country, city }) {
  const rows = Array.isArray(results) ? results : [];
  const countryKey = normalizeCountryKeyPreview(country);
  const cityKey = normalizeNamePreview(city);
  if (!countryKey && !cityKey) {
    return dedupeResults(rows);
  }
  return dedupeResults(rows.filter((item) => {
    const itemCountryKey = normalizeCountryKeyPreview(item.country || "");
    const itemCityKey = normalizeNamePreview(item.city || "");
    if (cityKey && itemCityKey !== cityKey) {
      return false;
    }
    if (countryKey && itemCountryKey !== countryKey) {
      return false;
    }
    return true;
  }));
}

function collectCurrentStateCompletedCities(state, projectKeyword = "") {
  const plan = state?.plan || {};
  const done = Number(plan.currentCityKeywordDone || 0);
  const total = Number(plan.currentCityKeywordTotal || 0);
  if (!plan.currentCountry || !plan.currentCity || !total || done < total) {
    return [];
  }
  return [{
    country: plan.currentCountry,
    city: plan.currentCity,
    projectKeyword
  }];
}

function findTargetMarketPreview(countryInput) {
  const normalized = String(countryInput || "").trim().toLowerCase();
  if (!normalized) {
    return null;
  }
  return TARGET_MARKETS.find((market) => market.aliases.some((alias) => alias.toLowerCase() === normalized)) || null;
}

function validateManualCityInput(countryInput, cityInput) {
  const parsedCity = splitLocationInputPreview(cityInput);
  const countryName = String(countryInput || parsedCity.country || parsedCity.rawCountry || "").trim();
  if (countryName && !isRecognizedCountryNamePreview(countryName)) {
    return {
      ok: false,
      field: "country",
      message: `国家 “${countryName}” 无法识别，请检查拼写。比如日本请填写 Japan 或 日本。`
    };
  }

  const cityName = parsedCity.city || String(cityInput || "").trim();
  if (cityName && !isPlausibleCityNamePreview(cityName)) {
    return {
      ok: false,
      field: "city",
      message: `城市 “${cityName}” 无法识别，请检查拼写或删除数字、网址、特殊符号。`
    };
  }

  return { ok: true };
}

function isPlausibleCityNamePreview(value) {
  const normalized = String(value || "").trim();
  if (!normalized) {
    return true;
  }
  return /\p{L}/u.test(normalized)
    && /^[\p{L}\p{M}\s.'’(),-]+$/u.test(normalized);
}

function isRecognizedCountryNamePreview(value) {
  const normalized = normalizeNamePreview(value);
  if (!normalized) {
    return false;
  }
  if (normalizeCountryNamePreview(value)) {
    return true;
  }
  return Object.values(COUNTRY_ALIASES).some((country) => normalizeNamePreview(country) === normalized)
    || TARGET_MARKETS.some((market) => {
      if (normalizeNamePreview(market.countryLabel) === normalized) {
        return true;
      }
      return market.aliases.some((alias) => normalizeNamePreview(alias) === normalized);
    });
}

function splitLocationInputPreview(rawValue) {
  const normalized = String(rawValue || "").trim().replace(/\s+/g, " ");
  if (!normalized) {
    return { city: "", country: "", rawCountry: "" };
  }

  const parts = normalized.split(",").map((item) => item.trim()).filter(Boolean);
  if (parts.length < 2) {
    return { city: normalized, country: "", rawCountry: "" };
  }

  const rawCountry = parts[parts.length - 1];
  const country = normalizeCountryNamePreview(rawCountry);
  if (!country) {
    return { city: parts.slice(0, -1).join(", "), country: "", rawCountry };
  }

  return {
    city: parts.slice(0, -1).join(", "),
    country,
    rawCountry
  };
}

function buildCompletedCityKeySetPreview(completedCities, country, projectKeyword = "") {
  const normalizedCountry = normalizeCountryKeyPreview(country);
  const normalizedProjectKey = makeProjectKeyPreview(projectKeyword);
  const set = new Set();
  for (const item of completedCities || []) {
    const itemProjectKey = makeProjectKeyPreview(item.projectKeyword || item.keyword || "");
    if (normalizedProjectKey && itemProjectKey !== normalizedProjectKey) {
      continue;
    }
    const itemCountryKey = normalizeCountryKeyPreview(item.country);
    if (normalizedCountry && itemCountryKey && itemCountryKey !== normalizedCountry) {
      continue;
    }
    const key = makeLocationKeyPreview(item.country, item.city);
    if (key) {
      set.add(key);
    }
    const cityOnlyKey = makeLocationKeyPreview("", item.city);
    if (cityOnlyKey) {
      set.add(cityOnlyKey);
    }
  }
  return set;
}

function buildManualSkipCityKeySet(value, countryLabel) {
  const set = new Set();
  for (const city of splitManualSkipCities(value)) {
    const key = makeLocationKeyPreview(countryLabel, city);
    if (key) {
      set.add(key);
    }
  }
  return set;
}

function buildProjectBlockedCityKeySetPreview(keywords) {
  const normalizedKeywords = new Set((keywords || []).map((keyword) => normalizeNamePreview(keyword)).filter(Boolean));
  const set = new Set();
  for (const rule of PROJECT_CITY_BLOCKLIST) {
    const ruleKeywords = Array.isArray(rule.keywords) ? rule.keywords : [];
    const matchesProject = !ruleKeywords.length
      || ruleKeywords.some((keyword) => normalizedKeywords.has(normalizeNamePreview(keyword)));
    if (!matchesProject) {
      continue;
    }
    for (const city of rule.cities || []) {
      const key = makeLocationKeyPreview(rule.country, city);
      if (key) {
        set.add(key);
      }
    }
  }
  return set;
}

function makeLocationKeyPreview(country, city) {
  const normalizedCountry = normalizeCountryKeyPreview(country);
  const normalizedCity = normalizeNamePreview(city);
  if (!normalizedCountry && !normalizedCity) {
    return "";
  }
  return `${normalizedCountry}|${normalizedCity}`;
}

function normalizeCountryKeyPreview(value) {
  const normalizedAlias = normalizeCountryNamePreview(value);
  if (normalizedAlias) {
    return normalizeNamePreview(normalizedAlias);
  }
  return normalizeNamePreview(value);
}

function normalizeCountryNamePreview(value) {
  const normalized = String(value || "").trim().toLowerCase();
  return COUNTRY_ALIASES[normalized] || "";
}

function normalizeNamePreview(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim();
}

function makeProjectKeyPreview(keyword) {
  return normalizeNamePreview(keyword);
}

function splitKeywords(raw) {
  const keywords = String(raw || "")
    .split(/[,\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
  if (keywords.length) {
    return keywords;
  }
  return [];
}

async function expandKeywordVariants(seedKeyword) {
  try {
    const response = await chrome.runtime.sendMessage({
      type: "GENERATE_KEYWORD_VARIANTS",
      payload: {
        keyword: seedKeyword
      }
    });
    return response?.ok ? uniqueValues((response.result || []).map((item) => String(item || "").trim()).filter(Boolean)) : [seedKeyword];
  } catch (error) {
    return [seedKeyword];
  }
}

function isMapsUrl(url) {
  return /^https:\/\/(www\.)?google\.[^/]+\/maps/i.test(url || "") || /^https:\/\/maps\.google\.[^/]+/i.test(url || "");
}

function getDefaultState() {
  return {
    running: false,
    status: "待命",
    detail: "请先打开 Google Maps 页面，再启动插件。",
    country: "",
    city: "",
    currentKeyword: "",
    countryCompletionNotice: null,
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
}

function formatMetric(value) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return String(value);
}

function formatCityKeywordProgress(plan) {
  const done = Number(plan?.currentCityKeywordDone || 0);
  const total = Number(plan?.currentCityKeywordTotal || 0);
  if (!total) {
    return "-";
  }
  return `${done} / ${total}`;
}

async function getState() {
  return getStorageValue("gmh_state", getDefaultState());
}

async function getBackupResults() {
  const backup = await getStorageValue("gmh_last_results_backup", null);
  return backup?.state?.results || [];
}

async function getStorageValue(key, fallbackValue) {
  const result = await chrome.storage.local.get(key);
  return result[key] ?? fallbackValue;
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function escapeAttribute(value) {
  return escapeHtml(value);
}

function normalizeWebsiteHost(value) {
  try {
    return new URL(value).hostname.replace(/^www\./i, "").toLowerCase();
  } catch (error) {
    return String(value || "").trim().toLowerCase().replace(/^https?:\/\//i, "").replace(/^www\./i, "").split("/")[0];
  }
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

function normalizePhone(value) {
  return String(value || "").replace(/\D/g, "");
}

function normalizeTextFingerprint(value) {
  return String(value || "").trim().toLowerCase().replace(/[^\p{L}\p{N}]+/gu, "");
}

function normalizeCompanyName(value) {
  return normalizeTextFingerprint(String(value || "").replace(/\b(inc|llc|ltd|limited|co|company|corp|corporation|gmbh|pty|plc)\b/ig, ""));
}
