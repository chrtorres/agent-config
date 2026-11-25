# Hardware Option Evaluation — Voice Satellite Matrix

Use this when deciding which physical device should act as the "ears, mouth, and optionally screen" of a local voice assistant. The heavy backend (STT/LLM/TTS) runs on a separate homelab server in this architecture.

## Evaluation axes

| Axis | Key questions |
|---|---|
| Mic + speaker | Built-in? Quality? Needs amp/driver board? |
| Always-on app | Will the OS kill a background service? (Android aggressive battery management) |
| Privacy / no-egress | Can it be LAN-firewalled? Preinstalled telemetry? |
| Wake word | STT-based (any Linux/Android), openWakeWord (Linux), microWakeWord (ESP32-S3 only) |
| Effort | Plug-in vs. solder vs. buy hardware |
| Screen | Available for status/transcript display? |

## Option comparison (generalised — fill in your devices)

| Option | Mic | Speaker | Wake word | No-egress | Effort | Notes |
|---|---|---|---|---|---|---|
| Generic Android tablet (Android 12+, ≥3 GB RAM) | ✅ built-in | ✅ built-in | STT-based or openWakeWord via Termux | ✅ firewall to backend | Low — install app | Watch for bloatware phoning home; debloat first |
| Raspberry Pi Zero 2 W + mic HAT | Needs HAT | Needs amp + speaker | openWakeWord | ✅ | Medium — assemble | Fits Echo Dot shell with small amp (PAM8302) |
| ESP32-S3 voice board | ✅ onboard dual mic | External | microWakeWord on-device | ✅ | Low–Medium | Ultra low power; best for always-on; needs buy |
| Classic ESP32-WROOM | ❌ cannot run voice satellite | ❌ | Not supported | ✅ | — | Use for sensors, relays, BT proxy only |
| Echo Dot (stock) | ✅ | ✅ | Only via Amazon cloud | ❌ cannot block Amazon | — | Stock firmware unusable without Amazon |
| Old phone (Android) | ✅ | ✅ | Same as tablet | ✅ | Low | Same considerations as tablet |

## Decision rules

1. **Fastest to working sound** → Android tablet (thin client, install app)
2. **Best long-term enclosure** → Pi Zero 2 W inside existing shell + amp
3. **Lowest power, cleanest always-on** → ESP32-S3 (buy new; classic ESP32 cannot substitute)
4. **Never use** classic ESP32-WROOM for voice — wrong hardware for microWakeWord/ESPHome voice satellite

## ESP32 variant identification

Look at the silkscreen on the module itself:
- `ESP32-S3` printed → S3 (PSRAM, vector instructions, can do microWakeWord)
- `ESP-32` or `ESP32` only → classic LX6 (cannot do voice satellite)
- `ESP32-C3` → RISC-V, Wi-Fi only, not voice
- `ESP32-C6` → RISC-V + 802.15.4, not voice

Do not rely on the dev-board PCB label; read the metal-shielded module's own text.

## No-egress firewall template (nftables, generalised)

```
# <satellite-ip>  = the voice device
# <backend-ip>    = the homelab server running STT/LLM/TTS
# <backend-port>  = e.g. 11434 for Ollama, or Home Assistant port
table inet satellite {
  chain forward {
    type filter hook forward priority 0; policy drop;
    ip saddr <satellite-ip> ip daddr <backend-ip> tcp dport { <backend-port> } accept
    # optional: also allow DNS to local resolver
    # everything else from <satellite-ip> dropped
  }
}
```
