# Gemini repository instructions

The shared instructions in [`AGENTS.md`](AGENTS.md) are authoritative. Read them before modifying this project.

Keep the project dependency-free, treat `curriculum/concepts.json` as the curriculum source of truth, verify time-sensitive claims with primary sources, and run `./run.sh check` before completion. Follow `.ai/BRANCHING.md` and the five phase gates in `.ai/PHASES.md`. UI work must be verified through the locally served application. Optional model/GPU work follows `docs/BYO_LLM_AND_GPU.md` and must not expose secrets or create paid resources implicitly.
