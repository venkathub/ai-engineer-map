# JarvisLabs GPU exercises

This directory contains jobs that learners submit deliberately; repository scripts never create paid infrastructure.

```bash
./run.sh hoe check --gpu jarvislabs --live
jl gpus
jl run gpu/jarvislabs/environment_check.py --gpu L4 --requirements requirements/hoe-gpu.txt
```

Select a currently available GPU appropriate to the lab. Confirm the result, then verify the created instance is paused and delete retained storage when it is no longer needed. See [`../../docs/BYO_LLM_AND_GPU.md`](../../docs/BYO_LLM_AND_GPU.md) for the full security, cost, and evidence contract.

To confirm only the presence of explicitly injected variables without revealing values, repeat `--require-env NAME`, for example `python3 gpu/jarvislabs/environment_check.py --require-env OPENAI_API_KEY` on the remote host. Avoid copying provider keys to a GPU unless that exercise actually needs them.

For a lab that depends on an attached shared filesystem, add `--require-shared-storage`. The ordinary check reports `/home/jl_fs` state but does not fail when no filesystem was attached.
