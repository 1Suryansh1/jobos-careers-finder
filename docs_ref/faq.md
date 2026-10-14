> ## Documentation Index
> Fetch the complete documentation index at: https://docs.tinyfish.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Frequently Asked Questions

> Common questions about TinyFish Web Agent

## General

<AccordionGroup>
  <Accordion title="What is TinyFish Web Agent?" icon="circle-info">
    TinyFish Web Agent is an AI-powered web automation API that lets you automate any website using natural language.
    Instead of writing brittle selectors, you describe what you want to do, and our AI handles the rest.
  </Accordion>

  <Accordion title="What sites can I automate?" icon="globe">
    Any publicly accessible website. For authenticated sites, use [Vault Credentials](/key-concepts/credentials) or a
    saved [Browser Context Profile](/key-concepts/browser-context-profiles) instead of putting passwords in your goal.
    For sites with bot protection, use stealth mode and a proxy.
  </Accordion>

  <Accordion title="How fast are automations?" icon="bolt">
    Typically 3-10 seconds for simple pages, 30-60 seconds for complex multi-step automations. Time depends on page load
    speed and task complexity.
  </Accordion>

  <Accordion title="Can I see the browser?" icon="eye">
    Yes. Runs provide a `streaming_url` where you can watch the browser execute live. With the SSE API, listen for the
    `STREAMING_URL` event; for queued runs, retrieve the run with `client.runs.get(run_id)` or `GET /v1/runs/:id`.
  </Accordion>
</AccordionGroup>

## API Usage

<AccordionGroup>
  <Accordion title="What authentication method do I use?" icon="key">
    The REST API uses the `X-API-Key` header:

    ```
    X-API-Key: $TINYFISH_API_KEY
    ```

    The Python SDK, TypeScript SDK, and CLI also use your API key. The MCP endpoint uses OAuth 2.1 for AI assistant
    integrations. CLI run IDs and MCP run IDs are scoped to different tokens, so a CLI lookup for an MCP-created run can
    return 404 by design.
  </Accordion>

  <Accordion title="Do you support proxies?" icon="route">
    Yes, configure proxy routing:

    ```typescript theme={null}
    {
      proxy_config: {
        enabled: true,
        country_code: "US"
      }
    }
    ```

    Supported countries: US, GB, CA, DE, FR, JP, AU.
  </Accordion>

  <Accordion title="How do I process many URLs?" icon="list-check">
    For a few immediate results, use concurrent sync requests with `asyncio.gather()`, `Promise.all()`, or shell
    background jobs. For larger or long-running sets, use `agent.queue()` in SDKs, `POST /v1/automation/run-batch` in
    REST, or `tinyfish agent batch run` in the CLI.

    See [Concurrent Requests](/examples/bulk-requests-sync) and [Async Bulk Requests](/examples/bulk-requests-async).
  </Accordion>
</AccordionGroup>

## Technical

<AccordionGroup>
  <Accordion title="What browsers do you use?" icon="browser">
    We use Chromium-based browsers. Choose between:

    * **Lite**: Standard Chromium (fast)
    * **Stealth**: Modified Chromium with anti-detection (slower but bypasses bot protection)
  </Accordion>

  <Accordion title="What about JavaScript-heavy sites?" icon="js">
    We fully support SPAs (React, Vue, Angular). Pages are rendered and JavaScript is executed before extraction.
  </Accordion>

  <Accordion title="Can I automate authenticated content?" icon="lock">
    Yes! For password-manager login, connect your password manager (1Password or Bitwarden) in **Settings → Vault**.
    Select credentials per run and TinyFish handles login securely — the AI agent never sees your actual passwords.
    For sites where saved session state matters, create a Browser Context Profile after signing in once, then use that
    profile on future runs.

    See the [Connect Your Vault](/vault-setup) guide for setup, [Vault Credentials](/key-concepts/credentials) for how
    credential access works, and [Browser Context Profiles](/key-concepts/browser-context-profiles) for reusing cookies,
    MFA state, and trusted-device sessions.

    API example:

    ```typescript theme={null}
    const run = await client.agent.run({
      url: "https://app.example.com/dashboard",
      goal: "Log in and summarize the account dashboard",
      use_vault: true,
      use_profile: true,
    });
    ```

    If you haven't connected a vault or saved profile, you can still include login steps in your goal:

    ```typescript theme={null}
    goal: `
      1. Login with username "user@example.com" and password "pass123"
      2. Navigate to dashboard
      3. Extract account balance
    `
    ```

    <Warning>Including credentials directly in goals is less secure — they appear in run logs and AI context. Use vault credentials when possible.</Warning>
  </Accordion>

  <Accordion title="Do you support pagination?" icon="arrows-left-right">
    Yes, describe pagination in your goal:

    ```typescript theme={null}
    goal: `Click "Next Page" button 5 times, extracting products from each page`
    ```
  </Accordion>
</AccordionGroup>

## Troubleshooting

<AccordionGroup>
  <Accordion title="What does COMPLETED status mean?" icon="circle-check" id="what-does-completed-status-mean">
    `status: "COMPLETED"` means the **infrastructure succeeded** - the browser launched, navigated, and the automation finished without crashing.

    **It does NOT mean the goal was achieved.** You must check the `result` field to determine if the goal succeeded.

    **Scenario 1: Goal achieved**

    ```json theme={null}
    {
      "status": "COMPLETED",
      "result": {
        "products": [
          { "name": "iPhone 15", "price": "$799" }
        ]
      },
      "error": null
    }
    ```

    The `result` contains the extracted data - goal succeeded.

    **Scenario 2: Infrastructure succeeded, goal failed**

    ```json theme={null}
    {
      "status": "COMPLETED",
      "result": {
        "status": "failure",
        "reason": "Could not find any products on the page",
        "product_price": null
      },
      "error": null
    }
    ```

    Status is COMPLETED (browser worked), but `result.status` is "failure" indicating the goal wasn't achieved.

    **Scenario 3: Infrastructure failed**

    ```json theme={null}
    {
      "status": "FAILED",
      "result": null,
      "error": {
        "message": "Browser crashed during execution"
      }
    }
    ```

    The automation couldn't complete due to infrastructure issues.

    **Best Practice:** Always validate `result` content, not just `status`:

    ```typescript theme={null}
    if (run.status === "COMPLETED" && run.result) {
      // Check if result indicates goal failure
      if (run.result.status === "failure" || run.result.error) {
        console.log("Goal not achieved:", run.result.reason || run.result.error);
      } else {
        console.log("Data extracted:", run.result);
      }
    } else if (run.status === "FAILED") {
      console.log("Automation failed:", run.error?.message);
    }
    ```
  </Accordion>

  <Accordion title="Why is my automation failing?" icon="bug">
    Common causes:

    1. **Timeout** - Site is slow or down
       * Solution: Retry or use stealth mode
    2. **Access Denied** - Anti-bot protection
       * Solution: Use stealth mode + proxy
    3. **Element Not Found** - Goal is too specific
       * Solution: Make goal more flexible (describe visually)
    4. **Invalid URL** - URL is malformed
       * Solution: Ensure URL includes `https://`
  </Accordion>

  <Accordion title="Site is blocking me. What do I do?" icon="shield">
    ```typescript theme={null}
    // Use stealth mode
    browser_profile: "stealth"

    // Add proxy
    proxy_config: {
      enabled: true,
      country_code: "US"
    }

    // Reduce speed (add delays in goal)
    goal: "Wait 3 seconds, then click button"
    ```
  </Accordion>
</AccordionGroup>

## Best Practices

<AccordionGroup>
  <Accordion title="What makes a good goal?" icon="bullseye">
    **Good** (specific, actionable):

    ```typescript theme={null}
    goal: "Extract product name, price, and stock status from the product details section"
    ```

    **Bad** (vague):

    ```typescript theme={null}
    goal: "Get data"
    ```
  </Accordion>

  <Accordion title="When should I use stealth mode?" icon="user-secret">
    Use stealth when:

    * Site shows CAPTCHA
    * Getting "Access Denied" errors
    * Site uses Cloudflare or anti-bot protection

    Otherwise use lite mode (faster).
  </Accordion>
</AccordionGroup>

## Getting Help

<CardGroup cols={2}>
  <Card title="Email Support" icon="envelope" href="mailto:support@tinyfish.io">
    [support@tinyfish.io](mailto:support@tinyfish.io)
  </Card>

  <Card title="Discord Community" icon="discord" href="https://discord.gg/tinyfish">
    Join our community
  </Card>
</CardGroup>

## Related

<CardGroup cols={3}>
  <Card title="Quick Start" icon="rocket" href="/quick-start">
    Get started in 5 minutes
  </Card>

  <Card title="API Reference" icon="code" href="/api-reference">
    Complete endpoint docs
  </Card>
</CardGroup>


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.