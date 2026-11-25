# ADB Inspection — Setup and Command Reference

## Install
```bash
sudo apt-get install android-tools-adb    # also installs fastboot
adb version
```

## Enable USB debugging on the device
Settings → About tablet/phone → tap **Build Number** 7× → Developer Options appears → enable **USB Debugging**.
This toggle persists across reboots. Each new adb installation generates a new RSA key; the device must approve it once per machine.

## Connect and authorize
```bash
lsusb                   # confirm device appears (Rockchip = VID 2207:xxxx)
adb kill-server && adb start-server
adb devices             # expect: <serial>  unauthorized  (prompt on device screen)
# → tap "Allow USB debugging from this computer" on device, tick "Always allow"
adb devices             # expect: <serial>  device
```

## Common connection failures

| `adb devices` output | Cause | Fix |
|---|---|---|
| (empty, device in lsusb) | USB mode is "Charging only" | Swipe down → USB notification → File Transfer/MTP |
| `unauthorized` | New key not approved | Tap Allow on device screen |
| (empty, device NOT in lsusb) | Cable is charge-only | Swap to a data cable on a rear motherboard port (not a hub) |
| (empty after `fastboot reboot`) | Device still booting | Wait ~60 s; Rockchip cold boot is slow |

## Fastboot mode (booted holding a volume key)
```bash
lsusb -v -d <VID:PID> | grep iInterface   # shows "fastboot" if in bootloader
fastboot devices                           # confirm
fastboot reboot                            # safe — reboots into Android
```

## Full spec-pull block
```bash
echo "Android: $(adb shell getprop ro.build.version.release) SDK $(adb shell getprop ro.build.version.sdk)"
echo "Model: $(adb shell getprop ro.product.model)"
echo "Device: $(adb shell getprop ro.product.device)"
echo "SoC board: $(adb shell getprop ro.board.platform)"
echo "HW: $(adb shell getprop ro.hardware)"
echo "ABI: $(adb shell getprop ro.product.cpu.abi)"
adb shell cat /proc/meminfo | grep -iE "MemTotal|MemAvailable"
adb shell cat /proc/cpuinfo | grep -c processor
adb shell df -h /data | tail -2
adb shell pm list features | grep -iE "microphone|audio"
```

## Debloat (requires explicit per-package user approval)
```bash
adb shell pm list packages -3              # list user-installed + preloaded packages
adb shell pm uninstall -k --user 0 <pkg>  # remove for user 0, reversible (APK stays)
adb shell pm install-existing <pkg>        # restore if needed
```

## ADB over Wi-Fi (fallback when USB is flaky)
```bash
# While still connected via USB:
adb tcpip 5555
# Then disconnect cable and:
adb connect <device-ip>:5555
adb devices    # should show <device-ip>:5555  device
```
Requires that the device and PC are on the same LAN segment.

## SoC notes
- **Rockchip RK3562**: quad Cortex-A53, small NPU, arm64. Capable thin-client SoC.
- **Rockchip RK3566/3568**: similar A55 cores, also viable.
- Confirm real RAM from `MemTotal` in `/proc/meminfo`; the box figure often includes virtual/expanded RAM.
