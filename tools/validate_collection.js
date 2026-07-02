#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const { Collection } = require('postman-collection');

function parseArgs(argv) {
  const args = {};
  for (let i = 2; i < argv.length; i += 1) {
    if (argv[i] === '--config') args.config = argv[++i];
    else if (argv[i] === '--collection') args.collection = argv[++i];
  }
  return args;
}

function readProjectId(configPath) {
  const text = fs.readFileSync(configPath, 'utf8');
  const match = text.match(/^project_id\s*=\s*"([^"]+)"/m);
  if (!match) throw new Error('project_id not found in TOML config');
  const outputMatch = text.match(/^output_root\s*=\s*"([^"]+)"/m);
  const outputRoot = outputMatch ? outputMatch[1] : 'outputs';
  return { projectId: match[1], outputRoot };
}

function normalizedKey(item) {
  const method = String(item.request.method || '').toUpperCase();
  const raw = item.request.url ? String(item.request.url.toString()) : '';
  const withoutBase = raw.replace(/^\{\{[^}]+\}\}/, '');
  const pathOnly = withoutBase.split('?')[0]
    .replace(/\{\{[^}]+\}\}/g, '{param}')
    .replace(/:\w+/g, '{param}')
    .replace(/\/\d+(?=\/|$)/g, '/{param}');
  return `${method} ${pathOnly}`;
}

const args = parseArgs(process.argv);
let collectionPath = args.collection;
if (!collectionPath && args.config) {
  const cfg = readProjectId(args.config);
  const repoRoot = path.resolve(path.dirname(args.config), '..');
  collectionPath = path.join(repoRoot, cfg.outputRoot, cfg.projectId, 'postman', `${cfg.projectId}.postman_collection.json`);
}
if (!collectionPath) throw new Error('Use --collection <path> or --config <path>');
const raw = JSON.parse(fs.readFileSync(collectionPath, 'utf8'));
if (!raw.info || !String(raw.info.schema || '').includes('/v2.1.0/')) {
  throw new Error('Collection must declare Postman Collection v2.1 schema');
}
const collection = new Collection(raw);
let requestCount = 0;
const secretLeaks = [];
const duplicates = [];
const seen = new Set();
collection.forEachItem((item) => {
  requestCount += 1;
  const text = JSON.stringify(item.toJSON());
  if (/Bearer\s+eyJ[A-Za-z0-9_-]+\./i.test(text)) secretLeaks.push(item.name);
  if (/"(password|token|secret|apiKey)"\s*:\s*"(?!\{\{|<REDACTED>|\")/i.test(text)) secretLeaks.push(item.name);
  const key = normalizedKey(item);
  if (seen.has(key)) duplicates.push(key);
  seen.add(key);
  if (!String(item.request.description || '').trim()) throw new Error(`Request has no description: ${item.name}`);
});
if (!requestCount) throw new Error('Collection contains no requests');
if (secretLeaks.length) throw new Error(`Possible secret values found in: ${[...new Set(secretLeaks)].join(', ')}`);
if (duplicates.length) throw new Error(`Duplicate normalized requests found: ${[...new Set(duplicates)].join(', ')}`);
console.log(JSON.stringify({ valid: true, collectionPath, requestCount, schema: raw.info.schema }, null, 2));
