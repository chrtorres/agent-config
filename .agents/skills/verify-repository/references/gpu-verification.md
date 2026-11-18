# GPU and rendering verification

Read this reference when repository claims concern GPU compute or rendering.

- Distinguish super resolution, frame interpolation, multi-frame generation, ray reconstruction, and neural lighting/material enhancement. API compatibility or a shared DLL name does not establish implementation of another vendor's algorithm.
- Discover GPU model, memory, driver, OS, architecture, graphics API support, and relevant runtime availability. Use read-only vendor tools where available, such as `nvidia-smi` for NVIDIA hardware.
- Separate public recording/viewer tools from a closed rendering core. Their tests cannot establish the core model's behavior.
- Prefer relevant standalone kits where available. Inspect launch scripts before execution; preserve individual case logs and verify aggregate results exist.
- On Linux, inspect a loader failure with `readelf --version-info` and `getconf GNU_LIBC_VERSION`. Compare actual dependencies with documented minimums. A missing host library blocks GPU execution; it does not prove the GPU unsupported.
- Preserve driver, system library, game file, launch setting, clock, and power configuration when only verification is authorized.
- Separate reference-frame parity from independent image quality, and GPU kernel timing from game FPS, frame pacing, and input latency. Record resolution, multiplier, execution path, warm-up, units, and memory when relevant.
- Compare equivalent inputs and settings. Publisher measurements on a different GPU do not establish performance on the user's GPU; a baseline requiring newer hardware may be unavailable locally.
- A synthetic benchmark pass does not prove per-game compatibility or justify system-wide adoption.
