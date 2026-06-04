# WhatsApp Product Journey Spec

## Goal

When a customer asks about a product, the reply should feel human, polite, and context-aware.

The bot should:
- confirm the product naturally
- match the customer’s language style
- give the price details cleanly
- softly persuade without sounding pushy
- continue the conversation with timed follow-ups
- branch correctly depending on what the customer says next

This is not just a pricing reply. It is a mini sales journey.

---

## Core Reply Principle

The response should usually follow this sequence:

1. Confirm the product
2. Match the customer’s tone/language
3. Introduce the price details
4. Show the price table
5. Add a soft purchase nudge
6. Wait for the customer’s response

### Example structure

For `Patta undo?`, the reply should feel like:

```text
Yes, patta undallo stock. Njan price thazhe kodukkam.

*CEYLON CINNAMON* • Sri Lanka

_Original Ceylon cinnamon_

*Size     | Price    | Delivery*
───────────────────────────────────
100g    | ₹320     | ₹40
200g    | ₹560     | ✅ FREE
500g    | ₹1400    | ✅ FREE

200g edukkunath nalla option aanu. Free delivery kittum, offer price um aanu.
Reply cheythal njaan order help cheyyam.
```

Important:
- Do not use a generic CTA like “reply with the size you want” if the customer did not ask that way.
- Avoid sounding robotic.
- Use the customer’s language style: English, Manglish, or Malayalam.

---

## Language And Tone Rules

### Tone detection

| Customer style | What we should reply in |
|---|---|
| English | English |
| Manglish | Manglish |
| Malayalam script | Malayalam |
| Mixed Manglish + Malayalam | Match the stronger tone |
| Very short / blunt | Short, polite, direct |
| Warm / enthusiastic | Warm, slightly more conversational |

### Tone matching examples

| Customer message | Best reply tone |
|---|---|
| `Patta undo?` | Manglish confirmation |
| `Patta?` | Short Manglish or English |
| `പട്ട ഉണ്ടോ?` | Malayalam |
| `Is cinnamon available?` | English |
| `Cinnamon undo?` | Manglish |
| `Need patta price` | Manglish / English mix |

### Preferred confirmation phrases

| Language style | Possible confirmation line |
|---|---|
| English | `Yes, we have Ceylon cinnamon in stock.` |
| Manglish | `Yes, patta undallo stock.` |
| Manglish | `Yes, patta available aanu.` |
| Malayalam | `അതെ, പട്ട സ്റ്റോക്കിലുണ്ട്.` |
| Friendly English | `Yes, absolutely. We have Ceylon cinnamon available.` |

---

## Canonical Response Structure

The reply should be built from these blocks:

| Block | Purpose |
|---|---|
| Confirmation | Acknowledge the product is available |
| Price intro | Say that prices are listed below |
| Price table | Show the actual pack/price/delivery details |
| Persuasion line | Encourage the best pack or offer |
| CTA | Ask them to reply if they want to order |

### Recommended order

1. Confirmation line
2. Price intro
3. Price table
4. Persuasion line
5. CTA

---

## Product Reply Scenarios

### 1. Simple product availability question

Examples:
- `Patta undo?`
- `kurumulak undo?`
- `grampu undo?`

Reply behavior:
- confirm availability first
- then show price table
- then suggest a purchase-friendly option

### 2. Price-only question

Examples:
- `patta ethra aanu?`
- `cinnamon price`
- `black pepper rate?`

Reply behavior:
- skip extra explanation
- show price immediately
- add a simple selling nudge

### 3. Purchase intent question

Examples:
- `patta venam`
- `cinnamon need`
- `pepper order`

Reply behavior:
- acknowledge desire to buy
- guide toward order placement
- collect name/address if needed

### 4. Weak interest / just browsing

Examples:
- `patta?`
- `price?`
- `info`

Reply behavior:
- stay soft
- keep it short
- do not overpush

### 5. Strong interest

Examples:
- `yes, send`
- `need 200g`
- `order now`

Reply behavior:
- move quickly to order capture
- ask for name, address, pin code, phone

### 6. No-interest / negation

Examples:
- `patta venda`
- `kurumulak venda`
- `not interested`

Reply behavior:
- do not keep selling the same product
- politely acknowledge
- ask if they want anything else

---

## Product Journey State Machine

Think of this as a conversation funnel.

| Stage | What we do | What we expect |
|---|---|---|
| Stage 1: Confirm | Say yes/available | Customer feels heard |
| Stage 2: Inform | Show price table | Customer understands value |
| Stage 3: Nudge | Suggest best pack | Customer sees a recommended choice |
| Stage 4: Wait | Pause | Customer replies naturally |
| Stage 5: Capture | Ask for name/address | Customer is ready to buy |
| Stage 6: Escalate | Human help if needed | Close the sale manually |

---

## Follow-Up Timing

### If the customer does not reply

| Time after reply | Next action | Goal |
|---|---|---|
| 3 to 5 minutes | Gentle reminder | Re-open the conversation |
| 30 minutes | Alternative product suggestion | Save the sale |
| Same day | Escalate to human or resend a softer prompt | Recover the lead |
| Next day | One more respectful check-in | Final recovery attempt |

### 3 to 5 minute follow-up

Goal:
- ask if they need help deciding
- offer assistance with the recommended pack

Example:

```text
Patta price kandille? 200g edukkan nalla value aanu. Vendengil order help cheyyam.
```

### 30 minute follow-up

Goal:
- try a related product or combo
- do not repeat the exact same message

Example:

```text
Patta nokkiyille? Venengil cardamom / clove combo um suggest cheyyam.
```

### Next-day follow-up

Goal:
- give one final polite reminder
- then stop if the customer is not interested

Example:

```text
Yesterday patta nokkiyirunno? Still interested aanel njaan help cheyyam.
```

---

## Customer Response Scenarios

### Scenario A: Customer says yes

Examples:
- `yes`
- `okay`
- `undu`
- `venam`

Action:
- move to order capture

### Scenario B: Customer asks price again

Examples:
- `price ethra?`
- `200g ethra?`
- `more details`

Action:
- restate price table
- keep it short
- offer recommendation again

### Scenario C: Customer asks for recommendation

Examples:
- `which one is better?`
- `nalla option ethanu?`

Action:
- recommend the best value pack
- explain why in one line

### Scenario D: Customer asks for delivery

Examples:
- `delivery undo?`
- `shipping charge?`

Action:
- answer delivery clearly
- if free delivery applies, mention it

### Scenario E: Customer asks wholesale

Examples:
- `wholesale undo?`
- `bulk rate?`

Action:
- switch to B2B flow
- ask quantity, city, and repeat or one-time requirement

### Scenario F: Customer says no

Examples:
- `venda`
- `not needed`

Action:
- politely stop pushing that product
- offer another product only if appropriate

### Scenario G: Customer is confused / unclear

Examples:
- `huh?`
- `what?`
- mixed unclear text

Action:
- ask a clarification question

### Scenario H: Customer complains

Examples:
- `not received`
- `damaged`

Action:
- stop selling
- apologize
- escalate to support

---

## Persuasion Patterns

The persuasion should be subtle, not salesy.

### Good persuasion lines

| Product context | Good persuasive line |
|---|---|
| Cinnamon | `200g edukkunath nalla value aanu. Free delivery um kittum.` |
| Pepper | `500g eduthal rate um delivery um nallathaayi manage cheyyam.` |
| Cardamom | `200g pack is a balanced option for first-time buyers.` |
| Clove | `100g try cheythu look & quality nokkam.` |
| Turmeric | `200g pack regular use-nu nalla choice aanu.` |

### Avoid

- sounding desperate
- repeating the same CTA twice
- saying “buy now” too aggressively
- using a generic size CTA when the product reply is already a full sales step

---

## Product Reply Templates

### Template 1: English

```text
Yes, we have {product_name} in stock.

I’ll share the price details below.

{pricing_table}

{soft_recommendation}

Reply if you’d like to place the order.
```

### Template 2: Manglish

```text
Yes, {product_name} undallo stock.

Price details thazhe kodukkam.

{pricing_table}

{soft_recommendation}

Reply cheythal order help cheyyam.
```

### Template 3: Malayalam

```text
അതെ, {product_name} സ്റ്റോക്കിലുണ്ട്.

വില വിവരങ്ങൾ താഴെ കൊടുക്കുന്നു.

{pricing_table}

{soft_recommendation}

Order വേണമെങ്കിൽ reply ചെയ്യൂ.
```

---

## Scenario Matrix

| Customer says | Product detected | Tone | Immediate reply | Follow-up if silent |
|---|---|---|---|---|
| `Patta undo?` | cinnamon | Manglish | Confirm + price + nudge | 3-5 min reminder |
| `Patta ethra?` | cinnamon | Manglish | Price first | 3-5 min reminder |
| `Patta venam` | cinnamon | Manglish | Acknowledge no-interest | Offer another product later |
| `Cinnamon price` | cinnamon | English | Price + recommendation | 3-5 min reminder |
| `പട്ട ഉണ്ടോ?` | cinnamon | Malayalam | Confirm + price | 3-5 min reminder |
| `grampu undo?` | clove | Manglish | Confirm + price | 3-5 min reminder |
| `kurumulak undo?` | pepper | Manglish | Confirm + price | 3-5 min reminder |
| `black pepper wholesale undo?` | pepper | Manglish | Wholesale flow | Human B2B follow-up |
| `combo offer?` | combo | Any | Combo pack reply | 3-5 min reminder |

---

## What Should Change In The Bot

### Needed behavior upgrades

| Area | What should improve |
|---|---|
| Confirmation line | Always start with a natural “yes” / “അതെ” / “undallo” style acknowledgement |
| Tone detection | Recognize English vs Manglish vs Malayalam more reliably |
| Product replies | Use product-specific sales copy, not generic size language |
| Recommendation | Suggest the best pack based on value |
| Follow-up engine | Send timed reminders at 3-5 min and 30 min |
| Branching | React differently to yes / no / price / wholesale / complaint |
| Human handoff | Escalate to a human when the customer shows real buying intent or confusion |

### Important rule

For product questions, do not end with a generic line that feels copy-pasted.

Instead:
- confirm the item is available
- show price
- recommend the best pack
- wait for reply

---

## Implementation Notes

This behavior probably needs three layers:

1. **Tone and intent detection**
   - English / Manglish / Malayalam
   - product question / purchase intent / no-interest / wholesale / complaint

2. **Reply composition**
   - confirmation line
   - price table
   - soft recommendation
   - CTA

3. **Journey scheduler**
   - 3-5 minute follow-up
   - 30 minute follow-up
   - next-day follow-up

---

## Recommended First Fixes

| Priority | Fix | Why |
|---|---|---|
| 1 | Add confirmation-first reply templates | Makes the bot sound human |
| 2 | Add better tone selection | Matches customer language |
| 3 | Add soft recommendation lines per product | Improves conversion |
| 4 | Add response-state tracking | Enables follow-up timing |
| 5 | Add follow-up scheduler | Lets the bot continue the journey |
| 6 | Add branch handling for no-interest / wholesale / complaint | Prevents wrong next messages |

---

## Open Questions To Implement

| Question | Decision needed |
|---|---|
| Which products get the strongest recommendation lines? | Top sellers first |
| Do we follow up by WhatsApp only or also email? | Decide channel policy |
| Should silent leads get one or two reminders? | Decide maximum touch count |
| Should the 30-minute follow-up suggest a different product? | Decide cross-sell rules |
| Should human handoff happen after 1 or 2 failed attempts? | Decide escalation threshold |

---

## Summary

The correct flow is not just:

> product → price table

It should be:

> confirm → price → nudge → wait → follow up → branch by customer response

That is what will make the conversation feel human, polite, and conversion-friendly.
