#!/usr/bin/env node
/**
 * 数据恢复脚本：将备份的 JSON 文件通过 API 批量提交回 HF 实例
 * 用法: cd web && node restore-data.js --base-url https://wuliao666-iptv-server.hf.space
 *
 * 数据文件放在 web 目录：config.json、setting.json、template.json、iptv_list.json
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = __dirname;

const BASE_URL = process.argv.includes("--base-url")
  ? process.argv[process.argv.indexOf("--base-url") + 1].replace(/\/$/, "")
  : "http://localhost:7860";

const AUTH_TOKEN = process.argv.includes("--token")
  ? process.argv[process.argv.indexOf("--token") + 1]
  : "9b8933c9f5a0481cafd5b36926081c5e";

const HEADERS = {
  "Content-Type": "application/json",
  "X-Auth-Token": AUTH_TOKEN,
};

async function req(method, url, body) {
  const resp = await fetch(url, {
    method,
    headers: HEADERS,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await resp.json();
  if (!resp.ok) throw new Error(`${method} ${url} -> ${resp.status}: ${JSON.stringify(data)}`);
  return data;
}

async function restoreSettings() {
  const file = path.join(ROOT, "setting.json");
  if (!fs.existsSync(file)) { console.log("⏭️ setting.json 不存在，跳过"); return; }
  const s = JSON.parse(fs.readFileSync(file, "utf8"));

  console.log("📝 恢复全局设置...");
  await req("PUT", `${BASE_URL}/api/settings`, {
    githubEnabled: s.github?.enabled ?? true,
    githubToken: s.github?.token ?? "",
    githubUserResultQuery: s.github?.userResultQuery ?? "",
    githubUserResultFetchCron: s.github?.userResultFetchCron ?? "",
    githubUserResultUrls: s.github?.userResultUrls ?? "",
    ozoneEnabled: s.ozone?.enabled ?? false,
    ozoneFetchCron: s.ozone?.fetchCron ?? "",
    zoomeyeEnabled: s.zoomeye?.enabled ?? false,
    zoomeyeFetchCron: s.zoomeye?.fetchCron ?? "",
    daydaymapEnabled: s.daydaymap?.enabled ?? false,
    daydaymapFetchCron: s.daydaymap?.fetchCron ?? "",
    hunterEnabled: s.hunter?.enabled ?? false,
    hunterApiKey: s.hunter?.apiKey ?? "",
    hunterFetchCron: s.hunter?.fetchCron ?? "",
    concurrency: s.engine?.concurrency ?? 64,
    timeout: s.engine?.timeout ?? 2000,
    configDelay: s.engine?.configDelay ?? 3,
    janitorCron: s.scheduling?.janitorCron ?? "",
    scanCron: s.scheduling?.scanCron ?? "",
    hfSyncCron: s.scheduling?.hfSyncCron ?? "",
    callbackToken: s.security?.callbackToken ?? "",
  });
  console.log("✅ 全局设置恢复完成");
}

async function restoreTemplates() {
  const file = path.join(ROOT, "template.json");
  if (!fs.existsSync(file)) { console.log("⏭️ template.json 不存在，跳过"); return {}; }
  const list = JSON.parse(fs.readFileSync(file, "utf8"));

  if (!Array.isArray(list) || list.length === 0) { console.log("⏭️ 无模板数据"); return {}; }

  // 先删除已有模板（防止重复）
  const existing = await req("GET", `${BASE_URL}/api/templates`);
  if (Array.isArray(existing) && existing.length > 0) {
    console.log(`  🗑️ 清理 ${existing.length} 条旧模板...`);
    for (const t of existing) {
      await req("DELETE", `${BASE_URL}/api/templates/${t.id}`);
    }
  }

  // 按原始 ID 升序恢复，让 auto_increment 对齐
  const sorted = [...list].sort((a, b) => a.id - b.id);
  console.log(`📝 恢复 ${sorted.length} 条模板（按 ID 升序）...`);

  const idMap = {};
  for (const t of sorted) {
    const resp = await req("POST", `${BASE_URL}/api/templates`, {
      name: t.name,
      region: t.region,
      operator: t.operator,
      targetName: t.targetName,
      targetAddress: t.targetAddress,
    });
    idMap[t.id] = resp.id;
    if (resp.id !== t.id) {
      console.log(`  ⚠️ 模板 "${t.name}" id 映射: ${t.id} -> ${resp.id}`);
    }
  }
  console.log("✅ 模板恢复完成");
  return idMap;
}

async function restoreConfigs(templateIdMap) {
  const file = path.join(ROOT, "config.json");
  if (!fs.existsSync(file)) { console.log("⏭️ config.json 不存在，跳过"); return; }
  const list = JSON.parse(fs.readFileSync(file, "utf8"));

  if (!Array.isArray(list) || list.length === 0) { console.log("⏭️ 无扫描配置数据"); return; }

  // 先删除已有配置
  const existing = await req("GET", `${BASE_URL}/api/configs`);
  if (Array.isArray(existing) && existing.length > 0) {
    console.log(`  🗑️ 清理 ${existing.length} 条旧配置...`);
    for (const c of existing) {
      await req("DELETE", `${BASE_URL}/api/configs/${c.id}`);
    }
  }

  console.log(`📝 恢复 ${list.length} 条扫描配置...`);

  for (const c of list) {
    const newTemplateId = templateIdMap[c.templateId];
    if (!newTemplateId) {
      console.log(`  ❌ "${c.name}" 找不到模板映射 templateId=${c.templateId}，跳过`);
      continue;
    }
    const resp = await req("POST", `${BASE_URL}/api/configs`, {
      name: c.name,
      templateId: newTemplateId,
      dataSource: c.dataSource,
      searchDepth: c.searchDepth ?? 30,
      enabled: !!c.enabled,
    });
    console.log(`  ✅ "${c.name}" -> id=${resp.id}`);
  }
  console.log("✅ 扫描配置恢复完成");
}

async function restoreIptv() {
  const file = path.join(ROOT, "iptv_list.json");
  if (!fs.existsSync(file)) { console.log("⏭️ iptv_list.json 不存在，跳过"); return; }
  const data = JSON.parse(fs.readFileSync(file, "utf8"));

  // 支持两种格式：iptv-pool 分组格式 / iptv-db/list 平铺格式
  let list;
  if (data.groups && Array.isArray(data.groups)) {
    list = [];
    for (const g of data.groups) {
      for (const h of (g.heads || [])) {
        const [ip, portStr] = h.host.includes(":")
          ? h.host.split(":")
          : [h.host, "80"];
        list.push({
          id: h.id ?? null,
          host: h.host,
          ip,
          port: parseInt(portStr, 10) || 80,
          sourceType: h.sourceType || "",
          sourceName: h.sourceName || "",
          region: g.region || "",
          operator: g.operator || "",
          geoRegion: h.geoRegion || "",
          geoOperator: h.geoOperator || "",
          delay: h.latencyMs ?? h.delay ?? 0,
          protocol: h.protocol || "rtp",
          target: h.target || "",
          channelName: h.channelName || "",
          createTime: h.createTime ? Math.floor(new Date(h.createTime).getTime()) : 0,
          updateTime: h.updateTime
            ? (typeof h.updateTime === "number" ? h.updateTime : Math.floor(new Date(h.updateTime).getTime()))
            : 0,
        });
      }
    }
  } else {
    list = Array.isArray(data) ? data : data.data;
  }

  if (!Array.isArray(list) || list.length === 0) { console.log("⏭️ 无活源数据"); return; }
  console.log(`📝 恢复 ${list.length} 条活源数据...`);

  const BATCH = 100;
  for (let i = 0; i < list.length; i += BATCH) {
    const batch = list.slice(i, i + BATCH);
    const resp = await req("POST", `${BASE_URL}/api/iptv-db/import`, batch);
    console.log(`  批次 ${Math.floor(i / BATCH) + 1}: ${resp.imported} 条`);
  }
  console.log(`✅ 活源数据恢复完成`);
}

(async () => {
  console.log(`🚀 开始数据恢复 -> ${BASE_URL}\n`);
  try {
    // await restoreSettings();
    // const idMap = await restoreTemplates();
    // await restoreConfigs(idMap);
    await restoreIptv();
    console.log("\n🎉 全部数据恢复完成！");
  } catch (e) {
    console.error(`\n❌ 恢复失败: ${e.message}`);
    process.exit(1);
  }
})();
