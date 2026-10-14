All pages were downloaded on 2026-10-14 to `docs_ref/` (`llms-full.txt`, 476 KB, plus the individual `.md` pages) and read in full. "Live" means we made a real call with our key today.

| Feature used | Docs URL | Documented behaviour we rely on | How verified |
|---|---|---|---|
| Agent run-sse | https://docs.tinyfish.ai/agent-api/reference | `POST /v1/automation/run-sse`, events STARTED/STREAMING_URL/PROGRESS/HEARTBEAT/COMPLETE, no Last-Event-ID reconnect | **Live:** 20+ runs (e.g. `ed99edb9-…`, `cc53a529-…`). All 5 event types seen |
| `output_schema` | https://docs.tinyfish.ai/key-concepts/structured-output | top-level object, `nullable`, ≤64 KB, depth ≤10, arrays for lists, "schema wins" | **Live:** results matched the schema. Unit test checks our schema follows the rules |
| `agent_config.max_duration_seconds` | agent-api/reference | Not beta-gated (unlike `max_steps` / `mode:strict`, which return 403 for non-beta accounts) | **Live:** accepted. We deliberately don't send `max_steps` |
| `browser_profile: lite` | https://docs.tinyfish.ai/key-concepts/browser-profiles | default lite. Stealth for anti-bot | **Live:** lite worked on Workday and Greenhouse |
| Live view | https://docs.tinyfish.ai/live-preview | iframe the `streaming_url`. It "may become unavailable after the run completes" | **Live:** embedded in UI. Confirmed it goes blank after completion |
| GET run | https://docs.tinyfish.ai/api-reference/runs/get-run-by-id | status, steps[], streaming_url, video_url | **Live** |
| Step screenshot | https://docs.tinyfish.ai/api-reference/runs/get-step-screenshot | `GET /v1/runs/{id}/steps/{stepId}/screenshot` with API key, returns JPEG | **Live:** proxied as filmstrip. Screenshot proved the submit was blocked |
| Cancel run | https://docs.tinyfish.ai/api-reference/runs/cancel-run-by-id | `POST /v1/runs/{id}/cancel`, only for async/sse runs | Read. Wired into the submit guard (guard did not trip after the fix) |
| Search | https://docs.tinyfish.ai/search-api/reference | `GET api.search.tinyfish.ai?query=` → results[{position,site_name,title,snippet,url}]. 30 req/min. Free up to 12,000/day | **Live:** ~1.5 s, `site:` operator works |
| Fetch | https://docs.tinyfish.ai/fetch-api/reference | `POST api.fetch.tinyfish.ai` {urls ≤10, format, ttl}. Per-URL `errors[]`. 150 URLs/min. Free up to 1,000 URLs/day. 110 s backend timeout, so client timeout should be ≥150 s | **Live:** saw `empty_content`, `target_unreachable` |
| Wallet / pricing | https://docs.tinyfish.ai/api-reference/wallet/get-wallet, https://www.tinyfish.ai/pricing | Agent $0.016/step, Browser $0.002/min, Search/Fetch $0. Agent limit 2 concurrent runs, Browser 5 sessions | **Live:** `GET /v1/wallet` rates match the pricing page ($12.92 → see report) |
| Rate limits / errors | https://docs.tinyfish.ai/error-codes | 429 RATE_LIMIT_EXCEEDED + Retry-After. 402 INSUFFICIENT_CREDITS (wallet). COMPLETED ≠ goal achieved | Read. Implemented backoff. Our own result validation |
| Webhooks | https://docs.tinyfish.ai/webhooks | run webhook_url must be HTTPS. Payload has the same shape as GET run | Read only (no public HTTPS endpoint on box) |
| Monitor | https://docs.tinyfish.ai/monitor/api-reference | `POST /v1/monitors` type fetch/search, schedule_cron (UTC), purpose ≤2000, webhook_url | **Live:** `GET /v1/monitors` → `[]`. Create not exercised (no public webhook) |
| Vault | https://docs.tinyfish.ai/key-concepts/credentials | `use_vault`, `credential_item_ids`, domain-matched, 1Password/Bitwarden | **Live:** `GET /v1/vault/connections` → none connected, so not exercised |
| Browser Context Profiles | https://docs.tinyfish.ai/agent-api/browser-context-profiles | `/v1/profiles`, setup-session via CDP, `use_profile`/`profile_id` | **Live:** `GET /v1/profiles` → one default profile, 0 domains |

**Undocumented behaviour or contradictions we found**
1. `GET /v1/runs/{id}` returned `num_of_steps` as a **string** ("3"). The reference types it `integer|null`.
2. The SSE stream gave 3 PROGRESS events, but the run's `steps[]` had 4 entries. Even so, across all 25 runs the wallet went from $12.92 to $9.448 (−$3.47), which matches 217 PROGRESS steps × $0.016 = $3.47 exactly. Billing appears to follow PROGRESS events, not `steps[]`.
3. `video_url` was `null` on every run, although the reference lists it. Recording appears to need `capture_config` (account-gated).
4. Monitor `webhook_url` is documented as "public HTTP **or HTTPS**", while run webhooks "must use https://". The two are inconsistent.
5. The FAQ points to `POST /v1/automation/run-batch`, but the llms.txt index titles it "Start multiple automations asynchronously" without the path. The OpenAPI spec confirms `/v1/automation/run-batch`. Minor.
6. The Search free tier is documented as "12,000 requests per day", while the pricing page says "500 requests / hour". These match daily but not as a burst rule.
7. The Live Preview docs show a `*.unikraft.app` streaming host. We received `*.tetra-data.production.tinyfish.io` hosts, so don't allow-list a single domain.
8. The agent obeyed `output_schema` but returned the string "not available" instead of `null` for missing fields. We normalise these.
9. The SSE COMPLETE event in the docs shows `result` as an object. In the SDK it's `result_json`. Raw REST gave an object (we also handle strings).
