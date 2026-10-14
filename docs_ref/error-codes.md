> ## Documentation Index
> Fetch the complete documentation index at: https://docs.tinyfish.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Error Codes

> API error codes and how to resolve them

TinyFish surfaces errors in two layers, and you need to handle both:

1. **API-level errors** — returned as non-2xx HTTP responses (auth, validation, rate limits, server errors).
2. **Run-response error codes** — returned with HTTP **200** inside the `error` object of a run response (agent failures, infrastructure issues that map to a finished run, cancellations).

Knowing which layer you're looking at tells you whether the issue is with the request, your account, or the automation itself.

## Error Response Format

API-level errors contain an `error` object with a `code`, a `message`, and optional `details`. The shape of `details` depends on the error code:

```json theme={null}
// 400 Bad Request — may include validation details
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "Field \"url\": Invalid input: expected string, received undefined",
    "details": [
      {
        "expected": "string",
        "code": "invalid_type",
        "path": ["url"],
        "message": "Invalid input: expected string, received undefined"
      }
    ]
  }
}
```

```json theme={null}
// 401 invalid API key — no additional details
{
  "error": {
    "code": "INVALID_API_KEY",
    "message": "Invalid or expired API key"
  }
}
```

```json theme={null}
// 401 vault reconnect required — affected provider IDs
{
  "error": {
    "code": "VAULT_RECONNECT_REQUIRED",
    "message": "1Password vault connection expired. Reconnect 1Password in Vault settings before starting a run with vault credentials.",
    "details": { "providers": ["1password"] }
  }
}
```

Most error bodies also carry a top-level `request_id` that matches the `X-Request-ID` response header. Include it when contacting support.

<Note>
  `details` is optional. For `INVALID_INPUT` (400), it can be an array of [Zod](https://zod.dev/) validation issues containing `code`, `path`, `message`, and issue-specific fields. For `VAULT_RECONNECT_REQUIRED` (401), it can be an object containing `providers`, an array of provider ID strings such as `1password` and `bitwarden`.
</Note>

`/v1/automation/run-batch` can return a per-run validation envelope; see [Batch Errors](#batch-errors). Vault reconnect failures before enqueueing use the top-level error shape shown above.

## API-level Error Codes

### MISSING\_API\_KEY

**HTTP Status:** 401

The `X-API-Key` header was not included in the request.

```json theme={null}
{
  "error": {
    "code": "MISSING_API_KEY",
    "message": "X-API-Key header is required"
  }
}
```

**Solution:** Add the `X-API-Key` header to your request:

```bash theme={null}
curl -H "X-API-Key: ***" ...
```

***

### INVALID\_API\_KEY

**HTTP Status:** 401

The provided API key does not exist or has been revoked.

```json theme={null}
{
  "error": {
    "code": "INVALID_API_KEY",
    "message": "Invalid or expired API key"
  }
}
```

**Solutions:**

1. Verify your API key is correct (no extra whitespace)
2. Check if the key was deleted in the [API Keys dashboard](https://agent.tinyfish.ai/api-keys)
3. Generate a new key if needed

***

### UNAUTHORIZED

**HTTP Status:** 401

Authentication failed for a reason other than missing/invalid key. For example, required user context may be missing. Expired vault credentials use `VAULT_RECONNECT_REQUIRED`.

```json theme={null}
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Authentication failed"
  }
}
```

**Solutions:**

1. Check your account status at [agent.tinyfish.ai/api-keys](https://agent.tinyfish.ai/api-keys)
2. For Vault-related calls, reconnect your vault under **Settings → Vault**
3. Try generating a new API key

***

### VAULT\_RECONNECT\_REQUIRED

**HTTP Status:** 401

A vault connection needs replacement credentials. Reconnect the affected provider from the Vault page, then retry the request. Vault-backed runs reject credentials already marked expired before enqueueing; other provider-scoped runs can remain usable.

The TypeScript and Python SDKs preserve `code = "VAULT_RECONNECT_REQUIRED"` on the authentication exception. Check this code to distinguish vault recovery from an invalid TinyFish API key. Responses may identify affected provider IDs in `error.details.providers`.

CLI users can reconnect with `tinyfish vault connection add --provider 1password` or `tinyfish vault connection add --provider bitwarden --client-id <client-id>`. Supply the replacement 1Password token through `TINYFISH_VAULT_TOKEN`, or Bitwarden secrets through `TINYFISH_VAULT_CLIENT_SECRET` and `TINYFISH_VAULT_MASTER_PASSWORD`, then retry. CLI guidance requires an updated CLI version.

***

### INVALID\_INPUT

**HTTP Status:** 400

The request body failed validation.

```json theme={null}
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "Field \"browser_profile\": Invalid option: expected one of \"lite\"|\"stealth\"",
    "details": [
      {
        "code": "invalid_value",
        "values": ["lite", "stealth"],
        "path": ["browser_profile"],
        "message": "Invalid option: expected one of \"lite\"|\"stealth\""
      }
    ]
  }
}
```

**Common Causes:**

* `url` is missing or not a valid URL (must include `https://`)
* `goal` is empty or missing
* `browser_profile` is not `"lite"` or `"stealth"`
* `proxy_config.country_code` is not a supported 2-letter code (US, GB, CA, DE, FR, JP, AU)
* `output_schema` is invalid JSON Schema
* Missing required query parameter (e.g. `query` on `/v1/search`)

**Solution:** Check the `details` field for specific validation errors. Each entry includes the failing field `path` and a human-readable `message`.

***

### FORBIDDEN

**HTTP Status:** 403

Authentication succeeded, but the request was rejected — usually because the account lacks an entitlement, capability, or remaining credits. The credit case applies to legacy credit/subscription accounts only; wallet accounts get [`INSUFFICIENT_CREDITS`](#insufficient-credits-wallet-accounts) at 402 instead.

```json theme={null}
{
  "error": {
    "code": "FORBIDDEN",
    "message": "Insufficient credits. You have 0 credits remaining. Requested 1 runs. Add credits at https://..."
  }
}
```

**Common Causes:**

* No remaining credits or expired subscription on a legacy credit/subscription account
* `proxy_config.type: "custom"` requested without the custom-proxy entitlement
* `output_schema` provided without the output-schema entitlement
* `capture_config` requests a capability the account isn't enabled for
* Attempting to access a resource you don't own

**Solution:** Check your account balance and subscription at [agent.tinyfish.ai/api-keys](https://agent.tinyfish.ai/api-keys), or contact support to enable a specific capability. The `message` field always specifies which entitlement or condition failed.

***

### INSUFFICIENT\_CREDITS (wallet accounts)

**HTTP Status:** 402

The account's TinyFish wallet balance is too low to start this run. This is a pre-flight check — the run is never created, and it is not retryable until money is added. Runs are never cut off mid-flight: a run already in progress finishes even if it takes the balance negative, and it's the next one that gets denied.

```json theme={null}
{
  "error": {
    "code": "INSUFFICIENT_CREDITS",
    "message": "Run not started: the user's TinyFish wallet balance is too low ($-2.50). This is not retryable and will keep failing until money is added. Tell the user to add money at https://agent.tinyfish.ai/wallet (minimum top-up $10), then try again.",
    "details": {
      "status": "failed",
      "error": "Run not started: the user's TinyFish wallet balance is too low ($-2.50). This is not retryable and will keep failing until money is added. Tell the user to add money at https://agent.tinyfish.ai/wallet (minimum top-up $10), then try again.",
      "reason": "wallet_out_of_funds",
      "non_retryable": true,
      "balance": "-2.50",
      "currency": "usd",
      "wallet_url": "https://agent.tinyfish.ai/wallet",
      "minimum_top_up": "10.00",
      "auto_reload_needs_payment_fix": false
    }
  }
}
```

**Common Causes:**

* Wallet balance is zero or negative
* Auto-reload is paused because the payment method on file was declined

`details` carries machine-readable fields (`balance`, `currency`, `wallet_url`, `minimum_top_up`, `auto_reload_needs_payment_fix`) so REST callers can act on the denial without parsing `message`. `/v1/automation/run-batch` includes the same `details` object on its wallet-denial error slot.

**Solution:** Add money at [agent.tinyfish.ai/wallet](https://agent.tinyfish.ai/wallet) (minimum top-up \$10), or update the payment method if auto-reload is paused, then retry.

**Search and Fetch:** these return the same status and code when the daily free allowance (12,000 Search requests, 1,000 Fetch URLs; resets at 00:00 UTC) is used and the wallet balance is zero or below. Nothing is fetched or searched. The error carries only `code` and `message`:

```json theme={null}
{
  "error": {
    "code": "INSUFFICIENT_CREDITS",
    "message": "Daily free Search allowance used and your wallet balance is empty. Add funds at https://agent.tinyfish.ai/wallet?utm_source=api&utm_medium=insufficient_funds&utm_campaign=search"
  }
}
```

Add funds and retry after a few seconds, or wait for the allowance to reset.

***

### FREE\_ALLOWANCE\_EXHAUSTED (metered products)

**HTTP Status:** 402

The product's daily free allowance is used and the product does not charge your wallet — products in beta ship this way, so adding funds does not help. Nothing is fetched or searched. The allowance resets at 00:00 UTC.

```json theme={null}
{
  "error": {
    "code": "FREE_ALLOWANCE_EXHAUSTED",
    "message": "Daily free Search allowance used; it resets at 00:00 UTC."
  }
}
```

**Solution:** Retry after the daily reset.

***

### FEATURE\_NOT\_AVAILABLE

**HTTP Status:** 404

The account is not enabled for the requested feature. Currently emitted only by `GET /v1/wallet`, when the account is on legacy credit/subscription billing rather than a wallet — this is the discriminator for telling the two billing modes apart at request time.

```json theme={null}
{
  "error": {
    "code": "FEATURE_NOT_AVAILABLE",
    "message": "Wallet is not available for your account yet."
  }
}
```

**Solution:** The account isn't wallet-enabled. Use the legacy credits/subscription flow instead — check your account at [agent.tinyfish.ai/api-keys](https://agent.tinyfish.ai/api-keys).

***

### NOT\_FOUND

**HTTP Status:** 404

The requested resource does not exist.

```json theme={null}
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Run with id 'a1b2c3d4-...' not found"
  }
}
```

**Common Causes:**

* Invalid `run_id` in `GET /v1/runs/:id`
* Vault connection not found
* Browser context profile not found
* Step HTML/screenshot not found (`GET /v1/runs/:id/steps/:stepId/...`)
* Run was deleted or never existed
* Run ID belongs to a different token scope — CLI/REST run IDs and MCP run IDs live in separate scopes, so a CLI lookup for an MCP-created run returns 404 by design

**Solution:** Verify the resource ID is correct. Run IDs are returned from `/v1/automation/run-async` or can be listed via `GET /v1/runs`.

***

### RETRY\_REQUIRED

**HTTP Status:** 409

A transient conflict prevented the request from completing. Currently emitted by Browser Context Profile setup endpoints (`/v1/profiles/:id/save`, `/v1/profiles/:id/setup-session`, `/v1/profiles/:id/setup-session/cancel`) when the setup session is in an intermediate state.

```json theme={null}
{
  "error": {
    "code": "RETRY_REQUIRED",
    "message": "Setup session is busy. Please retry in a moment."
  }
}
```

**Solution:** Wait briefly and retry. Use a short delay (1–2s) plus exponential backoff if the conflict persists.

***

### RATE\_LIMIT\_EXCEEDED

**HTTP Status:** 429

Too many requests in a short period.

```json theme={null}
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Limit: 30 requests per minute. Request a higher limit at https://agent.tinyfish.ai/wallet?utm_source=api&utm_medium=rate_limit_error&utm_campaign=search",
    "details": {
      "limit": 30,
      "unit": "requests",
      "window_seconds": 60,
      "upgrade_url": "https://agent.tinyfish.ai/wallet?utm_source=api&utm_medium=rate_limit_error&utm_campaign=search"
    }
  }
}
```

The `message` wording varies by endpoint. Read `details` instead of parsing it:

| Field | Values | Meaning |
| - | - | - |
| `details.limit` | integer | The ceiling that was hit |
| `details.unit` | `"requests"` or `"urls"` | What the limit counts (`urls` for Fetch, `requests` for Search) |
| `details.window_seconds` | integer | The window the limit applies over |
| `details.upgrade_url` | URL | Where to request a higher limit, routed to your billing page |

`details` is present when **your account's** per-minute limit rejected the call, which is the case this section describes. Two other conditions also return `RATE_LIMIT_EXCEEDED` and deliberately omit `details`, because no change to your plan would clear them:

* The upstream search or fetch provider throttled the request. Retry with backoff.
* The automation pending-run cap was hit. Wait for existing runs to finish.
* Too many usage reads or invalid requests (60 per minute combined). Invalid Search or Fetch requests count toward this limit even though each one returns 400. Fix the request, then retry with backoff.

Treat a missing `details` as "retry, do not upsell".

Rate limits depend on your account's limits and which API you're calling:

* `/v1/search` and `/v1/fetch` enforce per-minute request limits, applied per API key.
* `/v1/automation/run`, `/run-async`, and `/run-batch` enforce a pending-run cap tied to your account's concurrency limit.

See the [Search](/search-api/reference#rate-limits) and [Fetch](/fetch-api/reference#rate-limits) references for the specific numbers. To raise a limit, follow `details.upgrade_url` from the error body.

**Response headers:**

| Header | When set | Description |
| - | - | - |
| `Retry-After` | Search, Fetch (per-minute limits) | Suggested retry delay in seconds |
| `X-RateLimit-Limit` | Search, Fetch (200 and 429 responses) | Your current per-minute limit |
| `X-RateLimit-Remaining` | Search, Fetch (200 and 429 responses) | Requests (Search) or URLs (Fetch) left in the current window; `0` on a 429 |
| `X-RateLimit-Reset` | Search, Fetch (when the window is known) | Unix time in seconds when the current window resets |
| `X-Request-ID` | Search, Fetch | Request ID for support / observability |

<Note>
  The automation **pending-run cap** (429 from `/v1/automation/run`, `/run-async`, `/run-batch`) does **not** set `Retry-After` or `X-RateLimit-Limit` — wait for existing runs to finish and retry. The body message includes your current count and the maximum.
</Note>

**Solutions:**

1. Respect `Retry-After` when present, otherwise implement exponential backoff
2. Space out requests (recommended: 1-2 seconds between calls)
3. Use batch endpoints for high-volume workloads
4. Request a higher limit by following `details.upgrade_url` from the error body

**Example: Exponential Backoff**

```python theme={null}
import time
import random
from tinyfish import TinyFish, RateLimitError

client = TinyFish()

def call_with_backoff(fn, max_retries=5):
    for attempt in range(max_retries):
        try:
            return fn()
        except RateLimitError as exc:
            if attempt == max_retries - 1:
                raise
            # Prefer server hint when available
            retry_after = getattr(exc, "retry_after", None)
            wait = retry_after if retry_after else (2 ** attempt) + random.uniform(0, 1)
            time.sleep(wait)
```

***

### DAILY\_LIMIT\_EXCEEDED

**HTTP Status:** 429

The account reached its daily allowance for a capability. Research (`POST /v1/automation/run-research`) counts runs
started per Pacific calendar day, including runs still in progress. Runs that fail, time out, or are cancelled do not
count.

```json theme={null}
{
  "error": {
    "code": "DAILY_LIMIT_EXCEEDED",
    "message": "Today's Big Search limit has been reached. Please try again later.",
    "details": {
      "capability": "big_search_completion",
      "limit": 5,
      "used": 5,
      "remaining": 0,
      "reason": "exhausted",
      "window": "pacific_day",
      "resets_at": "2026-09-10T07:00:00.000Z"
    }
  }
}
```

| Field | Meaning |
| - | - |
| `details.capability` | Which allowance was exhausted |
| `details.limit` / `used` / `remaining` | The allowance and its consumption for the window |
| `details.window` | The window the allowance resets on (`pacific_day`) |
| `details.resets_at` | ISO 8601 timestamp when the allowance resets |

**Response headers:** `Retry-After`, `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` (Unix seconds).

**Solution:** Wait for `resets_at`, or contact support to raise the allowance. Unlike `RATE_LIMIT_EXCEEDED`, backoff
within the same day will not clear this error.

***

### INTERNAL\_ERROR

**HTTP Status:** 500

An unexpected error occurred on the server.

```json theme={null}
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "An unexpected error occurred"
  }
}
```

**Solutions:**

1. Retry the request after a brief delay
2. If the error persists, check [agent.tinyfish.ai/status](https://agent.tinyfish.ai/status) for outages
3. Contact support with your request details and timestamp (include `request_id` or `X-Request-ID` if you have it)

***

### BACKEND\_UNAVAILABLE

**HTTP Status:** 502, 503, or 504

The service handling the request was unreachable or timed out. An unavailable authentication or rate-limit store returns [`SERVICE_BUSY`](#service_busy) instead.

```json theme={null}
{
  "error": {
    "code": "BACKEND_UNAVAILABLE",
    "message": "Backend service timed out."
  },
  "request_id": "5f0c2b8e-…"
}
```

**Solution:** Retry with exponential backoff, honoring `Retry-After` when present. This is not caused by your request or your plan.

***

### UNKNOWN\_ROUTE

**HTTP Status:** 400 or 404

The request path does not match any API. Check the path against the API reference.

## Run-response Error Codes

Once a run is accepted, **completion-time failures** are reported inside the run response body — not as HTTP error codes. The HTTP response is **200**, and you inspect `status` + `error`:

```json theme={null}
{
  "run_id": "a1b2c3d4-...",
  "status": "FAILED",
  "result": null,
  "error": {
    "code": "SITE_BLOCKED",
    "message": "Target site blocked the automation. Try using stealth mode.",
    "category": "AGENT_FAILURE",
    "retry_after": null,
    "help_url": "https://docs.tinyfish.ai/key-concepts/browser-profiles#stealth",
    "help_message": "Getting blocked? Try enabling stealth mode."
  }
}
```

The `category` field gives you a quick branching key:

| Category | Meaning | Recommended action |
| - | - | - |
| `SYSTEM_FAILURE` | TinyFish-side issue (browser crash, capacity, infra timeout) | Retry the run |
| `AGENT_FAILURE` | The agent ran but couldn't achieve the goal (site blocked, content not found, auth required, etc.) | Refine input — change goal, enable stealth, attach a profile, etc. |
| `BILLING_FAILURE` | The run was rejected at the billing check before it started — wallet balance too low, or out of credits on a legacy account | Add money at [agent.tinyfish.ai/wallet](https://agent.tinyfish.ai/wallet) (minimum top-up \$10); legacy accounts add credits |
| `UNKNOWN` | Unclassified | Treat as retryable |

Optional fields:

* `retry_after` — suggested delay in seconds (`null` if not retryable)
* `help_url` — link to troubleshooting docs
* `help_message` — short human-readable guidance

### SERVICE\_BUSY

**Category:** `SYSTEM_FAILURE` · **In-body HTTP:** 200

The platform is temporarily out of capacity (browser pool exhausted, dependent service unavailable). Equivalent to a 503 if returned at the HTTP layer.

`/v1/search` and `/v1/fetch` return it as HTTP 503 when a backing store is down, including the rate-limit store.

**Solution:** Retry with exponential backoff.

### TIMEOUT

**Category:** `SYSTEM_FAILURE` · **In-body HTTP:** 200

An infrastructure or request timeout terminated the run. Equivalent to a 504.

**Solution:** Retry. If the goal is large/multi-step, consider splitting it or simplifying.

### BILLING\_REJECTED

**Category:** `BILLING_FAILURE` · **In-body HTTP:** 200

The run was rejected at the billing check before execution — the wallet balance was too low, or a legacy account was out of credits. The agent never started, so the run lands in a terminal `CANCELLED` status with no steps recorded. Runs are never cut off mid-flight: one already in progress finishes even if it takes the balance negative, and it's the next one that gets denied.

The same condition can also be caught earlier and reported at the HTTP layer, before the run record is created — [`INSUFFICIENT_CREDITS`](#insufficient-credits-wallet-accounts) at 402 for wallet accounts, [`FORBIDDEN`](#forbidden) at 403 for legacy credit/subscription accounts. Handle both.

**Solution:** Add money at [agent.tinyfish.ai/wallet](https://agent.tinyfish.ai/wallet) — minimum top-up \$10. Legacy accounts add credits at [agent.tinyfish.ai/api-keys](https://agent.tinyfish.ai/api-keys). Then retry.

### CONTENT\_POLICY\_VIOLATION

**Category:** `AGENT_FAILURE` · **In-body HTTP:** 200

The request — typically the goal text or a target URL — was blocked by content policy.

**Solution:** Adjust the goal or target. Contact support if you believe the block was a false positive.

### MAX\_STEPS\_EXCEEDED

**Category:** `AGENT_FAILURE` · **In-body HTTP:** 200

The automation hit the configured maximum step count without producing a result.

**Solution:** Simplify the goal, split it into multiple runs, or raise the step limit if your account's limits allow it.

### SITE\_BLOCKED

**Category:** `AGENT_FAILURE` · **In-body HTTP:** 200

The target site blocked the automation (anti-bot, CAPTCHA, IP block). The `status` field is still `FAILED`.

**Solution:** Switch `browser_profile` to `"stealth"`, attach a proxy via `proxy_config`, or use a Browser Context Profile with a warmed session. See the [anti-bot guide](/anti-bot-guide).

### TASK\_FAILED

**Category:** `AGENT_FAILURE` · **In-body HTTP:** 200

The agent ran but couldn't achieve the goal — navigation failed, content not found, authentication required, the result was incorrect, or the task wasn't achievable as described.

**Solution:** Make the goal more concrete (which page, which selector-equivalent description, which field). See the [prompting guide](/prompting-guide). For auth flows, use a vault credential or a saved profile.

### CANCELLED

**Category:** *N/A* · **Status:** `CANCELLED` · **In-body HTTP:** 200

The run was cancelled — either by you (`POST /v1/runs/:id/cancel`), by SDK cancellation, or because the async task lifecycle was terminated. Not an error in the usual sense.

**Solution:** No action needed unless the cancellation was unintended.

## Batch Errors

`/v1/automation/run-batch` validates the whole request first, then dispatches each child run. Batch-level failures (auth, missing capability, validation) follow the standard `{ "error": { "code", "message" } }` shape, with an optional `details` object on wallet-denial (`INSUFFICIENT_CREDITS`, 402) errors — see the example above. Per-run dispatch errors are returned inside the batch response under each run's slot. Treat the batch envelope as "did the batch get accepted?" and inspect each child for "did the individual run get scheduled?"

## Run Status vs Error Codes

<Note>
  HTTP error codes (the table below) indicate **request-level failures** — your request didn't make it to the agent. Run-response error codes indicate **completion-level outcomes** — the run reached the worker and reported back.

  For more on COMPLETED-but-failed runs, see [Understanding Run Status](/faq#what-does-completed-status-mean).
</Note>

## HTTP Status Code Summary

| Status | Meaning | Error codes returned |
| - | - | - |
| 200 | OK (run finished — may still carry a run-response error) | `SERVICE_BUSY`, `TIMEOUT`, `BILLING_REJECTED`, `CONTENT_POLICY_VIOLATION`, `MAX_STEPS_EXCEEDED`, `SITE_BLOCKED`, `TASK_FAILED`, `CANCELLED` (all inside the response body) |
| 400 | Bad Request | `INVALID_INPUT`, `UNKNOWN_ROUTE` |
| 401 | Unauthorized | `MISSING_API_KEY`, `INVALID_API_KEY`, `UNAUTHORIZED`, `VAULT_RECONNECT_REQUIRED` |
| 402 | Payment Required | `INSUFFICIENT_CREDITS` (wallet accounts, pre-flight), `FREE_ALLOWANCE_EXHAUSTED` (metered products that do not charge the wallet) |
| 403 | Forbidden | `FORBIDDEN` |
| 404 | Not Found | `NOT_FOUND`, `FEATURE_NOT_AVAILABLE` (`GET /v1/wallet`, legacy accounts), `UNKNOWN_ROUTE` |
| 409 | Conflict | `RETRY_REQUIRED` |
| 429 | Too Many Requests | `RATE_LIMIT_EXCEEDED`, `DAILY_LIMIT_EXCEEDED` |
| 500 | Server Error | `INTERNAL_ERROR` |
| 502, 504 | Bad Gateway, Gateway Timeout | `BACKEND_UNAVAILABLE` |
| 503 | Service Unavailable | `SERVICE_BUSY`, `BACKEND_UNAVAILABLE` |

## Related

<CardGroup cols={2}>
  <Card title="Authentication" icon="key" href="/authentication">
    API key setup and troubleshooting
  </Card>

  <Card title="FAQ" icon="circle-question" href="/faq">
    Common questions and issues
  </Card>
</CardGroup>


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.