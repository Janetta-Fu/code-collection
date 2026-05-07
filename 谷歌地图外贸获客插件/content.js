const DEFAULT_KEYWORDS = [
  "Restaurant",
  "Coffee Shop",
  "Hotel",
  "Gym"
];

const SOCIAL_HOSTS = ["facebook.com", "instagram.com", "linkedin.com"];
const CONTACT_LINK_WORDS = ["contact", "contact us", "about", "about us", "service", "services", "wholesale", "procurement", "purchasing"];
const CATEGORY_MAP = [
  { label: "Category A", patterns: ["pattern1", "pattern2"] },
  { label: "Category B", patterns: ["pattern3", "pattern4"] }
];
const BUSINESS_INTRO_FALLBACK = "Core business summary: [Summary of business]. Key points for outreach: [Point 1, Point 2].";
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
  "new zealand": "新西兰",
  singapore: "新加坡",
  malaysia: "马来西亚",
  thailand: "泰国",
  vietnam: "越南",
  indonesia: "印度尼西亚",
  philippines: "菲律宾",
  india: "印度",
  pakistan: "巴基斯坦",
  bangladesh: "孟加拉国",
  china: "中国",
  "hong kong": "中国香港",
  taiwan: "中国台湾",
  japan: "日本",
  korea: "韩国",
  "south korea": "韩国",
  "united arab emirates": "阿联酋",
  uae: "阿联酋",
  "saudi arabia": "沙特阿拉伯",
  "south africa": "南非"
};
const TARGET_MARKETS = [
  {
    countryLabel: "美国",
    searchCountry: "United States",
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
    searchCountry: "Canada",
    aliases: ["加拿大", "canada"],
    cities: ["Toronto", "Montreal", "Vancouver", "Calgary", "Edmonton", "Ottawa", "Winnipeg", "Quebec City", "Hamilton", "Kitchener"]
  },
  {
    countryLabel: "英国",
    searchCountry: "United Kingdom",
    aliases: ["英国", "uk", "u.k.", "united kingdom", "england"],
    cities: ["London", "Birmingham", "Manchester", "Glasgow", "Liverpool", "Leeds", "Bristol", "Sheffield", "Edinburgh", "Leicester"]
  },
  {
    countryLabel: "法国",
    searchCountry: "France",
    aliases: ["法国", "france", "french", "frensh"],
    cities: ["Paris", "Marseille", "Lyon", "Toulouse", "Nice", "Nantes", "Montpellier", "Strasbourg", "Bordeaux", "Lille"]
  },
  {
    countryLabel: "澳大利亚",
    searchCountry: "Australia",
    aliases: ["澳大利亚", "australia"],
    cities: ["Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide", "Gold Coast", "Canberra", "Newcastle", "Wollongong", "Geelong"]
  },
  {
    countryLabel: "阿联酋",
    searchCountry: "United Arab Emirates",
    aliases: ["阿联酋", "uae", "united arab emirates"],
    cities: ["Dubai", "Abu Dhabi", "Sharjah", "Ajman", "Ras Al Khaimah", "Fujairah", "Al Ain", "Umm Al Quwain", "Khor Fakkan", "Dibba Al Fujairah"]
  },
  {
    countryLabel: "沙特阿拉伯",
    searchCountry: "Saudi Arabia",
    aliases: ["沙特阿拉伯", "saudi arabia"],
    cities: ["Riyadh", "Jeddah", "Mecca", "Medina", "Dammam", "Khobar", "Tabuk", "Abha", "Taif", "Jubail"]
  },
  {
    countryLabel: "新西兰",
    searchCountry: "New Zealand",
    aliases: ["新西兰", "new zealand"],
    cities: ["Auckland", "Wellington", "Christchurch", "Hamilton", "Tauranga", "Dunedin", "Palmerston North", "Napier", "Nelson", "Rotorua"]
  },
  {
    countryLabel: "南非",
    searchCountry: "South Africa",
    aliases: ["南非", "south africa"],
    cities: ["Johannesburg", "Cape Town", "Durban", "Pretoria", "Port Elizabeth", "Bloemfontein", "East London", "Nelspruit", "Polokwane", "Pietermaritzburg"]
  },
  {
    countryLabel: "日本",
    searchCountry: "Japan",
    aliases: ["日本", "japan"],
    cities: ["Tokyo", "Yokohama", "Osaka", "Nagoya", "Sapporo", "Fukuoka", "Kobe", "Kyoto", "Kawasaki", "Saitama"]
  },
  {
    countryLabel: "新加坡",
    searchCountry: "Singapore",
    aliases: ["新加坡", "singapore"],
    cities: ["Singapore"]
  },
  {
    countryLabel: "马来西亚",
    searchCountry: "Malaysia",
    aliases: ["马来西亚", "malaysia"],
    cities: ["Kuala Lumpur", "Johor Bahru", "George Town", "Ipoh", "Shah Alam", "Petaling Jaya", "Kota Kinabalu", "Kuching", "Malacca City", "Penang"]
  }
];

const runtimeState = {
  stopRequested: false,
  running: false,
  lastCommandIssuedAt: 0
};
const PROCESSED_COMMAND_KEY = "__GMH_PROCESSED_COMMAND_AT__";

setupCommandBridge();

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === "EXTRACT_PAGE_CONTACTS") {
    extractCurrentPageContacts(message.payload)
      .then((result) => sendResponse(result))
      .catch((error) => sendResponse({ source: message.payload?.sourceLabel || "页面", notes: error.message }));
    return true;
  }

  if (message?.type === "START_SCRAPE") {
    startScrape(message.payload)
      .catch(async (error) => {
        await patchState({ running: false, status: "异常停止", detail: error.message });
      });
    sendResponse({ ok: true });
    return false;
  }

  if (message?.type === "STOP_SCRAPE") {
    runtimeState.stopRequested = true;
    patchState({ running: false, status: "已停止", detail: "用户手动停止了当前任务。" })
      .then(() => sendResponse({ ok: true }))
      .catch((error) => sendResponse({ ok: false, error: error.message }));
    return true;
  }
});

async function startScrape(payload) {
  if (!isGoogleMapsPage()) {
    throw new Error("当前页面不是 Google Maps，无法启动采集。");
  }

  if (runtimeState.running) {
    throw new Error("采集任务已在运行中。");
  }

  const country = sanitizeText(payload?.country || "");
  const city = sanitizeText(payload?.city || "");
  const restartCities = Boolean(payload?.restartCities);
  const keywords = (Array.isArray(payload?.keywords) ? payload.keywords : []).map((item) => item.trim()).filter(Boolean);
  if (!keywords.length) {
    throw new Error("请至少提供一个关键词。");
  }
  const projectKeyword = sanitizeText(payload?.projectKeyword || keywords[0] || "");
  const currentState = (await chrome.storage.local.get("gmh_state")).gmh_state || {};
  const resumeProgress = !restartCities ? getResumeCityProgress(currentState, { country, city, keywords }) : null;
  const seedResults = !restartCities && Array.isArray(payload?.seedResults)
    ? dedupeLeadRecords(payload.seedResults)
    : [];
  const scrapePlan = buildScrapePlan({
    country,
    city,
    cityBatchSize: Number(payload?.cityBatchSize || 0),
    manualSkipCities: Array.isArray(payload?.manualSkipCities) ? payload.manualSkipCities : [],
    projectKeyword,
    keywords,
    skipVisitedCities: Boolean(payload?.skipVisitedCities),
    restartCities,
    resumeProgress,
    existingKeywordRecords: Array.isArray(payload?.existingKeywordRecords) ? payload.existingKeywordRecords : [],
    completedCities: Array.isArray(payload?.completedCities) ? payload.completedCities : []
  });
  const runId = `run_${Date.now()}`;

  if (!restartCities && currentState.results?.length) {
    await chrome.runtime.sendMessage({
      type: "ARCHIVE_CURRENT_RESULTS",
      payload: {
        reason: "pre_run",
        keyword: keywords[0] || "",
        country,
        city
      }
    }).catch(() => undefined);
  }

  runtimeState.running = true;
  runtimeState.stopRequested = false;

  await patchState({
    running: true,
    status: "运行中",
    detail: seedResults.length
      ? `正在继续已有采集结果，已继承 ${seedResults.length} 条数据${resumeProgress ? "，并从未完成关键词继续" : ""}。`
      : (restartCities ? "正在从头启动新一轮城市采集。" : "正在初始化 Google Maps 页面。"),
    country,
    city,
    projectKeyword,
    currentKeyword: "",
    results: seedResults,
    startedAt: Date.now(),
      plan: {
        plannedCountries: scrapePlan.plannedCountries,
        remainingCountries: scrapePlan.plannedCountries,
        plannedCities: scrapePlan.targets.length,
        remainingCities: scrapePlan.targets.length,
        currentCountry: "",
        currentCity: "",
        currentCityKeywordDone: 0,
        currentCityKeywordTotal: 0,
        skippedCities: scrapePlan.skippedCities,
        mode: scrapePlan.mode
      },
    stats: { processed: 0, total: scrapePlan.totalTasks }
  });

  try {
    await waitForMapShell();
    let allResults = [...seedResults];
    let completedTasks = 0;

    for (let targetIndex = 0; targetIndex < scrapePlan.targets.length; targetIndex += 1) {
      ensureNotStopped();
      const target = scrapePlan.targets[targetIndex];
      await chrome.runtime.sendMessage({
        type: "REGISTER_CITY_RUN",
        payload: {
          runId,
          startedAt: Date.now(),
          country: target.countryLabel || country,
          city: target.cityLabel || city,
          projectKeyword,
          keyword: keywords[0] || ""
        }
      }).catch(() => undefined);
      await patchState({
        running: true,
        status: "运行中",
        country: target.countryLabel || country,
        city: target.cityLabel || city,
        detail: `已切换到 ${formatTargetLabel(target)}，准备执行关键词采集。`,
        plan: getPlanProgress(scrapePlan, targetIndex, target, { currentCityKeywordDone: 0 })
      });

      const targetKeywords = target.keywords?.length ? target.keywords : keywords;
      for (let keywordIndex = 0; keywordIndex < targetKeywords.length; keywordIndex += 1) {
        const keyword = targetKeywords[keywordIndex];
        try {
          ensureNotStopped();
          await patchState({
            running: true,
            status: "运行中",
            currentKeyword: keyword,
            detail: `正在搜索：${keyword} / ${formatTargetLabel(target)}`,
            plan: getPlanProgress(scrapePlan, targetIndex, target, { currentCityKeywordDone: keywordIndex })
          });

          const hasResults = await runSearch(buildSearchQuery(keyword, target));
          if (hasResults) {
            await autoScrollFeed();
          }
          const cards = hasResults ? collectResultCards() : [];

          await patchState({
            detail: cards.length
              ? `已载入 ${cards.length} 家候选商家，开始逐条采集。`
              : `${formatTargetLabel(target)} 暂未发现候选商家，准备切换下一个任务。`,
            plan: getPlanProgress(scrapePlan, targetIndex, target, { currentCityKeywordDone: keywordIndex })
          });

          for (let index = 0; index < cards.length; index += 1) {
            ensureNotStopped();
            const card = cards[index];
            const cardRecord = extractLeadFromCard(card.element);
            let baseRecord = { ...cardRecord };

            try {
              await openCard(
                card.element,
                allResults[allResults.length - 1]?.companyName || "",
                cardRecord.companyName || ""
              );
              await sleep(1200);
              const detailRecord = await extractBusinessFromMap();
              baseRecord = mergeLead(cardRecord, detailRecord, "地图");
            } catch (error) {
              await patchState({
                detail: `商家详情页加载超时，已使用列表信息：${cardRecord.companyName || `第 ${index + 1} 条`}`,
                plan: getPlanProgress(scrapePlan, targetIndex, target, { currentCityKeywordDone: keywordIndex })
              });
            }

            if (!baseRecord.companyName) {
              await patchState({
                detail: `第 ${index + 1} 条商家信息不完整，已跳过。`,
                plan: getPlanProgress(scrapePlan, targetIndex, target, { currentCityKeywordDone: keywordIndex })
              });
              continue;
            }

            if (!matchesTargetLocation(baseRecord, target)) {
              await patchState({
                detail: `${baseRecord.companyName} 的地址不属于 ${formatTargetLabel(target)}，已跳过。`,
                plan: getPlanProgress(scrapePlan, targetIndex, target, { currentCityKeywordDone: keywordIndex })
              });
              continue;
            }

            let enriched = {
              ...baseRecord,
              city: target.cityLabel || "",
              country: target.countryLabel || "",
              keyword,
              source: "地图"
            };
            const remoteUrls = collectRemoteTargets(baseRecord);
            let officialWebsiteEmail = "";
            let skipLeadWithoutOfficialEmail = false;

            for (const remote of remoteUrls) {
              ensureNotStopped();
              await patchState({
                detail: `正在补采 ${baseRecord.companyName} 的${remote.sourceLabel}信息。`,
                plan: getPlanProgress(scrapePlan, targetIndex, target, { currentCityKeywordDone: keywordIndex })
              });
              try {
                const remoteResponse = await chrome.runtime.sendMessage({ type: "SCRAPE_REMOTE_SOURCE", payload: remote });
                if (remoteResponse?.ok && remoteResponse.result) {
                  if (isOfficialWebsiteSource(remote.sourceLabel)) {
                    officialWebsiteEmail = sanitizeEmail(remoteResponse.result.email || "");
                    if (!officialWebsiteEmail) {
                      skipLeadWithoutOfficialEmail = true;
                      break;
                    }
                  }
                  enriched = mergeLead(enriched, remoteResponse.result, remote.sourceLabel);
                }
              } catch (error) {
                if (isOfficialWebsiteSource(remote.sourceLabel)) {
                  skipLeadWithoutOfficialEmail = true;
                  break;
                }
                await patchState({
                  detail: `${baseRecord.companyName} 的${remote.sourceLabel}补采失败，已跳过继续。`,
                  plan: getPlanProgress(scrapePlan, targetIndex, target, { currentCityKeywordDone: keywordIndex })
                });
              }
            }

            if (!officialWebsiteEmail || skipLeadWithoutOfficialEmail) {
              await patchState({
                detail: `${baseRecord.companyName} 的官网未获取到邮箱，已跳过不写入表格。`,
                plan: getPlanProgress(scrapePlan, targetIndex, target, { currentCityKeywordDone: keywordIndex })
              });
              continue;
            }

            allResults = upsertLead(allResults, enriched);
            await patchState({
              results: allResults,
              detail: `已完成 ${allResults.length} 条数据采集，最近处理：${baseRecord.companyName}`,
              plan: getPlanProgress(scrapePlan, targetIndex, target, { currentCityKeywordDone: keywordIndex })
            });
          }
        } catch (error) {
          if (runtimeState.stopRequested) {
            throw error;
          }
          await patchState({
            running: true,
            status: "运行中",
            detail: `${formatTargetLabel(target)} / ${keyword} 执行失败：${error.message}，已跳过继续下一个任务。`,
            plan: getPlanProgress(scrapePlan, targetIndex, target, { currentCityKeywordDone: keywordIndex })
          });
        }

        completedTasks += 1;
        await patchState({
          stats: { processed: completedTasks, total: scrapePlan.totalTasks },
          detail: `已完成任务 ${completedTasks}/${scrapePlan.totalTasks}，最近搜索：${keyword} / ${formatTargetLabel(target)}`,
          plan: getPlanProgress(scrapePlan, targetIndex, target, {
            cityCompleted: keywordIndex === targetKeywords.length - 1,
            currentCityKeywordDone: keywordIndex + 1
          })
        });

        if (keywordIndex === targetKeywords.length - 1) {
          await chrome.runtime.sendMessage({
            type: "REGISTER_COMPLETED_CITY",
            payload: {
              country: target.countryLabel || country,
              city: target.cityLabel || city,
              projectKeyword
            }
          }).catch(() => undefined);

          const countryCompletionNotice = buildCountryCompletionNotice(scrapePlan, targetIndex, target, allResults.length);
          if (countryCompletionNotice) {
            await patchState({
              detail: countryCompletionNotice.message,
              countryCompletionNotice,
              plan: getPlanProgress(scrapePlan, targetIndex, target, {
                cityCompleted: true,
                currentCityKeywordDone: keywordIndex + 1
              })
            });
          }
        }
      }
    }

    await patchState({
      running: false,
      status: "采集完成",
      detail: `任务完成，共采集 ${allResults.length} 条数据。`,
      currentKeyword: "",
      plan: {
        plannedCountries: scrapePlan.plannedCountries,
        remainingCountries: 0,
        plannedCities: scrapePlan.targets.length,
        remainingCities: 0,
        currentCountry: "",
        currentCity: "",
        currentCityKeywordDone: 0,
        currentCityKeywordTotal: 0,
        skippedCities: scrapePlan.skippedCities,
        mode: scrapePlan.mode
      },
      stats: { processed: completedTasks, total: scrapePlan.totalTasks }
    });
    await chrome.runtime.sendMessage({
      type: "FINALIZE_CITY_RUN",
      payload: { runId, status: "completed" }
    }).catch(() => undefined);
  } catch (error) {
    await chrome.runtime.sendMessage({
      type: "FINALIZE_CITY_RUN",
      payload: { runId, status: runtimeState.stopRequested ? "stopped" : "failed" }
    }).catch(() => undefined);
    throw error;
  } finally {
    runtimeState.running = false;
  }
}

async function extractCurrentPageContacts(payload) {
  await waitForDocumentReady();

  const source = payload?.sourceLabel || "页面";
  const url = location.href;
  const isOfficialWebsite = isOfficialWebsiteSource(source);
  if (!isOfficialWebsite) {
    await autoScrollPage();
  }

  const text = document.body?.innerText || "";
  const html = document.documentElement?.outerHTML || "";
  const direct = harvestContactsFromText(text, url);
  const socialLinks = extractSocialLinksFromDocument();
  const internalLinks = findInternalLinks();

  let aggregateText = text;
  const linkLimit = isOfficialWebsite && !direct.emails.length ? 3 : 5;
  for (const link of internalLinks.slice(0, linkLimit)) {
    try {
      const extraText = await fetchSameOriginText(link, isOfficialWebsite ? 2500 : 5000);
      aggregateText += `\n${extraText}`;
      if (isOfficialWebsite && harvestContactsFromText(aggregateText, url).emails.length) {
        break;
      }
    } catch (error) {
      continue;
    }
  }

  const extraDirect = harvestContactsFromText(aggregateText, url);
  const email = uniqueValues([...direct.emails, ...extraDirect.emails])[0] || "";
  if (isOfficialWebsite && !email) {
    return {
      source,
      companyName: extractWebsiteCompanyName(document, url),
      website: isWebsiteLike(url) ? url : "",
      socialLinks: normalizeSocialLinks([...socialLinks, ...extractSocialLinksFromText(html)]),
      phone: "",
      email: "",
      address: "",
      businessIntroduction: "",
      procurementInfo: "",
      contactPerson: "",
      notes: aggregateText.slice(0, 500)
    };
  }

  const procurementInfo = collectProcurementSnippets(text);
  const contactPerson = extractContactPerson(text);
  const businessIntroduction = shouldExtractBusinessIntroduction(url, source)
    ? await extractBusinessIntroduction({
        primaryDoc: document,
        primaryUrl: url,
        internalLinks
      })
    : "";

  return {
    source,
    companyName: extractWebsiteCompanyName(document, url),
    website: isWebsiteLike(url) ? url : "",
    socialLinks: normalizeSocialLinks([...socialLinks, ...extractSocialLinksFromText(html)]),
    phone: uniqueValues([...direct.phones, ...extraDirect.phones])[0] || "",
    email,
    address: uniqueValues([...direct.addresses, ...extraDirect.addresses])[0] || "",
    businessIntroduction,
    procurementInfo: procurementInfo || collectProcurementSnippets(aggregateText),
    contactPerson,
    notes: aggregateText.slice(0, 2000)
  };
}

async function waitForMapShell() {
  await waitFor(() => isMapsShellReady(), 20000, "未找到 Google Maps 搜索框");
}

async function runSearch(query) {
  if (hasSearchResultsForQuery(query)) {
    return hasSearchResults();
  }

  const input = await waitForSearchInput();
  if (!input) {
    throw new Error("未找到 Google Maps 搜索框，请刷新页面后重试。");
  }

  input.focus();
  setNativeInputValue(input, "");
  input.dispatchEvent(new Event("input", { bubbles: true }));
  input.dispatchEvent(new Event("change", { bubbles: true }));
  await sleep(150);

  setNativeInputValue(input, query);
  input.dispatchEvent(new Event("input", { bubbles: true }));
  input.dispatchEvent(new Event("change", { bubbles: true }));
  await sleep(250);

  const searchButton = getSearchButton();
  if (searchButton) {
    searchButton.click();
  } else {
    input.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, key: "Enter", code: "Enter" }));
    input.dispatchEvent(new KeyboardEvent("keyup", { bubbles: true, key: "Enter", code: "Enter" }));
  }

  await sleep(3000);
  await waitFor(() => hasSearchResults() || hasNoResultsState(), 25000, "搜索结果列表加载超时");
  return hasSearchResults();
}

async function autoScrollFeed() {
  const feed = getResultsContainer();
  if (!feed) {
    return;
  }

  let stableCount = 0;
  let previousHeight = 0;
  for (let i = 0; i < 18; i += 1) {
    ensureNotStopped();
    feed.scrollTo({ top: feed.scrollHeight, behavior: "smooth" });
    await sleep(1200);
    const nextHeight = feed.scrollHeight;
    if (nextHeight === previousHeight) {
      stableCount += 1;
      if (stableCount >= 3) {
        break;
      }
    } else {
      stableCount = 0;
    }
    previousHeight = nextHeight;
  }
}

function collectResultCards() {
  const links = Array.from(document.querySelectorAll([
    '[role="feed"] a[href*="/maps/place/"]',
    'a.hfpxzc[href*="/maps/place/"]',
    'a[href*="/maps/place/"]'
  ].join(", ")));
  const unique = new Map();
  for (const link of links) {
    const href = (link.href || "").split("?")[0];
    if (!href || unique.has(href)) {
      continue;
    }
    unique.set(href, {
      href,
      element: link.closest('[role="article"]')
        || link.closest(".Nv2PK")
        || link.closest(".hfpxzc")
        || link
    });
  }

  if (!unique.size) {
    const cards = Array.from(document.querySelectorAll([
      '[role="feed"] [role="article"]',
      '.Nv2PK',
      'div[role="article"]'
    ].join(", ")));

    cards.forEach((card, index) => {
      const href = card.querySelector('a[href*="/maps/place/"]')?.href || `card-${index}`;
      if (!unique.has(href)) {
        unique.set(href, { href, element: card });
      }
    });
  }
  return Array.from(unique.values());
}

async function openCard(element, previousTitle = "", expectedTitle = "") {
  element.scrollIntoView({ behavior: "smooth", block: "center" });
  await sleep(400);
  element.click();
  await waitFor(() => {
    const title = getBusinessTitleNode()?.textContent?.trim() || "";
    if (!title) {
      return false;
    }
    if (expectedTitle && normalizeName(title).includes(normalizeName(expectedTitle))) {
      return true;
    }
    return previousTitle ? title !== previousTitle : true;
  }, 15000, "商家详情页加载超时");
}

async function extractBusinessFromMap() {
  const panel = document.querySelector('div[role="main"]') || document.body;
  const text = panel.innerText || "";
  const anchors = Array.from(panel.querySelectorAll("a[href]"));
  const title = getBusinessTitleNode()?.textContent?.trim() || "";
  const website = extractWebsiteFromMap(panel, anchors);
  const socialLinks = normalizeSocialLinks(anchors.map((anchor) => anchor.href).filter((href) => SOCIAL_HOSTS.some((host) => href.includes(host))));
  const phone = extractLabeledValue(panel, ["phone"]) || harvestContactsFromText(text, location.href).phones[0] || "";
  const address = extractLabeledValue(panel, ["address"]) || harvestContactsFromText(text, location.href).addresses[0] || "";
  const rating = extractRating(panel);
  const hours = extractHours(panel);
  const categoryText = extractCategoryText(panel);
  const category = classifyBusiness(`${title}\n${categoryText}\n${website}`);

  return {
    companyName: title,
    phone,
    email: "",
    address,
    website,
    businessIntroduction: "",
    socialLinks,
    rating,
    hours,
    category,
    contactPerson: "",
    procurementInfo: ""
  };
}

function extractWebsiteFromMap(panel, anchors) {
  const websiteButton = panel.querySelector('a[data-item-id*="authority"], a[data-item-id*="url"], a[aria-label*="Website"]');
  if (websiteButton?.href) {
    return websiteButton.href;
  }

  const websiteLink = anchors.find((anchor) => {
    const href = anchor.href || "";
    return /^https?:\/\//i.test(href) && !href.includes("google.com") && !href.includes("gstatic.com") && !SOCIAL_HOSTS.some((host) => href.includes(host));
  });

  return websiteLink?.href || "";
}

function extractLabeledValue(root, keywords) {
  const candidate = Array.from(root.querySelectorAll("button, a, div"))
    .map((node) => ({ node, label: `${node.getAttribute("aria-label") || ""} ${node.getAttribute("data-item-id") || ""} ${node.textContent || ""}`.toLowerCase() }))
    .find((item) => keywords.some((keyword) => item.label.includes(keyword)));
  return sanitizeText(candidate?.node?.textContent || "");
}

function extractRating(root) {
  const ratingNode = root.querySelector('[role="img"][aria-label*="star"], span[aria-hidden="true"]');
  const text = ratingNode?.getAttribute("aria-label") || ratingNode?.textContent || "";
  const match = text.match(/([0-9.]+)/);
  return match?.[1] || "";
}

function extractHours(root) {
  const buttons = Array.from(root.querySelectorAll("button, div, span"));
  const hoursNode = buttons.find((node) => /open|closed|hours/i.test(node.textContent || ""));
  return sanitizeText(hoursNode?.textContent || "");
}

function extractCategoryText(root) {
  const buttons = Array.from(root.querySelectorAll("button, div, span"));
  const categoryNode = buttons.find((node) => {
    const text = sanitizeText(node.textContent || "");
    return text && text.length < 120 && /supplier|contractor|service|company|business/i.test(text);
  });
  return sanitizeText(categoryNode?.textContent || "");
}

function collectRemoteTargets(baseRecord) {
  const targets = [];
  if (baseRecord.website) {
    targets.push({ url: baseRecord.website, sourceLabel: "官网" });
  }
  for (const socialLink of baseRecord.socialLinks || []) {
    targets.push({ url: socialLink, sourceLabel: inferSocialSource(socialLink) });
  }
  return uniqueObjectsBy(targets, (item) => `${item.sourceLabel}:${item.url}`);
}

function isOfficialWebsiteSource(sourceLabel) {
  return String(sourceLabel || "").includes("官网");
}

function mergeLead(baseRecord, remoteRecord, sourceLabel) {
  const sources = new Set(String(baseRecord.source || "地图").split(" / ").filter(Boolean));
  sources.add(sourceLabel);
  const nextCompanyName = pickCanonicalCompanyName(baseRecord, remoteRecord, sourceLabel);
  return {
    ...baseRecord,
    companyName: nextCompanyName,
    phone: pickBestValue(baseRecord.phone, remoteRecord.phone),
    email: pickBestValue(baseRecord.email, remoteRecord.email),
    address: pickBestValue(baseRecord.address, remoteRecord.address),
    website: pickBestValue(baseRecord.website, remoteRecord.website),
    country: pickBestValue(baseRecord.country, remoteRecord.country),
    businessIntroduction: pickBestValue(baseRecord.businessIntroduction, remoteRecord.businessIntroduction),
    socialLinks: normalizeSocialLinks([...(baseRecord.socialLinks || []), ...(remoteRecord.socialLinks || [])]),
    contactPerson: pickBestValue(baseRecord.contactPerson, remoteRecord.contactPerson),
    procurementInfo: pickBestValue(baseRecord.procurementInfo, remoteRecord.procurementInfo),
    source: Array.from(sources).join(" / ")
  };
}

function upsertLead(list, record) {
  const index = findLeadIndex(list, record);
  if (index === -1) {
    return [...list, record];
  }
  const cloned = [...list];
  cloned[index] = mergeLead(cloned[index], record, record.source || "地图");
  return cloned;
}

function dedupeLeadRecords(list) {
  let merged = [];
  for (const item of list || []) {
    merged = upsertLead(merged, item);
  }
  return merged;
}

async function patchState(patch) {
  await chrome.runtime.sendMessage({ type: "STATE_PATCH", patch });
}

async function waitForDocumentReady() {
  if (document.readyState === "complete") {
    return;
  }
  await new Promise((resolve) => {
    const handler = () => {
      if (document.readyState === "complete") {
        document.removeEventListener("readystatechange", handler);
        resolve();
      }
    };
    document.addEventListener("readystatechange", handler);
  });
}

async function autoScrollPage() {
  let lastHeight = 0;
  for (let i = 0; i < 6; i += 1) {
    window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
    await sleep(700);
    const nextHeight = document.body.scrollHeight;
    if (nextHeight === lastHeight) {
      break;
    }
    lastHeight = nextHeight;
  }
  window.scrollTo({ top: 0, behavior: "auto" });
}

function findInternalLinks() {
  const base = location.origin;
  const anchors = Array.from(document.querySelectorAll("a[href]"));
  return uniqueValues(
    anchors
      .map((anchor) => ({
        href: anchor.href,
        text: sanitizeText(anchor.textContent || ""),
        label: `${sanitizeText(anchor.textContent || "")} ${sanitizeText(anchor.getAttribute("aria-label") || "")} ${anchor.href || ""}`.toLowerCase()
      }))
      .filter((item) => item.href.startsWith(base) && CONTACT_LINK_WORDS.some((word) => item.label.includes(word)))
      .map((item) => item.href)
  );
}

async function fetchSameOriginText(url, timeoutMs = 5000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { credentials: "include", signal: controller.signal });
    const html = await response.text();
    const doc = new DOMParser().parseFromString(html, "text/html");
    return sanitizeText(doc.body?.innerText || "");
  } finally {
    clearTimeout(timer);
  }
}

async function fetchSameOriginDocument(url) {
  const response = await fetch(url, { credentials: "include" });
  const html = await response.text();
  return new DOMParser().parseFromString(html, "text/html");
}

function harvestContactsFromText(text, url) {
  const rawEmails = text.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi) || [];
  const emails = uniqueValues(
    rawEmails
      .map((email) => sanitizeEmail(email))
      .filter(Boolean)
      .slice(0, 10)
  );
  const phones = uniqueValues(
    (text.match(/(?:\+\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{4,}/g) || [])
      .map((item) => item.trim())
      .filter((item) => item.replace(/\D/g, "").length >= 7)
      .slice(0, 10)
  );
  return { emails, phones, addresses: extractAddressCandidates(text), website: isWebsiteLike(url) ? url : "" };
}

function sanitizeEmail(email) {
  const cleaned = String(email || "")
    .toLowerCase()
    .trim()
    .replace(/^[^a-z0-9]+/, "")
    .replace(/[^a-z0-9._%+-]+$/, "");
  
  // 验证邮箱格式：必须有@符号和有效的域名
  if (!/^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$/.test(cleaned)) {
    return "";
  }
  
  // 检查邮箱长度
  if (cleaned.length < 5 || cleaned.length > 254) {
    return "";
  }
  
  // 检查本地部分（@前面）长度
  const [localPart] = cleaned.split("@");
  if (!localPart || localPart.length > 64) {
    return "";
  }
  
  // 检查连续的点或其他无效模式
  if (/\.\.|\.$|^\./.test(cleaned) || /^@|@$/.test(cleaned)) {
    return "";
  }
  
  return cleaned;
}

function extractAddressCandidates(text) {
  const lines = text.split(/\n+/).map((line) => sanitizeText(line)).filter(Boolean);
  const candidates = lines.filter((line) => {
    if (line.length < 12 || line.length > 160) {
      return false;
    }
    const hasStreetWord = /\b(st|street|rd|road|ave|avenue|blvd|boulevard|dr|drive|lane|ln|suite|ste|unit|floor)\b/i.test(line);
    const hasNumber = /\d/.test(line);
    const hasPostal = /\b[A-Z0-9]{3,10}\b/.test(line);
    return (hasStreetWord && hasNumber) || (hasStreetWord && hasPostal);
  });
  return uniqueValues(candidates.slice(0, 5));
}

function collectProcurementSnippets(text) {
  const lines = text.split(/\n+/).map((line) => sanitizeText(line)).filter(Boolean);
  const hits = lines.filter((line) => /\b(procurement|purchasing|buyer|wholesale|dealer|distributor|sourcing)\b/i.test(line));
  return hits.slice(0, 5).join(" | ");
}

function extractContactPerson(text) {
  const patterns = [
    /\b(?:procurement manager|purchasing manager|buyer|sales manager|wholesale manager)\s*[:\-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})/i,
    /\bcontact\s*[:\-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})/i
  ];
  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (match?.[1]) {
      return sanitizeText(match[1]);
    }
  }
  return "";
}

function extractSocialLinksFromDocument() {
  return normalizeSocialLinks(Array.from(document.querySelectorAll("a[href]")).map((anchor) => anchor.href).filter((href) => SOCIAL_HOSTS.some((host) => href.includes(host))));
}

function extractSocialLinksFromText(html) {
  const matches = html.match(/https?:\/\/(?:www\.)?(?:facebook|instagram|linkedin)\.com\/[^\s"'<>]+/gi) || [];
  return normalizeSocialLinks(matches);
}

function normalizeSocialLinks(links) {
  const bestByPlatform = new Map();
  for (const rawLink of uniqueValues(links || [])) {
    const normalized = normalizeSocialLink(rawLink);
    if (!normalized) {
      continue;
    }
    const platform = inferSocialSource(normalized);
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
    if (!SOCIAL_HOSTS.some((host) => hostname.includes(host))) {
      return "";
    }

    const pathname = url.pathname.replace(/\/+/g, "/").replace(/\/$/, "");
    const lowerPath = pathname.toLowerCase();
    if (!pathname || pathname === "/") {
      return "";
    }
    if (/(^|\/)(login|recover|checkpoint|share|sharer|dialog|plugins|privacy|policies|help|watch|reel|reels|stories|hashtag|explore|intent|search|accounts|oauth|signup)(\/|$)/i.test(lowerPath)) {
      return "";
    }

    if (hostname.includes("facebook.com")) {
      const match = pathname.match(/^\/(?:pages\/)?([^/?#]+)(?:\/about)?$/i);
      if (!match?.[1]) {
        return "";
      }
      return `https://www.facebook.com/${match[1].replace(/^people\//i, "people/")}`;
    }

    if (hostname.includes("instagram.com")) {
      const match = pathname.match(/^\/([^/?#]+)$/i);
      if (!match?.[1] || /^(p|reel|stories|explore)$/i.test(match[1])) {
        return "";
      }
      return `https://www.instagram.com/${match[1]}`;
    }

    if (hostname.includes("linkedin.com")) {
      const match = pathname.match(/^\/(company|in)\/([^/?#]+)/i);
      if (!match?.[1] || !match?.[2]) {
        return "";
      }
      return `https://www.linkedin.com/${match[1]}/${match[2]}`;
    }

    return url.origin + pathname;
  } catch (error) {
    return "";
  }
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
  if (/\/about$/.test(value)) {
    score -= 1;
  }
  if (/facebook\.com\/[^/]+$/.test(value) || /instagram\.com\/[^/]+$/.test(value)) {
    score += 5;
  }
  if (/linkedin\.com\/company\//.test(value)) {
    score += 5;
  }
  return score - value.length / 1000;
}

function classifyBusiness(text) {
  const normalized = text.toLowerCase();
  for (const item of CATEGORY_MAP) {
    if (item.patterns.some((pattern) => normalized.includes(pattern))) {
      return item.label;
    }
  }
  return "Product Supply";
}

function inferSocialSource(url) {
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

function ensureNotStopped() {
  if (runtimeState.stopRequested) {
    throw new Error("任务已停止。");
  }
}

function isGoogleMapsPage() {
  return ((/(^|\.)google\.[a-z.]+$/i.test(location.hostname) && location.pathname.startsWith("/maps")) || /^maps\.google\./i.test(location.hostname));
}

function isWebsiteLike(url) {
  return /^https?:\/\//i.test(url || "");
}

function sanitizeText(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function uniqueValues(list) {
  return Array.from(new Set((list || []).filter(Boolean)));
}

function uniqueObjectsBy(list, makeKey) {
  const seen = new Set();
  return list.filter((item) => {
    const key = makeKey(item);
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

function pickBestValue(primary, fallback) {
  return primary || fallback || "";
}

function splitLocationInput(rawValue) {
  const normalized = sanitizeText(rawValue);
  if (!normalized) {
    return { city: "", country: "", rawCountry: "" };
  }

  const parts = normalized.split(",").map((item) => sanitizeText(item)).filter(Boolean);
  if (parts.length < 2) {
    return { city: normalized, country: "", rawCountry: "" };
  }

  const rawCountry = parts[parts.length - 1];
  const country = normalizeCountryName(rawCountry);
  if (!country) {
    return { city: parts.slice(0, -1).join(", "), country: "", rawCountry };
  }

  return {
    city: parts.slice(0, -1).join(", "),
    country,
    rawCountry
  };
}

function normalizeCountryName(value) {
  const normalized = String(value || "").trim().toLowerCase();
  return COUNTRY_ALIASES[normalized] || "";
}

function findTargetMarket(countryInput) {
  const normalized = String(countryInput || "").trim().toLowerCase();
  if (!normalized) {
    return null;
  }
  return TARGET_MARKETS.find((market) => market.aliases.some((alias) => alias.toLowerCase() === normalized)) || null;
}

function isRecognizedCountryName(value) {
  const normalized = normalizeName(value);
  if (!normalized) {
    return false;
  }
  if (normalizeCountryName(value)) {
    return true;
  }
  return Object.values(COUNTRY_ALIASES).some((country) => normalizeName(country) === normalized)
    || TARGET_MARKETS.some((market) => {
      if (normalizeName(market.countryLabel) === normalized) {
        return true;
      }
      return market.aliases.some((alias) => normalizeName(alias) === normalized);
    });
}

function isPlausibleCityName(value) {
  const normalized = String(value || "").trim();
  if (!normalized) {
    return true;
  }
  return /\p{L}/u.test(normalized)
    && /^[\p{L}\p{M}\s.'’(),-]+$/u.test(normalized);
}

function buildScrapePlan({ country, city, cityBatchSize, manualSkipCities, projectKeyword, keywords, skipVisitedCities, restartCities, resumeProgress, existingKeywordRecords, completedCities }) {
  const normalizedCountry = sanitizeText(country);
  const normalizedCity = sanitizeText(city);
  const normalizedCityBatchSize = Number.isFinite(Number(cityBatchSize)) ? Math.max(0, Number(cityBatchSize)) : 0;
  const normalizedProjectKeyword = sanitizeText(projectKeyword || keywords?.[0] || "");
  const manualSkipCityKeys = buildManualSkipCityKeys(manualSkipCities, normalizedCountry);
  const normalizedKeywords = uniqueValues((keywords || []).map((item) => sanitizeText(item)).filter(Boolean));
  const projectBlockedCityKeys = buildProjectBlockedCityKeys(normalizedKeywords);
  const completedCityKeys = restartCities ? new Set() : buildCompletedCityKeySet(completedCities, normalizedCountry, normalizedProjectKeyword);
  const requestedCityMeta = splitLocationInput(normalizedCity);
  const requestedCountryInput = normalizedCountry || requestedCityMeta.country || requestedCityMeta.rawCountry || "";
  const matchedMarket = findTargetMarket(requestedCountryInput);
  const targets = [];
  let mode = "manual";

  if (requestedCountryInput && !isRecognizedCountryName(requestedCountryInput)) {
    throw new Error(`国家 “${requestedCountryInput}” 无法识别，请检查拼写。比如日本请填写 Japan 或 日本。`);
  }

  if (requestedCityMeta.city || normalizedCity) {
    const cityLabel = requestedCityMeta.city || normalizedCity;
    if (!isPlausibleCityName(cityLabel)) {
      throw new Error(`城市 “${cityLabel}” 无法识别，请检查拼写或删除数字、网址、特殊符号。`);
    }
    const countryLabel = matchedMarket?.countryLabel || normalizeCountryName(normalizedCountry) || normalizeCountryName(requestedCityMeta.country) || normalizedCountry || "";
    const searchCountry = matchedMarket?.searchCountry || requestedCityMeta.country || normalizedCountry || "";
    targets.push({
      countryLabel,
      cityLabel,
      searchCountry,
      searchCity: cityLabel
    });
  } else if (normalizedCountry) {
    mode = "country-auto";
    if (matchedMarket) {
      for (const cityName of matchedMarket.cities) {
        targets.push({
          countryLabel: matchedMarket.countryLabel,
          cityLabel: cityName,
          searchCountry: matchedMarket.searchCountry,
          searchCity: cityName
        });
      }
    } else {
      targets.push({
        countryLabel: normalizeCountryName(normalizedCountry) || normalizedCountry,
        cityLabel: "",
        searchCountry: normalizedCountry,
        searchCity: ""
      });
    }
  } else {
    mode = "global-auto";
    for (const market of TARGET_MARKETS) {
      for (const cityName of market.cities) {
        targets.push({
          countryLabel: market.countryLabel,
          cityLabel: cityName,
          searchCountry: market.searchCountry,
          searchCity: cityName
        });
      }
    }
  }

  const filteredTargets = [];
  let skippedCities = 0;

  for (const target of targets) {
    const targetCityKey = makeLocationKey(target.countryLabel, target.cityLabel);
    const targetCityOnlyKey = makeLocationKey("", target.cityLabel);
    if (manualSkipCityKeys.has(targetCityKey)) {
      skippedCities += 1;
      continue;
    }
    if (projectBlockedCityKeys.has(targetCityKey)) {
      skippedCities += 1;
      continue;
    }
    if (skipVisitedCities && (completedCityKeys.has(targetCityKey) || completedCityKeys.has(targetCityOnlyKey))) {
      skippedCities += 1;
      continue;
    }
    const targetKeywords = getResumableKeywordsForTarget(target, normalizedKeywords, resumeProgress);
    filteredTargets.push({
      ...target,
      keywords: targetKeywords,
      pendingKeywordCount: targetKeywords.length
    });
  }

  if (!filteredTargets.length) {
    throw new Error(skipVisitedCities ? "计划中的城市都已经完整采集过了，请关闭跳过选项或更换关键词。" : "未生成有效的采集计划，请检查国家或城市输入。");
  }

  const prioritizedTargets = prioritizeTargetsByKeywordCount(filteredTargets, normalizedKeywords);
  const limitedTargets = normalizedCityBatchSize > 0 && !normalizedCity
    ? prioritizedTargets.slice(0, normalizedCityBatchSize)
    : prioritizedTargets;

  return {
    mode,
    skippedCities,
    plannedCountries: countUniqueCountries(limitedTargets),
    totalTasks: limitedTargets.reduce((sum, target) => sum + (target.keywords?.length || normalizedKeywords.length || 0), 0),
    targets: limitedTargets
  };
}

function buildCompletedCityKeySet(completedCities, country, projectKeyword = "") {
  const normalizedCountry = normalizeCountryKey(country);
  const normalizedProjectKey = makeProjectKey(projectKeyword);
  const set = new Set();
  for (const item of completedCities || []) {
    const itemProjectKey = makeProjectKey(item.projectKeyword || item.keyword || "");
    if (normalizedProjectKey && itemProjectKey !== normalizedProjectKey) {
      continue;
    }
    const itemCountryKey = normalizeCountryKey(item.country);
    if (normalizedCountry && itemCountryKey && itemCountryKey !== normalizedCountry) {
      continue;
    }
    const key = makeLocationKey(item.country, item.city);
    if (key) {
      set.add(key);
    }
    const cityOnlyKey = makeLocationKey("", item.city);
    if (cityOnlyKey) {
      set.add(cityOnlyKey);
    }
  }
  return set;
}

function getResumableKeywordsForTarget(target, keywords, resumeProgress) {
  const normalizedKeywords = Array.isArray(keywords) ? [...keywords] : [];
  if (!resumeProgress?.cityKey || !normalizedKeywords.length) {
    return normalizedKeywords;
  }
  const targetCityKey = makeLocationKey(target.countryLabel, target.cityLabel);
  if (!targetCityKey || targetCityKey !== resumeProgress.cityKey) {
    return normalizedKeywords;
  }
  const done = Math.max(0, Math.min(normalizedKeywords.length, Number(resumeProgress.completedKeywordCount || 0)));
  return normalizedKeywords.slice(done);
}

function getResumeCityProgress(state, { country, city, keywords }) {
  const resumableStatuses = new Set(["已停止", "异常停止"]);
  if (!resumableStatuses.has(String(state?.status || ""))) {
    return null;
  }
  const plan = state?.plan || {};
  const done = Number(plan.currentCityKeywordDone || 0);
  const total = Number(plan.currentCityKeywordTotal || 0);
  if (!plan.currentCountry || !plan.currentCity || !total || done >= total) {
    return null;
  }
  const requestedCity = sanitizeText(city || "");
  const requestedCountry = sanitizeText(country || "");
  if (requestedCity && normalizeName(plan.currentCity) !== normalizeName(requestedCity)) {
    return null;
  }
  if (requestedCountry && normalizeCountryKey(plan.currentCountry) !== normalizeCountryKey(requestedCountry)) {
    return null;
  }
  const normalizedKeywords = uniqueValues((keywords || []).map((item) => sanitizeText(item)).filter(Boolean));
  if (normalizedKeywords.length && total !== normalizedKeywords.length) {
    return null;
  }
  return {
    cityKey: makeLocationKey(plan.currentCountry, plan.currentCity),
    completedKeywordCount: done
  };
}

function buildManualSkipCityKeys(manualSkipCities, country) {
  const set = new Set();
  for (const city of manualSkipCities || []) {
    const key = makeLocationKey(country, city);
    if (key) {
      set.add(key);
    }
  }
  return set;
}

function buildProjectBlockedCityKeys(keywords) {
  const normalizedKeywords = new Set((keywords || []).map((keyword) => normalizeName(keyword)).filter(Boolean));
  const set = new Set();
  for (const rule of PROJECT_CITY_BLOCKLIST) {
    const ruleKeywords = Array.isArray(rule.keywords) ? rule.keywords : [];
    const matchesProject = !ruleKeywords.length
      || ruleKeywords.some((keyword) => normalizedKeywords.has(normalizeName(keyword)));
    if (!matchesProject) {
      continue;
    }
    for (const city of rule.cities || []) {
      const key = makeLocationKey(rule.country, city);
      if (key) {
        set.add(key);
      }
    }
  }
  return set;
}

function prioritizeTargetsByKeywordCount(targets, keywords) {
  const fallbackKeywordCount = (keywords || []).length;
  const countryOrder = new Map();
  const cityOrder = new Map();
  const grouped = new Map();

  (targets || []).forEach((target, index) => {
    const countryKey = target.countryLabel || target.searchCountry || "";
    const cityKey = makeLocationKey(target.countryLabel, target.cityLabel);
    if (!countryOrder.has(countryKey)) {
      countryOrder.set(countryKey, index);
    }
    if (!cityOrder.has(cityKey)) {
      cityOrder.set(cityKey, index);
    }
    if (!grouped.has(countryKey)) {
      grouped.set(countryKey, []);
    }
    grouped.get(countryKey).push(target);
  });

  const rankedCountries = Array.from(grouped.entries())
    .map(([countryKey, countryTargets]) => ({
      countryKey,
      targets: countryTargets
        .slice()
        .sort((left, right) => {
          const keywordDiff = (right.pendingKeywordCount ?? fallbackKeywordCount) - (left.pendingKeywordCount ?? fallbackKeywordCount);
          if (keywordDiff !== 0) {
            return keywordDiff;
          }
          return (cityOrder.get(makeLocationKey(left.countryLabel, left.cityLabel)) || 0)
            - (cityOrder.get(makeLocationKey(right.countryLabel, right.cityLabel)) || 0);
        }),
      totalKeywordCount: countryTargets.reduce((sum, target) => sum + (target.pendingKeywordCount ?? fallbackKeywordCount), 0),
      order: countryOrder.get(countryKey) || 0
    }))
    .sort((left, right) => {
      const keywordDiff = right.totalKeywordCount - left.totalKeywordCount;
      if (keywordDiff !== 0) {
        return keywordDiff;
      }
      return left.order - right.order;
    });

  return rankedCountries.flatMap((item) => item.targets);
}

function countUniqueCountries(targets) {
  return new Set((targets || []).map((item) => item.countryLabel || item.searchCountry).filter(Boolean)).size;
}

function getPlanProgress(scrapePlan, targetIndex, target, options = {}) {
  const completedCities = Math.min(scrapePlan.targets.length, targetIndex + (options.cityCompleted ? 1 : 0));
  const remainingCities = Math.max(0, scrapePlan.targets.length - completedCities);
  const remainingCountries = countRemainingCountries(scrapePlan.targets, targetIndex + (options.cityCompleted ? 1 : 0));
  const currentCityKeywordDone = Math.min(
    Number(target?.keywords?.length || 0),
    Number(options.currentCityKeywordDone || 0)
  );
  return {
    plannedCountries: scrapePlan.plannedCountries,
    remainingCountries,
    plannedCities: scrapePlan.targets.length,
    remainingCities,
    currentCountry: target?.countryLabel || "",
    currentCity: target?.cityLabel || "",
    currentCityKeywordDone,
    currentCityKeywordTotal: Number(target?.keywords?.length || 0),
    skippedCities: scrapePlan.skippedCities,
    mode: scrapePlan.mode
  };
}

function countRemainingCountries(targets, startIndex) {
  return new Set((targets || []).slice(startIndex).map((item) => item.countryLabel || item.searchCountry).filter(Boolean)).size;
}

function buildCountryCompletionNotice(scrapePlan, targetIndex, target, resultCount) {
  if (!scrapePlan || scrapePlan.mode === "manual") {
    return null;
  }

  const countryLabel = target?.countryLabel || target?.searchCountry || "";
  if (!countryLabel) {
    return null;
  }

  const nextTarget = scrapePlan.targets[targetIndex + 1];
  const nextCountryLabel = nextTarget?.countryLabel || nextTarget?.searchCountry || "";
  if (nextCountryLabel === countryLabel) {
    return null;
  }

  const plannedCityCount = scrapePlan.targets
    .filter((item) => (item.countryLabel || item.searchCountry || "") === countryLabel)
    .length;
  return {
    id: `${countryLabel}:${Date.now()}`,
    country: countryLabel,
    plannedCities: plannedCityCount,
    resultCount,
    message: `${countryLabel} 本轮计划城市已全部采集完成，共 ${plannedCityCount} 个城市，当前累计 ${resultCount} 条数据。`
  };
}

function makeLocationKey(country, city) {
  const normalizedCountry = normalizeCountryKey(country);
  const normalizedCity = normalizeName(city);
  if (!normalizedCountry && !normalizedCity) {
    return "";
  }
  return `${normalizedCountry}|${normalizedCity}`;
}

function normalizeCountryKey(value) {
  const normalizedAlias = normalizeCountryName(value);
  if (normalizedAlias) {
    return normalizeName(normalizedAlias);
  }
  return normalizeName(value);
}

function makeProjectKey(keyword) {
  return normalizeName(keyword);
}

function buildSearchQuery(keyword, target) {
  return [keyword, target.searchCity, target.searchCountry].filter(Boolean).join(" ");
}

function matchesTargetLocation(record, target) {
  const targetCity = normalizeName(target?.cityLabel || target?.searchCity || "");
  const targetCountry = normalizeCountryKey(target?.countryLabel || target?.searchCountry || "");
  const locationText = normalizeName([
    record?.address,
    record?.city,
    record?.country
  ].filter(Boolean).join(" "));
  if (!locationText) {
    return true;
  }

  if (targetCity && locationText.includes(targetCity)) {
    return locationText.includes(targetCity);
  }

  if (targetCountry && locationText.includes(targetCountry)) {
    return true;
  }

  const detectedCountry = detectCountryFromLocationText(locationText);
  if (detectedCountry && targetCountry && detectedCountry !== targetCountry) {
    return false;
  }

  return true;
}

function detectCountryFromLocationText(locationText) {
  const normalizedText = normalizeName(locationText);
  if (!normalizedText) {
    return "";
  }

  const candidates = new Map();
  Object.entries(COUNTRY_ALIASES).forEach(([alias, country]) => {
    candidates.set(normalizeName(alias), normalizeCountryKey(country));
  });
  TARGET_MARKETS.forEach((market) => {
    candidates.set(normalizeName(market.countryLabel), normalizeCountryKey(market.countryLabel));
    candidates.set(normalizeName(market.searchCountry || ""), normalizeCountryKey(market.countryLabel));
    (market.aliases || []).forEach((alias) => {
      candidates.set(normalizeName(alias), normalizeCountryKey(market.countryLabel));
    });
  });

  for (const [aliasKey, countryKey] of candidates.entries()) {
    if (aliasKey && countryKey && normalizedText.includes(aliasKey)) {
      return countryKey;
    }
  }

  return "";
}

function formatTargetLabel(target) {
  return [target?.countryLabel, target?.cityLabel].filter(Boolean).join(" / ") || target?.searchCountry || target?.searchCity || "目标地区";
}

function shouldExtractBusinessIntroduction(url, sourceLabel) {
  return isWebsiteLike(url)
    && !SOCIAL_HOSTS.some((host) => url.includes(host))
    && String(sourceLabel || "").includes("官网");
}

async function extractBusinessIntroduction({ primaryDoc, primaryUrl, internalLinks }) {
  const primaryIntro = await buildBusinessIntroductionFromDocument(primaryDoc, primaryUrl, { prioritizeHero: true });
  if (primaryIntro) {
    return primaryIntro;
  }

  for (const link of (internalLinks || []).filter(isAboutOrServicesLink).slice(0, 5)) {
    try {
      const doc = await fetchSameOriginDocument(link);
      const intro = await buildBusinessIntroductionFromDocument(doc, link, { prioritizeHero: false });
      if (intro) {
        return intro;
      }
    } catch (error) {
      continue;
    }
  }

  return BUSINESS_INTRO_FALLBACK;
}

function isAboutOrServicesLink(url) {
  return /\b(about|about-us|company|service|services|solutions)\b/i.test(url || "");
}

async function buildBusinessIntroductionFromDocument(doc, url, options = {}) {
  const title = sanitizeText(doc.querySelector("title")?.textContent || "");
  const h1 = sanitizeText(doc.querySelector("h1")?.textContent || "");
  const prioritizedTexts = [
    title,
    h1,
    ...collectPriorityTextCandidates(doc, Boolean(options.prioritizeHero))
  ].filter(Boolean);
  const signalText = prioritizedTexts.join("\n");
  if (!containsIndustryKeyword(signalText)) {
    return "";
  }

  const aiSummary = await requestAiBusinessIntroduction({
    text: signalText,
    url,
    companyName: h1 || title
  });
  if (isValidBusinessIntroduction(aiSummary)) {
    return aiSummary;
  }

  const summary = composeBusinessIntroduction(signalText, url, {
    title,
    h1,
    prioritizeHero: Boolean(options.prioritizeHero)
  });
  return isValidBusinessIntroduction(summary) ? summary : "";
}

function collectPriorityTextCandidates(doc, prioritizeHero) {
  const candidates = [];
  const selectors = prioritizeHero
    ? ["main h2", "main p", "section h2", "section p", "header h2", "header p", ".hero h2", ".hero p", "[class*='hero'] h2", "[class*='hero'] p"]
    : ["main p", "section p", "article p"];

  for (const selector of selectors) {
    for (const node of Array.from(doc.querySelectorAll(selector)).slice(0, 12)) {
      const text = sanitizeText(node.textContent || "");
      if (!text || text.length < 20 || text.length > 260) {
        continue;
      }
      if (isNoiseText(text)) {
        continue;
      }
      candidates.push(text);
    }
    if (candidates.length >= 6) {
      break;
    }
  }

  const matched = candidates.filter((text) => containsIndustryKeyword(text));
  return matched.length ? matched.slice(0, 4) : candidates.slice(0, 4);
}

function isNoiseText(text) {
  return /\b(copyright|all rights reserved|privacy policy|terms of service|cookie|follow us|learn more|read more|home|about us|contact us)\b/i.test(text || "");
}

function containsIndustryKeyword(text) {
  return /\b(service|product|solution|company|business|provider|professional)\b/i.test(text || "");
}

function composeBusinessIntroduction(text, url, meta = {}) {
  const normalized = `${sanitizeText(text)} ${sanitizeText(url)}`.toLowerCase();
  const business = detectBusinessLabel(normalized);
  if (!business) {
    return "";
  }

  const service = detectServiceLabel(normalized);
  const audience = detectAudienceLabel(normalized);
  const advantage = detectAdvantageLabel(normalized);
  const direction = detectBusinessDirection(normalized);
  const scenarios = detectServiceScenarios(normalized);
  const products = detectProductScope(normalized, business);
  const positioning = detectIndustryPositioning(normalized);
  const coreSegments = [];
  const mailSegments = [];

  coreSegments.push(service ? `${business}${service}` : `${business}相关产品与服务`);
  if (products) {
    coreSegments.push(`覆盖${products}`);
  }
  if (positioning) {
    coreSegments.push(positioning);
  }

  if (audience) {
    mailSegments.push(`客户群体偏向${audience}`);
  }
  if (scenarios) {
    mailSegments.push(`应用场景含${scenarios}`);
  }
  if (direction) {
    mailSegments.push(`业务方向偏${direction}`);
  }
  if (advantage) {
    mailSegments.push(`卖点包括${advantage}`);
  }
  if (!mailSegments.length && meta.title) {
    mailSegments.push(`可围绕官网强调的${translateKeyword(meta.title)}切入合作沟通`);
  }

  const core = `核心业务提炼：${joinSegments(coreSegments, "，")}。`;
  const mail = `开发信可用要点：${joinSegments(mailSegments, "；")}。`;
  return `${core}\n${mail}`;
}

async function requestAiBusinessIntroduction(payload) {
  try {
    const response = await chrome.runtime.sendMessage({
      type: "GENERATE_BUSINESS_INTRO",
      payload
    });
    return response?.ok ? sanitizeText(response.result || "") : "";
  } catch (error) {
    return "";
  }
}

function detectBusinessLabel(text) {
  if (/\b(keyword1|keyword2)\b/i.test(text)) {
    return "Business Type A";
  }
  if (/\b(keyword3|keyword4)\b/i.test(text)) {
    return "Business Type B";
  }
  return "General Business";
}

function detectServiceLabel(text) {
  const hasFactory = /\b(factory|manufacturer|manufacturing|production|mill)\b/i.test(text);
  const hasSupply = /\b(supplier|supply|wholesale|distributor|dealer)\b/i.test(text);
  const hasInstall = /\b(install|installation|contractor|contracting)\b/i.test(text);
  const hasCustom = /\b(custom|customized|bespoke|oem|odm)\b/i.test(text);

  if (hasFactory && hasInstall && hasCustom) {
    return "Custom Production & Installation";
  }
  if (hasFactory && hasSupply) {
    return "Manufacturing & Supply";
  }
  if (hasSupply && hasInstall) {
    return "Supply & Installation";
  }
  if (hasInstall) {
    return "Installation Service";
  }
  if (hasFactory) {
    return "Manufacturing";
  }
  if (hasSupply) {
    return "Supply Service";
  }
  return "";
}

function detectAudienceLabel(text) {
  const audience = [];
  if (/\b(residential|homeowner|homeowners|backyard|garden|yard|patio)\b/i.test(text)) {
    audience.push("Residential");
  }
  if (/\b(commercial|retail|office|hospitality|hotel|business)\b/i.test(text)) {
    audience.push("Commercial");
  }
  if (/\b(contractor|builder|developer|architect)\b/i.test(text)) {
    audience.push("Contractors");
  }
  return audience.slice(0, 2).join(" & ");
}

function detectAdvantageLabel(text) {
  const advantages = [];
  if (/\b(factory direct|direct factory|source factory|manufacturer)\b/i.test(text)) {
    advantages.push("Direct from Source");
  }
  if (/\b(custom|customized|bespoke|oem|odm)\b/i.test(text)) {
    advantages.push("Customizable");
  }
  if (/\b(premium|high quality|durable|warranty|long lasting|weather resistant)\b/i.test(text)) {
    advantages.push("High Quality");
  }
  return advantages.slice(0, 3).join(", ");
}

function detectBusinessDirection(text) {
  const directions = [];
  if (/\b(rental|rentals|hire)\b/i.test(text)) {
    directions.push("Rental");
  }
  if (/\b(manufacturer|manufacturing|factory|production)\b/i.test(text)) {
    directions.push("Manufacturing");
  }
  if (/\b(retail|shop|store|online store)\b/i.test(text)) {
    directions.push("Retail");
  }
  if (/\b(wholesale|supplier|distributor|dealer)\b/i.test(text)) {
    directions.push("Wholesale");
  }
  return directions.slice(0, 3).join(", ");
}

function detectServiceScenarios(text) {
  const scenarios = [];
  if (/\b(outdoor|indoor|garden|office)\b/i.test(text)) {
    scenarios.push("General Scenario");
  }
  return scenarios.slice(0, 3).join(", ");
}

function detectProductScope(text, business) {
  const products = [];
  if (/\b(product1|product2)\b/i.test(text)) {
    products.push("Product Type A");
  }
  return uniqueValues(products).slice(0, 3).join(", ");
}

function detectIndustryPositioning(text) {
  if (/\b(one stop|full service|turnkey)\b/i.test(text)) {
    return "提供一站式解决方案";
  }
  if (/\b(specialist|expert|leader|professional)\b/i.test(text)) {
    return "强调专业化定位";
  }
  if (/\b(design build|design and install)\b/i.test(text)) {
    return "兼顾设计与落地";
  }
  return "";
}

function isValidBusinessIntroduction(text) {
  const normalized = sanitizeText(text);
  return normalized.length >= 20
    && normalized.length <= 220
    && normalized.includes("核心业务提炼：")
    && normalized.includes("开发信可用要点：")
    && /General Business|Business Type A|Business Type B/.test(normalized);
}

function limitChineseText(text, maxLength) {
  const normalized = sanitizeText(text).replace(/[,.!?;:]+$/g, "");
  if (normalized.length <= maxLength) {
    return normalized.endsWith("。") ? normalized : `${normalized}。`;
  }
  return `${normalized.slice(0, Math.max(0, maxLength - 1)).replace(/[，,；;、]+$/g, "")}。`;
}

function joinSegments(list, separator) {
  return uniqueValues((list || []).map((item) => sanitizeText(item)).filter(Boolean)).join(separator) || "信息有限";
}

function translateKeyword(text) {
  const normalized = sanitizeText(text);
  return limitChineseText(
    normalized
      .replace(/\b(supplier|provider)\b/ig, "供应能力")
      .replace(/\b(service|solution)\b/ig, "服务项目")
      .replace(/\b(company|business)\b/ig, "企业信息"),
    36
  );
}

function buildLeadKey(record) {
  return buildLeadIdentityKeys(record)[0] || "";
}

function findLeadIndex(list, record) {
  const targetKeys = new Set(buildLeadIdentityKeys(record));
  return (list || []).findIndex((item) => buildLeadIdentityKeys(item).some((key) => targetKeys.has(key)));
}

function buildLeadIdentityKeys(record) {
  const keys = [];
  const websiteHost = normalizeWebsiteHost(record.website || "");
  if (websiteHost) {
    keys.push(`website:${websiteHost}`);
  }

  const email = String(record.email || "").trim().toLowerCase();
  if (email) {
    keys.push(`email:${email}`);
  }

  const phone = normalizePhone(record.phone || "");
  if (phone) {
    keys.push(`phone:${phone}`);
  }

  const normalizedName = normalizeCompanyName(record.companyName || "");
  const normalizedAddress = normalizeTextFingerprint(record.address || "");
  const normalizedCity = normalizeTextFingerprint(record.city || "");
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

function pickCanonicalCompanyName(baseRecord, remoteRecord, sourceLabel) {
  const baseName = sanitizeText(baseRecord.companyName || "");
  const remoteName = sanitizeText(remoteRecord.companyName || "");
  if (sourceLabel === "官网" && remoteName) {
    return remoteName;
  }
  if (!baseName) {
    return remoteName;
  }
  if (!remoteName) {
    return baseName;
  }
  return remoteName.length > baseName.length ? remoteName : baseName;
}

function extractWebsiteCompanyName(doc, url) {
  const candidates = [
    sanitizeText(doc.querySelector('meta[property="og:site_name"]')?.getAttribute("content") || ""),
    sanitizeText(doc.querySelector('meta[name="application-name"]')?.getAttribute("content") || ""),
    sanitizeText(doc.querySelector("h1")?.textContent || ""),
    sanitizeText(doc.querySelector("title")?.textContent || "")
  ]
    .map((item) => cleanCompanyNameCandidate(item))
    .filter(Boolean);

  const hostLabel = cleanCompanyNameCandidate(deriveBrandFromUrl(url));
  const matched = candidates.find((item) => isLikelyCompanyName(item, hostLabel));
  return matched || candidates[0] || hostLabel || "";
}

function cleanCompanyNameCandidate(value) {
  return sanitizeText(String(value || ""))
    .replace(/\s*[|¦·-].*$/, "")
    .replace(/\b(home|homepage|welcome|official site|official website)\b/ig, "")
    .replace(/\s{2,}/g, " ")
    .trim();
}

function deriveBrandFromUrl(url) {
  try {
    const { hostname } = new URL(url);
    return hostname.replace(/^www\./i, "").split(".")[0].replace(/[-_]+/g, " ");
  } catch (error) {
    return "";
  }
}

function isLikelyCompanyName(value, hostLabel) {
  const normalized = cleanCompanyNameCandidate(value);
  if (!normalized || normalized.length < 2) {
    return false;
  }
  if (/^(contact|about|services|products|blog|news)$/i.test(normalized)) {
    return false;
  }
  if (hostLabel && normalizeCompanyName(normalized).includes(normalizeCompanyName(hostLabel))) {
    return true;
  }
  return normalized.split(/\s+/).length <= 8;
}

function normalizeWebsiteHost(value) {
  try {
    return new URL(value).hostname.replace(/^www\./i, "").toLowerCase();
  } catch (error) {
    return String(value || "").trim().toLowerCase().replace(/^https?:\/\//i, "").replace(/^www\./i, "").split("/")[0];
  }
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

async function waitFor(checker, timeoutMs = 15000, errorMessage = "页面元素等待超时。") {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    const value = checker();
    if (value) {
      return value;
    }
    await sleep(300);
  }
  throw new Error(errorMessage);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function navigateToSearchResults(query) {
  const origin = location.origin || "https://www.google.com";
  const targetUrl = `${origin}/maps/search/${encodeURIComponent(query)}`;
  location.assign(targetUrl);
  await waitFor(() => hasSearchResults() || getResultsContainer() || hasNoResultsState(), 30000, "搜索结果列表加载超时");
}

function setupCommandBridge() {
  if (globalThis.__GMH_COMMAND_BRIDGE_READY__) {
    return;
  }

  globalThis.__GMH_COMMAND_BRIDGE_READY__ = true;

  chrome.storage.onChanged.addListener((changes, areaName) => {
    if (areaName !== "local" || !changes.gmh_command?.newValue) {
      return;
    }
    processCommand(changes.gmh_command.newValue);
  });

  chrome.storage.local.get("gmh_command").then((result) => {
    if (result.gmh_command) {
      processCommand(result.gmh_command);
    }
  });
}

async function processCommand(command) {
  if (!command || !isGoogleMapsPage()) {
    return;
  }

  const processedIssuedAt = getProcessedCommandIssuedAt();
  if (command.issuedAt && (command.issuedAt <= runtimeState.lastCommandIssuedAt || command.issuedAt <= processedIssuedAt)) {
    return;
  }

  runtimeState.lastCommandIssuedAt = command.issuedAt || Date.now();
  setProcessedCommandIssuedAt(runtimeState.lastCommandIssuedAt);

  if (command.type === "STOP_SCRAPE") {
    runtimeState.stopRequested = true;
    await patchState({ running: false, status: "已停止", detail: "用户手动停止了当前任务。" });
    return;
  }

  if (command.type === "START_SCRAPE") {
    startScrape(command.payload).catch(async (error) => {
      await patchState({ running: false, status: "异常停止", detail: error.message });
    });
  }
}

function getSearchInput() {
  const direct = findFirstDeep((root) =>
    root.querySelector("#searchboxinput")
    || root.querySelector(".searchboxinput")
    || root.querySelector('input[name="q"]')
    || root.querySelector('input[aria-label*="Google Maps"]')
    || root.querySelector('input[aria-label*="Google 地图"]')
    || root.querySelector('input[placeholder*="Google Maps"]')
    || root.querySelector('input[placeholder*="Google 地图"]')
    || root.querySelector('input[role="combobox"]')
  );
  if (isUsableSearchInput(direct)) {
    return direct;
  }

  const candidates = findAllDeep("input, textarea");
  return candidates.find(isUsableSearchInput) || null;
}

async function waitForSearchInput() {
  const direct = getSearchInput();
  if (direct) {
    return direct;
  }
  try {
    return await waitFor(() => getSearchInput(), 8000, "未找到 Google Maps 搜索框");
  } catch (error) {
    return null;
  }
}

function getSearchButton() {
  const direct = findFirstDeep((root) =>
    root.querySelector("#searchbox-searchbutton")
    || root.querySelector('button[aria-label*="Search"]')
    || root.querySelector('button[aria-label*="搜索"]')
  );
  if (direct) {
    return direct;
  }

  const buttons = findAllDeep("button");
  return buttons.find((button) => {
    const label = getSearchNodeLabel(button);
    return /search|搜索/.test(label);
  }) || null;
}

function hasSearchResults() {
  return Boolean(
    document.querySelector('[role="feed"] a[href*="/maps/place/"]')
    || document.querySelector('[role="feed"] [role="article"]')
    || document.querySelector('.Nv2PK')
    || document.querySelector('.Nv2PK.THOPZb')
    || document.querySelector('a.hfpxzc[href*="/maps/place/"]')
    || document.querySelector('a[href*="/maps/place/"][href*="!4m"]')
    || document.querySelector('a[href*="/maps/place/"]')
    || document.querySelector('[role="main"] [data-result-index]')
    || document.querySelector('div[role="feed"]')
  );
}

function hasNoResultsState() {
  const text = sanitizeText(document.body?.innerText || "");
  return /no results found|no results|did not match any locations|找不到结果|没有结果/.test(text);
}

function hasSearchResultsForQuery(query) {
  const input = getSearchInput();
  const currentValue = String(input?.value || "").trim().toLowerCase();
  const normalizedQuery = String(query || "").trim().toLowerCase();
  const sidePanelText = getResultsContainer()?.innerText?.toLowerCase() || "";
  return Boolean(
    hasSearchResults()
    && (
      (currentValue && normalizedQuery && currentValue === normalizedQuery)
      || sidePanelText.includes(normalizedQuery)
    )
  );
}

function getResultsContainer() {
  return findFirstDeep((root) =>
    root.querySelector('[role="feed"]')
    || root.querySelector('[role="main"] [role="feed"]')
    || root.querySelector('div[role="main"] [aria-label][tabindex="-1"]')
    || root.querySelector('.m6QErb[aria-label]')
    || root.querySelector('.m6QErb.DxyBCb')
    || root.querySelector('.m6QErb[tabindex="-1"]')
    || root.querySelector('[role="main"] .m6QErb')
    || root.querySelector('.Nv2PK')
      ?.closest('.m6QErb')
  );
}

function isMapsShellReady() {
  return Boolean(getSearchInput() || hasSearchResults() || getResultsContainer() || document.querySelector("#scene"));
}

function getBusinessTitleNode() {
  return document.querySelector("h1.DUwDvf")
    || document.querySelector("h1")
    || document.querySelector('[role="main"] h1');
}

function setNativeInputValue(input, value) {
  if (input instanceof HTMLInputElement) {
    const descriptor = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value");
    descriptor?.set?.call(input, value);
    return;
  }
  if (input instanceof HTMLTextAreaElement) {
    const descriptor = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value");
    descriptor?.set?.call(input, value);
    return;
  }
  input.value = value;
}

function extractLeadFromCard(element) {
  const text = element?.innerText || "";
  const lines = text
    .split(/\n+/)
    .map((item) => sanitizeText(item))
    .filter(Boolean);

  return {
    companyName: extractCardCompanyName(element, lines),
    phone: extractCardPhone(text),
    email: "",
    address: extractCardAddress(lines),
    website: extractCardWebsite(element),
    businessIntroduction: "",
    socialLinks: extractCardSocialLinks(element),
    rating: extractCardRating(element, lines),
    hours: extractCardHours(lines),
    category: classifyBusiness(lines.join(" ")),
    contactPerson: "",
    procurementInfo: ""
  };
}

function extractCardCompanyName(element, lines) {
  const anchorTitle = element.querySelector('a[href*="/maps/place/"]');
  const ariaLabel = sanitizeText(anchorTitle?.getAttribute("aria-label") || "");
  if (ariaLabel) {
    return ariaLabel;
  }

  const heading = element.querySelector("h3, h4, [role='heading']");
  const headingText = sanitizeText(heading?.textContent || "");
  if (headingText) {
    return headingText;
  }

  return lines[0] || "";
}

function extractCardRating(element, lines) {
  const ratingNode = element.querySelector('[role="img"][aria-label*="星"], [role="img"][aria-label*="star"]');
  const ratingText = ratingNode?.getAttribute("aria-label") || "";
  const directMatch = ratingText.match(/([0-9.]+)/);
  if (directMatch?.[1]) {
    return directMatch[1];
  }

  for (const line of lines.slice(0, 4)) {
    const match = line.match(/^([0-9.]+)\s*[★⭐]?/);
    if (match?.[1]) {
      return match[1];
    }
  }

  return "";
}

function extractCardPhone(text) {
  const phones = text.match(/(?:\+\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{4,}/g) || [];
  return phones.find((item) => item.replace(/\D/g, "").length >= 7) || "";
}

function extractCardWebsite(element) {
  const links = Array.from(element.querySelectorAll("a[href]"));
  const website = links.find((link) => {
    const href = link.href || "";
    return /^https?:\/\//i.test(href)
      && !href.includes("google.")
      && !SOCIAL_HOSTS.some((host) => href.includes(host));
  });
  return website?.href || "";
}

function extractCardSocialLinks(element) {
  return uniqueValues(
    Array.from(element.querySelectorAll("a[href]"))
      .map((link) => link.href)
      .filter((href) => SOCIAL_HOSTS.some((host) => href.includes(host)))
  );
}

function extractCardAddress(lines) {
  return lines.find((line) => /\d+.*\b(st|street|rd|road|ave|avenue|blvd|boulevard|dr|drive|suite|ste)\b/i.test(line)) || "";
}

function extractCardHours(lines) {
  return lines.find((line) => /营业|open|closed|hours/i.test(line)) || "";
}

function normalizeName(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim();
}

function findFirstDeep(findInRoot, root = document) {
  const visited = new Set();
  const queue = [root];
  while (queue.length) {
    const current = queue.shift();
    if (!current || visited.has(current)) {
      continue;
    }
    visited.add(current);
    const found = findInRoot(current);
    if (found) {
      return found;
    }
    const elements = current.querySelectorAll ? Array.from(current.querySelectorAll("*")) : [];
    for (const element of elements) {
      if (element.shadowRoot) {
        queue.push(element.shadowRoot);
      }
    }
  }
  return null;
}

function findAllDeep(selector, root = document) {
  const visited = new Set();
  const queue = [root];
  const results = [];
  while (queue.length) {
    const current = queue.shift();
    if (!current || visited.has(current)) {
      continue;
    }
    visited.add(current);
    if (current.querySelectorAll) {
      results.push(...Array.from(current.querySelectorAll(selector)));
      const elements = Array.from(current.querySelectorAll("*"));
      for (const element of elements) {
        if (element.shadowRoot) {
          queue.push(element.shadowRoot);
        }
      }
    }
  }
  return uniqueValues(results);
}

function isUsableSearchInput(node) {
  if (!node) {
    return false;
  }
  const tagName = String(node.tagName || "").toLowerCase();
  if (!["input", "textarea"].includes(tagName)) {
    return false;
  }
  if (node.disabled || node.readOnly) {
    return false;
  }
  if (!isNodeVisible(node)) {
    return false;
  }
  const type = String(node.getAttribute("type") || "").toLowerCase();
  if (tagName === "input" && type && !["text", "search"].includes(type)) {
    return false;
  }
  if (node.id === "searchboxinput" || node.name === "q") {
    return true;
  }
  const label = getSearchNodeLabel(node);
  return /search|搜索|查找|在此搜索|google maps|google 地图|maps/.test(label);
}

function getSearchNodeLabel(node) {
  return [
    node?.id,
    node?.name,
    node?.getAttribute?.("aria-label"),
    node?.getAttribute?.("placeholder"),
    node?.getAttribute?.("role"),
    node?.className,
    node?.textContent
  ]
    .map((item) => sanitizeText(item))
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

function isNodeVisible(node) {
  if (!(node instanceof Element)) {
    return false;
  }
  const style = window.getComputedStyle(node);
  if (style.display === "none" || style.visibility === "hidden" || style.opacity === "0") {
    return false;
  }
  const rect = node.getBoundingClientRect();
  return rect.width > 0 && rect.height > 0;
}

function getProcessedCommandIssuedAt() {
  try {
    return Number(sessionStorage.getItem(PROCESSED_COMMAND_KEY) || 0);
  } catch (error) {
    return 0;
  }
}

function setProcessedCommandIssuedAt(value) {
  try {
    sessionStorage.setItem(PROCESSED_COMMAND_KEY, String(value || 0));
  } catch (error) {
    // ignore session storage failures
  }
}
