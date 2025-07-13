# Enterprise-D Voice Control System 🚀

A sophisticated Raspberry Pi-based voice control system that emulates the USS Enterprise NCC-1701-D computer from Star Trek: The Next Generation. Control your Apple TV, HomeKit devices, and have natural conversations with an AI assistant that sounds and behaves like the iconic starship computer.

![Enterprise Control Center](https://img.shields.io/badge/Star%20Trek-Enterprise--D-blue?style=for-the-badge&logo=startrek)
![Python](https://img.shields.io/badge/Python-3.8+-green?style=for-the-badge&logo=python)
![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-5-red?style=for-the-badge&logo=raspberrypi)
![Node.js](https://img.shields.io/badge/Node.js-18+-green?style=for-the-badge&logo=node.js)

## ✨ Features

### 🎙️ Voice Control System
- **Wake Word**: "Computer" (authentic Star Trek style)
- **Natural Language Processing**: Powered by Claude 4 Sonnet
- **Speech Recognition**: OpenAI Whisper with Voice Activity Detection
- **Text-to-Speech**: OpenAI TTS or ElevenLabs with Enterprise-D personality
- **Persistent Memory**: Conversation history and context awareness
- **Follow-up Conversations**: Continue talking without re-saying "computer"

### 📺 Apple TV Control
- **Network-Based Control**: Uses pyatv (no Bluetooth required)
- **Full Navigation**: Directional controls, home, menu, play/pause
- **App Launching**: Netflix, YouTube, Disney+, Hulu, Prime Video, Apple TV+, ESPN+
- **Volume Control**: Adjust volume through voice commands
- **Search Functionality**: Voice search across apps and content
- **Power Management**: Turn Apple TV on/off

### 🏠 HomeKit Integration
- **Homebridge Integration**: Control HomeKit devices via API
- **iOS Shortcuts Fallback**: For devices not supported by Homebridge
- **Device Types**: Lights, thermostats, switches, locks, cameras, fans
- **Scene Control**: Activate HomeKit scenes and automations
- **Status Queries**: Check device states and sensor readings

### 🔌 Dynamic MCP Server Management
- **Real-time Configuration**: Add/remove MCP servers via CLI
- **Pre-built Templates**: Quick setup for popular services
- **Supported Servers**: Filesystem, Brave Search, SQLite, GitHub, Slack, PostgreSQL
- **Live Updates**: Changes apply immediately to running AI assistant
- **Interactive Management**: Full CLI interface for server configuration

### 🖥️ Enterprise Control Center CLI
- **Star Trek UI**: Authentic TNG computer interface design
- **Real-time Monitoring**: System status, logs, and performance metrics
- **Voice System Control**: Start, stop, restart, diagnostics
- **Audio Testing**: TTS voices, microphone, speakers, TNG computer beeps
- **Emergency Protocols**: Red alert with authentic sounds and lighting
- **Configuration Management**: All settings manageable through CLI

### 🎵 Authentic Audio Experience
- **TNG Computer Sounds**: Real Star Trek computer beeps and acknowledgments
- **Red Alert Protocol**: Authentic klaxon with synchronized smart lighting
- **Voice Synthesis**: Enterprise-D computer personality and speech patterns
- **Audio Pipeline**: Professional-grade voice processing and output

## 🛠️ Hardware Requirements

### Required Components
- **Raspberry Pi 5** (4GB+ RAM recommended)
- **MicroSD Card** (32GB+ Class 10)
- **USB Microphone** (or USB sound card with microphone input)
- **Bluetooth Speaker** (JVC or similar recommended)
- **Network Connection** (WiFi or Ethernet)

### Recommended Setup
- **Apple TV 4K** (any generation with network connectivity)
- **HomeKit Hub** (iPad, HomePod, or Apple TV)
- **Smart Home Devices** (Philips Hue, smart switches, etc.)
- **Govee Floor Lamp** (for red alert lighting effects)

## 📦 Quick Installation

### 1. Raspberry Pi Setup
```bash
# Flash Raspberry Pi OS (64-bit) to SD card
# Enable SSH and WiFi in raspi-config
sudo raspi-config

# Update system
sudo apt update && sudo apt upgrade -y

# Install required system packages
sudo apt install -y python3-pip python3-venv nodejs npm git mpg123 alsa-utils curl
```

### 2. Clone Repository
```bash
cd ~
git clone https://github.com/yourusername/enterprise-voice-control.git
cd enterprise-voice-control
```

### 3. Install Dependencies
```bash
# Install Python dependencies
python3 -m venv pyatv_env
source pyatv_env/bin/activate
pip install -r requirements.txt

# Install Node.js dependencies for CLI
npm install
```

### 4. Configure API Keys
```bash
# Add API keys to environment
echo "export ANTHROPIC_API_KEY=your_claude_api_key_here" >> ~/.bashrc
echo "export OPENAI_API_KEY=your_openai_api_key_here" >> ~/.bashrc
echo "export ELEVENLABS_API_KEY=your_elevenlabs_key_here" >> ~/.bashrc  # Optional
source ~/.bashrc
```

### 5. Audio Setup
```bash
# Configure audio devices (run setup script)
./scripts/setup_audio.sh

# Download TNG computer sounds
python3 download_beeps.py
```

### 6. Device Discovery
```bash
# Find your Apple TV
source pyatv_env/bin/activate
python3 -c "import asyncio; from pyatv import scan; asyncio.run(scan())"

# Setup HomeKit integration (if using Homebridge)
./scripts/setup_homekit.sh
```

### 7. Launch System
```bash
# Start the voice control system
python3 conversational_voice_control.py

# Or use the Enterprise Control Center (in a new terminal)
npm run start
```

## 🎮 Enterprise Control Center Usage

Launch the interactive CLI control center:
```bash
npm run start
```

### Main Menu Options:
- **🚀 Voice System Control**: Start, stop, restart, and monitor the voice system
- **🔧 MCP Server Management**: Add, remove, and configure MCP servers
- **🔊 Audio & TTS Testing**: Test voice synthesis, microphones, and speakers
- **🚨 Emergency Protocols**: Red alert and ship-wide announcements
- **📜 System Monitoring**: View logs, performance metrics, and system status
- **⚙️ System Configuration**: Manage Pi settings, API keys, and voice options
- **📊 Status Reports**: Voice statistics, command history, and error reports

### Voice Commands Examples:
```
"Computer, go to Netflix"
"Computer, turn on the living room lights"
"Computer, what's the weather like?"
"Computer, set temperature to 72 degrees"
"Computer, red alert"
"Computer, play The Office on Apple TV"
```

## 🔧 Configuration

### Environment Variables
Create a `.env` file or add to `~/.bashrc`:
```bash
# Required API Keys
export ANTHROPIC_API_KEY=your_claude_api_key
export OPENAI_API_KEY=your_openai_api_key

# Optional TTS Enhancement
export ELEVENLABS_API_KEY=your_elevenlabs_api_key

# Optional Service API Keys for MCP
export BRAVE_API_KEY=your_brave_search_api_key
export GITHUB_TOKEN=your_github_personal_access_token
export SLACK_BOT_TOKEN=your_slack_bot_token
```

### Device Configuration
Edit `config.json` to customize:
```json
{
  "piAddress": "pi@raspberrypi.local",
  "piPath": "/home/pi",
  "appleTV": {
    "deviceId": "your-apple-tv-uuid",
    "name": "Living Room Apple TV"
  },
  "homekit": {
    "homebridgeUrl": "http://your-homebridge-ip:8581",
    "credentials": {
      "username": "admin",
      "password": "your-password"
    }
  },
  "audio": {
    "microphoneIndex": "2,0",
    "bluetoothSpeaker": "13:95:F2:0A:0D:53"
  }
}
```

## 🚨 Red Alert Protocol

The system includes an authentic Star Trek red alert protocol:

**Voice Command**: `"Computer, red alert"`

**Actions**:
1. Plays authentic TNG red alert klaxon
2. Flashes compatible smart lights red
3. Announces "Red alert! All hands to battle stations!"
4. Maintains red lighting for 10 seconds

**Requirements**:
- Govee floor lamp or compatible RGB smart lights
- Homebridge integration configured
- Audio output enabled

## 🔌 MCP (Model Context Protocol) Integration

The system supports dynamic MCP server management for extending AI capabilities:

### Supported MCP Servers:
- **Filesystem**: File operations on the Pi
- **Brave Search**: Web search capabilities
- **SQLite**: Database operations
- **GitHub**: Repository access and management
- **Slack**: Team communication integration
- **PostgreSQL**: Advanced database operations

### Adding MCP Servers:
1. Open Enterprise Control Center
2. Navigate to "MCP Server Management"
3. Use "Quick Add" options or "Add Server Templates"
4. Configure required API keys/environment variables
5. Test connections
6. Apply changes (restarts voice assistant)

### Custom MCP Servers:
Edit `/home/pi/mcp_config.json` to add custom servers:
```json
{
  "mcpServers": {
    "your-custom-server": {
      "command": "npx",
      "args": ["-y", "@your/mcp-server"],
      "env": {
        "YOUR_API_KEY": "your-api-key"
      }
    }
  }
}
```

## 📱 Mobile Integration

### iOS Shortcuts
The system can trigger iOS Shortcuts for advanced HomeKit control:

1. Create shortcuts in the iOS Shortcuts app
2. Name them descriptively (e.g., "Movie Mode", "Bedtime Scene")
3. Use voice commands like "Computer, activate movie mode"

### Remote Access
Access the Enterprise Control Center remotely:
```bash
ssh pi@your-pi-ip
cd ~/enterprise-voice-control
npm run start
```

## 🔊 Audio Setup Guide

### Microphone Configuration
```bash
# List audio devices
arecord -l

# Test microphone
arecord -d 5 -f cd test.wav && aplay test.wav

# Set default microphone in config
# Usually device index 2,0 for USB microphones
```

### Bluetooth Speaker Setup
```bash
# Pair Bluetooth speaker
bluetoothctl
scan on
pair [MAC_ADDRESS]
connect [MAC_ADDRESS]
trust [MAC_ADDRESS]

# Auto-reconnect script (included)
./scripts/keep_jvc_connected.sh
```

### TNG Computer Sounds
```bash
# Download authentic TNG computer beeps
python3 download_beeps.py

# Test audio playback
mpg123 tng_beeps/beep_1.mp3
```

## 🐛 Troubleshooting

### Common Issues

#### Voice System Won't Start
```bash
# Check API keys
echo $ANTHROPIC_API_KEY
echo $OPENAI_API_KEY

# Check Python environment
source pyatv_env/bin/activate
python3 -c "import anthropic, openai, pyatv; print('All imports successful')"

# Check logs
tail -f voice_system.log
```

#### Apple TV Not Responding
```bash
# Rediscover Apple TV
source pyatv_env/bin/activate
atvremote scan

# Test connection
atvremote --id YOUR_DEVICE_ID playing
```

#### Audio Issues
```bash
# Check audio devices
arecord -l
aplay -l

# Test microphone
arecord -d 3 -f cd test.wav && aplay test.wav

# Check Bluetooth speaker
bluetoothctl info [MAC_ADDRESS]
```

#### HomeKit Integration Issues
```bash
# Test Homebridge connection
curl -u username:password http://homebridge-ip:8581/api/accessories

# Check iOS Shortcuts
# Ensure shortcuts are named clearly and work manually first
```

### Debug Mode
Enable verbose logging:
```bash
export DEBUG=true
python3 conversational_voice_control.py
```

### Log Files
- **Voice System**: `~/voice_system.log`
- **Control Center**: `~/control_center.log`
- **Audio Issues**: `~/audio_debug.log`

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup
```bash
# Clone repository
git clone https://github.com/yourusername/enterprise-voice-control.git
cd enterprise-voice-control

# Install development dependencies
pip install -r requirements-dev.txt
npm install

# Run tests
python3 -m pytest tests/
npm test

# Code formatting
black conversational_voice_control.py
prettier --write enterprise-control-simple.js
```

### Feature Requests
- Open an issue with the "enhancement" label
- Describe the desired functionality
- Include use cases and examples

### Bug Reports
- Use the bug report template
- Include system information and logs
- Provide steps to reproduce

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🖖 Acknowledgments

- **Star Trek: The Next Generation** for inspiration and audio assets
- **OpenAI** for speech recognition and synthesis APIs
- **Anthropic** for Claude AI integration
- **pyatv** library for Apple TV control
- **Homebridge** community for HomeKit integration
- **Model Context Protocol** for extensible AI capabilities

## 🚀 Star Trek Computer Experience

This project brings the iconic USS Enterprise-D computer experience to life:

- **Authentic Voice**: Formal, precise responses matching TNG computer personality
- **Starfleet Terminology**: Uses appropriate technical language and references
- **Enterprise Sounds**: Real TNG computer beeps, alerts, and acknowledgments
- **Red Alert Protocol**: Full starship emergency procedures
- **Bridge Operations**: Complete control center interface for system management

*"Computer, end program."*

---

**Live long and prosper!** 🖖

For support, questions, or to share your Enterprise setup, visit our [Discussions](https://github.com/yourusername/enterprise-voice-control/discussions) page.