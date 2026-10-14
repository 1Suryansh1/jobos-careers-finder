> ## Documentation Index
> Fetch the complete documentation index at: https://docs.tinyfish.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Browser Context Profiles

> Persist logged-in browser state across TinyFish runs

Stop logging in from scratch on every run.

Browser Context Profiles let TinyFish save browser state — cookies, local storage, and session storage — and
reuse it later. Recurring automations can start where a real returning user would: already signed in,
with the right workspace, preferences, and site context loaded.

<Note>
  **Browser Context Profiles are not Browser Profiles.**
  [Browser Profiles](/key-concepts/browser-profiles) choose the runtime mode with
  `browser_profile: "lite" | "stealth"`. Browser Context Profiles save session state across runs.
</Note>

<CardGroup cols={2}>
  <Card title="Use the API" icon="code" href="/agent-api/browser-context-profiles">
    Create and run with Browser Context Profiles programmatically
  </Card>

  <Card title="Vault Credentials" icon="vault" href="/key-concepts/credentials">
    Add stale-session repair
  </Card>
</CardGroup>

## The flow

<CardGroup cols={3}>
  <Card title="1. Set up once" icon="right-to-bracket">
    Open a setup browser, sign in, and save the session.
  </Card>

  <Card title="2. Run many times" icon="repeat">
    Reuse saved state so recurring runs start authenticated.
  </Card>

  <Card title="3. Repair when stale" icon="rotate">
    Add Vault so TinyFish can log back in if the session expires.
  </Card>
</CardGroup>

## Set up a Browser Context Profile

<Tabs>
  <Tab title="Dashboard">
    1. Go to **Browser Context Profiles** in the TinyFish dashboard.
    2. Click **Create Profile**.
    3. Name the profile.
    4. Optional: mark it as the default profile.
    5. Optional: choose a proxy location for the profile.
    6. Click **Create and set up**.
    7. Sign in to the target site in the setup browser.
    8. Save the setup session.

    <Tip>
      Use one Browser Context Profile per account or environment, such as `Salesforce Production` and
      `Salesforce Sandbox`.
    </Tip>
  </Tab>

  <Tab title="API">
    Create the profile, start a setup session, connect your own Playwright/Puppeteer/CDP controller
    to `cdp_url`, sign in, then save it with the returned `session_id`. The hosted setup UI is
    only a manual helper; API setup is controlled through these endpoints.

    ```bash theme={null}
    curl -X POST https://agent.tinyfish.ai/v1/profiles \
      -H "X-API-Key: $TINYFISH_API_KEY" \
      -H "Content-Type: application/json" \
      -d '{
        "name": "Salesforce Production",
        "set_as_default": true
      }'
    ```

    ```bash theme={null}
    curl -X POST https://agent.tinyfish.ai/v1/profiles/prof_abc123def4567890/setup-session \
      -H "X-API-Key: $TINYFISH_API_KEY" \
      -H "Content-Type: application/json" \
      -d '{ "url": "https://app.example.com/login" }'
    ```

    The setup-session response includes `session_id`, `cdp_url`, `base_url`, `timeout_seconds`, and
    `expires_at`. Use `cdp_url` for Playwright/Puppeteer/CDP. Use `base_url` only for TinyFish HTTP
    session endpoints such as `/pages`. After signing in, save the setup browser state:

    ```bash theme={null}
    curl -X POST https://agent.tinyfish.ai/v1/profiles/prof_abc123def4567890/save \
      -H "X-API-Key: $TINYFISH_API_KEY" \
      -H "Content-Type: application/json" \
      -d '{ "session_id": "sess_123" }'
    ```

    <Card title="Browser Context Profiles API" icon="code" href="/agent-api/browser-context-profiles">
      Full setup, upload, update, and cleanup reference
    </Card>
  </Tab>
</Tabs>

## Use a Browser Context Profile

<Tabs>
  <Tab title="Playground">
    1. Open the Playground.
    2. Click the profile icon in the toolbar.
    3. Turn on **Use Browser Context Profile**.
    4. Choose a profile, or use your default profile.
    5. Run the automation.

    If no profile exists, click **Go to Browser Context Profiles** to create one first.
  </Tab>

  <Tab title="API: default profile">
    Use your default Browser Context Profile with `use_profile: true`:

    ```bash theme={null}
    curl -X POST https://agent.tinyfish.ai/v1/automation/run \
      -H "X-API-Key: $TINYFISH_API_KEY" \
      -H "Content-Type: application/json" \
      -d '{
        "url": "https://app.example.com/dashboard",
        "goal": "Open the dashboard and summarize the latest alerts",
        "use_profile": true
      }'
    ```
  </Tab>

  <Tab title="API: specific profile">
    Target a specific Browser Context Profile by ID:

    ```bash theme={null}
    curl -X POST https://agent.tinyfish.ai/v1/automation/run-async \
      -H "X-API-Key: $TINYFISH_API_KEY" \
      -H "Content-Type: application/json" \
      -d '{
        "url": "https://app.example.com/dashboard",
        "goal": "Export the weekly usage report",
        "use_profile": true,
        "profile_id": "prof_abc123def4567890"
      }'
    ```
  </Tab>
</Tabs>

## Manage Browser Context Profiles

On the **Browser Context Profiles** page, you can:

* Rename Browser Context Profiles
* Set a default Browser Context Profile
* Copy a profile ID
* View saved domains
* Set or clear a profile proxy location
* Upload cookies manually
* Delete individual domains
* Delete Browser Context Profiles

<Note>
  You cannot delete your only active profile. Create another profile first.
</Note>

## Browser Context Profiles + Vault

The best authenticated setup is Browser Context Profiles plus [Vault Credentials](/key-concepts/credentials).

<CardGroup cols={3}>
  <Card title="Browser Context Profiles" icon="window">
    Keep persistent logged-in browser state across runs.
  </Card>

  <Card title="Vault" icon="vault">
    Provide matching credentials when a login form appears.
  </Card>

  <Card title="Together" icon="rotate">
    Repair stale sessions instead of logging in cold every run.
  </Card>
</CardGroup>

Use this pairing for authenticated workflows where sessions expire over time. The Browser Context Profile starts
the run with saved state. If that state has gone stale and a matching Vault credential is available,
TinyFish can sign in again and refresh the profile state for future runs.

```json theme={null}
{
  "url": "https://app.example.com/dashboard",
  "goal": "Check the dashboard and summarize anything urgent",
  "use_profile": true,
  "use_vault": true
}
```

<Steps>
  <Step title="Start with saved state">
    TinyFish opens the site with the cookies and storage saved in the Browser Context Profile.
  </Step>

  <Step title="Detect stale login">
    If the site asks for login again, the agent proceeds through the normal login flow.
  </Step>

  <Step title="Repair with Vault">
    When `use_vault: true` is set and a matching credential exists, TinyFish can use it to restore
    the session and keep future profile runs healthy.
  </Step>
</Steps>

<Tip>
  Start with Browser Context Profiles for persistence, then add Vault for stale-session repair. This is usually
  more reliable than asking the agent to log in from scratch on every run.
</Tip>

## When to use Browser Context Profiles

| Use Browser Context Profiles when... | Start fresh when... |
| - | - |
| A run should stay logged in | The site is public or anonymous |
| You repeat the same workflow often | Browser history or cookies would bias the result |
| Logging in every run is slow, fragile, or MFA-heavy | The task must prove it can work from a blank browser |
| The account has site preferences, workspace context, or saved filters | You are testing a first-time visitor flow |

## Proxies and stealth mode

Browser Context Profiles answer “what state should this run start with?” Proxies and Browser Profiles answer
“how should the browser connect and behave?”

| Capability | Use it for |
| - | - |
| Browser Context Profile | Reusing saved cookies and storage |
| Profile proxy location | Keeping a logged-in session tied to one country |
| Per-run proxy | Choosing a location for one run when the profile has no proxy location |
| `browser_profile: "stealth"` | Using the anti-detection browser runtime |

Choose a profile proxy location when a logged-in session should consistently come from the same
country. Leave it blank when location should be decided per run with [Proxies](/key-concepts/proxies).
Use [Browser Profiles](/key-concepts/browser-profiles) when you need `lite` or `stealth` runtime mode.

## Limits and expectations

| Limit | What to expect |
| - | - |
| Account scope | Browser Context Profiles are scoped to your TinyFish account and API key owner |
| Session expiry | Sites can still expire cookies, require MFA, or force re-authentication |
| CAPTCHA | Browser Context Profiles reduce repeated-login friction, but do not solve reCAPTCHA or hCaptcha |
| Fresh-browser tasks | Disable `use_profile` when the run should start with no saved state |

## Next steps

<CardGroup cols={2}>
  <Card title="Browser Context Profiles API" icon="code" href="/agent-api/browser-context-profiles">
    Manage profiles programmatically
  </Card>

  <Card title="Vault Credentials" icon="vault" href="/key-concepts/credentials">
    Add stale-session repair
  </Card>

  <Card title="Browser Profiles" icon="browser" href="/key-concepts/browser-profiles">
    Choose lite or stealth runtime mode
  </Card>
</CardGroup>


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.