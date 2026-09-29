# JarvisLabs L4 environment audit — 2026-09-29

## Scope

A single explicitly authorized, billable container instance was created for the environment audit and permanently destroyed immediately afterward. No provider credential was transferred to the instance, and no model API request was made.

## Target and cost evidence

- GPU: NVIDIA L4
- Region and workload: IN2 container
- Configured instance storage: 100 GB
- Observed on-demand rate at audit time: ₹41.31/hour
- Measured lifecycle duration: approximately 17 seconds
- Observed balance difference: ₹0.71

Prices and availability are point-in-time evidence, not durable defaults. Run `./run.sh hoe check --gpu jarvislabs --live` immediately before future work.

## Runtime evidence

- Python 3.10.20
- PyTorch 2.11.0 with CUDA 13.0 runtime
- NVIDIA driver 595.58.03
- One NVIDIA L4, compute capability 8.9
- Reported device memory: 22.04 GiB
- CUDA matrix identity test: passed, checksum 120.0
- Working directory: writable
- Available working disk reported by the container: 646.98 GiB
- Environment-name propagation using a non-secret audit variable: passed

The advertised 24 GB GPU capacity uses decimal units; the runtime reports memory in binary GiB, so 22.04 GiB is consistent rather than a capacity mismatch.

## Storage finding

`/home/jl_fs` was absent because no shared filesystem was created or attached. The environment checker therefore treats shared storage as optional by default and provides `--require-shared-storage` for exercises that depend on it.

## Cleanup evidence

- Remote command exit code: 0
- Instance destroy operation: successful
- Matching audit instances remaining: 0
- Running instances after cleanup: 0
- Paused instances after cleanup: 0
- Persistent filesystems after cleanup: 0

The instance identifier, account identity, exact remaining balance, API tokens, URLs, IP addresses, and SSH command are intentionally excluded.
