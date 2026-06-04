#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';

const workspaceRoot = process.cwd();
const productListPath = path.join(workspaceRoot, 'product_list.csv');
const mapPath = path.join(workspaceRoot, 'migration/catalog_consolidation/current_to_target_mapping.csv');
const specPath = path.join(workspaceRoot, 'migration/catalog_consolidation/final_catalog_spec.csv');
const outDir = path.join(workspaceRoot, 'migration/catalog_consolidation/out');

const targetVariantSet = new Set(['50g', '100g', '200g']);

function readCsv(filePath) {
  const raw = fs.readFileSync(filePath, 'utf8').trim();
  const lines = raw.split(/\r?\n/);
  const headers = splitCsvLine(lines[0]);
  return lines.slice(1).map((line) => {
    const row = splitCsvLine(line);
    const obj = {};
    for (let i = 0; i < headers.length; i += 1) {
      obj[headers[i]] = row[i] ?? '';
    }
    return obj;
  });
}

function splitCsvLine(line) {
  const out = [];
  let cur = '';
  let inQuotes = false;

  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (ch === '"') {
      if (inQuotes && line[i + 1] === '"') {
        cur += '"';
        i += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }
    if (ch === ',' && !inQuotes) {
      out.push(cur);
      cur = '';
      continue;
    }
    cur += ch;
  }
  out.push(cur);
  return out;
}

function toCsvLine(values) {
  return values
    .map((value) => {
      const s = String(value ?? '');
      if (s.includes(',') || s.includes('"') || s.includes('\n')) {
        return `"${s.replaceAll('"', '""')}"`;
      }
      return s;
    })
    .join(',');
}

function handleFromUrl(url) {
  const m = url.match(/\/products\/([^/?#]+)/);
  return m ? m[1] : '';
}

function ensureDir(dirPath) {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
}

function main() {
  const productRows = readCsv(productListPath).map((r) => ({
    ...r,
    handle: handleFromUrl(r.url),
  }));
  const mappingRows = readCsv(mapPath);
  const specRows = readCsv(specPath);

  const productByHandle = new Map(productRows.map((r) => [r.handle, r]));
  const mappingByHandle = new Map(mappingRows.map((r) => [r.current_handle, r]));
  const specByFamily = new Map(specRows.map((r) => [r.family_key, r]));

  const redirects = [];
  const unresolved = [];
  const familyReport = new Map();

  for (const row of mappingRows) {
    const src = productByHandle.get(row.current_handle);
    const spec = specByFamily.get(row.family_key);

    if (!familyReport.has(row.family_key)) {
      familyReport.set(row.family_key, {
        family_key: row.family_key,
        canonical_handle: row.target_canonical_handle,
        canonical_title: spec?.canonical_title || '',
        mapped_variants: new Set(),
        source_handles: [],
        missing_target_variants: [],
      });
    }

    const family = familyReport.get(row.family_key);
    family.source_handles.push(row.current_handle);
    if (row.target_variant_value) {
      family.mapped_variants.add(row.target_variant_value);
    }

    if (!src) {
      unresolved.push({
        current_handle: row.current_handle,
        reason: 'not_found_in_product_list',
      });
      continue;
    }

    if (row.current_handle !== row.target_canonical_handle) {
      redirects.push({
        old_path: `/products/${row.current_handle}`,
        new_path: `/products/${row.target_canonical_handle}`,
      });
    }
  }

  for (const family of familyReport.values()) {
    const missing = [...targetVariantSet].filter((v) => !family.mapped_variants.has(v));
    family.missing_target_variants = missing;
  }

  ensureDir(outDir);

  const redirectsCsv = [
    toCsvLine(['old_path', 'new_path']),
    ...redirects.map((r) => toCsvLine([r.old_path, r.new_path])),
  ].join('\n');
  fs.writeFileSync(path.join(outDir, 'redirects_to_create.csv'), `${redirectsCsv}\n`, 'utf8');

  const unresolvedCsv = [
    toCsvLine(['current_handle', 'reason']),
    ...unresolved.map((u) => toCsvLine([u.current_handle, u.reason])),
  ].join('\n');
  fs.writeFileSync(path.join(outDir, 'unresolved_mapping_rows.csv'), `${unresolvedCsv}\n`, 'utf8');

  const familyRows = [
    toCsvLine([
      'family_key',
      'canonical_handle',
      'canonical_title',
      'mapped_variants',
      'missing_target_variants',
      'source_handles',
    ]),
    ...[...familyReport.values()].map((f) =>
      toCsvLine([
        f.family_key,
        f.canonical_handle,
        f.canonical_title,
        [...f.mapped_variants].sort().join('|'),
        f.missing_target_variants.join('|'),
        f.source_handles.join('|'),
      ]),
    ),
  ].join('\n');
  fs.writeFileSync(path.join(outDir, 'family_variant_coverage.csv'), `${familyRows}\n`, 'utf8');

  const reportLines = [];
  reportLines.push('# Catalog Consolidation Dry Plan');
  reportLines.push('');
  reportLines.push(`Generated: ${new Date().toISOString()}`);
  reportLines.push('');
  reportLines.push(`- Product rows parsed: ${productRows.length}`);
  reportLines.push(`- Mapping rows parsed: ${mappingRows.length}`);
  reportLines.push(`- Redirects required: ${redirects.length}`);
  reportLines.push(`- Unresolved mapping rows: ${unresolved.length}`);
  reportLines.push('');
  reportLines.push('## Families and Target Variant Coverage (50g, 100g, 200g)');
  reportLines.push('');

  for (const family of [...familyReport.values()].sort((a, b) => a.family_key.localeCompare(b.family_key))) {
    reportLines.push(`### ${family.family_key}`);
    reportLines.push(`- Canonical: /products/${family.canonical_handle}`);
    reportLines.push(`- Mapped variants: ${[...family.mapped_variants].sort().join(', ') || '(none)'}`);
    reportLines.push(
      `- Missing target variants: ${family.missing_target_variants.length ? family.missing_target_variants.join(', ') : 'none'}`,
    );
    reportLines.push(`- Source handles: ${family.source_handles.join(', ')}`);
    reportLines.push('');
  }

  if (unresolved.length > 0) {
    reportLines.push('## Unresolved Mapping Rows');
    reportLines.push('');
    for (const row of unresolved) {
      reportLines.push(`- ${row.current_handle}: ${row.reason}`);
    }
    reportLines.push('');
  }

  reportLines.push('## Next Mutation-Safe Steps');
  reportLines.push('');
  reportLines.push('1. Fill prices/SKUs/inventory for missing target variants before mutation run.');
  reportLines.push('2. Confirm canonical handles and titles in mapping CSV.');
  reportLines.push('3. Run consolidation script in dry-run mode and compare with these outputs.');
  reportLines.push('4. Execute production only after backup checklist is signed.');
  reportLines.push('');

  fs.writeFileSync(path.join(outDir, 'dry_run_report.md'), `${reportLines.join('\n')}\n`, 'utf8');

  console.log('Prepared consolidation planning artifacts:');
  console.log(`- ${path.relative(workspaceRoot, path.join(outDir, 'dry_run_report.md'))}`);
  console.log(`- ${path.relative(workspaceRoot, path.join(outDir, 'family_variant_coverage.csv'))}`);
  console.log(`- ${path.relative(workspaceRoot, path.join(outDir, 'redirects_to_create.csv'))}`);
  console.log(`- ${path.relative(workspaceRoot, path.join(outDir, 'unresolved_mapping_rows.csv'))}`);
}

main();
