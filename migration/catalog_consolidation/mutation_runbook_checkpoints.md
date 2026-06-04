# Catalog Consolidation Mutation Runbook Checkpoints

This runbook is for production mutation phase only. Do not execute if any required checkpoint is red.

## Checkpoint 0 - Freeze and Backup (must pass)

1. Freeze product content edits for affected handles.
2. Export current products (CSV) and keep timestamped snapshot.
3. Export current redirects list.
4. Confirm rollback script path and credentials are valid.
5. Confirm store target (production) and operator identity.

Go/No-Go criteria:
- GO only if all five items are complete and documented.

## Checkpoint 1 - Mapping and Canonical Validation (must pass)

1. Review `migration/catalog_consolidation/current_to_target_mapping.csv`.
2. Review `migration/catalog_consolidation/final_catalog_spec.csv`.
3. Confirm each family has exactly one canonical handle.
4. Confirm grade-separate policy is preserved where required.
5. Confirm combo products remain separate family (`spice_combo_3in1`).

Go/No-Go criteria:
- GO only if no conflicts in canonical handle assignments.

## Checkpoint 2 - Dry-Run Output Validation (must pass)

1. Run: `node scripts/prepare-catalog-consolidation-plan.mjs`.
2. Validate outputs under `migration/catalog_consolidation/out/`:
- `dry_run_report.md`
- `family_variant_coverage.csv`
- `redirects_to_create.csv`
- `unresolved_mapping_rows.csv`
3. Ensure unresolved rows count is zero.
4. Validate missing target variants are explicitly planned (create vs defer).

Go/No-Go criteria:
- GO only if unresolved rows = 0 and family coverage is accepted.

## Checkpoint 3 - Mutation Payload Readiness (must pass)

1. Build per-variant payload for create/update:
- SKU
- price
- compare-at price (if used)
- inventory policy
- weight and unit
2. Confirm default image/media behavior per canonical product.
3. Confirm inventory source and location IDs.

Go/No-Go criteria:
- GO only if payload is complete for all variants to be created/updated.

## Checkpoint 4 - Controlled Production Execution (must pass)

Execution order:
1. Create missing canonical variants first.
2. Verify PDP variant selection and cart add for each family.
3. Archive duplicate products (do not delete immediately).
4. Create redirects from retired handles to canonical handles.

Go/No-Go criteria:
- Pause immediately if any GraphQL userErrors or storefront 404 spikes occur.

## Checkpoint 5 - Post-Mutation QA (must pass)

1. Validate key collection pages no longer show fragmented duplicate sizes.
2. Validate canonical PDP has expected variants (50g/100g/200g) where applicable.
3. Validate search results and related products display canonical items.
4. Validate redirects for all retired handles.
5. Confirm GA4/search console monitoring baseline captured.

Go/No-Go criteria:
- GO only if all critical storefront paths pass and redirects resolve 200 on targets.

## Checkpoint 6 - Stabilization Window and Deletion Policy

1. Keep retired products archived for 30 days.
2. Monitor:
- crawl errors
- top landing pages
- conversion rate by canonical handles
3. Delete archived products only after 30-day clean window and explicit approval.

## Emergency Rollback Trigger

Rollback immediately if any of these occur:
1. Material traffic drop on affected product landing pages.
2. Redirect failures on high-traffic legacy handles.
3. Variant purchase flow failure on canonical PDPs.

Rollback scope:
1. Restore archived products to active state.
2. Revert redirect imports added in this migration.
3. Restore previous variant state from backup snapshot.
