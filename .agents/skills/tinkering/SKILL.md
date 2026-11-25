---
name: tinkering
description: Resume and advance a hardware/software homelab project — continuing from existing docs, diagnosing audio/peripheral issues, connecting and inspecting physical devices (Android via ADB, USB peripherals via lsusb/fastboot, 3D printers via Marlin serial), and evaluating hardware options against project requirements. Use when picking up an in-progress project, debugging why something isn't making sound, driving or troubleshooting a USB-connected 3D printer, or deciding which device to use for a build.
---

# Tinkering — Hardware + Software Investigation

Exploratory investigation on a homelab or personal build project: pick up where docs left off, diagnose hardware/software issues, inspect physical devices, and make evidence-based hardware decisions. Scope is **read-only diagnosis and evaluation** unless the user grants explicit authorization for each action that changes state (reboot, install, flash, write).

## Procedure

### 1. Reorient from project docs

Before acting, read the project's existing PLAN.md, DOCUMENTATION.md, SCOPE.md and HANDOFF.md if present. Identify:
- What phase the project is in and what's already done
- The open decisions that belong to the user vs. work that can proceed
- Known gaps and the TODOs explicitly listed

Summarize where things stand in one short paragraph and state what you're picking up, rather than re-deriving everything from scratch.

### 2. Audio output diagnosis

When a user reports no sound, work through layers in order — do not skip to complex fixes before the basics:

1. **Check physical outputs exist** — `pactl list short sinks`. Desktops have no built-in speaker; outputs are line-out, headphone jack, and HDMI only.
2. **Check the active port and its jack-sense** — `pactl list sinks | grep -E "Active Port|analog-output"`. A port marked `not available` means nothing is detected in that jack.
3. **Check ALSA mutes underneath PulseAudio** — `amixer -c <card_number> sget Master`, `Front`, `PCM`. PulseAudio showing 100% unmuted doesn't mean ALSA is.
4. **Check Realtek Auto-Mute** — `amixer -c <card_number> sget "Auto-Mute Mode"`. If `Enabled`, it can silence one port based on jack detection. Disable with `amixer -c <card_number> sset "Auto-Mute Mode" Disabled`.
5. **Find the right card number** — `aplay -l` maps card numbers to hardware names (e.g., ALCS1200A = onboard Realtek, often card 2, not card 0 or 1 which may be HDMI/digital).
6. **Distinguish line-out vs. headphone ports** — rear green jack is typically `analog-output-lineout`; front panel is `analog-output-headphones`. If the front panel shows `not available` permanently, the front-panel audio header may not be connected inside the case.
7. **Test with a generated clip** — synthesize a test WAV (e.g. via `python3 -c "import numpy as np, wave; ..."`) and `paplay --device=<sink> file.wav`. rc=0 means audio was sent; it does not confirm transducer output.
8. **Cable and device check** — if a powered speaker is silent despite rc=0: confirm it's in the green (line-out) jack, powered on with its own volume up, and connected by an analog 3.5 mm cable (not USB audio, which appears as a separate sink).
9. **USB audio devices** appear as additional sinks in `pactl list short sinks`. If a USB speaker is connected but not in the list, the cable may be charge-only or the device may need an `amixer` unmute.

### 3. Android device inspection via ADB

**Prerequisites:** `adb` installed (`sudo apt-get install android-tools-adb`), USB debugging enabled on the device (Settings → About → tap Build Number 7× → Developer Options → USB Debugging), device unlocked on the home screen, **data-capable USB cable** (charge-only cables are the most common failure).

**Connection checklist:**
- `lsusb` — confirm the device appears. Rockchip tablets enumerate as VID `2207:xxxx`; generic Android as `0bb4:xxxx`. If it appears as `iInterface: fastboot`, the tablet booted into the bootloader (held a key during power-on); use `fastboot reboot` to get it back into Android.
- `adb devices` — if `unauthorized`, the "Allow USB debugging?" prompt is on the device screen. Tap Allow (tick "Always allow"). If empty despite the device being in `lsusb`, the USB interface isn't presenting ADB (charging-only mode); pull down the notification shade on the device and switch to "File Transfer" or "MTP".
- After authorization, `adb devices` shows `<serial>  device`.

**Pull spec sheet:**
```bash
adb shell getprop ro.build.version.release      # Android version
adb shell getprop ro.build.version.sdk          # SDK level
adb shell getprop ro.product.model
adb shell getprop ro.board.platform             # SoC (e.g. rk3562)
adb shell getprop ro.product.cpu.abi            # arm64-v8a etc.
adb shell cat /proc/meminfo | grep -iE "MemTotal|MemAvailable"
adb shell cat /proc/cpuinfo | grep -c processor
adb shell df -h /data
adb shell pm list features | grep -iE "microphone|audio"
```

**Key interpretation notes:**
- "X GB RAM" on the box often includes virtual/expanded RAM. `MemTotal` from `/proc/meminfo` is the real silicon figure.
- Rockchip RK3562 (quad A53 + small NPU) is a capable satellite SoC; plain Rockchip RK3566/3568 are also viable. Budget Allwinner/MediaTek variants are typically weaker.
- Android 12+ has better security posture; Android 15 on a no-name tablet is a good sign.
- `feature:android.hardware.microphone` and `feature:android.hardware.audio.output` confirm mic and speaker are present.

**ADB debloat (do not run without explicit user approval per package):**
```bash
adb shell pm list packages -3   # list third-party / preinstalled packages
adb shell pm uninstall -k --user 0 <package.name>   # remove for user, reversible
```

### 4. Hardware option evaluation

When the user asks "would this work?" or "should I use X or Y?", evaluate each option against the project's stated requirements. For Rocky-style local voice assistant satellites the key axes are:

| Axis | Questions |
|---|---|
| **Ears + mouth** | Has mic? Has speaker? Can an app run always-on without OS killing it? |
| **Privacy / no-egress** | Can it be firewalled to LAN-only? Does preinstalled software phone home? |
| **Heavy lifting location** | Thin client (mic+speaker only, backend does STT/LLM/TTS) vs. on-device |
| **Effort to first sound** | No-solder path vs. hardware build |
| **Wake word** | Software (STT-based gate), openWakeWord (Linux/Pi), microWakeWord (ESP32-S3 only) |

**ESP32 notes:**
- Classic ESP32-WROOM (dual-core LX6): *cannot* run microWakeWord or ESPHome voice satellite. Those require an **ESP32-S3** (PSRAM + vector instructions). Do not conflate the two.
- Classic ESP32s are useful as sensor nodes (temperature, motion, door), relay/IR control, BT proxies, button+LED pucks — not voice front-ends.
- Confirm board variant from the silkscreen: "ESP32-S3" is printed explicitly on S3 variants.

**Tablet (generic Android) notes:**
- Viable as a thin-client satellite if Android 12+ and ≥3 GB real RAM.
- Weakness: preinstalled bloatware may phone home; treat the same as the voice device — firewall to backend-only.
- Advantage: mic + speaker + screen + battery in one unit, no soldering.
- Check whether the specific ROM allows a background service to stay alive (some aggressive battery ROMs kill it).

**Pi Zero 2 W:**
- Best balance for a custom-enclosure build (Echo Dot shell): full Linux, runs openWakeWord, fits a small amp and the existing speaker driver.
- Needs a small amp (PAM8302 or similar) to drive a passive speaker.

### 5. Booting and USB mode gotchas

| Symptom | Cause | Fix |
|---|---|---|
| `lsusb` shows tablet as `iInterface: fastboot` | Booted holding volume key | `fastboot reboot` |
| `adb devices` shows `unauthorized` | New adb key needs approval | Tap "Allow USB debugging" on device screen |
| `adb devices` empty despite `lsusb` seeing it | USB data mode is "charging only" | Pull down notification → switch to MTP/File Transfer |
| Tablet disappears from `lsusb` during session | Charge-only cable or flaky hub | Swap to a known-data cable on a rear motherboard port |
| `adb shell` returns empty on all getprops | Shell connected mid-reboot | Wait and retry individual commands |

### 6. 3D printer control via USB serial (Marlin / Creality-class)

Driving an FDM printer (Ender-3-class, 8-bit Marlin, no probe) over its USB serial port
to inspect, tune, list the SD card, and run a print. Heating and motion are
**state-changing** — authorize them, watch the first layer, never leave it hot and alone.

**Connect:** `ls -l /dev/ttyUSB* /dev/ttyACM*` (CH340 = `/dev/ttyUSB0`); user must be in
`dialout`. Baud 115200 (stock Creality). Only one program owns the port — a GUI host that
is *connected* blocks you; one merely *open* leaves the port free. Opening usually resets
the board (DTR) to a clean state; wait ~4 s.

**Safety invariants:**
- **Closing the port does NOT cool many 8-bit boards.** After any stop, send `M104 S0` +
  `M140 S0` and confirm with `M105`. Verify after a kill-signalled background streamer too.
- **Keep every move inside the bed, clear of bed clips** — a print reaching the edge can
  knock a glass bed off. Parse the sliced G-code's min/max X/Y and bound prime/print/end moves.
- Never leave it printing unattended.

**Inspect & tune (`scripts/printer_serial.py`):** `M115` (caps — `AUTOLEVEL:0` = manual
level, no mesh), `M503` (EEPROM), `M303 E0 S<t> C8 U1` then `M301`+`M500` (**tune FIRST,
then save**), `M21`/`M20` (mount+list SD — no command returns file contents; pull the card
to read it), `M290 Z0` (probe babystep support).

**Squish on a manual-level machine is physical** (bed knobs + Z-endstop), not a software
offset. Don't chase adhesion by babystepping far down — on a correct endstop that starves
flow, clogs the nozzle, and drags corners. "Straights stick, corners drag" is usually
first-layer **accel/jerk too high** (lower via `M204 P200`/`M205 X4 Y4`) + sharp corners
(add a brim), not glue.

**Fastest root-cause when a vendor sample prints but yours fails:** pull the SD card, read
the known-good sample's settings block (sliced-in `;` comments), and copy its first-layer
recipe — often lower temps + thick slow first layer + raft + **no Z offset**.

**Run:** prefer SD card (copy `.gcode`, `sync`, `cmp`, `udisksctl unmount`/`power-off`;
don't delete the user's old files) over USB streaming (`scripts/printer_stream.py`, live
`M290` babystep via a nudge file, aborts cold) which tethers the host for the whole job.
Full command tables, slicing, and the babystep workflow: [3d-printer-serial-reference.md](references/3d-printer-serial-reference.md).

## Reproduction resources

- [audio-diagnosis-reference.md](references/audio-diagnosis-reference.md) — extended ALSA/PulseAudio command cheat sheet
- [adb-inspection-reference.md](references/adb-inspection-reference.md) — ADB setup, common errors, full spec-pull command block
- [hardware-evaluation-matrix.md](references/hardware-evaluation-matrix.md) — axes and scoring table for satellite hardware options
- [3d-printer-serial-reference.md](references/3d-printer-serial-reference.md) — Marlin serial commands, safety invariants, manual leveling, slicing, SD workflow
- `scripts/printer_serial.py` — one-off G-code / inspection / PID-tune-then-save / SD list / cooldown
- `scripts/printer_stream.py` — stream a G-code file with live `M290` babystep injection; aborts cold
- `scripts/adhesion_patch.py` — generate a slow concentric single-layer squish-finder patch

## Validation and delivery

This skill produces **documentation + decisions**, not compiled artifacts. Validation is:
1. The audio test clip plays (`rc=0`) and the user confirms they hear it.
2. `adb devices` shows `<serial>  device` (not `unauthorized` or empty).
3. The spec sheet fields are populated from real `getprop`/`/proc` reads, not inferred from the box.
4. Hardware recommendation cites concrete evidence (actual MemTotal, confirmed mic/speaker features, confirmed SoC).
5. For a 3D printer: `M115`/`M503` return real firmware + EEPROM; after any heat/stop, `M105` shows targets at 0; the sliced G-code's parsed X/Y extents sit inside the clip-safe box before sending; the first printed layer is confirmed clean by the user.

Evidence (adb output, `lsusb` dumps, `amixer` state, printer serial logs, sliced G-code) stays in the project's local notes, not in this shared skill directory. The printer scripts import `pyserial` (`python3 -c "import serial"`) and talk to real hardware, so they are syntax/parameter-validated here; the end-to-end print is validated on the user's machine.

**Generalized value categories:** sink names, card numbers, device serial numbers, USB VID:PIDs, project names, hostnames, file paths, Android package names, Ollama model names, backend IP/port values, **serial port/baud, bed dimensions and center, nozzle/bed temperatures, Z offsets, and SD-card paths** are all placeholders or parameters in this skill — discover them at run time.
