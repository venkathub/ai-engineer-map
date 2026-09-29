# Bring your own LLM and GPU

Some hands-on exercises benefit from a hosted model or CUDA GPU. These integrations are optional: the static learning site and the default labs do not need credentials, paid APIs, or cloud infrastructure.

## Security boundary

The browser application never reads API keys. Put secrets in process environment variables or a local `.env` copied from `.env.example`; `.env` is ignored by Git. The terminal-only checker loads that file without overwriting variables already exported by the shell and reports variable names, never values.

Do not paste a key into curriculum JSON, browser storage, a URL, a notebook output, a screenshot, or a support issue. Use a restricted project key when the provider supports one, set a spend limit, and rotate a key that may have leaked.

## Configure an LLM

```bash
cp .env.example .env
# Add exactly the provider and model you intend to use.
./run.sh hoe check --provider openai
```

Supported configuration profiles are `openai`, `anthropic`, `gemini`, `openrouter`, and `compatible`. The compatible profile accepts an OpenAI-compatible endpoint such as a local vLLM or Ollama server through `LLM_BASE_URL`, `LLM_MODEL`, and optional `LLM_API_KEY`.

The checker performs configuration validation only. Provider SDKs are optional and belong in an isolated lab environment, not the core web application:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements/hoe-api.txt
```

A lab that makes a billable request must display its provider, model, request size, output path, and an explicit run command before execution. It must also record token usage when the provider returns it. Official SDKs read their respective environment variables; no key should be passed as a command-line argument.

## Choose a compute mode

Use the least expensive mode that proves the outcome:

1. `none` for conceptual, data, orchestration, evaluation-design, and mocked-provider exercises.
2. `local` when a workstation already has a suitable CUDA GPU.
3. `jarvislabs` for an explicit remote GPU run.

Check the intended setup without creating anything:

```bash
./run.sh hoe check --provider compatible --gpu local
./run.sh hoe check --provider openai --gpu jarvislabs
./run.sh hoe check --provider openai --gpu jarvislabs --live
```

## JarvisLabs quick path

Install and authenticate the official CLI on your own machine, inspect current availability, and then submit the small smoke test:

```bash
uv tool install jarvislabs
jl setup
jl gpus
jl run gpu/jarvislabs/smoke_test.py --gpu L4 --requirements requirements/hoe-gpu.txt
```

For unattended automation, JarvisLabs supports `JL_API_KEY`; keep it in the secret store of the automation system or the ignored `.env`, never in a command committed to Git. GPU names and availability change, so use `jl gpus` immediately before a run rather than treating an example GPU as guaranteed.

The official managed-run workflow pauses the instance it creates when the job completes. Paused storage and shared storage can still incur cost. Inspect the JarvisLabs dashboard after every exercise and remove resources you no longer need. The documented shared filesystem is mounted at `/home/jl_fs`; use it only for artifacts that must survive instance replacement and never store plaintext API keys there.

Set `JARVISLABS_REGION` and `JARVISLABS_WORKLOAD` as well as `JARVISLABS_GPU`: the same GPU can have different container and VM availability in each region. The `--live` audit authenticates, checks whether the account is funded, matches the exact target against current inventory and reports instance counts. It intentionally omits the balance amount, identity, tokens, IPs, URLs, and SSH commands.

The environment check validates CUDA visibility, driver/runtime metadata, GPU memory, a small matrix multiplication, writable working storage, shared-storage presence, and optional environment-variable names without printing their values. It does not download a model or dataset, create a service, or expose a network port. For serving exercises, follow the official JarvisLabs vLLM or Ollama tutorial and restrict public access; both can present an OpenAI-compatible API to the `compatible` profile.

## Topic execution catalog

`curriculum/hoe.json` assigns every concept to a versioned execution profile. Inspect the resolved contract before starting:

```bash
./run.sh hoe inspect model-apis
./run.sh hoe inspect peft
```

The CLI refuses API/GPU command execution unless `--allow-billable` is supplied. That flag is acknowledgement only: it never provisions a service, buys credits, or creates a GPU instance. A `setup-ready` result means prerequisites and safety guidance exist; it does not mean the topic experiment has been automated.

## Reproducibility record

For a remote exercise, save these non-secret facts in the lab evidence:

- curriculum concept and exercise ID;
- Git commit SHA;
- provider and model or GPU type;
- Python and relevant package versions;
- input dataset/version and random seed;
- command, acceptance result, duration, and approximate cost;
- artifact location and confirmation that the instance was paused or removed.

## Primary references

- [OpenAI SDKs and environment configuration](https://developers.openai.com/api/docs/libraries)
- [Anthropic Python SDK](https://platform.claude.com/docs/en/cli-sdks-libraries/sdks/python)
- [Gemini API quickstart](https://ai.google.dev/gemini-api/docs/get-started)
- [OpenRouter Python SDK](https://openrouter.ai/docs/client-sdks/python/overview)
- [JarvisLabs quickstart](https://docs.jarvislabs.ai/)
- [JarvisLabs Python SDK and CLI setup](https://docs.jarvislabs.ai/sdk)
- [JarvisLabs shared storage](https://docs.jarvislabs.ai/filestorage)
- [Serving LLMs with Ollama and vLLM](https://docs.jarvislabs.ai/tutorials/getting-started/serving-llms)
- [JarvisLabs CLI product guide](https://jarvislabs.ai/products/cli)
