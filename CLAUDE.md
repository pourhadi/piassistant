# Apple TV Remote Voice Control System

## Overview
This is a sophisticated Raspberry Pi-based voice control system that emulates the USS Enterprise NCC-1701-D computer from Star Trek: The Next Generation. The system provides voice control for Apple TV, HomeKit devices, and general conversations with authentic TNG computer sounds and personality.

## Current Implementation Status: ✅ PRODUCTION READY

### Core System Architecture

**Main File:** `conversational_voice_control.py`
- **Deployment:** Raspberry Pi 5 at `dan@pi5.local`
- **Status:** Active production system with Enterprise-D computer personality
- **API Keys:** Uses Claude 4 Sonnet and OpenAI APIs (keys stored in ~/.bashrc on Pi)

### Key Features

#### 🎙️ Voice Recognition & Processing
- **Wake Word:** "Computer" (Star Trek style)
- **Speech Recognition:** OpenAI Whisper with Voice Activity Detection (VAD)
- **AI Processing:** Claude 4 Sonnet API for natural language understanding
- **Follow-up Conversations:** Users can continue talking without re-saying "computer"
- **Persistent Memory:** Conversation history saved to `/home/dan/voice_assistant_memory.json`

#### 🎵 Audio System
- **TTS:** OpenAI TTS with Piper TTS fallback
- **Audio Input:** USB microphone (device index 2,0)
- **Audio Output:** JVC Bluetooth speaker (MAC: 13:95:F2:0A:0D:53)
- **Processing Sounds:** Random TNG computer beeps from `/home/dan/tng_beeps/`
- **Red Alert:** TNG red alert sound at `/home/dan/tng_red_alert1.mp3`

#### 📺 Apple TV Control
- **Technology:** pyatv (network-based, not Bluetooth)
- **Apple TV Device ID:** 6DD04867-AD74-4FE7-AFD2-30BA83DFD648
- **Commands:** Navigation, playback, volume, app launching, search, power
- **Apps Supported:** Netflix, YouTube, Disney+, Hulu, Amazon Prime, Apple TV+, ESPN+

#### 🏠 HomeKit Integration
- **Primary:** Homebridge API integration at `pi1.local:8581`
- **Authentication:** Bearer token (username: dan, password: windoze)
- **Fallback:** iOS Shortcuts for unsupported devices
- **Devices:** Lights, thermostats, switches, locks, cameras

#### 🖖 Enterprise-D Computer Personality
- **Voice:** Formal, precise tone matching TNG computer
- **Responses:** Uses Starfleet terminology and technical language
- **Phrases:** "Acknowledged", "Confirmed", "Working", "Please specify"
- **Time Response:** Federation Standard chronometer reference

### Special Commands

#### Red Alert Protocol
- **Trigger:** "Computer, red alert"
- **Actions:**
  - Plays TNG red alert sound
  - Flashes Govee floor lamp red for 10 seconds
  - Speaks: "Red alert! All hands to battle stations!"

#### Intent Classification
- **HomeKit:** Smart home device control
- **Apple TV:** Media system control
- **Conversation:** General questions and chat

### Technical Implementation

#### Audio Processing Pipeline
1. Continuous audio stream via `arecord` (44.1kHz, 16-bit mono)
2. Real-time Voice Activity Detection with energy thresholds
3. Intelligent speech boundary detection
4. Automatic audio buffering and transcription queuing
5. Whisper-based speech-to-text conversion

#### Command Processing Flow
1. Wake word detection → Command extraction
2. Claude API intent classification (homekit/apple_tv/conversation)
3. Context-aware command interpretation using conversation memory
4. Device-specific command execution (pyatv/Homebridge)
5. Response generation with Enterprise computer personality
6. TTS output with authentic TNG computer sounds

### File Structure (Post-Cleanup)

#### Active Files
```
conversational_voice_control.py    # Main system (Enterprise-D computer)
homekit_setup.py                   # HomeKit device pairing utility
download_beeps.py                   # TNG computer beep downloader
requirements.txt                    # Updated dependencies
keep_jvc_connected.sh              # JVC speaker auto-reconnection
monitor_logs.sh                     # Remote monitoring script
launch_claude_control.sh           # System launcher
```

#### Documentation
```
README_PYATV.md                    # Current system documentation
SOLUTIONS_SUMMARY.md               # Historical solution evolution
CLAUDE.md                          # This comprehensive guide
```

#### Historical Documentation (Archived)
```
BLUETOOTH_*.md                     # Failed Bluetooth HID attempts
BTSTACK_*.md                       # BTstack experiments
BLUEZ_*.md                         # BlueZ downgrade attempts
```

### Dependencies

#### Core Python Packages
- `anthropic>=0.34.0` - Claude API client
- `openai>=1.0.0` - OpenAI API for Whisper and TTS
- `whisper>=20231117` - Speech recognition
- `requests>=2.31.0` - HTTP requests for APIs
- `numpy>=1.24.3` - Audio processing
- `sounddevice>=0.4.0` - Audio capture
- `pyatv>=0.12.0` - Apple TV control
- `mutagen>=1.47.0` - Audio file metadata
- `homekit>=0.1.0` - HomeKit integration

#### System Dependencies
- `mpg123` - Audio playback
- `arecord/aplay` - Audio recording/playback
- `curl` - HTTP requests

### Deployment Details

#### Hardware Requirements
- Raspberry Pi 5 (current deployment)
- USB microphone with good voice pickup
- Bluetooth speaker for audio output
- Network connectivity for API calls and device control

#### Installation Process
1. Set up Raspberry Pi with Python 3.x
2. Install system dependencies: `sudo apt install mpg123 alsa-utils curl`
3. Install Python dependencies: `pip install -r requirements.txt`
4. Configure API keys in ~/.bashrc
5. Set up audio devices (microphone index 2,0)
6. Pair JVC Bluetooth speaker
7. Configure Apple TV device ID
8. Set up Homebridge connection
9. Deploy TNG computer beep files
10. Run system: `python3 conversational_voice_control.py`

### Voice Command Examples

#### Apple TV Control
- "Computer, go to Netflix"
- "Computer, play"
- "Computer, volume up"
- "Computer, search for The Office"
- "Computer, go home"

#### HomeKit Control
- "Computer, turn on the lights"
- "Computer, set temperature to 72 degrees"
- "Computer, lock the front door"
- "Computer, turn off the living room lamp"

#### Special Commands
- "Computer, red alert" → Activates red alert protocol
- "Computer, what time is it?" → "The time is now [time]. Chronometer synchronized with Federation Standard."

#### Conversation
- "Computer, what's the weather like?"
- "Computer, tell me about quantum mechanics"
- "Computer, remember that I like science fiction"

### System Evolution History

#### Phase 1: Bluetooth HID Attempts (Failed)
- Extensive experiments with BlueZ, BTstack, bthidhub
- Hardware alternatives: ESP32, Raspberry Pi Pico W, NRF52
- Issues: Apple TV Bluetooth compatibility, pairing problems
- **Result:** Abandoned due to Apple TV's restrictive Bluetooth implementation

#### Phase 2: Network-Based Solution (Success)
- Discovered pyatv library for network-based Apple TV control
- Eliminated need for Bluetooth entirely
- Much more reliable and feature-rich
- **Result:** Stable, working system

#### Phase 3: Enhanced Features (Current)
- Added Claude AI integration for natural language processing
- Implemented HomeKit control via Homebridge
- Added Enterprise-D computer personality
- Integrated authentic TNG computer sounds
- Added conversation memory and follow-up capability
- **Result:** Production-ready voice assistant

### Monitoring and Maintenance

#### Remote Monitoring
- **Script:** `monitor_logs.sh` - SSH-based log monitoring
- **Logs:** Real-time system status and error tracking
- **Audio:** JVC speaker auto-reconnection via `keep_jvc_connected.sh`

#### System Health
- **Memory Management:** Automatic cleanup of old conversation entries
- **Audio Processing:** VAD-based intelligent speech detection
- **API Resilience:** Fallback mechanisms for API failures
- **Device Recovery:** Automatic reconnection for audio devices

### Future Enhancements

#### Planned Features
- Multi-room audio support
- Enhanced HomeKit device discovery
- Voice command macro system
- Integration with additional smart home platforms
- Advanced conversation context awareness

#### Technical Improvements
- Optimize audio processing latency
- Enhance TNG computer sound variety
- Improve HomeKit device response times
- Add voice command confirmation options

### Troubleshooting

#### Common Issues
1. **Audio not working:** Check microphone index and JVC speaker connection
2. **Apple TV not responding:** Verify device ID and network connectivity
3. **HomeKit commands failing:** Check Homebridge API authentication
4. **TNG sounds not playing:** Verify `/home/dan/tng_beeps/` directory exists

#### Debug Commands
```bash
# Check audio devices
arecord -l

# Test Apple TV connection
python3 -c "import pyatv; print('pyatv works')"

# Check Homebridge API
curl -u dan:windoze http://pi1.local:8581/api/accessories

# Monitor system logs
tail -f /home/dan/voice_control.log
```

### API Key Management

#### Required Keys
- `ANTHROPIC_API_KEY` - Claude API access
- `OPENAI_API_KEY` - Whisper and TTS access

#### Storage Location
- Pi deployment: `~/.bashrc`
- Keys must be exported in shell environment

### Development Workflow

#### System Update Checklist
- Always copy the conversation script to the pi after editing it

### Project Status: ✅ PRODUCTION READY

The system successfully evolved from complex Bluetooth HID experiments to a robust network-based voice control system. It demonstrates enterprise-level features including:

- **Reliability:** Network-based control eliminates Bluetooth issues
- **Intelligence:** Claude AI provides natural language understanding
- **Authenticity:** TNG computer sounds and personality create immersive experience
- **Expandability:** HomeKit integration allows control of entire smart home
- **Maintainability:** Clean codebase with comprehensive error handling

The current implementation represents a complete, working voice control system that provides both functionality and entertainment value through its authentic Star Trek computer interface.

### Memoranda

#### Development Best Practices
- when working with the dashboard CLI, always build UI with Ink elements / components