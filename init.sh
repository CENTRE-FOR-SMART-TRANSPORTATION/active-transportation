#!/bin/bash
# Check if an IP address is provided as an argument
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: $0 <GPS Port Name>"
    exit 1
fi

GPS_PORT=$1

# Function to check if a package is installed
is_pkg_installed() {
    dpkg -s "$1" &>/dev/null
    return $?
}

# List of required packages
required_pkgs=("ptpd" "net-tools" "gpsd" "gpsd-clients", "python3.12")

# Check and install missing packages
for pkg in "${required_pkgs[@]}"; do
    if is_pkg_installed "$pkg"; then
        echo "$pkg is already installed."
    else
        echo "$pkg is not installed. Installing..."
        sudo apt-get update
        sudo apt-get install -y "$pkg"
        if is_pkg_installed "$pkg"; then
            echo "$pkg has been successfully installed."
        else
            echo "Failed to install $pkg."
            exit 1
        fi
    fi
done

# Install Python packages
python3 -m ensurepip --default-pip  # Ensure pip is installed
python3 -m pip install --upgrade pip  # Upgrade pip

python_pkgs=("pyserial" "gpsd-py3" "numpy")

for pkg in "${python_pkgs[@]}"; do
    if python3 -c "import $pkg" &>/dev/null; then
        echo "Python package $pkg is already installed."
    else
        echo "Installing Python package: $pkg..."
        python3 -m pip install "$pkg"
        if python3 -c "import $pkg" &>/dev/null; then
            echo "Successfully installed $pkg."
        else
            echo "Failed to install $pkg."
            exit 1
        fi
    fi
done

echo "All required system and Python packages are installed."


# --- Configure GPS ---
sudo systemctl enable gpsd
GPS_CONF="/etc/default/gpsd"

if [ ! -f "$GPS_CONF" ]; then
    GPS_CONF=$(find /etc -name "gpsd" | head -n 1)
    if [ -z "$GPS_CONF" ]; then
        echo "Error: Could not find gpsd configuration file."
        exit 1
    fi
fi

# Add GPS reference if not already present
if ! grep -q "$GPS_PORT" "$GPS_CONF"; then
    echo -e "DEVICES=\""$GPS_PORT"\"\n\nGPSD_OPTIONS=\"-n\"\nSPEED=115200\n\nSTART_DAEMON=\"true\"\n" | sudo tee "$GPS_CONF"
    echo "Updated $GPS_CONF with GPS reference."
else
    echo "GPS reference already present in $GPS_CONF."
fi

# Restart NTP service
sudo systemctl restart gpsd
echo "GPSD System Initialized"
