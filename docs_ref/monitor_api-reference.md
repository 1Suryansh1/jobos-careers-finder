> ## Documentation Index
> Fetch the complete documentation index at: https://docs.tinyfish.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Monitor API Reference

> Create and manage Page and Topic Monitors through the REST API

## Base URL

```text theme={null}
https://agent.tinyfish.ai
```

All requests require an `X-API-Key` header. See [Authentication](/authentication).

## Endpoints

| Method | Path | Description |
| - | - | - |
| `POST` | `/v1/monitors` | Create a Monitor and capture its baseline |
| `GET` | `/v1/monitors` | List your Monitors |
| `GET` | `/v1/monitors/{id}` | Get one Monitor |
| `PATCH` | `/v1/monitors/{id}` | Pause, resume, or edit a Monitor |
| `DELETE` | `/v1/monitors/{id}` | Delete a Monitor and its schedule |
| `POST` | `/v1/monitors/{id}/runs` | Run a Monitor immediately |

## Create a Monitor

<Tabs>
  <Tab title="Page">
    ```bash theme={null}
    curl -X POST "https://agent.tinyfish.ai/v1/monitors" \
      -H "X-API-Key: $TINYFISH_API_KEY" \
      -H "Content-Type: application/json" \
      -d '{
        "type": "fetch",
        "name": "Competitor pricing",
        "config": {
          "url": "https://example.com/pricing",
          "format": "markdown"
        },
        "schedule_cron": "0 9 * * *",
        "purpose": "A plan price changes",
        "webhook_url": "https://example.com/webhooks/monitor"
      }'
    ```
  </Tab>

  <Tab title="Topic">
    ```bash theme={null}
    curl -X POST "https://agent.tinyfish.ai/v1/monitors" \
      -H "X-API-Key: $TINYFISH_API_KEY" \
      -H "Content-Type: application/json" \
      -d '{
        "type": "search",
        "name": "EV policy updates",
        "config": {
          "query": "new electric vehicle policies",
          "recency_minutes": 1440,
          "result_limit": 5
        },
        "schedule_cron": "0 */6 * * *",
        "purpose": "A new policy is announced"
      }'
    ```
  </Tab>
</Tabs>

The response is `201 Created` and contains the new Monitor plus its first baseline run:

```json theme={null}
{
  "monitor": {
    "id": "e047c12d-5e82-43db-a826-cd45bc3ca4b7",
    "name": "Competitor pricing",
    "type": "fetch",
    "config": {
      "url": "https://example.com/pricing",
      "format": "markdown",
      "links": false,
      "image_links": false,
      "ttl": 0
    },
    "schedule_cron": "0 9 * * *",
    "status": "active",
    "last_error": null,
    "webhook_url": "https://example.com/webhooks/monitor",
    "created_at": "2026-09-09 09:00:00",
    "updated_at": "2026-09-09 09:00:00"
  },
  "run": {
    "id": "a497ee29-e1d4-4477-a285-ec86b35cff2c",
    "is_baseline": true,
    "results": [
      {
        "url": "https://example.com/pricing",
        "final_url": "https://example.com/pricing",
        "title": "Pricing",
        "description": null,
        "language": "en",
        "format": "markdown",
        "text": "# Pricing",
        "author": null,
        "published_date": null,
        "latency_ms": 412
      }
    ],
    "errors": []
  }
}
```

Monitor responses do not currently echo `purpose` or dashboard-managed email settings.

### Common Fields

<ParamField body="type" type="string" required>
  `fetch` for a Page Monitor or `search` for a Topic Monitor.
</ParamField>

<ParamField body="config" type="object" required>
  Type-specific configuration. See the Page and Topic fields below.
</ParamField>

<ParamField body="schedule_cron" type="string" required>
  A five-field cron expression. It runs in UTC unless prefixed with an IANA time zone, for example
  `CRON_TZ=America/New_York 0 9 * * 1-5`. Topic schedules must keep every run at least 30 minutes
  apart.
</ParamField>

<ParamField body="name" type="string">
  Optional Monitor name, up to 100 characters.
</ParamField>

<ParamField body="purpose" type="string">
  Optional description of the change that matters, up to 2000 characters. TinyFish evaluates
  detected changes against this purpose.
</ParamField>

<ParamField body="webhook_url" type="string">
  Optional public HTTP or HTTPS URL that receives every scheduled run result.
</ParamField>

<Note>
  Email delivery is currently configured in the dashboard. The REST API does not accept email
  settings.
</Note>

### Page Config

<ParamField body="config.url" type="string" required>
  Public HTTP or HTTPS webpage URL.
</ParamField>

<ParamField body="config.format" type="string" default="json">
  Extracted content format: `json`, `markdown`, or `html`.
</ParamField>

<ParamField body="config.links" type="boolean" default="false">
  Include links found on the webpage.
</ParamField>

<ParamField body="config.image_links" type="boolean" default="false">
  Include image links found on the webpage.
</ParamField>

Page Monitors always run Fetch with `ttl: 0` to prefer fresh content. The deprecated `config.ttl`
field is accepted for compatibility but does not change this behavior.

### Topic Config

<ParamField body="config.query" type="string" required>
  Search query to repeat, up to 2000 characters.
</ParamField>

<ParamField body="config.recency_minutes" type="integer">
  Optional freshness window from 1 to 5,256,000 minutes.
</ParamField>

<ParamField body="config.result_limit" type="integer" default="10">
  Number of results to compare per run, from 1 to 10.
</ParamField>

## List and Get Monitors

```bash theme={null}
curl "https://agent.tinyfish.ai/v1/monitors" \
  -H "X-API-Key: $TINYFISH_API_KEY"
```

The list response wraps Monitor objects in a `monitors` array. To retrieve one Monitor:

```bash theme={null}
curl "https://agent.tinyfish.ai/v1/monitors/$MONITOR_ID" \
  -H "X-API-Key: $TINYFISH_API_KEY"
```

Saved run history is currently available in the dashboard. The REST API returns the baseline from
creation and the result of each run-now request, but does not provide a run-history list endpoint.

## Pause or Resume

Send a status-only update. `active` resumes the schedule and `paused` stops future scheduled runs
without removing history.

```bash theme={null}
curl -X PATCH "https://agent.tinyfish.ai/v1/monitors/$MONITOR_ID" \
  -H "X-API-Key: $TINYFISH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"status":"paused"}'
```

## Edit a Monitor

Schedule edits must include `schedule_cron`. You can also replace or clear the name, purpose, and
webhook URL. Omitted optional fields keep their existing values.

```bash theme={null}
curl -X PATCH "https://agent.tinyfish.ai/v1/monitors/$MONITOR_ID" \
  -H "X-API-Key: $TINYFISH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "schedule_cron": "CRON_TZ=America/Los_Angeles 0 8 * * 1-5",
    "name": "Weekday pricing",
    "purpose": "The enterprise plan price changes",
    "webhook_url": null
  }'
```

The target type and its `config` cannot be changed after creation. Create a new Monitor to watch a
different page or topic.

<Warning>
  Do not combine `status` with schedule or metadata fields in one request. Send lifecycle and edit
  updates separately.
</Warning>

## Run Now

```bash theme={null}
curl -X POST "https://agent.tinyfish.ai/v1/monitors/$MONITOR_ID/runs" \
  -H "X-API-Key: $TINYFISH_API_KEY"
```

The response is `201 Created` with the Page Fetch result or Topic Search result under `run`. Run now
works for active, paused, and failed Monitors.

A Topic Monitor run can return `409 Conflict` with `error.code` set to `RETRY_REQUIRED` when the run
could not be created. Retry the request.

<Note>
  Run now records the result but does not send webhook or email notifications. Those delivery paths
  run only for scheduled checks.
</Note>

## Delete a Monitor

```bash theme={null}
curl -X DELETE "https://agent.tinyfish.ai/v1/monitors/$MONITOR_ID" \
  -H "X-API-Key: $TINYFISH_API_KEY"
```

Deleting a Monitor permanently removes the Monitor and its schedule. Its run history is no longer
available from Monitor.

```json theme={null}
{
  "deleted": true,
  "id": "e047c12d-5e82-43db-a826-cd45bc3ca4b7"
}
```

## Scheduled Webhook Payloads

Webhooks are sent for every scheduled run, including runs with no changes. Page payloads include a
`fetch_monitor_id`; Topic payloads include a `search_monitor_id`.

<Tabs>
  <Tab title="Page">
    ```json theme={null}
    {
      "fetch_monitor_id": "e047c12d-5e82-43db-a826-cd45bc3ca4b7",
      "id": "a497ee29-e1d4-4477-a285-ec86b35cff2c",
      "is_baseline": false,
      "results": [
        {
          "url": "https://example.com/pricing",
          "final_url": "https://example.com/pricing",
          "title": "Pricing",
          "description": null,
          "language": "en",
          "format": "markdown",
          "text": "# Pricing",
          "author": null,
          "published_date": null,
          "latency_ms": 398
        }
      ],
      "errors": []
    }
    ```
  </Tab>

  <Tab title="Topic">
    ```json theme={null}
    {
      "search_monitor_id": "e047c12d-5e82-43db-a826-cd45bc3ca4b7",
      "id": "a497ee29-e1d4-4477-a285-ec86b35cff2c",
      "request_id": "search-monitor:e047c12d:scheduled:message-id",
      "query": "new electric vehicle policies",
      "status_code": 200,
      "result_count": 1,
      "results": [
        {
          "position": 1,
          "site_name": "example.gov",
          "title": "New electric vehicle policy",
          "snippet": "The policy takes effect next year.",
          "url": "https://example.gov/ev-policy"
        }
      ],
      "new_result_positions": [],
      "created_at": "2026-09-09T16:00:00.000Z"
    }
    ```
  </Tab>
</Tabs>

Webhook delivery is best effort and retried up to three times. A delivery failure does not change
the completed Monitor run.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.