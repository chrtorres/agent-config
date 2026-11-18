# GPU kernel-module and firmware-loader verification

Read this reference when a repository installs a kernel module, initramfs hook, pre-driver loader, firmware payload, hardware unlock, or register-level GPU procedure.

- Establish the live device identity from read-only vendor and PCI tools. Record the reported product name, PCI vendor/device ID, architecture, VRAM, driver, kernel, OS, and relevant runtime versions. Do not rely on the user's product label when the host reports a different identity.
- Separate an allowlist entry from tested support. A PCI ID in a table only proves that the module can select the device; it does not prove that the firmware, register layout, microcode, boot path, or recovery path matches that GPU.
- Compare the implementation family at every layer: source comments and constants, firmware filenames and manifests, architecture-specific generated assets, documented test cards, and release notes. A generic family name such as Turing or Ampere is not enough evidence for a model-specific procedure.
- Inspect the module entry path and target-selection behavior. Determine whether an untested device is skipped, reported, or actively modified when the broad target option is used. Treat “not tested” entries that are actively selected as a compatibility hazard.
- Inspect install and removal scripts for DKMS registration, initramfs regeneration, boot-parameter changes, driver ordering, firmware placement, and recovery behavior. Do not run package installation, rebuild initramfs, add boot options, or load the module during verification unless the user explicitly authorizes those mutations.
- Build the module out of tree against the target kernel headers when practical. Treat a successful build as compiler/kernel-API compatibility only; it does not validate device behavior or firmware correctness.
- Do not infer runtime safety from static inspection. A meaningful hardware test requires a recoverable console/recovery path, an exact supported device and driver combination, preserved clocks/power settings, pre/post device health, error logs, and a workload-specific correctness and stability check.
- Prefer a documented supported test card or an isolated spare system before any test on a primary display GPU. A failed pre-driver path may blank the display, reset the card, retain DMA resources, or require power cycling.
- Keep unavailable vendor binaries, firmware, models, and closed runtime components outside the shared skill. Record their URLs, hashes, licenses, and regeneration/download recipe in task evidence; do not claim a source-only inspection proved the binary path.

## Minimum claim matrix

| Claim | Minimum evidence | Does not prove it |
|---|---|---|
| Device is selectable | Exact PCI ID matches an inspected allowlist | That the procedure is correct for the device |
| Module builds | Out-of-tree build succeeds for the target kernel | Hardware or firmware compatibility |
| Firmware is reproducible | Pinned inputs, publisher checksums, generated-output checks | Correctness on another GPU family |
| Unlock executes | Controlled runtime log with successful target-specific checks | Stability, performance, or application compatibility |
| Performance improves | Equivalent before/after workload, warm-up, samples, units, thermals and power | Safety or per-game benefit |
