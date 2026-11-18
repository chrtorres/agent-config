
#!/usr/bin/env bash
# Read-only Linux storage inventory.
# Run with sudo for SMART health checks.

# Stop if an undefined variable is used
set -u

echo "===== DEVICE ====="
date -Is
hostnamectl

echo "===== PHYSICAL DRIVES ====="
lsblk -d -e 7 -o NAME,SIZE,MODEL,SERIAL,TRAN,ROTA,TYPE

echo "===== PARTITIONS ====="
lsblk -e 7 -o NAME,SIZE,FSTYPE,FSVER,LABEL,UUID,MOUNTPOINTS

echo "===== STORAGE USAGE ====="
df -hT

echo "===== UNMOUNTED PARTITIONS ====="
lsblk -P -o NAME,TYPE,SIZE,FSTYPE,LABEL,MOUNTPOINT |
    grep 'TYPE="part"' |
    grep 'MOUNTPOINT=""' || true

echo "===== SMART HEALTH ====="

if ! command -v smartctl >/dev/null; then
    echo "smartmontools missing."
    echo "Install: sudo apt install smartmontools"

elif [[ $EUID -ne 0 ]]; then
    echo "Run script with sudo for SMART health."

else
    # Automatically find all SMART-compatible drives
    for drive in $(smartctl --scan-open | awk '{print $1}'); do
        echo "===== DRIVE: $drive ====="
        smartctl -a "$drive"
    done
fi

echo "===== INVENTORY COMPLETE ====="
