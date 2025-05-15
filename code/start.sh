#!/bin/bash
# TODO: Make computer use GPS Time.
# Check if an IP address is provided as an argument
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: $0 <INTERFACE_NAME> <GPS Port Name>"
    exit 1
fi

INTERFACE_NAME=$1
GPS_PORT=$2
BAUD_RATE=115200

# Function to stop ptpd if it is running
stop_ptpd() {
    PTDP_PID=$(pgrep ptpd)
    if [ -n "$PTDP_PID" ]; then
        echo "Stopping existing ptpd process (PID: $PTDP_PID)..."
        sudo kill "$PTDP_PID"
        sleep 2  # Wait for the process to terminate
    else
        echo "No running ptpd process found."
    fi
}

# Stop ptpd if it is already running
stop_ptpd

# Configure the network interface with the provided IP address
sudo ifconfig "$INTERFACE_NAME" 192.168.1.100

# --- Configure GPS ---
sudo systemctl enable gpsd
sudo systemctl restart gpsd
echo "GPSD System Initialized"

# Start PTP daemon with the specified interface
echo "Starting ptpd on interface $INTERFACE_NAME..."
sudo ptpd -M -i "$INTERFACE_NAME"

# Sleep for 5 seconds to allow ptpd to initialize
sleep 5

echo "ptpd is now running on interface $INTERFACE_NAME."

python3 recording.py