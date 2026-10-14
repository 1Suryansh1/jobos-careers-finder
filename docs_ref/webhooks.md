> ## Documentation Index
> Fetch the complete documentation index at: https://docs.tinyfish.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Webhooks

> Get notified when runs complete, fail, or are cancelled

Webhooks let you receive an HTTP callback when a run reaches a terminal state, so you don't need to poll for results.

## How It Works

1. Pass a `webhook_url` when you create a run
2. When the run finishes (`COMPLETED`, `FAILED`, or `CANCELLED`), TinyFish sends a `POST` request to your URL
3. The payload contains the full run data — the same shape as `GET /v1/runs/{id}`

<Info>
  Webhook delivery is non-blocking. If your endpoint is down, the run still succeeds — you can always fetch the result via the API.
</Info>

***

## Configuration

Add `webhook_url` to any run creation endpoint. The URL must use HTTPS.

```bash theme={null}
curl -X POST "https://agent.tinyfish.ai/v1/automation/run-async" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "goal": "Extract the page title",
    "webhook_url": "https://your-server.com/webhooks/tinyfish"
  }'
```

Webhooks are supported on all run endpoints: `/run`, `/run-async`, `/run-sse`, and `/run-batch`.

***

## Payload

Your endpoint receives a `POST` request with `Content-Type: application/json`:

```json theme={null}
{
  "event": "run.completed",
  "run_id": "4562765d-156e-4c47-b217-55b3ec4a9720",
  "status": "COMPLETED",
  "data": {
    "run_id": "4562765d-156e-4c47-b217-55b3ec4a9720",
    "status": "COMPLETED",
    "goal": "Extract the page title",
    "created_at": "2026-03-25T10:30:00Z",
    "started_at": "2026-03-25T10:30:05Z",
    "finished_at": "2026-03-25T10:30:45Z",
    "num_of_steps": 3,
    "result": { "title": "Example Domain" },
    "error": null,
    "streaming_url": "https://tf-abc123.fra0-tinyfish.unikraft.app/stream/0",
    "browser_config": {
      "proxy_enabled": false,
      "proxy_country_code": null
    },
    "steps": [
      {
        "id": "09de224d-fb2b-45b7-b067-585726194a2e",
        "timestamp": "2026-03-25T10:30:05Z",
        "status": "COMPLETED",
        "action": "Navigate to https://example.com",
        "screenshot": null,
        "duration": "1.2s"
      }
    ]
  }
}
```

### Minimal Example

A simplified view of the webhook payload with just the key fields:

```json theme={null}
{
  "event": "run.completed",
  "run_id": "run_abc123",
  "status": "COMPLETED",
  "data": {
    "started_at": "2026-01-15T10:30:00Z",
    "finished_at": "2026-01-15T10:30:45Z",
    "result": {
      "product_name": "Example Product",
      "price": 29.99
    },
    "error": null
  }
}
```

### Event Types

| Event | When |
| - | - |
| `run.completed` | Run finished (check `result` for data) |
| `run.failed` | Infrastructure error occurred |
| `run.cancelled` | Run was manually cancelled |

### Payload Fields

| Field | Type | Description |
| - | - | - |
| `event` | string | Event type (e.g. `run.completed`) |
| `run_id` | string | Unique run identifier |
| `status` | string | `COMPLETED`, `FAILED`, or `CANCELLED` |
| `data` | object | Full run data — same shape as `GET /v1/runs/{id}` |
| `data.result` | object \| null | Extracted data (when completed) |
| `data.error` | object \| null | Error details (when failed) |
| `data.steps` | array | List of actions the agent took |

<Note>
  Screenshots are not included in webhook payloads to keep the payload size small. To get screenshots, call `GET /v1/runs/{id}?screenshots=base64` after receiving the webhook.
</Note>

***

## Error Payload

When a run fails, `data.error` contains details about what went wrong:

```json theme={null}
{
  "event": "run.failed",
  "run_id": "run-2",
  "status": "FAILED",
  "data": {
    "error": {
      "message": "Site blocked access",
      "category": "AGENT_FAILURE"
    },
    "result": null
  }
}
```

***

## Retry Behavior

TinyFish retries failed webhook deliveries automatically:

| Behavior | Detail |
| - | - |
| Total attempts | 4 (1 initial + 3 retries) |
| Backoff | Exponential: 1s, 2s, 4s |
| Timeout | 10 seconds per attempt |
| 4xx responses | No retry (fails immediately) |
| 5xx responses | Retried with backoff |
| Network errors | Retried with backoff |

***

## Receiving Webhooks

Here's how to handle webhook events on your server:

<CodeGroup>
  ```typescript Express theme={null}
  import express from "express";

  const app = express();
  app.use(express.json());

  app.post("/webhooks/tinyfish", (req, res) => {
    const { event, run_id, data } = req.body;

    switch (event) {
      case "run.completed":
        console.log(`Run ${run_id} completed:`, data.result);
        // Process the result
        break;
      case "run.failed":
        console.error(`Run ${run_id} failed:`, data.error?.message);
        // Handle the error
        break;
      case "run.cancelled":
        console.log(`Run ${run_id} was cancelled`);
        break;
    }

    // Respond quickly — TinyFish has a 10s timeout
    res.status(200).send("OK");
  });
  ```

  ```python Flask theme={null}
  from flask import Flask, request

  app = Flask(__name__)

  @app.route("/webhooks/tinyfish", methods=["POST"])
  def handle_webhook():
      payload = request.json
      event = payload["event"]
      run_id = payload["run_id"]
      data = payload["data"]

      if event == "run.completed":
          print(f"Run {run_id} completed:", data["result"])
          # Process the result
      elif event == "run.failed":
          print(f"Run {run_id} failed:", data.get("error", {}).get("message"))
          # Handle the error
      elif event == "run.cancelled":
          print(f"Run {run_id} was cancelled")

      # Respond quickly — TinyFish has a 10s timeout
      return "OK", 200
  ```
</CodeGroup>

***

## Best Practices

<AccordionGroup>
  <Accordion title="Respond within 10 seconds">
    TinyFish waits up to 10 seconds for your response. Do heavy processing asynchronously — acknowledge the webhook immediately and handle the data in the background.
  </Accordion>

  <Accordion title="Handle duplicates idempotently">
    In rare cases (network retries, server restarts), you may receive the same webhook more than once. Use `run_id` to deduplicate.
  </Accordion>

  <Accordion title="Verify by fetching the run">
    For sensitive workflows, confirm the webhook data by calling `GET /v1/runs/{run_id}` before acting on the payload.
  </Accordion>

  <Accordion title="Return 2xx to acknowledge">
    Any 2xx response acknowledges the webhook. Non-2xx responses trigger retries (except 4xx, which fail immediately).
  </Accordion>
</AccordionGroup>

***

## Related

<CardGroup cols={2}>
  <Card title="Runs" icon="play" href="/key-concepts/runs">
    Understand run lifecycle and statuses
  </Card>

  <Card title="Endpoints" icon="plug" href="/key-concepts/endpoints">
    Choose sync, async, or streaming
  </Card>
</CardGroup>


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.