#!/usr/bin/python3
"""Stream a G-code file to a Marlin printer over USB, accepting LIVE Z babysteps
mid-print from a small command file so first-layer squish can be dialed WITHOUT
pausing. Run it in the background and feed nudges from another shell.

Babystep protocol -- write one signed float (mm) into the babystep file:
    echo "-0.04" > babystep.txt     # nozzle DOWN 0.04 -> more squish
    echo "+0.04" > babystep.txt     # nozzle UP   0.04 -> less squish
The streamer applies `M290 Z<delta>` before the next line and truncates the file.
(M290 requires BABYSTEPPING in firmware -- probe once with `M290 Z0` -> ok.)

SIGINT / kill -> abort: hotend + bed OFF, fan off, lift, motors off. Always force
heaters off on stop; closing the port alone does not cool many 8-bit boards.

Usage:
  printer_stream.py --file part.gcode                     # babystep.txt in CWD
  printer_stream.py --file part.gcode --babystep-file /tmp/bs.txt --port /dev/ttyUSB0
"""
import os, time, argparse, serial  # pyserial


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--port", default="/dev/ttyUSB0")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--reset-wait", type=float, default=4.0)
    ap.add_argument("--babystep-file", default="babystep.txt")
    ap.add_argument("--long-timeout", type=float, default=420.0)  # M109/M190 heat waits
    args = ap.parse_args()

    cmds, layer_marks = [], 0
    with open(args.file) as f:
        for raw in f:
            if raw.startswith((";LAYER_CHANGE", ";LAYER:")):
                layer_marks += 1
            line = raw.split(";", 1)[0].strip()
            if line:
                cmds.append(line)
    total = len(cmds)
    print(f"[stream] {args.file}: {total} commands, ~{layer_marks} layers", flush=True)

    open(args.babystep_file, "w").close()
    ser = serial.Serial(args.port, args.baud, timeout=2)
    time.sleep(args.reset_wait)
    ser.reset_input_buffer()
    cum = 0.0

    def send(cmd, timeout):
        ser.write((cmd + "\n").encode())
        t0 = time.time()
        while time.time() - t0 < timeout:
            ln = ser.readline().decode(errors="replace").strip()
            if not ln:
                continue
            if ln.lower().startswith("ok"):
                return True
            if any(w in ln.lower() for w in ("error", "kill", "resend")):
                print(f"    [printer: {ln}]", flush=True)
        print(f"    [timeout {timeout}s on: {cmd}]", flush=True)
        return False

    def poll_babystep():
        nonlocal cum
        try:
            if os.path.getsize(args.babystep_file) == 0:
                return
            txt = open(args.babystep_file).read().strip()
            open(args.babystep_file, "w").close()
            if not txt:
                return
            delta = max(-0.5, min(0.5, float(txt)))   # clamp per-nudge
            send(f"M290 Z{delta:+.3f}", 10)
            cum += delta
            print(f"    *** BABYSTEP {delta:+.3f}  (cumulative {cum:+.3f} mm) ***", flush=True)
        except Exception as e:
            print(f"    [babystep parse err: {e}]", flush=True)

    try:
        t0 = time.time()
        while time.time() - t0 < 2:
            ser.readline()
        send("M290 Z0", 10)
        start = time.time()
        for i, cmd in enumerate(cmds, 1):
            if i % 5 == 0:
                poll_babystep()
            head = cmd[:4]
            to = args.long_timeout if head in ("M109", "M190") else 60
            if head in ("M109", "M190", "G28", "M104", "M140"):
                print(f">>> {cmd}", flush=True)
            send(cmd, to)
            if i % 200 == 0 or head in ("M109", "M190"):
                el = int(time.time() - start)
                print(f"[progress] {i}/{total} ({100*i//total}%)  {el//60}m{el%60:02d}s  Zoff {cum:+.3f}", flush=True)
        print(f"[stream DONE] {total} commands", flush=True)
    except KeyboardInterrupt:
        print("\n[ABORT -> cooling]", flush=True)
        for c in ("M104 S0", "M140 S0", "M107", "G91", "G1 Z10 F600", "G90", "M84"):
            try:
                send(c, 8)
            except Exception:
                pass
    finally:
        ser.close()


if __name__ == "__main__":
    main()
