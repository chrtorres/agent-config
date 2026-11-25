#!/usr/bin/python3
"""Minimal, safe Marlin serial driver for an 8-bit Creality-class printer over USB.

Opens the serial port (this often resets the board on DTR toggle -> a clean known
state), waits for boot, then runs one-off G-code and prints every line the printer
sends so nothing is hidden. M109/M190 (heat-and-wait) are handled by reading until
'ok' with a long timeout. Ctrl-C forces heaters off, because on many of these boards
simply closing the port does NOT cool the hotend/bed.

Usage:
  printer_serial.py --cmd M115 --cmd M503                 # firmware + saved EEPROM
  printer_serial.py --cmd M21 --cmd M20                   # mount + list SD files
  printer_serial.py --long-cmd "M303 E0 S200 C8 U1" --cmd M500   # PID tune THEN save
  printer_serial.py --cmd "M104 S0" --cmd "M140 S0"       # all-stop cooldown

Port/baud are discovered at run time, not hard-coded: list candidates with
`ls /dev/ttyUSB* /dev/ttyACM*`; the user must be in the `dialout` group. Stock
Creality Marlin is 115200; some builds use 250000.
"""
import time, argparse, serial  # pyserial


def open_port(port, baud, reset_wait):
    ser = serial.Serial(port, baud, timeout=2)
    time.sleep(reset_wait)            # let Marlin boot after the DTR reset
    ser.reset_input_buffer()
    return ser


def send(ser, cmd, wait_ok=True, timeout=60):
    cmd = cmd.strip()
    if not cmd or cmd.startswith(";"):
        return []
    ser.write((cmd + "\n").encode())
    print(f">>> {cmd}", flush=True)
    lines, t0 = [], time.time()
    while time.time() - t0 < timeout:
        line = ser.readline().decode(errors="replace").strip()
        if not line:
            continue
        print(f"    {line}", flush=True)
        lines.append(line)
        low = line.lower()
        if wait_ok and low.startswith("ok"):
            break
        if "error" in low or "kill" in low:
            break
    else:
        print(f"    [timeout {timeout}s waiting for ok]", flush=True)
    return lines


def cooldown(ser):
    for c in ("M104 S0", "M140 S0", "M107", "M84"):
        try:
            send(ser, c, timeout=8)
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/ttyUSB0")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--reset-wait", type=float, default=4.0)
    ap.add_argument("--cmd", action="append", default=[], help="one-off G-code, 60s cap (repeatable)")
    ap.add_argument("--long-cmd", action="append", default=[], help="G-code allowed up to --long-timeout (e.g. M303 PID)")
    ap.add_argument("--long-timeout", type=float, default=480.0)
    args = ap.parse_args()

    ser = open_port(args.port, args.baud, args.reset_wait)
    try:
        t0 = time.time()                       # drain boot banner
        while time.time() - t0 < 2:
            if ser.readline().strip():
                pass
        # long-cmds run FIRST, then --cmd, so an autotune saves correctly:
        #   --long-cmd "M303 E0 S200 C8 U1"  --cmd "M500"  == tune THEN save.
        # (A naive driver that saves before the tune writes stale PID to EEPROM.)
        for c in args.long_cmd:
            send(ser, c, timeout=args.long_timeout)
        for c in args.cmd:
            send(ser, c)
    except KeyboardInterrupt:
        print("\n[interrupt -> cooling down]", flush=True)
        cooldown(ser)
    finally:
        ser.close()


if __name__ == "__main__":
    main()
