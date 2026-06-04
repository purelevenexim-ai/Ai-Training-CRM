# WhatsApp Server Orchestration Control

## Goal

Make PureLeven the single decision-maker for WhatsApp replies when enabled, while keeping an instant emergency fallback where Wabis can continue without server-generated replies.

## Cleanest Operating Model

| Mode | Server behavior | Wabis behavior | Use case |
|---|---|---|---|
| Server Control ON | Receives webhook, checks state, routes message, sends product/AI replies when needed | Continues only when structured button/expected flow input is detected | Normal production mode |
| Wabis Fallback Mode | Receives/audits webhook but does not route, mutate state, or send replies | Native Wabis automation can continue | Emergency kill switch |
| AI Paused | Server can still audit/protect flows, but generated replies are paused | Wabis button flows can continue | Debugging AI quality without losing visibility |

## Routing Rules

| Customer action | Expected owner | Result |
|---|---|---|
| Sends `hi` | Wabis flow | Welcome/language flow can start |
| Clicks Malayalam/English button | Wabis flow | Continue Wabis flow |
| Types `cardamom` during Wabis flow | Server/Product catalog | Break Wabis flow and send product reply |
| Types `patta undo?` | Server/Product catalog | Reply in Manglish tone |
| Types complaint/refund/damaged | Human/escalation | Escalate, do not sell |
| Server Control OFF | Wabis fallback | Server stands down immediately |

## Main Failure Modes

| Risk | Guardrail |
|---|---|
| Wabis sends welcome again after product text | Server-first routing plus Wabis native trigger restriction |
| Gemini gives wrong answer | Product catalog canonical replies before AI fallback |
| Button clicks get mistaken for product text | Structured button passthrough guard |
| Product text trapped inside Wabis flow | Flow-break detector |
| Emergency incident during live chat | Dashboard `Wabis Fallback` switch |
| Legacy flow table missing | Flow cleanup tolerates missing `conversation_flow` table |
| Server receives webhook but Wabis also auto-replies | Wabis dashboard must restrict native triggers to greetings/buttons |

## Dashboard Controls

| Control | Meaning |
|---|---|
| Instant WhatsApp Control: Server Controls | PureLeven backend owns routing first |
| Instant WhatsApp Control: Wabis Fallback | Backend stands down; Wabis can continue |
| AI Reply Generation: Start/Stop AI | Pauses generated replies without changing the ownership mode |
| Detect flow breaks | Allows product/support text to exit Wabis flow |
| Let Wabis structured button clicks continue | Protects native flow buttons from AI override |
| Live follow-up sending | Controls delayed follow-up sends |

## Test Coverage Added

| Test | Coverage |
|---|---|
| `test_server_control_off_stands_down_before_routing` | Emergency switch prevents routing/sending |
| `test_wabis_button_click_stays_with_wabis_flow` | Native button clicks remain in Wabis |
| `test_product_text_breaks_active_wabis_flow_when_guardrail_enabled` | Product text exits active Wabis flow |
| `test_product_text_does_not_break_wabis_flow_when_guardrail_disabled` | Guardrail can be disabled safely |
| Existing product reply tests | Canonical cardamom, pepper, cinnamon, clove, turmeric replies |

## Required Wabis Configuration

The backend can stand down or take control after receiving webhooks, but it cannot cancel a native Wabis message that Wabis has already sent.

For the clean setup, Wabis native automations should be restricted so they trigger only on:

- Exact greetings such as `hi`, `hello`, `start`
- Structured button/postback interactions
- Explicit Wabis flow steps

Wabis native automations should not trigger on product/free-text terms such as:

- `cardamom`, `elakka`
- `pepper`, `kurumulak`
- `patta`, `cinnamon`
- `clove`, `grambu`, `gampoo`
- `turmeric`, `manjal`
- `undo`, `venam`, `venda`, `price`, `rate`, `ethra`

