> ## Documentation Index
> Fetch the complete documentation index at: https://docs.tinyfish.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Live Browser Preview

> Embed a real-time browser view in your app using the streaming URL

Every TinyFish automation provides a `streaming_url`, a live feed of the browser as it runs. Drop it in an iframe to show users what's happening in real time.

You'll see our little fish swimming through the web for you, navigating pages, clicking buttons, and extracting data while you watch.

<img src="https://mintcdn.com/tinyfish/SAWuKzAHuR-ZMRAB/images/live-preview/live-preview.png?fit=max&auto=format&n=SAWuKzAHuR-ZMRAB&q=85&s=1f25a1245fc4a3a2ade7d386672a699e" alt="TinyFish live browser preview showing the fish navigating a webpage" style={{ maxWidth: "500px", display: "block", margin: "0 auto" }} width="1760" height="1148" data-path="images/live-preview/live-preview.png" />

## Getting the Streaming URL

When you use the [SSE endpoint](/key-concepts/endpoints#streaming-run-sse), one of the events you'll receive is `STREAMING_URL`:

```json theme={null}
{
  "type": "STREAMING_URL",
  "run_id": "abc123",
  "streaming_url": "https://tf-abc123.fra0-tinyfish.unikraft.app/stream/0"
}
```

<Warning>
  The streaming URL may become unavailable after the run completes. To preserve run recordings, capture the stream content during execution.
</Warning>

## Embedding It

Once you have the URL, embed it in an iframe:

```html theme={null}
<iframe
  id="preview"
  src="YOUR_STREAMING_URL"
  width="100%"
  height="600"
  style="border: 1px solid #e5e7eb; border-radius: 8px;"
></iframe>
```

For a responsive container that maintains a 16:9 aspect ratio:

```html theme={null}
<div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden;">
  <iframe
    src="YOUR_STREAMING_URL"
    style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none; border-radius: 8px;"
  ></iframe>
</div>
```

## Full Example

Start an automation, listen for the `STREAMING_URL` event in the SSE stream, and set it as the iframe source to display the live browser.

<CodeGroup>
  ```typescript TypeScript theme={null}
  import { TinyFish, EventType } from "@tiny-fish/sdk";

  const client = new TinyFish();

  const stream = await client.agent.stream(
    {
      url: "https://example.com/products",
      goal: "Extract all product names and prices",
    },
    {
      onStreamingUrl: (event) => {
        // Set iframe src to show the live browser
        const iframe = document.getElementById("preview");
        if (iframe) {
          iframe.setAttribute("src", event.streaming_url);
        }
      },
    },
  );

  for await (const event of stream) {
    if (event.type === EventType.COMPLETE) {
      console.log("Result:", event.result);
    }
  }
  ```

  ```python Python theme={null}
  from tinyfish import TinyFish, StreamingUrlEvent

  client = TinyFish()

  with client.agent.stream(
      url="https://example.com/products",
      goal="Extract all product names and prices",
  ) as stream:
      for event in stream:
          if isinstance(event, StreamingUrlEvent):
              # Use this URL in an iframe to show the live browser
              print("Embed this:", event.streaming_url)
              break
  ```
</CodeGroup>

## Tips

* **Keep your API key server-side.** Call the SSE endpoint from your backend and pass the `streaming_url` to the frontend. The streaming URL itself is safe to expose to the browser.
* **Show a loading state.** The streaming URL arrives a few seconds after the automation starts, so show a spinner or placeholder until then.
* **The iframe is read-only.** Users can watch but can't interact with the browser session.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.