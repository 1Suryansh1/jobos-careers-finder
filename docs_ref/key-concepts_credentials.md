> ## Documentation Index
> Fetch the complete documentation index at: https://docs.tinyfish.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Vault Credentials

> How TinyFish uses your password manager credentials to log into websites during runs

When your vault is connected, you select which credentials TinyFish uses for each run. The AI agent handles navigation and identifies login forms. TinyFish fills in the actual credentials securely, without the agent ever seeing your passwords.

***

## Using the Playground

<Steps>
  <Step title="Open the vault selector">
    Click the lock icon in the playground toolbar.

    <img src="https://mintcdn.com/tinyfish/syPJyeND12dEB_sp/images/vault/playground-no-vault.png?fit=max&auto=format&n=syPJyeND12dEB_sp&q=85&s=ea4c41fe46e5d39b513e7ee6518c9c29" alt="Playground toolbar with vault lock icon in gray state" width="735" height="263" data-path="images/vault/playground-no-vault.png" />
  </Step>

  <Step title="Select credentials">
    Check the credentials you want to use for the run. Items are grouped by provider and vault name, and you can use **Select all** or **Deselect all**.

    <img src="https://mintcdn.com/tinyfish/syPJyeND12dEB_sp/images/vault/playground-credential-selector.png?fit=max&auto=format&n=syPJyeND12dEB_sp&q=85&s=f0498d8490fefeeac957a17634a563ef" alt="Vault access popover with credentials grouped by provider and checkboxes" width="440" height="401" data-path="images/vault/playground-credential-selector.png" />
  </Step>

  <Step title="Run your automation">
    Write your goal, then click **Run**. TinyFish handles login during the run when a matching site requires it.

    <img src="https://mintcdn.com/tinyfish/syPJyeND12dEB_sp/images/vault/playground-vault-connected.png?fit=max&auto=format&n=syPJyeND12dEB_sp&q=85&s=034abd7f4a0080061a2d580fc0817835" alt="Playground with vault icon showing credential count badge and goal filled in" width="712" height="251" data-path="images/vault/playground-vault-connected.png" />
  </Step>
</Steps>

<Note>
  Your credential selections persist across sessions.
</Note>

***

## Using the API

<CodeGroup>
  ```python Python theme={null}
  from tinyfish import TinyFish

  client = TinyFish()

  # Use all vault credentials for the run
  response = client.agent.run(
      url="https://www.linkedin.com",
      goal="Log in and capture the latest 3 posts from the feed",
      use_vault=True,
  )

  # Scope the run to specific credentials only
  scoped = client.agent.run(
      url="https://www.linkedin.com",
      goal="Log in and capture the latest 3 posts from the feed",
      use_vault=True,
      credential_item_ids=[
          "cred:conn-abc:Work:item-123",
          "cred:conn-def:Personal:item-456",
      ],
  )
  ```

  ```typescript TypeScript theme={null}
  import { TinyFish } from "@tiny-fish/sdk";

  const client = new TinyFish();

  // Use all vault credentials for the run
  const response = await client.agent.run({
    url: "https://www.linkedin.com",
    goal: "Log in and capture the latest 3 posts from the feed",
    use_vault: true,
  });

  // Scope the run to specific credentials only
  const scoped = await client.agent.run({
    url: "https://www.linkedin.com",
    goal: "Log in and capture the latest 3 posts from the feed",
    use_vault: true,
    credential_item_ids: [
      "cred:conn-abc:Work:item-123",
      "cred:conn-def:Personal:item-456",
    ],
  });
  ```

  ```bash cURL theme={null}
  # Use all vault credentials for the run
  curl -X POST https://agent.tinyfish.ai/v1/automation/run \
    -H "X-API-Key: $TINYFISH_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
      "url": "https://www.linkedin.com",
      "goal": "Log in and capture the latest 3 posts from the feed",
      "use_vault": true
    }'

  # Scope the run to specific credentials only
  curl -X POST https://agent.tinyfish.ai/v1/automation/run \
    -H "X-API-Key: $TINYFISH_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
      "url": "https://www.linkedin.com",
      "goal": "Log in and capture the latest 3 posts from the feed",
      "use_vault": true,
      "credential_item_ids": [
        "cred:conn-abc:Work:item-123",
        "cred:conn-def:Personal:item-456"
      ]
    }'
  ```

  ```bash CLI theme={null}
  # Use all vault credentials for the run
  tinyfish agent run "Log in and capture the latest 3 posts from the feed" \
    --url https://www.linkedin.com \
    --use-vault

  # Scope the run to specific credentials only (IDs from `tinyfish vault item list`)
  tinyfish agent run "Log in and capture the latest 3 posts from the feed" \
    --url https://www.linkedin.com \
    --use-vault \
    --credential-item-id cred:conn-abc:Work:item-123 \
    --credential-item-id cred:conn-def:Personal:item-456
  ```
</CodeGroup>

***

## Parameters

| Parameter | Type | Required | Default | Description |
| - | - | - | - | - |
| `use_vault` | boolean | No | `false` | Enable vault credentials for this run |
| `credential_item_ids` | string\[] | No | All synced items | Scope to specific credential URIs from [`GET /v1/vault/items`](/vault-setup#managing-your-vault). Requires `use_vault: true` |

***

## Domain Matching

Credentials are matched by domain.

For example, a credential with `linkedin.com` in its URL will be available when the agent navigates to `www.linkedin.com` or `login.linkedin.com`.

Credentials are not available on unrelated domains.

If you have multiple credentials for the same domain, TinyFish uses the ones you selected for that run.

***

## Security

### What the AI agent sees

Labels and field names only. Never actual values. The agent tells TinyFish where to type, and TinyFish handles what to type.

### What we don't do

Credentials never appear in agent prompts, run logs, screenshots, or streaming output. We do not rely on visual obfuscation as a security measure.

### Credential lifecycle

Credentials are resolved at the browser automation layer, not the AI planning layer. Values exist in memory only for the duration of the input action, then are discarded.

### Per-run access

Each run only gets the credentials you explicitly selected. The default is no vault access with `use_vault: false`.

### Encryption

Vault provider tokens are encrypted at rest and never stored in plaintext. You can revoke access by disconnecting the vault or rotating the token.

***

## Limitations

| Limitation | Notes |
| - | - |
| MFA / TOTP | Supported for time-based codes if the vault item has a TOTP field. Hardware keys and push notifications are not supported |
| Anti-bot | Some sites block automated login even with correct credentials. Use stealth mode and a proxy |
| Account lockout | Failed attempts count against normal lockout policies |
| OAuth / SSO | Redirect-based flows may not work for all providers |

<Tip>
  For logged-in workflows, combine vault credentials with
  [Browser Context Profiles](/key-concepts/browser-context-profiles). Browser Context Profiles maintain session state; Vault can
  repair it when a matching credential is available. For bot protection, also use
  [Proxies](/key-concepts/proxies).
</Tip>

***

## Troubleshooting

<AccordionGroup>
  <Accordion title="credential_item_ids requires use_vault to be true" icon="triangle-exclamation">
    Add `use_vault: true` to the request body.
  </Accordion>

  <Accordion title="Credentials not being used during run" icon="circle-question">
    Verify the credential domain matches the target site.
  </Accordion>

  <Accordion title="use_vault is true but no vault connected" icon="plug-circle-xmark">
    Connect a vault first in **Settings → Vault**.
  </Accordion>

  <Accordion title="Wrong credential used" icon="key">
    Use `credential_item_ids` to scope the run to the exact credential you want.
  </Accordion>

  <Accordion title="Login failed or keeps repeating" icon="shield">
    Pair Vault with [Browser Context Profiles](/key-concepts/browser-context-profiles). Browser Context Profiles keep the browser
    logged in; if the session goes stale and a matching vault credential is available, TinyFish can
    use the credential to repair the session. For bot challenges, also add
    `browser_profile: "stealth"` and `proxy_config: { enabled: true }`.
  </Accordion>

  <Accordion title="Vault icon not in playground toolbar" icon="lock">
    Connect a vault first in **Settings → Vault**.
  </Accordion>
</AccordionGroup>

***

## FAQ

<AccordionGroup>
  <Accordion title="Can TinyFish read all my passwords?" icon="eye">
    No. Values are only accessed at the moment of typing, and the AI agent never sees them.
  </Accordion>

  <Accordion title="Do credentials appear in run recordings?" icon="camera">
    No. Credentials are not captured in screenshots, streaming output, or logs.
  </Accordion>

  <Accordion title="What if I change a password?" icon="rotate">
    Click **Sync** in **Settings → Vault**. The next run uses the updated credential.
  </Accordion>

  <Accordion title="What happens if login fails?" icon="triangle-exclamation">
    TinyFish retries with available credentials for that domain. After multiple failures, the run continues without login.
  </Accordion>

  <Accordion title="What if I update my vault mid-run?" icon="clock">
    Runs use the credential state from when they started. Sync before starting a new run.
  </Accordion>
</AccordionGroup>

***

## Related

<CardGroup cols={2}>
  <Card title="Connect Your Vault" icon="vault" href="/vault-setup">
    Set up 1Password or Bitwarden
  </Card>

  <Card title="Runs" icon="play" href="/key-concepts/runs">
    Parameters, lifecycle, and result handling
  </Card>

  <Card title="Browser Context Profiles" icon="window" href="/key-concepts/browser-context-profiles">
    Reuse Browser Context Profile state across runs
  </Card>
</CardGroup>


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.