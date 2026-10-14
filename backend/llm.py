"""Gemini (Google Generative Language API) structured output. The AQ.* key was verified live on generativelanguage.googleapis.com.
Free tier = ~20 req/day/model, so we fall back across models when a daily quota is exhausted."""
import os, json, time, threading, httpx
SEM = threading.Semaphore(int(os.environ.get("LLM_CONCURRENCY", "3")))
MODELS = os.environ.get("GEMINI_MODELS", "gemini-2.5-flash,gemini-3-flash-preview,gemini-2.5-flash-lite").split(",")
MODEL = MODELS[0]
_dead = {}  # model -> until ts (daily quota exhausted)
def available(): return bool(os.environ.get("GEMINI_API_KEY"))
def structured(prompt, schema, temperature=0.2, timeout=60):
    global MODEL
    t = time.time(); last = None
    with SEM:
        for model in MODELS:
            if _dead.get(model, 0) > time.time(): continue
            gen = {"temperature": temperature, "responseMimeType": "application/json", "responseSchema": schema}
            if model.startswith("gemini-2.5"): gen["thinkingConfig"] = {"thinkingBudget": 0}
            body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}], "generationConfig": gen}
            for i in range(3):
                try:
                    r = httpx.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                                   headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]}, json=body, timeout=timeout)
                except httpx.TimeoutException:
                    last = "timeout"; continue
                if r.status_code == 429 and ("PerDay" in r.text or "free_tier_requests" in r.text):
                    _dead[model] = time.time() + 3600; last = f"{model} daily quota"; break
                if r.status_code in (429, 500, 503): last = f"{model} {r.status_code}"; time.sleep(2 * (i + 1)); continue
                if r.status_code >= 400: last = f"{model} HTTP {r.status_code}: {r.text[:120]}"; break
                txt = r.json()["candidates"][0]["content"]["parts"][-1]["text"]
                MODEL = model
                out = json.loads(txt); out["_model"] = model
                return out, int((time.time() - t) * 1000)
    raise RuntimeError(f"Gemini unavailable: {last}")
