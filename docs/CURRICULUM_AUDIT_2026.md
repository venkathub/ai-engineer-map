# AI engineering curriculum audit — 2026-09-29

## Scope and claim

This audit tests whether the map covers the durable responsibilities of an AI engineer as of the review date. It does not claim to enumerate every research paper, model release, library, industry vertical, or jurisdiction. Coverage means a learner can move from software and ML foundations through data, model application, retrieval, agents, multimodal systems, evaluation, security, governance, customization, inference, and production operations.

## Research method

The audit used primary specifications, standards bodies, official project documentation, original papers, and maintained educational catalogs. Version-sensitive areas were checked separately from durable concepts. Vendor features were included only when they represented a transferable engineering pattern, such as grounded search, asynchronous tools, reasoning budgets, structured output, or realtime session recovery.

The review compared the existing map against:

- current model interfaces, reasoning, tools, long context, multimodal, and realtime patterns;
- the 2026 MCP core and Tasks extension plus A2A interoperability;
- current agent skills, plugins, hooks, durable execution, and multi-agent patterns;
- end-to-end RAG and agentic evaluation and performance benchmarking;
- current LLM and agentic application security guidance;
- provenance, transparency, risk-management, and compliance operations;
- classic ML domains, data lifecycle, MLOps, open-model customization, and inference engineering.

## Result

The pre-audit map had strong LLM-application coverage but lacked sufficient depth in Data/MLOps, applied ML domains, reasoning-era inference, reusable agent context, asynchronous MCP work, agentic security, provenance, compliance operations, system-level TEVV, standardized end-to-end benchmarks, and edge inference.

The corrected map contains **104 concepts across 12 tracks**:

| Track | Coverage |
|---|---|
| Engineering foundations | Python, contracts, async systems, SQL, testing, jobs, containers, networking |
| ML and transformer foundations | math, validation, neural networks, tokenization, transformers, alignment, embeddings, decoding |
| Models and inference APIs | streaming APIs, structured output, open models, routing, long context, batch work, reasoning models, grounded tools |
| Prompt and context engineering | instruction hierarchy, examples, assembly, memory, caching, trust boundaries |
| Retrieval and RAG | ingestion, chunking, vector and lexical retrieval, rewriting, reranking, citations, structured retrieval, quality and permissions |
| Agents and interoperability | tools, workflows, planning, durable state, approvals, MCP, A2A, multi-agent, computer use, skills/hooks, MCP Tasks |
| Multimodal and realtime | vision-language, speech, realtime voice, image and video generation, multimodal retrieval |
| Evaluation and observability | datasets, evaluators, human review, RAG and agent evals, tracing, online feedback, TEVV, performance benchmarks |
| Safety, security and governance | threat modeling, injection, output safety, privilege, privacy, supply chain, red teaming, incidents, agentic security, provenance, regulation |
| Data and MLOps | collection, labeling, data quality, feature stores, experiment tracking, pipelines, registry, drift, synthetic data |
| Applied ML domains | NLP, vision, audio, time series, recommenders, graph ML, reinforcement learning, diffusion, robotics |
| Customization and production | SFT, PEFT, preference optimization, quantization, serving, distributed inference, cost/SLOs, deployment, UX, speculative decoding, edge, capstone |

## Hands-on exercise framework

Every topic has one unique exercise. The application derives a topic-specific lab artifact and acceptance checklist from the exercise, track, and outcomes.

### Inspect

The learner observes or benchmarks a mechanism, captures inputs and versions, records measurements, and explains the result. Examples include tokenizer comparison, retrieval benchmarks, model-card audits, and decoding experiments.

### Modify

The learner changes a baseline, predicts the outcome, runs the comparison, and explains the difference. Examples include adding approval gates, securing an output sink, reducing privileges, or rewriting an instruction contract.

### Build

The learner creates an implementation, evaluation, design, policy, or operational artifact. A valid artifact includes provenance, both learning outcomes, one explicit failure case, and one production trade-off.

The browser lab provides a starter artifact and review checklist. Its animated validation is a learning aid, not proof that arbitrary code executed. Completion requires attaching real output, measurements, traces, tests, screenshots, or reviewed documents appropriate to the topic.

## Automated guarantees

`./run.sh check` rejects a curriculum that has fewer than 12 tracks or 100 concepts, omits a modern core topic, has dangling or cyclic prerequisites, has non-contiguous track ordering, lacks primary references, duplicates an exercise, omits the three exercise modes, or uses an exercise without an observable action verb.

## Primary sources reviewed

- [Hugging Face Learn catalog](https://huggingface.co/learn) — LLMs, agents, context engineering, computer vision, audio, diffusion, deep RL, robotics, and 3D ML.
- [OpenAI API documentation](https://platform.openai.com/docs/) — model APIs, structured output, tools, realtime, evaluation, and production patterns.
- [Anthropic documentation](https://docs.anthropic.com/) — prompting, long context, caching, tool and agent patterns.
- [Gemini built-in tools](https://ai.google.dev/gemini-api/docs/tools) and [long-context guide](https://ai.google.dev/gemini-api/docs/long-context) — grounding, code execution, URL/file tools, multimodal long context, and caching.
- [MCP 2026-07-28 specification](https://modelcontextprotocol.io/specification/2026-07-28) and [Tasks extension](https://tasks.extensions.modelcontextprotocol.io/specification/draft/tasks) — interoperable context/tools and durable asynchronous requests.
- [A2A v0.3 specification](https://a2a-protocol.org/v0.3.0/specification/) — independent agent discovery and task exchange.
- [OpenTelemetry GenAI semantic conventions](https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/) — model, retrieval, tool, token, latency, and conversation telemetry.
- [MLPerf Inference](https://mlcommons.org/benchmarks/inference-datacenter/) — reproducible model, end-to-end RAG, agentic, edge, latency, throughput, energy, and accuracy benchmarking.
- [OWASP LLM Top 10 2026](https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/) and [Agentic Top 10 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) — application and agent-specific risks and controls.
- [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework), [Generative AI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf), and [TEVV-Athlon draft](https://www.nist.gov/artificial-intelligence/ai-research/tevv-athlon-framework-evaluating-ai-systems) — risk management and system assessment.
- [C2PA Content Credentials 2.3](https://spec.c2pa.org/specifications/specifications/2.3/index.html) — synthetic-media provenance and authenticity metadata.
- [European Commission AI Act implementation](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai) — current transparency, GPAI, governance, and phased enforcement requirements.
- [Kubeflow Pipelines](https://www.kubeflow.org/docs/components/pipelines/) and [Kubeflow Hub](https://www.kubeflow.org/docs/components/hub/overview/) — repeatable ML workflows, artifacts, model lifecycle, and lineage.
- [Transformers PEFT](https://huggingface.co/docs/transformers/peft), [quantization](https://huggingface.co/docs/transformers/main/quantization/overview), and [vLLM](https://docs.vllm.ai/) — efficient adaptation and inference.

## Maintenance rule

Perform a focused review at least every six months, or sooner when a relevant protocol, security list, regulation, model interface, or benchmark changes materially. Advance the global review date only after every version-sensitive claim affected by the change has been verified.
