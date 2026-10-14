> ## Documentation Index
> Fetch the complete documentation index at: https://docs.tinyfish.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Runs

> The lifecycle of a TinyFish Web Agent automation

A run is a single execution of an automation. When you call any TinyFish Web Agent endpoint, you create a run that moves through a lifecycle from start to finish.

## Run Lifecycle

Every run moves through these statuses:

| Status | Meaning |
| - | - |
| `PENDING` | Queued, waiting to start |
| `RUNNING` | Browser is executing your goal |
| `COMPLETED` | Finished (check result for data) |
| `FAILED` | Infrastructure error occurred |
| `CANCELLED` | Manually stopped |

<Info>
  Cancellation is only supported for runs created via `/run-async` or `/run-sse`. Runs created via the synchronous `/run` endpoint cannot be cancelled because the request blocks until completion.
</Info>

***

## Strict Agent Mode

<Info>
  **Beta:** Strict Agent Mode is in beta — you must join the beta to use it (contact support to enable it
  for your account). Set `agent_config.mode` to `strict` when creating a run.
</Info>

```json theme={null}
{
  "url": "https://example.com",
  "goal": "Check that checkout succeeds with a saved test account",
  "agent_config": {
    "mode": "strict"
  }
}
```

Strict mode is designed for precise tests and repeatable automation. When the agent encounters an
unexpected state, it stops faster instead of exploring workarounds. Use the default mode for
open-ended browsing, search, or recovery-oriented tasks.

***

## Max Steps

<Info>
  **Beta:** Custom `max_steps` is in beta — you must join the beta to use it (contact support to
  enable it for your account). Set `agent_config.max_steps` when creating a run.
</Info>

```json theme={null}
{
  "url": "https://example.com",
  "goal": "Extract all pricing information",
  "agent_config": {
    "max_steps": 50
  }
}
```

`max_steps` caps how many tool-call steps the agent takes before it stops. Accepts an integer from
1 to 500; runs default to 150 when omitted. Lower it to fail fast and bound cost on simple goals,
raise it for multi-page workflows that legitimately need more steps to finish.

***

## The Run Object

When you fetch a run, you get back the following object:

```json theme={null}
{
  "run_id": "abc123",
  "status": "COMPLETED",
  "goal": "Extract all pricing information",
  "created_at": "2026-01-14T10:30:00Z",
  "started_at": "2026-01-14T10:30:05Z",
  "finished_at": "2026-01-14T10:31:30Z",
  "num_of_steps": 5,
  "result": { ... },
  "output_schema": null,
  "profile_attached": false,
  "profile_id": null,
  "error": null,
  "streaming_url": "https://tf-abc123.fra0-tinyfish.unikraft.app/stream/0",
  "browser_config": { "proxy_enabled": false, "proxy_country_code": null },
  "video_url": null,
  "steps": [ ... ]
}
```

| Field | Description |
| - | - |
| `run_id` | Unique identifier for this run |
| `status` | Current lifecycle status |
| `goal` | Natural language goal for this run |
| `created_at` | ISO 8601 timestamp when the run was created |
| `started_at` | ISO 8601 timestamp when the run started executing. `null` while pending. |
| `finished_at` | ISO 8601 timestamp when the run finished. `null` until terminal. |
| `num_of_steps` | Number of steps taken during the run. `null` while in progress. |
| `result` | Your extracted data (when COMPLETED) |
| `output_schema` | Structured-output schema subset originally requested for this run. `null` when none was provided. |
| `profile_attached` | Whether this run attached a Browser Context Profile internally |
| `profile_id` | Browser Context Profile ID attached to this run, or `null` when none attached |
| `error` | Error details (when FAILED). See [The Error Object](#the-error-object). |
| `streaming_url` | URL to watch the browser live (available while running) |
| `browser_config` | Browser configuration used for the run (`proxy_enabled`, `proxy_country_code`) |
| `video_url` | Presigned URL to the run recording, if available. `null` when no recording exists. URL expires after 15 minutes. |
| `steps` | Steps the agent took during this run. See [Retrieving Steps and Screenshots](#retrieving-steps-and-screenshots). |

### The Error Object

When a run fails, `error` is a structured object (otherwise it is `null`):

```json theme={null}
{
  "code": "service_busy",
  "message": "Browser crashed during execution",
  "category": "SYSTEM_FAILURE",
  "retry_after": 60,
  "help_url": "https://docs.tinyfish.ai/prompting-guide",
  "help_message": "Need help? Check out our goal prompting guide for tips and examples."
}
```

| Field | Description |
| - | - |
| `code` | Machine-readable error code for programmatic handling (optional) |
| `message` | Human-readable error message describing why the run failed |
| `category` | One of `SYSTEM_FAILURE`, `AGENT_FAILURE`, `BILLING_FAILURE`, or `UNKNOWN` |
| `retry_after` | Suggested retry delay in seconds, or `null` if not retryable |
| `help_url` | URL to troubleshooting documentation (optional) |
| `help_message` | Human-readable guidance (optional) |

Use `category` to decide how to react: `SYSTEM_FAILURE` is a TinyFish issue (retry after `retry_after`), `AGENT_FAILURE` means the input needs fixing, `BILLING_FAILURE` means the run was rejected at the billing check before it started — add money at [agent.tinyfish.ai/wallet](https://agent.tinyfish.ai/wallet) (minimum top-up \$10), or add credits on a legacy account — and `UNKNOWN` should be treated as retryable.

Runs can also use [vault credentials](/key-concepts/credentials) for authenticated automation. Pass `use_vault: true` and optionally `credential_item_ids` when creating a run to let TinyFish log into sites using your connected password manager.

***

## Searching and Filtering Runs

`GET /v1/runs` supports filtering, text search, sorting, and pagination to help you find specific runs.

### Query Parameters

| Parameter | Type | Description |
| - | - | - |
| `status` | string | Filter by status: `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED` |
| `goal` | string | Search runs by goal text (case-insensitive partial match) |
| `created_after` | ISO 8601 | Only return runs created after this timestamp |
| `created_before` | ISO 8601 | Only return runs created before this timestamp |
| `sort_direction` | `asc` \| `desc` | Sort order by creation date (default: `desc`) |
| `cursor` | string | Pagination cursor from a previous response |
| `limit` | number | Results per page, 1–100 (default: 20) |

### Examples

**Search by goal text:**

```bash theme={null}
curl "https://agent.tinyfish.ai/v1/runs?goal=linkedin" \
  -H "X-API-Key: YOUR_API_KEY"
```

**Filter by status and date range:**

```bash theme={null}
curl "https://agent.tinyfish.ai/v1/runs?status=COMPLETED&created_after=2026-01-01T00:00:00Z&created_before=2026-02-01T00:00:00Z" \
  -H "X-API-Key: YOUR_API_KEY"
```

**Oldest first with pagination:**

```bash theme={null}
curl "https://agent.tinyfish.ai/v1/runs?sort_direction=asc&limit=10" \
  -H "X-API-Key: YOUR_API_KEY"
```

### Response Shape

`GET /v1/runs` returns a `data` array of run objects and a `pagination` object:

```json theme={null}
{
  "data": [
    {
      "run_id": "run_abc123",
      "status": "COMPLETED",
      "goal": "Extract the page title",
      "created_at": "2026-01-01T00:00:00Z",
      "started_at": "2026-01-01T00:00:01Z",
      "finished_at": "2026-01-01T00:00:30Z"
    }
  ],
  "pagination": {
    "total": 42,
    "next_cursor": null,
    "has_more": false
  }
}
```

### Cursor Pagination

When there are more results, the pagination object includes `next_cursor`:

```json theme={null}
{
  "data": [ ... ],
  "pagination": {
    "total": 142,
    "next_cursor": "eyJpZCI6...",
    "has_more": true
  }
}
```

Pass `next_cursor` as the `cursor` parameter to fetch the next page.

***

## Watching Runs Live

Every run includes a `streaming_url` where you can watch the browser execute in real-time. This is useful for debugging, demos, or showing users what's happening behind the scenes.

Embed the URL in an iframe to display the live browser view in your app:

```html theme={null}
<iframe
  src="https://tf-abc123.fra0-tinyfish.unikraft.app/stream/0"
  width="800"
  height="600"
/>
```

The streaming URL is available while the run is active. After the run completes, use `video_url` from the run object to access the recording.

***

## Retrieving Steps and Screenshots

<Warning>
  `?screenshots=base64` is available to unblock current integrations but is temporary — it will be deprecated soon in favor of URL-based access. Avoid building long-term workflows that depend on this format.
</Warning>

`GET /v1/runs/{id}` always returns a `steps` array. The `screenshots` query param controls how the per-step `screenshot` field is delivered:

| `screenshots` | Behavior |
| - | - |
| `url` (default) | Each step's `screenshot` is an absolute URL to the screenshot image |
| `base64` | Each step's `screenshot` is an inline `data:image/jpeg;base64,...` data URI (\~50–100 KB each — use only for audit trails or visual debugging) |
| `none` | Screenshots are omitted (`screenshot` is `null`) |

```bash theme={null}
curl "https://agent.tinyfish.ai/v1/runs/abc123?screenshots=base64" \
  -H "X-API-Key: YOUR_API_KEY"
```

The `html` query param controls the per-step `html` field, a URL to the full-page HTML snapshot captured at that step. It is only non-`null` when the run was created with `capture_config.html: true`.

| `html` | Behavior |
| - | - |
| `url` (default) | Each step's `html` is an absolute URL to the HTML snapshot |
| `none` | HTML URLs are omitted (`html` is `null`) |

Each step has the following shape (this example reflects the default `screenshots=url`):

```json theme={null}
{
  "run_id": "abc123",
  "status": "COMPLETED",
  "result": { ... },
  "steps": [
    {
      "id": "09de224d-fb2b-45b7-b067-585726194a2e",
      "timestamp": "2026-03-23T10:00:01Z",
      "status": "COMPLETED",
      "action": "Navigate to https://example.com",
      "screenshot": "https://agent.tinyfish.ai/runs/abc123/steps/09de224d/screenshot",
      "html": "https://agent.tinyfish.ai/runs/abc123/steps/09de224d/html",
      "duration": "1.2s"
    },
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "timestamp": "2026-03-23T10:00:03Z",
      "status": "COMPLETED",
      "action": "Click the 'Sign In' button",
      "screenshot": "https://agent.tinyfish.ai/runs/abc123/steps/3fa85f64/screenshot",
      "html": null,
      "duration": "0.8s"
    }
  ]
}
```

***

## Understanding COMPLETED Status

<Warning>
  `COMPLETED` means the infrastructure worked, not that your goal succeeded.
</Warning>

Always check the `result` field:

**Goal succeeded:**

```json theme={null}
{
  "status": "COMPLETED",
  "result": {
    "products": [
      { "name": "Widget", "price": 29.99 }
    ]
  }
}
```

**Infrastructure worked, goal failed:**

The browser worked fine, but TinyFish Web Agent couldn't achieve your goal.

```json theme={null}
{
  "status": "COMPLETED",
  "result": {
    "status": "failure",
    "reason": "Could not find any products on the page"
  }
}
```

***

## Handling Run Results

Use this pattern to handle both infrastructure failures and goal failures in your code.

```typescript theme={null}
import { TinyFish, RunStatus } from "@tiny-fish/sdk";
import type { Run } from "@tiny-fish/sdk";

const client = new TinyFish();

// Fetch a run by ID, then handle the result
const run = await client.runs.get(runId);
const result = await handleRunResult(run);

async function handleRunResult(run: Run) {
  switch (run.status) {
    case RunStatus.COMPLETED:
      if (!run.result) {
        return { success: false, error: "No result returned" };
      }

      // Check for goal-level failure in result
      if (run.result.status === "failure" || run.result.error) {
        return {
          success: false,
          error: run.result.reason || run.result.error || "Goal not achieved",
        };
      }

      return { success: true, data: run.result };

    case RunStatus.FAILED:
      return {
        success: false,
        error: run.error?.message || "Automation failed",
        retryable: true,
      };

    case RunStatus.CANCELLED:
      return { success: false, error: "Run was cancelled" };

    default:
      return { success: false, error: `Unexpected status: ${run.status}` };
  }
}
```

***

## Cancelling Runs

You can cancel a run that is `PENDING` or `RUNNING` by sending a POST request to `/v1/runs/{id}/cancel`. This works for runs created via `/run-async` or `/run-sse` only.

```typescript theme={null}
const response = await fetch(`https://agent.tinyfish.ai/v1/runs/${run_id}/cancel`, {
  method: "POST",
  headers: {
    "X-API-Key": process.env.TINYFISH_API_KEY,
  },
});

const result = await response.json();
// result.status: CANCELLED, COMPLETED, or FAILED
// result.cancelled_at: timestamp if cancelled
// result.message: additional context (e.g. "Run already cancelled")
```

The cancel endpoint is **idempotent** — calling it on an already-cancelled or completed run returns the current state without error.

| Scenario | Response `status` | `cancelled_at` | `message` |
| - | - | - | - |
| Run cancelled | `CANCELLED` | Timestamp | `null` |
| Already cancelled | `CANCELLED` | Timestamp | `"Run already cancelled"` |
| Already completed | `COMPLETED` | `null` | `"Run already finished"` |

<Warning>
  Only runs created via the API (`/run-async` or `/run-sse`) can be cancelled using this endpoint. Runs created through the dashboard UI or via the synchronous `/run` endpoint cannot be cancelled.
</Warning>

***

## Related

<CardGroup cols={2}>
  <Card title="Endpoints" icon="plug" href="/key-concepts/endpoints">
    Choose sync, async, or streaming
  </Card>

  <Card title="Error Codes" icon="triangle-exclamation" href="/error-codes">
    Handle errors gracefully
  </Card>

  <Card title="Vault Credentials" icon="lock" href="/key-concepts/credentials">
    Use password manager credentials in runs
  </Card>
</CardGroup>


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.