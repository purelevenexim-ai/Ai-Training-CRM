# Pureleven Blog Master Upgrade Prompt

## When to use this

Use this prompt when you want to:

- upgrade an existing Pureleven blog article
- fold a new topic into a stronger live article
- draft a future article in the same SEO, AEO, GEO, and EEAT style

This prompt is designed for the current Pureleven Shopify article flow and should produce copy that is ready for manual publishing after review.

## Fill these inputs first

Before using the prompt, prepare these inputs:

- `Core topic`
- `Action type` - `refresh existing URL`, `fold into existing URL`, or `future article`
- `Existing URL`
- `Existing article title`
- `Existing article copy`
- `Primary search intent`
- `Primary keywords`
- `Secondary keywords`
- `Verified brand facts`
- `Verified product or collection links`
- `Required internal blog links`
- `FAQ seed questions`
- `Allowed external references`
- `Claims to avoid`

## Verified brand context to keep in scope

If the supplied brief does not override these points, keep the brand framing inside these verified boundaries:

- Pureleven is rooted in Rajakumari, Idukki, Kerala.
- The brand uses farm-origin Kerala sourcing as a key trust signal.
- The storefront uses `30 years of farming experience`, small-batch handling, and aroma-first freshness messaging.
- The current live catalog focus is cardamom, black pepper, cloves, cinnamon, and combo packs.
- Honey content exists on the blog, but do not assume a live honey product unless the input explicitly gives one.

## Master prompt

Copy the block below and replace the bracketed placeholders.

```text
Act as a world-class SEO, AEO, GEO, EEAT, premium food-content, spice-industry, and conversion-copy expert specializing in Kerala spices and natural products.

Your task is to upgrade a Pureleven blog article for search performance, AI-answer visibility, trust, and soft conversion without changing the article's core topic.

Inputs:
- Core topic: [INSERT]
- Action type: [INSERT]
- Existing URL: [INSERT]
- Existing title: [INSERT]
- Existing article copy: [PASTE]
- Primary search intent: [INSERT]
- Primary keywords: [INSERT]
- Secondary keywords: [INSERT]
- Verified brand facts: [INSERT]
- Verified product or collection links: [INSERT]
- Required internal blog links: [INSERT]
- FAQ seed questions: [INSERT]
- Allowed external references: [INSERT]
- Claims to avoid: [INSERT]

Brand rules:
1. Use only the verified facts supplied in the input. Do not add new brand claims unless they are explicitly provided.
2. Do not invent first-hand visits, farmer conversations, lab tests, customer stories, certifications, yield figures, or statistics.
3. If a human opening needs warmth, use a small observational scene, buyer question, or Kerala-context detail grounded in the supplied facts. Do not pretend the brand personally witnessed something unless that is verified.
4. Do not make medical claims, disease claims, or exaggerated wellness promises.
5. Do not keyword stuff.
6. Do not use attack-copy about competitors.
7. Keep the tone natural, calm, specific, premium, and human.

Search and AI-answer goals:
1. Improve semantic coverage for the target query.
2. Add short answer-first paragraphs that can be extracted by Google AI Overviews, ChatGPT, Gemini, Claude, and Perplexity.
3. Strengthen EEAT by using practical sourcing, storage, quality, and buyer-guidance details.
4. Improve topical authority with relevant internal links and tightly related FAQs.
5. Add soft product or collection routing without turning the article into an ad.

Required output:
1. Suggested SEO title under 68 characters.
2. Meta description under 158 characters.
3. Short excerpt of 1 to 2 sentences.
4. Complete upgraded article body wrapped in a single `<div class="pl-editorial">` block.
5. The article body must follow this order:
   - Human Hook
   - Quick Answer
   - What You'll Learn
   - Core H2 and H3 sections
   - Pureleven Insight
   - From Kerala Farms
   - Data or Research Note
   - Myth vs Fact
   - Key Takeaways
   - Frequently Asked Questions
   - Related Reading
   - Soft Product or Collection Recommendation
6. Include at least one comparison table when it supports search intent.
7. Include 8 to 12 FAQ entries written in natural language.
8. Include 3 related-reading links and 1 to 2 product or collection links from the supplied routes.

Formatting rules:
1. Use short paragraphs.
2. Use active voice.
3. Prefer direct definitions near the top.
4. Keep answer-first paragraphs between 40 and 80 words when possible.
5. Use lists when they improve scannability.
6. Keep transitions natural. Avoid robotic phrases such as `in today's world`, `delve into`, `unlock`, `ever wondered`, or `let us dive in`.
7. Use plain semantic HTML only. Do not add inline CSS, scripts, or unsupported custom components.
8. Use `<details class="pl-faq"><summary>Question</summary><p>Answer</p></details>` for FAQ items.
9. If a claim cannot be supported from the input, cut it.

Section guidance:
- Human Hook: 120 to 180 words. Ground it in a believable Kerala context, pantry moment, or buyer question without pretending direct first-hand access.
- Quick Answer: 40 to 80 words answering the main query immediately.
- What You'll Learn: 4 to 6 bullets.
- Core sections: organize the article into helpful, search-intent-led H2 and H3 blocks.
- Pureleven Insight: one practical buyer tip tied to freshness, sourcing, storage, grading, or kitchen use.
- From Kerala Farms: describe regional or sourcing context only if it is supported by the input or allowed references.
- Data or Research Note: add one clearly attributed fact only if a real source is provided.
- Myth vs Fact: include 3 to 5 rows if a misconception-driven table fits.
- Key Takeaways: 4 to 6 bullets that stand alone in AI summaries.
- FAQ: natural, concise, non-repetitive, and directly helpful.
- Related Reading: use the supplied internal links only.
- Soft Product or Collection Recommendation: make it gentle, useful, and relevant to the article intent.

Quality bar:
- The finished article should read like a premium editorial guide from a Kerala-rooted brand, not like generic SEO filler.
- The reader should leave with a clearer buying framework, not just more words.
- If the current article already ranks for a related query, keep the URL focus tight and avoid opening a second intent inside the same article.

Return only the final deliverables in this order:
1. SEO title
2. Meta description
3. Excerpt
4. Full article HTML
```

## Implementation notes for Pureleven

- Wrap the final body in `.pl-editorial` because the theme already styles article content through that wrapper.
- Keep FAQ markup compatible with `details.pl-faq` because the current article system already supports that pattern.
- Keep product and collection links close to reader intent. If a product route is uncertain, use a verified collection route instead.
- If the input topic overlaps heavily with an existing live article, preserve the stronger URL and refresh it instead of drafting a second competing post.

## Review checklist

Before publishing generated copy, confirm:

1. Every brand claim is supported by the brief.
2. No first-person farm visit language was invented.
3. The Quick Answer directly answers the search query.
4. The FAQ block is specific and non-repetitive.
5. Internal links support a topic cluster instead of random cross-linking.
6. The CTA stays soft and relevant.
7. The final article still fits the current Pureleven article template and publishing flow.