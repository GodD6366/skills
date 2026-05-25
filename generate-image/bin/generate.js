#!/usr/bin/env node

const fs = require('node:fs/promises');
const path = require('node:path');
const { homedir } = require('node:os');

const DEFAULT_SIZE = '1008x1792';
const DEFAULT_QUALITY = 'high';
const DEFAULT_MODEL = 'gpt-image-2';
const AZURE_DEFAULT_API_VERSION = '2024-02-01';
const ALLOWED_QUALITY = new Set(['low', 'medium', 'high', 'auto']);
const SUPPORTED_MIME = new Set([
  'image/jpeg',
  'image/png',
  'image/webp',
  'image/gif',
]);
const MIME_BY_EXT = {
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.png': 'image/png',
  '.webp': 'image/webp',
  '.gif': 'image/gif',
};

function printHelp() {
  process.stdout.write(`Usage:
  generate --prompt "..." [--size 1008x1792] [--model gpt-image-2] [--file ./ref.jpg]...
  generate --input ./payload.json

Options:
  --prompt     Required when --input is not used
  --size       Default: ${DEFAULT_SIZE}
  --quality    Default: ${DEFAULT_QUALITY}, One of: low, medium, high, auto
  --model      Default: ${DEFAULT_MODEL}
  --file       Repeatable reference image path
  --input      JSON file with { prompt, size, quality, model, files }
  --help       Show this message
`);
}

function fail(message) {
  process.stderr.write(`${message}\n`);
  process.exit(1);
}

function parseArgs(argv) {
  const result = { files: [] };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--help') {
      result.help = true;
      continue;
    }
    if (!arg.startsWith('--')) {
      fail(`Unexpected argument: ${arg}`);
    }
    const key = arg.slice(2);
    const value = argv[i + 1];
    if (!value || value.startsWith('--')) {
      fail(`Missing value for --${key}`);
    }
    i += 1;
    if (key === 'file') {
      result.files.push(value);
      continue;
    }
    result[key] = value;
  }
  return result;
}

async function loadInput(inputPath) {
  const raw = await fs.readFile(inputPath, 'utf8');
  const parsed = JSON.parse(raw);
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    fail('--input must point to a JSON object');
  }
  return parsed;
}

function normalizePayload(cliInput, fileInput) {
  const merged = {
    ...fileInput,
    ...cliInput,
    files:
      cliInput.files && cliInput.files.length > 0
        ? cliInput.files
        : Array.isArray(fileInput.files)
          ? fileInput.files
          : [],
  };

  const prompt = typeof merged.prompt === 'string' ? merged.prompt.trim() : '';
  if (!prompt) {
    fail('prompt is required');
  }

  const size = merged.size || DEFAULT_SIZE;
  validateSize(size);

  const quality = merged.quality || DEFAULT_QUALITY;
  if (!ALLOWED_QUALITY.has(quality)) {
    fail(`quality must be one of: ${Array.from(ALLOWED_QUALITY).join(', ')}`);
  }

  const model = merged.model || DEFAULT_MODEL;
  const files = merged.files.map((file) =>
    typeof file === 'string' ? { filepath: file } : file,
  );

  return { prompt, size, quality, model, files };
}

function validateSize(size) {
  if (!/^\d+x\d+$/.test(size)) {
    fail('size must use "宽x高" format, for example 1008x1792');
  }
  const [width, height] = size.split('x').map(Number);
  const longEdge = Math.max(width, height);
  const shortEdge = Math.min(width, height);
  const pixels = width * height;

  if (longEdge > 3840) {
    fail('size long edge must be <= 3840');
  }
  if (width % 16 !== 0 || height % 16 !== 0) {
    fail('size width and height must both be multiples of 16');
  }
  if (longEdge / shortEdge > 3) {
    fail('size aspect ratio must not exceed 3:1');
  }
  if (pixels < 655360 || pixels > 8294400) {
    fail('size pixel count must be between 655360 and 8294400');
  }
}

function inferMime(filepath) {
  const ext = path.extname(filepath).toLowerCase();
  return MIME_BY_EXT[ext] || null;
}

function cleanString(value) {
  return typeof value === 'string' ? value.trim() : '';
}

async function appendFiles(form, files) {
  for (const file of files) {
    if (!file || typeof file.filepath !== 'string' || !file.filepath.trim()) {
      fail('each file must provide filepath');
    }
    const filepath = path.resolve(process.cwd(), file.filepath.trim());
    const mime = file.mime || inferMime(filepath);
    if (!mime || !SUPPORTED_MIME.has(mime)) {
      fail(`unsupported mime for file: ${filepath}`);
    }
    const content = await fs.readFile(filepath);
    const blob = new Blob([content], { type: mime });
    form.append('image', blob, path.basename(filepath));
  }
}

function truncate(value, max = 400) {
  return value.length > max ? `${value.slice(0, max)}...` : value;
}

function assertHttpUrl(value, label = 'url') {
  if (!/^https?:\/\/\S+$/i.test(value)) {
    fail(`${label} must be a real http(s) URL`);
  }
  if (/example\.invalid/i.test(value)) {
    fail(`${label} must not be a dry-run placeholder`);
  }
}

function readNestedString(value, keys) {
  let current = value;
  for (const key of keys) {
    if (!current || typeof current !== 'object') {
      return '';
    }
    current = current[key];
  }
  return cleanString(current);
}

async function readJsonIfPresent(filePath) {
  try {
    const raw = await fs.readFile(filePath, 'utf8');
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed : null;
  } catch {
    return null;
  }
}

function tokenFromHermesAuth(data) {
  const providerToken = readNestedString(data, [
    'providers',
    'openai-codex',
    'tokens',
    'access_token',
  ]);
  if (providerToken) return providerToken;
  const pool =
    data && typeof data === 'object'
      ? data.credential_pool?.['openai-codex']
      : null;
  if (Array.isArray(pool)) {
    for (const item of pool) {
      const token = readNestedString(item, ['access_token']);
      if (token) return token;
    }
  }
  return '';
}

function tokenFromCodexAuth(data) {
  return (
    readNestedString(data, ['tokens', 'access_token']) ||
    readNestedString(data, ['OPENAI_API_KEY'])
  );
}

function detectAzureEndpoint(baseUrl) {
  return (
    /\.azure\.com\b/i.test(baseUrl) || /\/openai\/deployments\//i.test(baseUrl)
  );
}

function buildOpenAIImageUrl(baseUrl, endpoint, isAzure) {
  let parsed;
  try {
    parsed = new URL(baseUrl);
  } catch {
    return `${baseUrl.replace(/\/$/, '')}/images/${endpoint}`;
  }
  parsed.pathname = parsed.pathname.replace(/\/+$/, '') + `/images/${endpoint}`;
  if (isAzure && !parsed.searchParams.has('api-version')) {
    parsed.searchParams.set('api-version', AZURE_DEFAULT_API_VERSION);
  }
  return parsed.toString();
}

async function fetchWithTimeout(url, init, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

async function responseImageBuffer(response) {
  const text = await response.text();
  if (!response.ok) {
    fail(`openai ${response.status}: ${truncate(text)}`);
  }
  let json;
  try {
    json = JSON.parse(text);
  } catch {
    fail(`openai returned non-JSON response: ${truncate(text)}`);
  }
  const item = Array.isArray(json.data) ? json.data[0] : null;
  const entry = item && typeof item === 'object' ? item : {};
  const b64 = cleanString(entry.b64_json);
  if (b64) {
    return Buffer.from(b64, 'base64');
  }
  const url = cleanString(entry.url);
  if (url) {
    const imageResponse = await fetch(url);
    if (!imageResponse.ok) {
      fail(`openai image fetch ${imageResponse.status}`);
    }
    return Buffer.from(await imageResponse.arrayBuffer());
  }
  fail('openai response had neither b64_json nor url');
}

async function generateImage(payload) {
  const apiKey = process.env.OPENAI_API_KEY;
  const baseUrl = process.env.OPENAI_BASE_URL;

  if (!apiKey) fail('OPENAI_API_KEY environment variable is required');
  if (!baseUrl) fail('OPENAI_BASE_URL environment variable is required');

  const azure = detectAzureEndpoint(baseUrl);
  let response;

  if (payload.files.length > 0) {
    const formData = new FormData();
    if (!azure) {
      formData.append('model', payload.model);
    }
    formData.append('prompt', payload.prompt);
    formData.append('size', payload.size);
    formData.append('quality', payload.quality);
    await appendFiles(formData, payload.files);
    response = await fetchWithTimeout(
      buildOpenAIImageUrl(baseUrl, 'edits', azure),
      {
        method: 'POST',
        headers: azure
          ? { Authorization: `Bearer ${apiKey}`, 'api-key': apiKey }
          : { Authorization: `Bearer ${apiKey}` },
        body: formData,
      },
      600_000,
    );
  } else {
    const body = {
      prompt: payload.prompt,
      n: 1,
      size: payload.size,
      quality: payload.quality,
    };
    if (!azure) {
      body.model = payload.model;
    }
    response = await fetchWithTimeout(
      buildOpenAIImageUrl(baseUrl, 'generations', azure),
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${apiKey}`,
          'Content-Type': 'application/json',
          ...(azure ? { 'api-key': apiKey } : {}),
        },
        body: JSON.stringify(body),
      },
      600_000,
    );
  }

  const buffer = await responseImageBuffer(response);
  const outputDir = path.join(process.cwd(), '.tmp', 'generate-image');
  await fs.mkdir(outputDir, { recursive: true });
  const outputPath = path.join(outputDir, `${Date.now()}.png`);
  await fs.writeFile(outputPath, buffer);
  return outputPath;
}

async function loadDotenv() {
  const envPath = path.resolve(__dirname, '../.env');
  try {
    const stat = await fs.stat(envPath);
    if (!stat.isFile()) return;
    const content = await fs.readFile(envPath, 'utf8');
    for (const rawLine of content.split('\n')) {
      let line = rawLine.trim();
      if (!line || line.startsWith('#')) continue;
      if (line.startsWith('export ')) {
        line = line.slice(7).trim();
      }
      const eqIndex = line.indexOf('=');
      if (eqIndex === -1) continue;
      const key = line.slice(0, eqIndex).trim();
      if (!key) continue;
      let value = line.slice(eqIndex + 1).trim();
      if (value.length >= 2 && (value[0] === '"' || value[0] === "'") && value[value.length - 1] === value[0]) {
        value = value.slice(1, -1);
      }
      if (process.env[key] === undefined) {
        process.env[key] = value;
      }
    }
  } catch (e) {
    // Ignore if not exists
  }
}

async function main() {
  await loadDotenv();
  const cliInput = parseArgs(process.argv.slice(2));
  if (cliInput.help) {
    printHelp();
    return;
  }
  const fileInput = cliInput.input ? await loadInput(cliInput.input) : {};
  const payload = normalizePayload(cliInput, fileInput);
  const localPath = await generateImage(payload);
  process.stdout.write(localPath);
}

main().catch((error) => {
  fail(error instanceof Error ? error.message : String(error));
});
