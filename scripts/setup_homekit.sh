#!/bin/bash

# Enterprise Voice Control - HomeKit Setup Script
# Configures Homebridge integration for HomeKit device control

echo "🏠 Enterprise Voice Control - HomeKit Setup"
echo "==========================================="

echo
echo "This script will help you set up HomeKit integration via Homebridge."
echo

# Check if Homebridge is already running
echo "Step 1: Checking for existing Homebridge installation..."

# Check if we can reach a Homebridge instance
HOMEBRIDGE_FOUND=false
for host in "localhost" "pi1.local" "homebridge.local" "192.168.1.10" "192.168.1.100"; do
    for port in "8581" "8080"; do
        if curl -s --connect-timeout 3 "http://$host:$port" >/dev/null 2>&1; then
            echo "✅ Found Homebridge at http://$host:$port"
            HOMEBRIDGE_URL="http://$host:$port"
            HOMEBRIDGE_FOUND=true
            break 2
        fi
    done
done

if [ "$HOMEBRIDGE_FOUND" = false ]; then
    echo "❌ No existing Homebridge found."
    echo
    echo "Would you like to install Homebridge on this system? (y/n)"
    read -r install_homebridge
    
    if [[ "$install_homebridge" =~ ^[Yy]$ ]]; then
        echo
        echo "Step 2: Installing Homebridge..."
        
        # Install Node.js if not present
        if ! command -v node &> /dev/null; then
            echo "Installing Node.js..."
            curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
            sudo apt-get install -y nodejs
        fi
        
        # Install Homebridge
        echo "Installing Homebridge..."
        sudo npm install -g homebridge homebridge-config-ui-x
        
        # Create homebridge user and directories
        sudo useradd -rm homebridge
        sudo mkdir -p /var/lib/homebridge
        sudo chown homebridge:homebridge /var/lib/homebridge
        
        # Create systemd service
        sudo tee /etc/systemd/system/homebridge.service > /dev/null << 'EOF'
[Unit]
Description=Homebridge
After=network-online.target

[Service]
Type=simple
User=homebridge
EnvironmentFile=/etc/default/homebridge
ExecStart=/usr/bin/homebridge $HOMEBRIDGE_OPTS
Restart=on-failure
RestartSec=10
KillMode=process

[Install]
WantedBy=multi-user.target
EOF
        
        # Create environment file
        sudo tee /etc/default/homebridge > /dev/null << 'EOF'
# Defaults / Configuration options for homebridge
# The following settings tells homebridge where to find the config.json file and where to persist the data (i.e. pairing information)
HOMEBRIDGE_OPTS=-U /var/lib/homebridge -P /var/lib/homebridge
EOF
        
        # Enable and start service
        sudo systemctl daemon-reload
        sudo systemctl enable homebridge
        sudo systemctl start homebridge
        
        echo "✅ Homebridge installed and started"
        echo "🌐 Access Homebridge UI at: http://$(hostname -I | awk '{print $1}'):8581"
        HOMEBRIDGE_URL="http://localhost:8581"
    else
        echo "Skipping Homebridge installation."
        echo "You can set up HomeKit integration manually later."
        exit 0
    fi
else
    echo "Using existing Homebridge at: $HOMEBRIDGE_URL"
fi

echo
echo "Step 3: Setting up Homebridge credentials..."
echo "Please enter your Homebridge admin credentials:"
read -p "Username (default: admin): " hb_username
hb_username=${hb_username:-admin}

read -s -p "Password: " hb_password
echo

# Test credentials
echo
echo "Testing Homebridge API connection..."
if curl -s -u "$hb_username:$hb_password" "$HOMEBRIDGE_URL/api/status" >/dev/null; then
    echo "✅ Homebridge API connection successful"
else
    echo "❌ Failed to connect to Homebridge API"
    echo "Please check your credentials and try again."
    exit 1
fi

echo
echo "Step 4: Discovering HomeKit accessories..."
accessories=$(curl -s -u "$hb_username:$hb_password" "$HOMEBRIDGE_URL/api/accessories" | jq -r '.[].displayName' 2>/dev/null | head -10)

if [ -n "$accessories" ]; then
    echo "Found HomeKit accessories:"
    echo "$accessories" | sed 's/^/  - /'
else
    echo "No accessories found or jq not installed."
    echo "Install jq for better JSON parsing: sudo apt install jq"
fi

echo
echo "Step 5: Creating configuration..."
# Extract host and port from URL
hb_host=$(echo "$HOMEBRIDGE_URL" | sed 's|http://||' | cut -d: -f1)
hb_port=$(echo "$HOMEBRIDGE_URL" | sed 's|http://||' | cut -d: -f2)

# Create or update config file
config_file="config.json"
if [ -f "$config_file" ]; then
    # Update existing config
    echo "Updating existing config.json..."
    # Use jq if available, otherwise manual editing
    if command -v jq &> /dev/null; then
        jq --arg url "$HOMEBRIDGE_URL" --arg user "$hb_username" --arg pass "$hb_password" \
           '.homekit.homebridgeUrl = $url | .homekit.credentials.username = $user | .homekit.credentials.password = $pass' \
           "$config_file" > "$config_file.tmp" && mv "$config_file.tmp" "$config_file"
        echo "✅ Updated config.json with Homebridge settings"
    else
        echo "Manual config update required (jq not installed)"
        echo "Add to config.json:"
        echo "  \"homekit\": {"
        echo "    \"homebridgeUrl\": \"$HOMEBRIDGE_URL\","
        echo "    \"credentials\": {"
        echo "      \"username\": \"$hb_username\","
        echo "      \"password\": \"$hb_password\""
        echo "    }"
        echo "  }"
    fi
else
    # Create new config
    echo "Creating new config.json..."
    cat > "$config_file" << EOF
{
  "piAddress": "pi@$(hostname).local",
  "piPath": "/home/$(whoami)",
  "homekit": {
    "homebridgeUrl": "$HOMEBRIDGE_URL",
    "credentials": {
      "username": "$hb_username",
      "password": "$hb_password"
    }
  },
  "audio": {
    "microphoneIndex": "2,0",
    "bluetoothSpeaker": ""
  },
  "appleTV": {
    "deviceId": "",
    "name": "Living Room Apple TV"
  }
}
EOF
    echo "✅ Created config.json with Homebridge settings"
fi

echo
echo "Step 6: Testing HomeKit integration..."
echo "Testing basic HomeKit commands..."

# Test script for HomeKit
cat > test_homekit.py << 'EOF'
#!/usr/bin/env python3
import requests
import json
import sys

def test_homekit(url, username, password):
    try:
        # Test API connection
        response = requests.get(f"{url}/api/status", auth=(username, password), timeout=5)
        if response.status_code == 200:
            print("✅ Homebridge API connection successful")
            
            # Get accessories
            response = requests.get(f"{url}/api/accessories", auth=(username, password), timeout=5)
            if response.status_code == 200:
                accessories = response.json()
                print(f"✅ Found {len(accessories)} HomeKit accessories")
                
                # Show first few accessories
                for i, acc in enumerate(accessories[:5]):
                    print(f"  - {acc.get('displayName', 'Unknown')} ({acc.get('serviceName', 'Unknown')})")
                    
                return True
            else:
                print(f"❌ Failed to get accessories: {response.status_code}")
                return False
        else:
            print(f"❌ API connection failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

if __name__ == "__main__":
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    homekit = config.get('homekit', {})
    url = homekit.get('homebridgeUrl')
    creds = homekit.get('credentials', {})
    username = creds.get('username')
    password = creds.get('password')
    
    if test_homekit(url, username, password):
        print("\n🏠 HomeKit integration is ready!")
    else:
        print("\n❌ HomeKit integration needs troubleshooting")
        sys.exit(1)
EOF

python3 test_homekit.py
rm -f test_homekit.py

echo
echo "✅ HomeKit setup complete!"
echo
echo "Next steps:"
echo "1. Test voice commands like 'Computer, turn on the lights'"
echo "2. Add more HomeKit devices through the Homebridge web interface"
echo "3. Configure iOS Shortcuts for advanced automation"
echo
echo "HomeKit Resources:"
echo "- Homebridge UI: $HOMEBRIDGE_URL"
echo "- Configuration file: $(pwd)/config.json"
echo "- Supported devices: https://homebridge.io/plugins"
echo
echo "🏠 Ready for Enterprise home automation!"