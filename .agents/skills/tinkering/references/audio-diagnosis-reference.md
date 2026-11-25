# Audio Diagnosis — Command Reference

## List sinks and default
```bash
pactl list short sinks                          # all outputs + current state
pactl get-default-sink                          # which sink is the default
```

## Sink detail (mute, volume, active port, jack sense)
```bash
pactl list sinks | awk '/Name: <sink-name>/{f=1} f{print} /^$/{if(f)exit}'
```
Key fields: `Mute`, `Volume`, `Active Port`, and per-port `available`/`not available`.

## Switch active port
```bash
pactl set-sink-port <sink-name> analog-output-headphones
pactl set-sink-port <sink-name> analog-output-lineout
```

## Find the ALSA card number for a sink
```bash
aplay -l    # maps card N to hardware name
# e.g. "card 2: Generic [HD-Audio Generic], device 0: ALCS1200A Analog"
```

## ALSA mixer — check controls and states
```bash
amixer -c <N> scontrols                        # list all controls on card N
amixer -c <N> sget Master                      # check Master volume + mute
amixer -c <N> sget Front
amixer -c <N> sget PCM
amixer -c <N> sget Headphone
amixer -c <N> sget "Auto-Mute Mode"            # Realtek: Enabled silences one port
```

## ALSA mixer — fix mutes
```bash
amixer -c <N> sset Master 100% unmute
amixer -c <N> sset Front 100% unmute
amixer -c <N> sset Headphone 100% unmute
amixer -c <N> sset "Auto-Mute Mode" Disabled   # prevent jack-detection muting
```

## Generate and play a test clip
```bash
# Generate a 3s two-tone beep (requires numpy, available in most venvs or system python3)
python3 -c "
import numpy as np, wave
sr=48000; t=np.linspace(0,3,sr*3,False)
x=0.5*np.sin(2*np.pi*440*t)+0.3*np.sin(2*np.pi*880*t)
pcm=(x*32767).astype('<i2')
with wave.open('/tmp/test_tone.wav','wb') as w:
  w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm.tobytes())
"
paplay --device=<sink-name> /tmp/test_tone.wav; echo "rc=$?"
```
rc=0 means the audio system accepted the data. It does not confirm transducer output.

## Check for USB audio devices (appear as extra sinks)
```bash
pactl list short sinks      # a USB speaker shows as a separate entry
pactl list short cards      # USB audio cards appear here too
```

## Common hardware facts (desktop towers)
- No built-in speaker. All output goes to: rear analog jacks, front panel jacks, or HDMI.
- Rear green = Line Out (always "available", no jack-sense).
- Front green = Headphone (shows "not available" unless plugged in; front-panel header may not be wired inside the case).
- HDMI audio goes to the monitor's speakers if it has them.
- `pcspkr` kernel module = motherboard beep buzzer (mostly absent on modern boards; check `lsmod | grep pcspkr`).
