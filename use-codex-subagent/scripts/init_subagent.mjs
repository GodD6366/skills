#!/usr/bin/env node

import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import { createInterface } from "node:readline";
import { homedir } from "node:os";
import { resolve } from "node:path";
import { parseArgs } from "node:util";

const THINKING_LEVELS = ["low", "medium", "high", "xhigh"];
const BASE_MODEL_PROVIDERS = [
  { key: "gpt-4o", name: "OpenAI Base", model: "gpt-4o" },
  { key: "gpt-4o-mini", name: "OpenAI Base", model: "gpt-4o-mini" },
  { key: "o3-mini", name: "OpenAI Base", model: "o3-mini" },
];

const ROLES = [
  {
    key: "explorer",
    desc: "定位与取证 — 搜索代码、定位文件、查调用链、收集证据",
    defaultModel: "gpt-4o-mini",
    defaultThinking: "medium",
    sandboxMode: "read-only",
    nicknameCandidates: ["Scout", "Trace", "Atlas"],
    developerInstructions: `Stay in exploration mode.

Use fast search and targeted file reads to map the real code path.
Return exact file paths, symbols, and line references.
Distinguish confirmed facts from hypotheses.
Summarize only the evidence needed for the parent agent to decide the next step.

Prefer:
- locating entry points, owners, call chains, config sources, and impact radius
- concise snippets or line references instead of full-file dumps
- read-heavy work that can be summarized cleanly

Do not:
- modify files or generate patches
- propose broad fixes unless the parent agent asks
- expand into unrelated areas or repeat work already assigned elsewhere

If the implementation path is clear, say so.
If the remaining question is architectural, ambiguous, or risk-heavy, recommend planner.`,
  },
  {
    key: "planner",
    desc: "方案与规划 — 根因分析、最小方案设计、风险评估",
    defaultModel: "gpt-4o",
    defaultThinking: "xhigh",
    sandboxMode: "read-only",
    nicknameCandidates: ["Helm", "Northstar", "Sage"],
    developerInstructions: `Work from evidence, not broad repository exploration.

Use the parent agent's supplied context to:
- identify the root cause
- compare the smallest viable fixes
- choose the safest implementation path
- define validation and rollback considerations

Optimize for minimal, defensible changes.
Call out assumptions, compatibility risks, and unknowns.
When more code discovery is needed, ask for a narrow explorer follow-up instead of searching broadly yourself.

Do not:
- do large mechanical searches
- implement patches unless the parent agent explicitly asks
- recommend multi-file rewrites when a smaller fix is sufficient

Return:
- root cause
- recommended fix
- affected files or modules
- key risks
- validation plan

If the path is clear, hand off to the parent agent for implementation.`,
  },
  {
    key: "worker",
    desc: "实现与执行 — 按方案实施代码修改，最小改动",
    defaultModel: "gpt-4o",
    defaultThinking: "high",
    sandboxMode: "workspace-write",
    nicknameCandidates: ["Patch", "Forge", "Bolt"],
    developerInstructions: `Own implementation only after the target behavior, files, and boundaries are clear.

Make the smallest coherent change that solves the assigned task.
Stay within the assigned files or responsibility boundary.
Preserve existing behavior outside the requested scope.
Validate the changed behavior with the narrowest useful checks.

You are not alone in the codebase:
- do not revert edits you did not make
- adapt to concurrent changes when possible
- stop and report if another change creates a real conflict

Do not:
- redesign architecture without explicit instruction
- expand scope into unrelated cleanup
- invent new abstractions unless they are required to complete the fix

Report:
- modified files
- behavior changed
- validation performed
- remaining risks or gaps`,
  },
  {
    key: "verifier",
    desc: "验证与测试 — 运行测试、复现问题、检查行为",
    defaultModel: "gpt-4o-mini",
    defaultThinking: "medium",
    sandboxMode: "read-only",
    nicknameCandidates: ["Check", "Probe", "Gauge"],
    developerInstructions: `Verify the assigned behavior, command, or risk area.

Prefer real tests, builds, typechecks, logs, browser checks, or API checks over trusting summaries.
Keep the scope narrow and report the exact command or inspection performed.

Do not:
- change production code
- broaden the task into implementation
- mask failures or omit relevant output

If verification fails, include:
- failing command or check
- key output
- suspected cause if evidence supports it
- whether a targeted fixer should be used

Return PASS, FAIL, or INCONCLUSIVE with concise evidence.`,
  },
  {
    key: "reviewer",
    desc: "代码审查 — 审查实现是否符合需求、质量、风险",
    defaultModel: "gpt-4o",
    defaultThinking: "xhigh",
    sandboxMode: "read-only",
    nicknameCandidates: ["Lens", "Guard", "Critic"],
    developerInstructions: `Review the implementation against the user request and repository conventions.

Look for:
- missing requirements
- incorrect behavior
- unnecessary scope expansion
- maintainability issues
- regression risks
- weak or missing tests
- security or compatibility concerns

Do not nitpick style unless it affects correctness, maintainability, or local conventions.
Do not modify files.

Return:
- verdict: APPROVED or REQUEST_CHANGES
- findings ordered by severity
- exact files and line references when possible
- tests that should still be run`,
  },
  {
    key: "fixer",
    desc: "定点修复 — 针对失败测试或 review 做局部补救",
    defaultModel: "gpt-4o",
    defaultThinking: "high",
    sandboxMode: "workspace-write",
    nicknameCandidates: ["Mend", "Patch", "Triage"],
    developerInstructions: `Fix exactly one assigned failure or review finding.

Use the provided failure output, review finding, or parent-agent instructions as the boundary.
Make the smallest safe change and preserve all unrelated work.
Run the failing check again when possible.

Do not:
- redesign the solution
- fix unrelated issues
- touch files outside the assigned scope unless explicitly necessary and reported

Report:
- status
- changed files
- what changed
- verification result
- remaining risk`,
  },
];

function parseConfig(configPath) {
  if (!existsSync(configPath)) return [];

  const text = readFileSync(configPath, "utf-8");
  const providerRe = /^\[model_providers\.(\w+)\]\s*\n([\s\S]*?)(?=^\[|$(?![\s\S]))/gm;
  const profileRe = /^\[profiles\.(\w+)\]\s*\n([\s\S]*?)(?=^\[|$(?![\s\S]))/gm;

  function extractField(block, field) {
    const m = block.match(new RegExp(`^${field}\\s*=\\s*"([^"]*)"`, "m"));
    return m?.[1] ?? null;
  }

  const profileModels = {};
  for (const m of text.matchAll(profileRe)) {
    const model = extractField(m[2], "model");
    if (model) profileModels[m[1]] = model;
  }

  const providers = [];
  const seen = new Set();
  for (const m of text.matchAll(providerRe)) {
    const key = m[1];
    const block = m[2];
    const name = extractField(block, "name") ?? key;
    const model = profileModels[key] ?? "";
    const isCustom = !BASE_MODEL_PROVIDERS.some((bp) => bp.key === key);

    let baseUrl = null;
    let apiKey = null;
    if (isCustom) {
      baseUrl = extractField(block, "base_url");
      apiKey = extractField(block, "api_key") ?? extractField(block, "experimental_bearer_token");
    }

    const dedup = `${key}:${model}`;
    if (seen.has(dedup)) continue;
    seen.add(dedup);
    providers.push({ key, name, model, isCustom, baseUrl, apiKey });
  }
  return providers;
}

function withBaseModelProviders(providers) {
  const seen = new Set(providers.map((p) => `${p.key}:${p.model}`));
  const merged = [...providers];

  for (const provider of BASE_MODEL_PROVIDERS) {
    const dedup = `${provider.key}:${provider.model}`;
    if (seen.has(dedup)) continue;
    seen.add(dedup);
    merged.push({ ...provider, isCustom: false, baseUrl: null, apiKey: null });
  }

  return merged;
}

// --- Custom provider model discovery ---

async function fetchModelsFromProvider(provider) {
  const base = (provider.baseUrl || "").replace(/\/+$/, "");
  if (!base) return [];

  const url = base.endsWith("/v1") ? `${base}/models` : `${base}/v1/models`;
  const headers = { "Content-Type": "application/json" };
  if (provider.apiKey) {
    headers["Authorization"] = `Bearer ${provider.apiKey}`;
  }

  let resp;
  try {
    resp = await fetch(url, { headers, signal: AbortSignal.timeout(10000) });
  } catch (e) {
    console.error(`  ⚠ 无法连接 ${provider.name} (${url}): ${e.message}`);
    return [];
  }

  if (!resp.ok) {
    console.error(`  ⚠ ${provider.name} 模型列表请求失败: HTTP ${resp.status}`);
    return [];
  }

  let data;
  try {
    data = await resp.json();
  } catch {
    console.error(`  ⚠ ${provider.name} 返回数据解析失败`);
    return [];
  }

  const models = (data.data || []).map((m) => m.id).filter(Boolean).sort();
  return models;
}

async function enrichCustomProviders(providers) {
  const result = [];
  let hasCustomModels = false;

  for (const p of providers) {
    if (!p.isCustom || !p.baseUrl) {
      result.push(p);
      continue;
    }

    console.error(`  🔍 正在查询 ${p.name} 支持的模型列表...`);
    const models = await fetchModelsFromProvider(p);

    if (models.length === 0) {
      console.error(`  ⚠ ${p.name} 模型列表为空或不可用，回退到配置中的模型 "${p.model || "(无)"}"`);
      result.push(p);
      continue;
    }

    console.error(`  ✅ ${p.name} 提供 ${models.length} 个模型`);
    hasCustomModels = true;
    for (const model of models) {
      result.push({
        key: p.key,
        name: p.name,
        model,
        isCustom: true,
        baseUrl: p.baseUrl,
        apiKey: p.apiKey,
      });
    }
  }

  // 仅在没有自定义模型可用时才补充内置模型
  return hasCustomModels ? result : withBaseModelProviders(result);
}

function printProviders(providers) {
  if (!providers.length) {
    console.log("  (无可用 provider)");
    return;
  }
  const keyW = Math.max(3, ...providers.map((p) => p.key.length));
  const nameW = Math.max(4, ...providers.map((p) => p.name.length));
  const hdr = `  # `.padEnd(6) + `Key`.padEnd(keyW) + ` Name`.padEnd(nameW + 1) + ` Model`;
  console.log(hdr);
  console.log("  " + "-".repeat(hdr.length - 2));
  for (let i = 0; i < providers.length; i++) {
    const p = providers[i];
    console.log(
      `  ${String(i + 1).padEnd(4)}${p.key.padEnd(keyW)} ${p.name.padEnd(nameW)} ${p.model}`
    );
  }
}

function printSummary(selections) {
  console.log("\n" + "═".repeat(66));
  console.log("✅ 配置摘要\n");
  console.log(
    "  " + "角色".padEnd(12) + "模型Key".padEnd(28) + "模型".padEnd(22) + "思考强度"
  );
  console.log("  " + "-".repeat(66));
  for (const s of selections) {
    const key = s.key ?? "(未匹配)";
    console.log(`  ${s.role.padEnd(12)}${key.padEnd(28)}${s.model.padEnd(22)}${s.thinking}`);
  }
}

function tomlEscape(s) {
  return s.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
}

function renderAgentToml(roleSpec, model, thinking) {
  const nicknames = roleSpec.nicknameCandidates.map((n) => `"${tomlEscape(n)}"`).join(", ");
  return `name = "${tomlEscape(roleSpec.key)}"
description = "${tomlEscape(roleSpec.desc)}"
model = "${tomlEscape(model)}"
model_reasoning_effort = "${tomlEscape(thinking)}"
sandbox_mode = "${tomlEscape(roleSpec.sandboxMode)}"
nickname_candidates = [${nicknames}]
developer_instructions = """
${roleSpec.developerInstructions.trimEnd()}
"""
`;
}

function writeAgents(selections, targetDir, force) {
  mkdirSync(targetDir, { recursive: true });

  const created = [];
  const overwritten = [];
  const skipped = [];
  const backups = [];
  const bakDir = resolve(targetDir, "baks");

  for (const s of selections) {
    const roleSpec = ROLES.find((r) => r.key === s.role);
    const filePath = resolve(targetDir, `${s.role}.toml`);

    if (existsSync(filePath) && !force) {
      skipped.push(filePath);
      continue;
    }

    if (existsSync(filePath) && force) {
      mkdirSync(bakDir, { recursive: true });
      const ts = new Date().toISOString().replace(/[-:T]/g, "").slice(0, 14);
      const bakName = `${s.role}.toml.bak.${ts}`;
      const backupPath = resolve(bakDir, bakName);
      renameSync(filePath, backupPath);
      backups.push(backupPath);
      overwritten.push(filePath);
    } else {
      created.push(filePath);
    }

    const modelForToml = s.model;
    const content = renderAgentToml(roleSpec, modelForToml, s.thinking);
    writeFileSync(filePath, content, "utf-8");
  }

  if (created.length) {
    console.log("\n📄 已创建:");
    for (const p of created) console.log(`  ${p}`);
  }
  if (overwritten.length) {
    console.log("\n📄 已覆盖:");
    for (const p of overwritten) console.log(`  ${p}`);
  }
  if (backups.length) {
    console.log("\n💾 备份:");
    for (const p of backups) console.log(`  ${p}`);
  }
  if (skipped.length) {
    console.log("\n⏭ 已跳过 (文件已存在，使用 --force 覆盖):");
    for (const p of skipped) console.log(`  ${p}`);
  }
}

async function interactiveSetup(providers) {
  const rl = createInterface({ input: process.stdin, output: process.stdout });
  const ask = (q) => new Promise((res) => rl.question(q, res));

  console.log("\n╔══════════════════════════════════════════════╗");
  console.log("║   Codex Subagent 配置向导                    ║");
  console.log("╚══════════════════════════════════════════════╝\n");

  console.log("📋 可用 Model Providers (输入编号或 Key):\n");
  printProviders(providers);
  console.log();

  console.log("🧠 思考强度等级: 1.low  2.medium  3.high  4.xhigh\n");
  console.log("─".repeat(50));

  const selections = [];

  function findDefaultIdx(model) {
    const p = providers.find((pr) => pr.model === model);
    return p ? providers.indexOf(p) + 1 : 0;
  }

  for (const role of ROLES) {
    const defaultIdx = findDefaultIdx(role.defaultModel);
    const defaultLabel = defaultIdx ? `${defaultIdx}` : role.defaultModel;

    console.log(`\n🔹 ${role.key.toUpperCase()} — ${role.desc}`);
    console.log(`   默认: #${defaultLabel} (${role.defaultModel})  |  思考: ${role.defaultThinking}\n`);

    let provider;
    while (true) {
      const ans = (await ask(`   选择模型 (编号/Key) [#${defaultLabel}]: `)).trim();
      if (!ans) {
        provider = providers[defaultIdx - 1];
        break;
      }
      if (/^\d+$/.test(ans)) {
        const idx = +ans - 1;
        if (idx >= 0 && idx < providers.length) {
          provider = providers[idx];
          break;
        }
        console.log(`   ⚠ 编号超出范围，请输入 1-${providers.length}`);
      } else {
        const found = providers.find((p) => p.key === ans);
        if (found) { provider = found; break; }
        console.log(`   ⚠ 未找到 Key "${ans}"，请输入编号或 provider Key`);
      }
    }

    let thinking;
    while (true) {
      const ans = (await ask(`   思考强度 [${role.defaultThinking}]: `)).trim().toLowerCase();
      if (!ans) { thinking = role.defaultThinking; break; }
      if (/^\d+$/.test(ans)) {
        const idx = +ans - 1;
        if (idx >= 0 && idx < THINKING_LEVELS.length) { thinking = THINKING_LEVELS[idx]; break; }
        console.log(`   ⚠ 编号超出范围，请输入 1-${THINKING_LEVELS.length}`);
      } else if (THINKING_LEVELS.includes(ans)) {
        thinking = ans; break;
      } else {
        console.log(`   ⚠ 无效等级，可选: ${THINKING_LEVELS.join(", ")}`);
      }
    }

    selections.push({ role: role.key, key: provider.key, model: provider.model, thinking });
  }

  rl.close();
  return selections;
}

// --- CLI ---

const options = {
  config: { type: "string", default: resolve(homedir(), ".codex/config.toml") },
  "target-dir": { type: "string", default: resolve(homedir(), ".codex/agents") },
  auto: { type: "boolean", short: "a", default: false },
  list: { type: "boolean", default: false },
  interactive: { type: "boolean", short: "i", default: false },
  force: { type: "boolean", short: "f", default: false },
  json: { type: "boolean", default: false },
  help: { type: "boolean", short: "h", default: false },
};
for (const r of ROLES) {
  options[`${r.key}-model`] = { type: "string", default: "" };
  options[`${r.key}-effort`] = { type: "string", default: "" };
}

const { values: args } = parseArgs({ options });

if (args.help) {
  console.log(`
用法: node init_subagent.mjs [选项]

选项:
  -a, --auto            一键生成，使用全部默认值 (无需交互)
  -i, --interactive     交互式配置向导 (完成后自动生成 TOML 文件)
  --list                列出所有可用 model providers
  --json                输出 JSON 格式配置
  -f, --force           覆盖已有配置文件 (自动备份)
  --target-dir <dir>    生成目录 (默认 ~/.codex/agents)
  --config <path>       指定 config.toml 路径 (默认 ~/.codex/config.toml)
  -h, --help            显示帮助

非交互式指定:
  --<role>-model <model>    模型名
  --<role>-effort <level>   思考强度 (low/medium/high/xhigh)

角色: ${ROLES.map((r) => r.key).join(", ")}
`);
  process.exit(0);
}

const configPath = args.config;
const rawProviders = parseConfig(configPath);
const providers = await enrichCustomProviders(rawProviders);

if (args.list) {
  printProviders(providers);
  process.exit(0);
}

// Interactive mode
if (args.interactive) {
  const selections = await interactiveSetup(providers);
  printSummary(selections);
  writeAgents(selections, resolve(args["target-dir"]), args.force);
  console.log();
  process.exit(0);
}

// Non-interactive: build from CLI args
const selections = ROLES.map((role) => {
  const modelInput = args[`${role.key}-model`] || "";
  const thinking = args[`${role.key}-effort`] || role.defaultThinking;

  // Priority: 1) match by provider key  2) match by model name  3) use model name as-is  4) default
  let matched = null;
  if (modelInput) {
    matched = providers.find((p) => p.key === modelInput) ?? providers.find((p) => p.model === modelInput);
  }
  if (!matched) {
    matched = providers.find((p) => p.model === role.defaultModel);
  }

  const key = matched?.key ?? "";
  const model = matched?.model ?? (modelInput || role.defaultModel);
  return { role: role.key, key, model, thinking };
});

if (args.json) {
  const config = Object.fromEntries(
    selections.map((s) => [s.role, { key: s.key, model: s.model, thinking: s.thinking }])
  );
  console.log(JSON.stringify(config, null, 2));
  process.exit(0);
}

// Default: generate files
printSummary(selections);
writeAgents(selections, resolve(args["target-dir"]), args.force);
console.log();
