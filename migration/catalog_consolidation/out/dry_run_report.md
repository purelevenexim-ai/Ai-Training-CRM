# Catalog Consolidation Dry Plan

Generated: 2026-06-01T01:47:15.531Z

- Product rows parsed: 17
- Mapping rows parsed: 17
- Redirects required: 17
- Unresolved mapping rows: 0

## Families and Target Variant Coverage (50g, 100g, 200g)

### black_pepper
- Canonical: /products/kerala-black-pepper
- Mapped variants: 100g, 200g
- Missing target variants: 50g
- Source handles: kerala-black-pepper-100gm, kerala-black-pepper-200gm, kerala-black-pepper-300gm, kerala-black-pepper-500gm

### cassia_cinnamon
- Canonical: /products/premium-cassia-cinnamon
- Mapped variants: 100g, 200g
- Missing target variants: 50g
- Source handles: premium-cassia-cinnamon-100g, premium-cassia-cinnamon-200g

### ceylon_cinnamon
- Canonical: /products/aromatic-true-cinnamon-ceylon
- Mapped variants: 100g, 200g
- Missing target variants: 50g
- Source handles: aromatic-true-cinnamon-ceylon-100g, aromatic-true-cinnamon-ceylon-200g

### clove
- Canonical: /products/kerala-adimali-clove
- Mapped variants: 100g, 200g
- Missing target variants: 50g
- Source handles: kerala-clove-100gm, kerala-clove-200gm

### green_cardamom
- Canonical: /products/kerala-cardamom
- Mapped variants: 100g, 200g, 50g
- Missing target variants: none
- Source handles: kerala-cardamom-500gm, kerala-cardamom-50gm, kerala-cardamom-8mm-200gm, kerala-cardamom-8mm-fruit-100gm

### spice_combo_3in1
- Canonical: /products/kerala-spice-combo-pack
- Mapped variants: 100g+200g+100g, 50g+100g+100g
- Missing target variants: 50g, 100g, 200g
- Source handles: cardamom-100g-black-pepper-200g-clove-100g-3-in-1-spice-combo-pack, cardamom-50g-black-pepper-100g-clove-100g-3-in-1-spice-combo-pack

### white_pepper
- Canonical: /products/kerala-white-pepper
- Mapped variants: 100g
- Missing target variants: 50g, 200g
- Source handles: kerala-white-pepper-100gm

## Next Mutation-Safe Steps

1. Fill prices/SKUs/inventory for missing target variants before mutation run.
2. Confirm canonical handles and titles in mapping CSV.
3. Run consolidation script in dry-run mode and compare with these outputs.
4. Execute production only after backup checklist is signed.

