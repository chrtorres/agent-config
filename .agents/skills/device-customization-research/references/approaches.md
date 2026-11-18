# Feasibility branches

For each route record: exact target/build scope, prerequisites, observed or published procedure, blockers, required access, recovery limits and confidence. Rank methods for the user's full objective separately from partial compromises.

| Branch | Questions that change the decision |
| --- | --- |
| Stock Android app | Is installation authorized and possible? Actual API/ABI? Compatible rendering/input/audio APIs and dependencies? Can the app record while vendor services run? |
| ADB/sideloading | Is adbd running, reachable and authenticated? Gadget configuration vs service triggers? Installer policy and actual error? Avoid borrowing Fire TV/other-model advice. |
| Root | What initial execution channel exists? Is the exact vulnerability/patch state known? UID0, SELinux, verified boot and persistent privileges are separate. |
| Bootloader/unlock | Production vs diagnostic fork? Owner-controllable key/token? Vendor signature check vs ordinary state flag? Data loss, security changes and restore prerequisites? |
| Modified Android/userspace | Actual device tree/image exists? Vendor kernel/HAL/framework ABI compatible? Verification/update layout? No assumed Treble/GSI support. |
| Independent Linux/other OS | Can it execute at all? ACPI/GPIO/panel/input/audio/DSP/Wi-Fi firmware and userspace support? Vendor modules cannot simply move to another kernel. |
| Hardware I/O | Configuration, shipped module and fitted silicon are different facts. Verify display modes, touch mapping, mic/speaker routes, privacy latch and networking externally. |
| Startup/HOME | One-time launch vs cold-start persistence? Default UI reclamation/background policy? Keep an uninstall/default-restoration channel before takeover. |
| Self-hosted backend | Actual client route, server address/trust/auth, STT/LLM/TTS locations, media contract, cancellation, bounds and errors? localhost on device is not server. |
| Browser/vendor interface | Local page/microphone/TLS support vs cloud skills/session restrictions? What full-objective requirements fail? Do not silently relax standalone/privacy goals. |
| Physical acquisition/repair | Validated board/voltage/pinout and skilled recovery? Readable storage is not trusted custom execution. A public OTA does not replace unique data backups. |

Use this matrix to close research, not to expand every task into every conceivable attack. An architecture can be preferred conditionally even when no implementation path is currently established. Do not turn old kernel versions, a generic CVE, certificate presence or an unsupported command into a working root/unlock claim. Investigating a destructive procedure is not permission to execute it.
