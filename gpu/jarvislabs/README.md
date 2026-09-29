# JarvisLabs GPU exercises

This directory contains jobs that learners submit deliberately; repository scripts never create paid infrastructure.

```bash
./run.sh hoe check --gpu jarvislabs
jl gpus
jl run gpu/jarvislabs/smoke_test.py --gpu L4 --requirements requirements/hoe-gpu.txt
```

Select a currently available GPU appropriate to the lab. Confirm the result, then verify the created instance is paused and delete retained storage when it is no longer needed. See [`../../docs/BYO_LLM_AND_GPU.md`](../../docs/BYO_LLM_AND_GPU.md) for the full security, cost, and evidence contract.
