#!/bin/bash
# Keep JVC speaker connected

JVC_MAC='13:95:F2:0A:0D:53'

while true; do
    if ! sudo bluetoothctl info $JVC_MAC | grep -q 'Connected: yes'; then
        echo "🔊 Reconnecting JVC speaker..."
        sudo bluetoothctl pair $JVC_MAC 2>/dev/null
        sudo bluetoothctl connect $JVC_MAC
        sleep 2
    fi
    sleep 5
done