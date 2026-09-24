# Integrating NVIDIA NIM / Nemotron

CareerPath AI already ships an `nvidia` provider that speaks the same
OpenAI-compatible `chat/completions` API that NVIDIA NIM exposes, so switching
is configuration-only. You can use either the **hosted NIM** on
`build.nvidia.com` (free API key) or a **self-hosted NIM container** on your
own GPU box.

> The code base already handles this without any code changes. The one thing
> the app needs is your NVIDIA **API key** (`nvapi-...`) and the exact
> **model id** for the Nemotron model you want.

## 1. Hosted NIM (easiest)

1. Go to <https://build.nvidia.com> and sign in (or create a free account).
2. Open the model card for the Nemotron release you want (e.g.
   `nvidia/llama-3.3-nemotron-super-49b-v1`, or the latest **Nemotron 3**
   model listed there).
3. Click **Get API Key** and copy the `nvapi-...` key.
4. Note the exact **model id** shown on the card - you must use it verbatim in
   `AI_MODEL`.

Update `.env`:

```
# --- Provider -------------------------------------------------
AI_PROVIDER=nvidia
AI_API_KEY=nvapi-<your-nim-key>
AI_MODEL=nvidia/<exact-model-id-from-build.nvidia.com>

# Optional: hosted NIM is the default, so this line is not needed.
# NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1/chat/completions
```

Restart `runserver` and generate a roadmap. All AI pipeline calls (roadmap
generation, resource suggestions, optional video suggestions) now go through
your Nemotron model.

## 2. Self-hosted NIM container

If you have an NVIDIA GPU and the NGC access, run the Nemotron NIM locally and
point the app at it:

```
docker run -d --gpus all -p 8000:8000 --ipc=host \
  -e NVIDIA_NIM_API_KEY=nvapi-<key> \
  -v /var/nim-cache:/opt/nim/.cache \
  nvcr.io/nim/<namespace>/<nemotron-model>:latest
```

Then in `.env`:

```
AI_PROVIDER=nvidia
AI_API_KEY=nvapi-<your-nim-key>
AI_MODEL=nvidia/<exact-model-id>
NVIDIA_BASE_URL=http://localhost:8000/v1
```

> The provider appends `/chat/completions` to `NVIDIA_BASE_URL`. Set it to the
> base of your NIM server (e.g. `http://localhost:8000/v1`), not the full
> endpoint URL.

## 3. What the app does differently

| Config | Effect |
| --- | --- |
| `AI_PROVIDER=nvidia` | Uses `NvidiaProvider` (`ai_engine/services/providers/nvidia.py`) |
| `AI_API_KEY` | Sent as `Authorization: Bearer nvapi-...` |
| `AI_MODEL` | Overrides the default `deepseek-ai/deepseek-r1` |
| `NVIDIA_BASE_URL` | Endpoint; defaults to the hosted NIM URL |

The provider is instantiated by the registry
(`ai_engine/services/provider_registry.py`), which passes `base_url` only when
`AI_PROVIDER=nvidia`, so the other providers are unaffected.

## 4. Verifying it works

Quick check from the project folder:

```
venv\Scripts\python.exe -c "from ai_engine.services.provider_registry import get_provider; p=get_provider(); print(type(p).__name__, p.model); print(p.generate('Reply with just: OK')[:200])"
```

Expected output: `NvidiaProvider nvidia/<your-model>` followed by a short reply
from Nemotron.

## 5. Falls back gracefully

If the key is invalid, the model id is wrong, the endpoint is unreachable, or
NIM is rate-limited, the app retries (default 2, `AI_MAX_RETRIES`) and then
simply uses the curated fallback - roadmap generation never hangs or errors.