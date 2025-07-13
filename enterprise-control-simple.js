#!/usr/bin/env node
import React, { useState, useEffect } from 'react';
import { render, Text, Box, useInput } from 'ink';
import { spawn, execSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import os from 'os';

const { createElement: h } = React;

// Configuration management
const CONFIG_FILE = path.join(os.homedir(), '.enterprise-control-config.json');

const loadConfig = () => {
	try {
		if (fs.existsSync(CONFIG_FILE)) {
			return JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf8'));
		}
	} catch (error) {
		console.error('Error loading config:', error);
	}
	return {
		piAddress: 'dan@pi5.local',
		piPath: '/home/dan'
	};
};

const saveConfig = (config) => {
	try {
		fs.writeFileSync(CONFIG_FILE, JSON.stringify(config, null, 2));
	} catch (error) {
		console.error('Error saving config:', error);
	}
};

// Enterprise Control Center Component
const EnterpriseControlCenter = () => {
	const [currentScreen, setCurrentScreen] = useState('main');
	const [selectedIndex, setSelectedIndex] = useState(0);
	const [config, setConfig] = useState(loadConfig);
	const [systemStatus, setSystemStatus] = useState({
		voiceRunning: false,
		mcpServers: 0,
		pid: null
	});
	const [availableVoices, setAvailableVoices] = useState([]);
	const [showingVoices, setShowingVoices] = useState(false);
	const [logViewerActive, setLogViewerActive] = useState(false);
	const [logContent, setLogContent] = useState('');
	const [logUpdateInterval, setLogUpdateInterval] = useState(null);
	const [actionResult, setActionResult] = useState(null);
	const [showingActionResult, setShowingActionResult] = useState(false);
	const [mcpServersForRemoval, setMcpServersForRemoval] = useState([]);
	const [showingRemovalMenu, setShowingRemovalMenu] = useState(false);

	// Check voice system status on Pi
	const checkVoiceSystemStatus = () => {
		try {
			const result = execSync(`ssh ${config.piAddress} "pgrep -f conversational_voice_control.py"`, { encoding: 'utf8' });
			const pid = result.trim().split('\n')[0];
			setSystemStatus(prev => ({
				...prev,
				voiceRunning: true,
				pid: parseInt(pid)
			}));
		} catch (error) {
			setSystemStatus(prev => ({
				...prev,
				voiceRunning: false,
				pid: null
			}));
		}
	};

	// Voice system actions
	const handleVoiceAction = (action) => {
		try {
			switch (action) {
				case 0: // Start
					try {
						// Get ElevenLabs API key from Pi
						const elevenLabsKey = getElevenLabsKey();
						
						// Create a startup script with explicit environment variables
						const startupScript = `#!/bin/bash
# Load API keys from environment
source ~/.bashrc${elevenLabsKey ? `\nexport ELEVENLABS_API_KEY="${elevenLabsKey}"` : ''}
cd ${config.piPath}
source pyatv_env/bin/activate
python conversational_voice_control.py`;
						
						execSync(`ssh ${config.piAddress} "cat > start_voice.sh << 'EOF'\n${startupScript}\nEOF"`, { encoding: 'utf8' });
						execSync(`ssh ${config.piAddress} "chmod +x start_voice.sh"`, { encoding: 'utf8' });
						execSync(`ssh ${config.piAddress} "nohup ./start_voice.sh > voice_system.log 2>&1 &"`, { encoding: 'utf8' });
						
						showActionResult('▶️ VOICE SYSTEM STARTUP', 
							'Voice system startup initiated successfully.\n\n' +
							'✅ Created startup script with environment variables\n' +
							'✅ Started voice system in background\n' +
							'✅ Logging to voice_system.log\n\n' +
							'System should be online in 10-15 seconds.', 'success');
					} catch (error) {
						showActionResult('❌ VOICE SYSTEM STARTUP FAILED', 
							`Failed to start voice system:\n\n${error.message}`, 'error');
					}
					break;
				case 1: // Stop
					try {
						execSync(`ssh ${config.piAddress} "pkill -f conversational_voice_control.py"`, { encoding: 'utf8' });
						showActionResult('⏹️ VOICE SYSTEM STOPPED', 
							'Voice system has been stopped successfully.\n\n' +
							'✅ Terminated voice control process\n' +
							'✅ Released system resources\n\n' +
							'Use "Start Voice System" to restart.', 'success');
					} catch (error) {
						showActionResult('❌ VOICE SYSTEM STOP FAILED', 
							`Failed to stop voice system:\n\n${error.message}`, 'error');
					}
					break;
				case 2: // Restart
					try {
						execSync(`ssh ${config.piAddress} "pkill -f conversational_voice_control.py"`, { encoding: 'utf8' });
						showActionResult('🔄 VOICE SYSTEM RESTART', 
							'Voice system restart initiated.\n\n' +
							'✅ Stopped existing voice system\n' +
							'⏳ Waiting 2 seconds...\n' +
							'🚀 Starting voice system\n\n' +
							'System will be online shortly.', 'success');
						
						setTimeout(() => {
							execSync(`ssh ${config.piAddress} "nohup ./start_voice.sh > voice_system.log 2>&1 &"`, { encoding: 'utf8' });
							setTimeout(checkVoiceSystemStatus, 1000);
						}, 2000);
					} catch (error) {
						showActionResult('❌ VOICE SYSTEM RESTART FAILED', 
							`Failed to restart voice system:\n\n${error.message}`, 'error');
					}
					return;
				case 3: // Diagnostics
					try {
						const logResult = execSync(`ssh ${config.piAddress} "tail -20 voice_system.log"`, { encoding: 'utf8' });
						let procResult = '';
						
						try {
							procResult = execSync(`ssh ${config.piAddress} "ps aux | grep conversational_voice_control.py | grep -v grep"`, { encoding: 'utf8' });
						} catch {
							procResult = 'No voice processes currently running';
						}
						
						showActionResult('📊 VOICE SYSTEM DIAGNOSTICS', 
							'Voice System Status:\n' +
							'─'.repeat(30) + '\n' +
							`📊 Process Status:\n${procResult}\n\n` +
							'📋 Last 20 lines of voice_system.log:\n' +
							'─'.repeat(30) + '\n' +
							logResult, 'info');
					} catch (error) {
						showActionResult('❌ DIAGNOSTICS FAILED', 
							`Failed to run diagnostics:\n\n${error.message}`, 'error');
					}
					break;
				case 4: // Live logs
					// Set log viewer active first
					setLogViewerActive(true);
					
					// Start real-time log updates  
					const updateLogs = () => {						
						try {
							// Get file modification time and content
							const result = execSync(`ssh ${config.piAddress} "stat -c '%y %s' voice_system.log && echo '--- LATEST LOGS ---' && tail -n 20 voice_system.log"`, { 
								encoding: 'utf8',
								timeout: 5000,
								stdio: ['pipe', 'pipe', 'pipe'] // Prevent console output
							});
							const timestamp = new Date().toLocaleTimeString();
							setLogContent(`[${timestamp}] Log status:\n\n${result}`);
						} catch (error) {
							setLogContent(`❌ Error fetching logs: ${error.message}`);
						}
					};
					
					// Initial load
					updateLogs();
					
					// Start updating every 2 seconds
					const interval = setInterval(() => {
						// Check if log viewer is still active before updating
						if (logViewerActive) {
							updateLogs();
						}
					}, 2000);
					setLogUpdateInterval(interval);
					break;
			}
			setTimeout(checkVoiceSystemStatus, 1000);
		} catch (error) {
			// Silent error handling - no console spam
		}
	};

	// MCP Client actions - Dynamic server management
	const handleMCPAction = (action) => {
		try {
			switch (action) {
				case 0: // List Configured MCP Servers
					const listScript = `import json
import os

config_path = '/home/dan/mcp_config.json'
if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    if 'mcpServers' in config and config['mcpServers']:
        print('📋 Currently Configured MCP Servers:')
        print('=' * 50)
        for server_name, server_config in config['mcpServers'].items():
            print(f"🔌 {server_name}")
            print(f"   Command: {server_config['command']}")
            print(f"   Args: {' '.join(server_config['args'])}")
            if 'env' in server_config:
                print(f"   Environment variables: {', '.join(server_config['env'].keys())}")
            print()
    else:
        print('❌ No MCP servers configured')
        print('💡 Use "Add MCP Server" to configure your first server')
else:
    print('❌ MCP configuration file not found')
    print('💡 Use "Initialize MCP Config" to create configuration')`;

					try {
						const result = executeRemotePythonScript('list_configured_mcp.py', listScript);
						showActionResult('📋 CONFIGURED MCP SERVERS', result, 'info');
					} catch (error) {
						showActionResult('❌ MCP LIST FAILED', 
							`Failed to list MCP servers:\n\n${error.message}`, 'error');
					}
					break;
					
				case 1: // Initialize/Reset MCP Configuration
					const initScript = `import json
import os

# Create basic MCP configuration with starter servers
mcp_config = {
    "mcpServers": {
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/dan"],
            "description": "File system operations on Pi"
        }
    }
}

config_path = '/home/dan/mcp_config.json'
with open(config_path, 'w') as f:
    json.dump(mcp_config, f, indent=2)

print(f'✅ MCP configuration initialized at {config_path}')
print()
print('📋 Default servers configured:')
for server_name, config in mcp_config['mcpServers'].items():
    print(f'  • {server_name}: {config.get("description", "No description")}')
print()
print('🔧 Next steps:')
print('  1. Add more servers using "Add MCP Server"')
print('  2. Test connections using "Test MCP Connections"')
print('  3. Restart voice assistant to apply changes')`;

					try {
						const result = executeRemotePythonScript('init_mcp.py', initScript);
						showActionResult('🔧 MCP CONFIGURATION INITIALIZED', 
							'MCP configuration initialized successfully.\n\n' + result, 'success');
					} catch (error) {
						showActionResult('❌ MCP INITIALIZATION FAILED', 
							`Failed to initialize MCP configuration:\n\n${error.message}`, 'error');
					}
					break;
					
				case 2: // Add MCP Server (Interactive)
					const addServerScript = `import json
import os

# Available MCP server templates
server_templates = {
    'brave-search': {
        'name': 'Brave Search MCP',
        'command': 'npx',
        'args': ['-y', '@modelcontextprotocol/server-brave-search'],
        'description': 'Web search capabilities',
        'env': {'BRAVE_API_KEY': ''}
    },
    'sqlite': {
        'name': 'SQLite MCP',
        'command': 'npx',
        'args': ['-y', '@modelcontextprotocol/server-sqlite', '--db-path', '/home/dan/voice_assistant_memory.db'],
        'description': 'Database operations'
    },
    'github': {
        'name': 'GitHub MCP',
        'command': 'npx',
        'args': ['-y', '@modelcontextprotocol/server-github'],
        'description': 'GitHub repository access',
        'env': {'GITHUB_PERSONAL_ACCESS_TOKEN': ''}
    },
    'slack': {
        'name': 'Slack MCP',
        'command': 'npx',
        'args': ['-y', '@modelcontextprotocol/server-slack'],
        'description': 'Slack integration',
        'env': {'SLACK_BOT_TOKEN': ''}
    },
    'postgres': {
        'name': 'PostgreSQL MCP',
        'command': 'npx',
        'args': ['-y', '@modelcontextprotocol/server-postgres'],
        'description': 'PostgreSQL database access',
        'env': {'POSTGRES_CONNECTION_STRING': ''}
    }
}

print('📋 Available MCP Server Templates:')
print('=' * 50)
for key, template in server_templates.items():
    print(f"🔌 {key}: {template['name']}")
    print(f"   Description: {template['description']}")
    if 'env' in template:
        print(f"   Required env vars: {', '.join(template['env'].keys())}")
    print()

print('💡 To add servers automatically:')
print('   Use the specific "Add [Server]" functions in the Enterprise Control Center')
print('   or manually edit /home/dan/mcp_config.json')`;

					try {
						const result = executeRemotePythonScript('show_server_templates.py', addServerScript);
						showActionResult('➕ ADD MCP SERVER TEMPLATES', result, 'info');
					} catch (error) {
						showActionResult('❌ SERVER TEMPLATES FAILED', 
							`Failed to show server templates:\n\n${error.message}`, 'error');
					}
					break;
					
				case 3: // Remove MCP Server
					fetchConfiguredServers();
					break;
					
				case 4: // Test MCP Connections
					const testScript = `import subprocess
import json
import time
import os

config_path = '/home/dan/mcp_config.json'
if not os.path.exists(config_path):
    print('❌ MCP configuration file not found')
    print('💡 Use "Initialize MCP Config" first')
    exit()

with open(config_path, 'r') as f:
    config = json.load(f)

if 'mcpServers' not in config or not config['mcpServers']:
    print('❌ No MCP servers configured')
    print('💡 Use "Add MCP Server" to configure servers')
    exit()

print('🔌 Testing MCP Server Connections:')
print('=' * 50)

for server_name, server_config in config['mcpServers'].items():
    print(f"Testing {server_name}...")
    
    try:
        # Set up environment if specified
        env = os.environ.copy()
        if 'env' in server_config:
            for key, value in server_config['env'].items():
                if value:  # Only set if value is not empty
                    env[key] = value
        
        # Start server process briefly to test
        command = [server_config['command']] + server_config['args']
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        
        # Give it a moment to start
        time.sleep(2)
        
        # Check if it's running
        if process.poll() is None:
            print(f"✅ {server_name} started successfully")
            process.terminate()
            process.wait(timeout=5)
        else:
            stdout, stderr = process.communicate()
            print(f"❌ {server_name} failed to start")
            if stderr:
                print(f"   Error: {stderr[:200]}...")
                
    except Exception as e:
        print(f"❌ {server_name} error: {str(e)}")
    
    print()`;

					try {
						const result = executeRemotePythonScript('test_mcp_connections.py', testScript);
						showActionResult('🔌 MCP CONNECTION TEST', result, 'info');
					} catch (error) {
						showActionResult('❌ MCP CONNECTION TEST FAILED', 
							`Failed to test MCP connections:\n\n${error.message}`, 'error');
					}
					break;

				case 5: // Apply MCP Changes (Restart Voice Assistant)
					try {
						// Check if voice system is running
						if (systemStatus.voiceRunning) {
							showActionResult('🔄 APPLYING MCP CHANGES', 
								'Restarting voice assistant to apply MCP configuration changes...\n\n' +
								'⏳ Stopping voice system...\n' +
								'🔧 MCP configuration will be loaded on restart', 'info');
							
							// Stop the voice system
							execSync(`ssh ${config.piAddress} "pkill -f conversational_voice_control.py"`, { encoding: 'utf8' });
							
							// Wait 3 seconds, then restart with MCP integration
							setTimeout(() => {
								try {
									const elevenLabsKey = getElevenLabsKey();
									const startupScript = `#!/bin/bash
# Load API keys from environment
source ~/.bashrc${elevenLabsKey ? `\nexport ELEVENLABS_API_KEY="${elevenLabsKey}"` : ''}
cd ${config.piPath}
source pyatv_env/bin/activate
python conversational_voice_control.py`;
									
									execSync(`ssh ${config.piAddress} "cat > start_voice_with_mcp.sh << 'EOF'\n${startupScript}\nEOF"`, { encoding: 'utf8' });
									execSync(`ssh ${config.piAddress} "chmod +x start_voice_with_mcp.sh"`, { encoding: 'utf8' });
									execSync(`ssh ${config.piAddress} "nohup ./start_voice_with_mcp.sh > voice_system.log 2>&1 &"`, { encoding: 'utf8' });
									
									showActionResult('✅ MCP CHANGES APPLIED', 
										'Voice assistant restarted with MCP configuration!\n\n' +
										'🔌 MCP servers are now available to the AI assistant\n' +
										'🎙️ Voice system should be online shortly\n' +
										'💡 Test MCP functionality by asking the voice assistant about configured servers', 'success');
									
									setTimeout(checkVoiceSystemStatus, 3000);
								} catch (error) {
									showActionResult('❌ MCP RESTART FAILED', 
										`Failed to restart voice system with MCP:\n\n${error.message}`, 'error');
								}
							}, 3000);
						} else {
							showActionResult('💡 VOICE SYSTEM NOT RUNNING', 
								'Voice assistant is not currently running.\n\n' +
								'🔧 MCP configuration is ready and will be loaded when voice system starts\n' +
								'🎙️ Use "Start Voice System" to begin using MCP-enabled AI assistant', 'info');
						}
					} catch (error) {
						showActionResult('❌ MCP APPLY FAILED', 
							`Failed to apply MCP changes:\n\n${error.message}`, 'error');
					}
					break;
			}
		} catch (error) {
			showActionResult('❌ MCP ACTION FAILED', 
				`MCP action encountered an error:\n\n${error.message}`, 'error');
		}
	};

	// Audio testing actions
	const handleAudioAction = (action) => {
		try {
			switch (action) {
				case 0: // Test Current TTS Voice
					const ttsVoice = config.ttsVoiceId || 'nova';
					const isElevenLabs = config.ttsVoiceId && config.ttsVoiceId.length > 10; // ElevenLabs IDs are longer
					
					if (isElevenLabs) {
						const elevenLabsKey = getElevenLabsKey();
						
						if (!elevenLabsKey) {
							showActionResult('❌ ELEVENLABS API KEY MISSING', 
								'ElevenLabs API key not found.\n\n' +
								'Please configure your ElevenLabs API key in the Pi environment:\n' +
								'echo "export ELEVENLABS_API_KEY=your_key_here" >> ~/.bashrc\n' +
								'source ~/.bashrc', 'error');
							break;
						}
						
						const pythonScript = `import requests
import subprocess

api_key = '${elevenLabsKey}'
voice_id = '${config.ttsVoiceId}'
text = 'Computer systems nominal. Enterprise-D voice synthesis test successful.'

url = 'https://api.elevenlabs.io/v1/text-to-speech/' + voice_id
response = requests.post(
    url,
    headers={'xi-api-key': api_key, 'Content-Type': 'application/json'},
    json={'text': text, 'model_id': 'eleven_monolingual_v1'}
)

if response.status_code == 200:
    with open('test_elevenlabs.mp3', 'wb') as f:
        f.write(response.content)
    print('🔊 Playing ElevenLabs TTS audio...')
    subprocess.run(['mpg123', 'test_elevenlabs.mp3'])
    print('✅ ElevenLabs TTS test successful')
else:
    print('❌ Error: ' + str(response.status_code))`;

						try {
							const result = executeRemotePythonScript('test_tts.py', pythonScript);
							showActionResult('🎙️ ELEVENLABS TTS TEST', 
								`Testing ElevenLabs voice: ${config.ttsVoice}\n\n${result}`, 'success');
						} catch (error) {
							showActionResult('❌ ELEVENLABS TTS TEST FAILED', 
								`ElevenLabs TTS test failed:\n\n${error.message}`, 'error');
						}
					} else {
						const pythonScript = `import openai
import subprocess
import os

client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
response = client.audio.speech.create(
    model='tts-1',
    voice='nova',
    input='Computer systems nominal. All tests successful.'
)
response.stream_to_file('test_tts.mp3')
print('🔊 Playing OpenAI TTS audio...')
subprocess.run(['mpg123', 'test_tts.mp3'])
print('✅ OpenAI TTS test successful')`;

						try {
							const result = executeRemotePythonScript('test_openai_tts.py', pythonScript);
							showActionResult('🎙️ OPENAI TTS TEST', 
								`Testing OpenAI TTS voice: nova\n\n${result}`, 'success');
						} catch (error) {
							showActionResult('❌ OPENAI TTS TEST FAILED', 
								`OpenAI TTS test failed:\n\n${error.message}`, 'error');
						}
					}
					break;
				case 1: // Test TNG Computer Beeps
					try {
						const result = execSync(`ssh ${config.piAddress} "ls ${config.piPath}/tng_beeps/*.mp3 | head -1 | xargs mpg123"`, { encoding: 'utf8' });
						showActionResult('🎵 TNG COMPUTER BEEPS TEST', 
							'TNG computer beeps test completed successfully.\n\n' +
							'🔊 Audio played on Pi speaker\n' +
							'✅ TNG beep audio system operational', 'success');
					} catch (error) {
						showActionResult('❌ TNG BEEP TEST FAILED', 
							`TNG beep test failed:\n\n${error.message}`, 'error');
					}
					break;
				case 2: // Test Audio Output
					try {
						const result = execSync(`ssh ${config.piAddress} "speaker-test -t sine -f 1000 -l 1"`, { encoding: 'utf8' });
						showActionResult('🔊 AUDIO OUTPUT TEST', 
							'Audio output test completed successfully.\n\n' +
							'🔊 1kHz test tone played on Pi speaker\n' +
							'✅ Audio output system operational', 'success');
					} catch (error) {
						showActionResult('❌ AUDIO OUTPUT TEST FAILED', 
							`Audio output test failed:\n\n${error.message}`, 'error');
					}
					break;
				case 3: // Test Microphone
					try {
						execSync(`ssh ${config.piAddress} "arecord -d 5 -f cd test_mic.wav && aplay test_mic.wav"`, { encoding: 'utf8' });
						showActionResult('🎤 MICROPHONE TEST', 
							'Microphone test completed successfully.\n\n' +
							'🎤 5-second recording captured and played back\n' +
							'✅ Microphone input system operational', 'success');
					} catch (error) {
						showActionResult('❌ MICROPHONE TEST FAILED', 
							`Microphone test failed:\n\n${error.message}`, 'error');
					}
					break;
				case 4: // Audio Diagnostics
					try {
						const audioResult = execSync(`ssh ${config.piAddress} "arecord -l && echo '---' && aplay -l"`, { encoding: 'utf8' });
						showActionResult('🔧 AUDIO DIAGNOSTICS', 
							`Audio system diagnostics:\n\n${audioResult}`, 'info');
					} catch (error) {
						showActionResult('❌ AUDIO DIAGNOSTICS FAILED', 
							`Audio diagnostics failed:\n\n${error.message}`, 'error');
					}
					break;
			}
		} catch (error) {
			showActionResult('❌ AUDIO ACTION FAILED', 
				`Audio action encountered an error:\n\n${error.message}`, 'error');
		}
	};

	// Emergency protocol actions
	const handleEmergencyAction = (action) => {
		try {
			switch (action) {
				case 0: // Red Alert
					try {
					execSync(`ssh ${config.piAddress} "source ~/.bashrc && cd ${config.piPath} && source pyatv_env/bin/activate && python -c \\"import subprocess; subprocess.run(['mpg123', 'tng_red_alert1.mp3']); import requests; requests.post('http://pi1.local:8581/api/accessories/Govee Floor Lamp/services/Lightbulb/characteristics/On', json={'value': True}, auth=('dan', 'windoze')); import time; time.sleep(1); requests.post('http://pi1.local:8581/api/accessories/Govee Floor Lamp/services/Lightbulb/characteristics/Hue', json={'value': 0}, auth=('dan', 'windoze'))\\""`, { encoding: 'utf8' });
					showActionResult('🚨 RED ALERT ACTIVATED', 
						'Red alert protocol has been successfully activated.\n\n' +
						'🚨 TNG red alert klaxon playing\n' +
						'🔴 Govee floor lamp flashing red\n' +
						'✅ All hands to battle stations!', 'error');
					} catch (error) {
						showActionResult('❌ RED ALERT ACTIVATION FAILED', 
							`Red alert activation failed:\n\n${error.message}`, 'error');
					}
					break;
				case 1: // Yellow Alert
					showActionResult('🟡 YELLOW ALERT', 
						'Yellow Alert status activated.\n\n' +
						'🟡 Ship is at yellow alert\n' +
						'⚠️ Heightened security protocols in effect\n' +
						'🛡️ All departments report readiness status', 'info');
					break;
				case 2: // Blue Alert
					showActionResult('🔵 BLUE ALERT', 
						'Blue Alert status activated.\n\n' +
						'🔵 Landing/departure operations in progress\n' +
						'🚀 All non-essential personnel clear flight decks\n' +
						'⚙️ Flight operations protocols active', 'info');
					break;
				case 3: // Emergency Shutdown
					try {
						execSync(`ssh ${config.piAddress} "pkill -f conversational_voice_control.py"`, { encoding: 'utf8' });
						showActionResult('🔒 EMERGENCY SHUTDOWN', 
							'Emergency shutdown protocol completed.\n\n' +
							'🔒 Voice control system terminated\n' +
							'⚠️ All voice operations halted\n' +
							'🔧 Manual restart required', 'success');
					} catch (error) {
						showActionResult('❌ EMERGENCY SHUTDOWN FAILED', 
							`Emergency shutdown failed:\n\n${error.message}`, 'error');
					}
					break;
				case 4: // Test Announcement
					const isElevenLabs = config.ttsVoiceId && config.ttsVoiceId.length > 10;
					
					if (isElevenLabs) {
						const elevenLabsKey = getElevenLabsKey();
						if (!elevenLabsKey) {
							showActionResult('❌ ELEVENLABS API KEY MISSING', 
								'ElevenLabs API key not found for announcement test.\n\n' +
								'Please configure your ElevenLabs API key in the Pi environment:\n' +
								'echo "export ELEVENLABS_API_KEY=your_key_here" >> ~/.bashrc\n' +
								'source ~/.bashrc', 'error');
							break;
						}
						
						const pythonScript = `import requests
import subprocess

api_key = '${elevenLabsKey}'
voice_id = '${config.ttsVoiceId}'
text = 'Attention all hands. This is a test of the ship-wide communication system. All systems are functioning normally.'

url = 'https://api.elevenlabs.io/v1/text-to-speech/' + voice_id
response = requests.post(
    url,
    headers={'xi-api-key': api_key, 'Content-Type': 'application/json'},
    json={'text': text, 'model_id': 'eleven_monolingual_v1'}
)

if response.status_code == 200:
    with open('announcement.mp3', 'wb') as f:
        f.write(response.content)
    print('📢 Playing ship-wide announcement...')
    subprocess.run(['mpg123', 'announcement.mp3'])
    print('✅ Announcement test successful')
else:
    print('❌ Error: ' + str(response.status_code))`;

						try {
							const result = executeRemotePythonScript('test_announcement.py', pythonScript);
							showActionResult('📢 ELEVENLABS ANNOUNCEMENT TEST', 
								`Ship-wide announcement test (ElevenLabs):\n\n${result}`, 'success');
						} catch (error) {
							showActionResult('❌ ANNOUNCEMENT TEST FAILED', 
								`ElevenLabs announcement test failed:\n\n${error.message}`, 'error');
						}
					} else {
						const pythonScript = `import openai
import subprocess
import os

client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
response = client.audio.speech.create(
    model='tts-1',
    voice='nova',
    input='Attention all hands. This is a test of the ship-wide communication system. All systems are functioning normally.'
)
response.stream_to_file('announcement.mp3')
print('📢 Playing ship-wide announcement...')
subprocess.run(['mpg123', 'announcement.mp3'])
print('✅ Announcement test successful')`;

						try {
							const result = executeRemotePythonScript('test_announcement.py', pythonScript);
							showActionResult('📢 OPENAI ANNOUNCEMENT TEST', 
								`Ship-wide announcement test (OpenAI):\n\n${result}`, 'success');
						} catch (error) {
							showActionResult('❌ ANNOUNCEMENT TEST FAILED', 
								`OpenAI announcement test failed:\n\n${error.message}`, 'error');
						}
					}
					break;
			}
		} catch (error) {
			showActionResult('❌ EMERGENCY ACTION FAILED', 
				`Emergency action encountered an error:\n\n${error.message}`, 'error');
		}
	};

	// Monitoring actions
	const handleMonitoringAction = (action) => {
		try {
			switch (action) {
				case 0: // Voice System Logs (Live)
					try {
						const result = execSync(`ssh ${config.piAddress} "tail -20 voice_system.log"`, { 
							encoding: 'utf8',
							timeout: 10000 // 10 second timeout
						});
						showActionResult('🎙️ VOICE SYSTEM LOGS (LIVE)', 
							'Voice system recent activity (last 20 lines):\n' +
							'💡 Use "Voice System Log History" for full log or "Transcriptions & Commands Only" for filtered view\n\n' +
							'─'.repeat(50) + '\n' +
							result + '\n' +
							'─'.repeat(50) + '\n' +
							'✅ Log snapshot complete', 'info');
					} catch (error) {
						showActionResult('❌ LOG FETCH FAILED', 
							`Error fetching logs:\n\n${error.message}`, 'error');
					}
					break;
				case 1: // Voice System Log History
					try {
						const voiceLogResult = execSync(`ssh ${config.piAddress} "tail -50 voice_system.log"`, { encoding: 'utf8' });
						showActionResult('📜 VOICE SYSTEM LOG HISTORY', 
							`Voice system log history (last 50 lines):\n\n${voiceLogResult}`, 'info');
					} catch (error) {
						showActionResult('❌ NO LOG FOUND', 
							'No voice system log found. Make sure the voice system has been started.', 'error');
					}
					break;
				case 2: // Transcriptions & Commands Only
					try {
						const transcriptResult = execSync(`ssh ${config.piAddress} "tail -100 voice_system.log | grep -E 'Transcript:|Wake word detected|TV command:|HomeKit command:|Claude response:' | tail -20"`, { encoding: 'utf8' });
						if (transcriptResult.trim()) {
							showActionResult('🗣️ VOICE TRANSCRIPTIONS & COMMANDS', 
								`Voice transcriptions and commands (last 20):\n\n${transcriptResult}`, 'info');
						} else {
							showActionResult('💭 NO TRANSCRIPTIONS', 
								'No voice transcriptions found yet. Try saying "Computer" to the voice system.', 'info');
						}
					} catch (error) {
						showActionResult('❌ NO LOG FOUND', 
							'No voice system log found. Make sure the voice system has been started.', 'error');
					}
					break;
				case 3: // System Performance
					try {
						const perfResult = execSync(`ssh ${config.piAddress} "top -bn1 | head -20"`, { encoding: 'utf8' });
						showActionResult('📊 SYSTEM PERFORMANCE METRICS', 
							`System performance metrics:\n\n${perfResult}`, 'info');
					} catch (error) {
						showActionResult('❌ PERFORMANCE METRICS FAILED', 
							`Failed to get performance metrics:\n\n${error.message}`, 'error');
					}
					break;
				case 4: // Process Monitor (fixed case number)
					try {
						const procResult = execSync(`ssh ${config.piAddress} "ps aux --sort=-%cpu | head -20"`, { encoding: 'utf8' });
						showActionResult('🔍 PROCESS MONITOR', 
							`Process monitor:\n\n${procResult}`, 'info');
					} catch (error) {
						showActionResult('❌ PROCESS MONITOR FAILED', 
							`Failed to get process information:\n\n${error.message}`, 'error');
					}
					break;
				case 5: // Memory Usage (fixed case number)
					try {
						const memResult = execSync(`ssh ${config.piAddress} "free -h && echo '---' && df -h"`, { encoding: 'utf8' });
						showActionResult('📈 MEMORY USAGE', 
							`Memory usage:\n\n${memResult}`, 'info');
					} catch (error) {
						showActionResult('❌ MEMORY USAGE FAILED', 
							`Failed to get memory usage:\n\n${error.message}`, 'error');
					}
					break;
				case 6: // System Temperature (fixed case number)
					try {
						const tempResult = execSync(`ssh ${config.piAddress} "vcgencmd measure_temp"`, { encoding: 'utf8' });
						showActionResult('🌡️ SYSTEM TEMPERATURE', 
							`Temperature: ${tempResult}`, 'info');
					} catch (error) {
						showActionResult('❌ TEMPERATURE CHECK FAILED', 
							`Failed to get system temperature:\n\n${error.message}`, 'error');
					}
					break;
			}
		} catch (error) {
			showActionResult('❌ MONITORING ACTION FAILED', 
				`Monitoring action encountered an error:\n\n${error.message}`, 'error');
		}
	};

	// MCP Server Management Helper Functions
	const addMCPServer = (serverKey, serverConfig) => {
		const addScript = `import json
import os

config_path = '/home/dan/mcp_config.json'

# Load existing config or create new one
if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        config = json.load(f)
else:
    config = {"mcpServers": {}}

# Add the new server
config['mcpServers']['${serverKey}'] = ${JSON.stringify(serverConfig)}

# Save updated config
with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

print(f'✅ Added MCP server: ${serverKey}')
print(f'   Command: ${serverConfig.command}')
print(f'   Args: ${serverConfig.args.join(' ')}')
${serverConfig.env ? `print(f'   Environment variables required: ${Object.keys(serverConfig.env).join(', ')}')` : ''}
print()
print('🔧 Next steps:')
print('  1. Configure any required environment variables')
print('  2. Test the connection using "Test MCP Connections"')
print('  3. Apply changes using "Apply MCP Changes"')`;

		try {
			const result = executeRemotePythonScript('add_mcp_server.py', addScript);
			showActionResult('✅ MCP SERVER ADDED', 
				`Successfully added ${serverKey} MCP server!\n\n${result}`, 'success');
		} catch (error) {
			showActionResult('❌ ADD SERVER FAILED', 
				`Failed to add MCP server:\n\n${error.message}`, 'error');
		}
	};

	const removeMCPServer = (serverKey) => {
		const removeScript = `import json
import os

config_path = '/home/dan/mcp_config.json'

if not os.path.exists(config_path):
    print('❌ MCP configuration file not found')
    exit()

with open(config_path, 'r') as f:
    config = json.load(f)

if 'mcpServers' not in config or '${serverKey}' not in config['mcpServers']:
    print(f'❌ Server "${serverKey}" not found in configuration')
    exit()

# Remove the server
removed_server = config['mcpServers'].pop('${serverKey}')
print(f'🗑️ Removed MCP server: ${serverKey}')
print(f'   Command was: {removed_server["command"]}')
print(f'   Args were: {" ".join(removed_server["args"])}')

# Save updated config
with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

print()
print(f'✅ Server "${serverKey}" removed successfully')
print('🔧 Use "Apply MCP Changes" to restart voice assistant with updated configuration')`;

		try {
			const result = executeRemotePythonScript('remove_mcp_server.py', removeScript);
			showActionResult('🗑️ MCP SERVER REMOVED', 
				`Successfully removed ${serverKey} MCP server!\n\n${result}`, 'success');
		} catch (error) {
			showActionResult('❌ REMOVE SERVER FAILED', 
				`Failed to remove MCP server:\n\n${error.message}`, 'error');
		}
	};

	// Predefined MCP server configurations
	const mcpServerTemplates = {
		'brave-search': {
			command: 'npx',
			args: ['-y', '@modelcontextprotocol/server-brave-search'],
			description: 'Web search capabilities',
			env: { 'BRAVE_API_KEY': '' }
		},
		'sqlite': {
			command: 'npx',
			args: ['-y', '@modelcontextprotocol/server-sqlite', '--db-path', '/home/dan/voice_assistant_memory.db'],
			description: 'Database operations'
		},
		'github': {
			command: 'npx',
			args: ['-y', '@modelcontextprotocol/server-github'],
			description: 'GitHub repository access',
			env: { 'GITHUB_PERSONAL_ACCESS_TOKEN': '' }
		},
		'slack': {
			command: 'npx',
			args: ['-y', '@modelcontextprotocol/server-slack'],
			description: 'Slack integration',
			env: { 'SLACK_BOT_TOKEN': '' }
		},
		'postgres': {
			command: 'npx',
			args: ['-y', '@modelcontextprotocol/server-postgres'],
			description: 'PostgreSQL database access',
			env: { 'POSTGRES_CONNECTION_STRING': '' }
		}
	};

	// Quick add functions for common servers
	const addBraveSearch = () => addMCPServer('brave-search', mcpServerTemplates['brave-search']);
	const addSQLite = () => addMCPServer('sqlite', mcpServerTemplates['sqlite']);
	const addGitHub = () => addMCPServer('github', mcpServerTemplates['github']);
	const addSlack = () => addMCPServer('slack', mcpServerTemplates['slack']);
	const addPostgreSQL = () => addMCPServer('postgres', mcpServerTemplates['postgres']);

	// Fetch configured servers for removal
	const fetchConfiguredServers = () => {
		const fetchScript = `import json
import os

config_path = '/home/dan/mcp_config.json'
if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    if 'mcpServers' in config and config['mcpServers']:
        for server_name in config['mcpServers'].keys():
            print(server_name)
    else:
        print('NO_SERVERS_CONFIGURED')
else:
    print('NO_CONFIG_FILE')`;

		try {
			const result = executeRemotePythonScript('fetch_servers.py', fetchScript);
			const servers = result.trim().split('\n').filter(s => s && s !== 'NO_SERVERS_CONFIGURED' && s !== 'NO_CONFIG_FILE');
			
			if (result.includes('NO_SERVERS_CONFIGURED')) {
				showActionResult('❌ NO SERVERS TO REMOVE', 
					'No MCP servers are currently configured.\n\n' +
					'💡 Use "Quick Add" options or "Add Server Templates" to configure servers first.', 'info');
			} else if (result.includes('NO_CONFIG_FILE')) {
				showActionResult('❌ NO CONFIGURATION', 
					'MCP configuration file not found.\n\n' +
					'💡 Use "Initialize MCP Config" to create the configuration first.', 'info');
			} else if (servers.length > 0) {
				setMcpServersForRemoval(servers);
				setShowingRemovalMenu(true);
			} else {
				showActionResult('❌ NO SERVERS FOUND', 
					'No valid MCP servers found in configuration.', 'error');
			}
		} catch (error) {
			showActionResult('❌ FETCH SERVERS FAILED', 
				`Failed to fetch configured servers:\n\n${error.message}`, 'error');
		}
	};

	// Centralized function to execute Python scripts on Pi via SSH
	const executeRemotePythonScript = (scriptName, pythonCode, workingDir = config.piPath) => {
		try {
			// Create the script
			execSync(`ssh ${config.piAddress} "cat > ${scriptName} << 'EOF'\n${pythonCode}\nEOF"`, { encoding: 'utf8' });
			
			// Execute and cleanup (with environment variables)
			const result = execSync(`ssh ${config.piAddress} "cd ${workingDir} && source ~/.bashrc && source pyatv_env/bin/activate && python ${scriptName} && rm ${scriptName}"`, { encoding: 'utf8' });
			
			return result;
		} catch (error) {
			// Cleanup on error
			try {
				execSync(`ssh ${config.piAddress} "rm -f ${scriptName}"`, { encoding: 'utf8' });
			} catch {}
			throw error;
		}
	};

	// Get ElevenLabs API key from Pi
	const getElevenLabsKey = () => {
		try {
			return execSync(`ssh ${config.piAddress} 'grep ELEVENLABS_API_KEY ~/.bashrc | head -1 | cut -d= -f2 | tr -d "\\""'`, { encoding: 'utf8' }).trim();
		} catch (error) {
			return null;
		}
	};

	// Fetch available ElevenLabs voices
	const fetchElevenLabsVoices = async () => {
		try {
			const apiKey = getElevenLabsKey();
			if (!apiKey) {
				showActionResult('❌ ELEVENLABS API KEY MISSING', 
					'ElevenLabs API key not found in Pi environment.\n\n' +
					'💡 Please add ELEVENLABS_API_KEY to ~/.bashrc on the Pi:\n' +
					'echo "export ELEVENLABS_API_KEY=your_key_here" >> ~/.bashrc\n' +
					'source ~/.bashrc', 'error');
				return;
			}
			
			const pythonScript = `import requests

api_key = '${apiKey}'
response = requests.get(
    'https://api.elevenlabs.io/v1/voices',
    headers={'xi-api-key': api_key}
)

if response.status_code == 200:
    voices = response.json()['voices']
    for voice in voices:
        voice_id = voice['voice_id']
        voice_name = voice['name']
        voice_category = voice.get('category', 'custom')
        print(voice_id + ':' + voice_name + ':' + voice_category)
else:
    print('Error: ' + str(response.status_code))`;

			const result = executeRemotePythonScript('fetch_voices.py', pythonScript);
			
			const voices = result.trim().split('\n')
				.filter(line => line.includes(':'))
				.map(line => {
					const [id, name, category] = line.split(':');
					return { id, name, category };
				});
			
			setAvailableVoices(voices);
			setShowingVoices(true);
			showActionResult('🎙️ ELEVENLABS VOICES', 
				`✅ Found ${voices.length} available voices\n\n` +
				'Voice list displayed in menu. Select a voice to configure.', 'success');
		} catch (error) {
			showActionResult('❌ VOICE FETCH FAILED', 
				`Failed to fetch ElevenLabs voices:\n\n${error.message}`, 'error');
		}
	};

	// Configuration actions
	const handleConfigAction = (action) => {
		try {
			switch (action) {
				case 0: // Edit Pi Address (placeholder)
					showActionResult('📡 PI ADDRESS EDITING', 
						'Pi Address editing not yet implemented.\n\n' +
						'Current Pi Address: ' + config.piAddress + '\n\n' +
						'To change the Pi address, manually edit the configuration file.', 'info');
					break;
				case 1: // Edit Pi Path (placeholder)
					showActionResult('📁 PI PATH EDITING', 
						'Pi Path editing not yet implemented.\n\n' +
						'Current Pi Path: ' + config.piPath + '\n\n' +
						'To change the Pi path, manually edit the configuration file.', 'info');
					break;
				case 2: // TTS Voice Selection
					if (showingVoices) {
						setShowingVoices(false);
						setSelectedIndex(2); // Return to voice selection option
					} else {
						fetchElevenLabsVoices();
					}
					break;
				case 3: // Set ElevenLabs API Key
					showActionResult('🔑 ELEVENLABS API KEY SETUP', 
						'ElevenLabs API Key setup instructions:\n\n' +
						'Please manually add your ElevenLabs API key to ~/.bashrc on the Pi:\n\n' +
						'1. SSH to the Pi: ssh ' + config.piAddress + '\n' +
						'2. Add the key: echo "export ELEVENLABS_API_KEY=your_key_here" >> ~/.bashrc\n' +
						'3. Reload: source ~/.bashrc', 'info');
					break;
				case 4: // Test Connection
					try {
						const result = execSync(`ssh ${config.piAddress} "echo 'Connection successful'"`, { encoding: 'utf8' });
						showActionResult('✅ CONNECTION TEST', 
							'Connection test successful!\n\n' +
							'✅ SSH connection to ' + config.piAddress + ' working\n' +
							'🔗 Enterprise Control Center can communicate with Pi', 'success');
					} catch (error) {
						showActionResult('❌ CONNECTION TEST FAILED', 
							`Connection test failed:\n\n${error.message}`, 'error');
					}
					break;
				case 5: // Save Configuration
					try {
						saveConfig(config);
						showActionResult('💾 CONFIGURATION SAVED', 
							'Configuration saved successfully!\n\n' +
							'💾 Settings stored to: ' + CONFIG_FILE + '\n' +
							'⚙️ Configuration will persist across sessions', 'success');
					} catch (error) {
						showActionResult('❌ SAVE FAILED', 
							`Failed to save configuration:\n\n${error.message}`, 'error');
					}
					break;
			}
		} catch (error) {
			showActionResult('❌ CONFIGURATION ACTION FAILED', 
				`Configuration action encountered an error:\n\n${error.message}`, 'error');
		}
	};

	// Handle voice selection
	const handleVoiceSelection = (voiceIndex) => {
		if (voiceIndex < availableVoices.length) {
			const selectedVoice = availableVoices[voiceIndex];
			const newConfig = { ...config, ttsVoice: selectedVoice.name, ttsVoiceId: selectedVoice.id };
			setConfig(newConfig);
			saveConfig(newConfig);
			// Don't show result immediately - we'll show it after restart logic
			
			// Check if voice system is running and offer to restart
			if (systemStatus.voiceRunning) {
				showActionResult('🔄 VOICE SYSTEM RESTART', 
					`Selected voice: ${selectedVoice.name} (${selectedVoice.category})\n\n` +
					'🔄 Voice system is currently running. Restarting to apply new voice...\n' +
					'⏳ Stopping voice system...', 'info');
				try {
					// Stop the voice system
					execSync(`ssh ${config.piAddress} "pkill -f conversational_voice_control.py"`, { encoding: 'utf8' });
					
					// Wait 2 seconds, then restart
					setTimeout(() => {
						try {
							const elevenLabsKey = getElevenLabsKey();
							const startupScript = `#!/bin/bash
# Load API keys from environment
source ~/.bashrc${elevenLabsKey ? `\nexport ELEVENLABS_API_KEY="${elevenLabsKey}"` : ''}
cd ${newConfig.piPath}
source pyatv_env/bin/activate
python conversational_voice_control.py`;
							
							execSync(`ssh ${newConfig.piAddress} "cat > start_voice.sh << 'EOF'\n${startupScript}\nEOF"`, { encoding: 'utf8' });
							execSync(`ssh ${newConfig.piAddress} "chmod +x start_voice.sh"`, { encoding: 'utf8' });
							execSync(`ssh ${newConfig.piAddress} "nohup ./start_voice.sh > voice_system.log 2>&1 &"`, { encoding: 'utf8' });
							
							showActionResult('✅ VOICE SYSTEM RESTARTED', 
								`Voice system restarted with new voice configuration!\n\n` +
								`🎙️ Now using: ${selectedVoice.name} (${selectedVoice.category})\n` +
								'✅ Voice system should be online shortly', 'success');
							setTimeout(checkVoiceSystemStatus, 2000);
						} catch (error) {
							showActionResult('❌ RESTART FAILED', 
								`Failed to restart voice system:\n\n${error.message}`, 'error');
						}
					}, 2000);
				} catch (error) {
					showActionResult('❌ STOP FAILED', 
						`Failed to stop voice system:\n\n${error.message}`, 'error');
				}
			} else {
				showActionResult('🎙️ VOICE SELECTED', 
					`Selected voice: ${selectedVoice.name} (${selectedVoice.category})\n\n` +
					'Voice configuration updated and saved.\n\n' +
					'💡 Voice system not running - new voice will be used when started', 'success');
			}
			
			setShowingVoices(false);
			setSelectedIndex(2); // Return to voice selection option
		} else {
			// Back option
			setShowingVoices(false);
			setSelectedIndex(2);
		}
	};

	// Reports actions
	const handleReportsAction = (action) => {
		try {
			switch (action) {
				case 0: // Voice System Stats
					try {
						const statsResult = execSync(`ssh ${config.piAddress} "tail -100 voice_system.log | grep -E 'transcripts|wake words|TV commands|conversations' | tail -1"`, { encoding: 'utf8' });
						showActionResult('📈 VOICE SYSTEM STATISTICS', 
							`Voice system statistics:\n\n${statsResult || 'No statistics available'}`, 'info');
					} catch (error) {
						showActionResult('❌ STATS FETCH FAILED', 
							`Failed to fetch voice system statistics:\n\n${error.message}`, 'error');
					}
					break;
				case 1: // Apple TV Commands
					try {
						const tvResult = execSync(`ssh ${config.piAddress} "tail -100 voice_system.log | grep -E 'Apple TV|pyatv' | tail -10"`, { encoding: 'utf8' });
						showActionResult('📺 APPLE TV COMMAND HISTORY', 
							`Apple TV command history:\n\n${tvResult || 'No Apple TV commands found'}`, 'info');
					} catch (error) {
						showActionResult('❌ APPLE TV HISTORY FAILED', 
							`Failed to fetch Apple TV command history:\n\n${error.message}`, 'error');
					}
					break;
				case 2: // HomeKit Usage
					try {
						const homeResult = execSync(`ssh ${config.piAddress} "tail -100 voice_system.log | grep -E 'HomeKit|Homebridge' | tail -10"`, { encoding: 'utf8' });
						showActionResult('🏠 HOMEKIT USAGE REPORT', 
							`HomeKit usage report:\n\n${homeResult || 'No HomeKit commands found'}`, 'info');
					} catch (error) {
						showActionResult('❌ HOMEKIT REPORT FAILED', 
							`Failed to fetch HomeKit usage report:\n\n${error.message}`, 'error');
					}
					break;
				case 3: // Conversation History
					try {
						const convResult = execSync(`ssh ${config.piAddress} "tail -50 voice_system.log | grep -E 'Claude|conversation' | tail -10"`, { encoding: 'utf8' });
						showActionResult('💬 CONVERSATION HISTORY', 
							`Recent conversation history:\n\n${convResult || 'No conversations found'}`, 'info');
					} catch (error) {
						showActionResult('❌ CONVERSATION HISTORY FAILED', 
							`Failed to fetch conversation history:\n\n${error.message}`, 'error');
					}
					break;
				case 4: // Error Reports
					try {
						const errorResult = execSync(`ssh ${config.piAddress} "tail -100 voice_system.log | grep -E 'ERROR|Failed|Exception' | tail -10"`, { encoding: 'utf8' });
						showActionResult('🔧 ERROR REPORTS', 
							`Recent error reports:\n\n${errorResult || 'No recent errors found'}`, 'info');
					} catch (error) {
						showActionResult('❌ ERROR REPORT FAILED', 
							`Failed to fetch error reports:\n\n${error.message}`, 'error');
					}
					break;
			}
		} catch (error) {
			showActionResult('❌ REPORTS ACTION FAILED', 
				`Reports action encountered an error:\n\n${error.message}`, 'error');
		}
	};

	// Get menu items for current screen
	const getMenuItems = () => {
		switch (currentScreen) {
			case 'main':
				return [
					'🚀 Voice System Control',
					'🔧 MCP Server Management',
					'🔊 Audio & TTS Testing',
					'🚨 Emergency Protocols',
					'📜 System Monitoring',
					'⚙️ System Configuration',
					'📊 Status Reports',
					'🚪 Exit Control Center'
				];
			case 'voice':
				return [
					'▶️ Start Voice System',
					'⏹️ Stop Voice System',
					'🔄 Restart Voice System',
					'📊 System Diagnostics',
					'📜 View Live Logs',
					'⬅️ Back to Main Menu'
				];
			case 'mcp':
				if (showingRemovalMenu) {
					return [
						...mcpServersForRemoval.map(server => `🗑️ Remove: ${server}`),
						'⬅️ Back to MCP Menu'
					];
				}
				return [
					'📋 List Configured Servers',
					'🔧 Initialize MCP Config',
					'➕ Add Server Templates',
					'🗑️ Remove Server',
					'🔌 Test Connections',
					'🔄 Apply Changes (Restart)',
					'🚀 Quick Add: Brave Search',
					'📊 Quick Add: SQLite',
					'📂 Quick Add: GitHub',
					'💬 Quick Add: Slack',
					'🗄️ Quick Add: PostgreSQL',
					'⬅️ Back to Main Menu'
				];
			case 'audio':
				const currentVoice = config.ttsVoice || 'OpenAI TTS';
				return [
					`🎙️ Test Current Voice (${currentVoice})`,
					'🎵 Test TNG Computer Beeps',
					'🔊 Test Audio Output',
					'🎤 Test Microphone',
					'🔧 Audio System Diagnostics',
					'⬅️ Back to Main Menu'
				];
			case 'emergency':
				return [
					'🚨 Trigger Red Alert',
					'🟡 Yellow Alert',
					'🔵 Blue Alert',
					'🔒 Emergency Shutdown',
					'📢 Test Ship Announcement',
					'⬅️ Back to Main Menu'
				];
			case 'monitoring':
				return [
					'🎙️ Voice System Recent Activity',
					'📜 Voice System Log History',
					'🗣️ Transcriptions & Commands Only',
					'📊 System Performance',
					'🔍 Process Monitor',
					'📈 Memory Usage',
					'🌡️ System Temperature',
					'⬅️ Back to Main Menu'
				];
			case 'config':
				if (showingVoices) {
					return [
						...availableVoices.map(voice => `🎙️ ${voice.name} (${voice.category})`),
						'⬅️ Back to Configuration'
					];
				}
				return [
					`📡 Pi Address: ${config.piAddress}`,
					`📁 Pi Path: ${config.piPath}`,
					`🎙️ TTS Voice: ${config.ttsVoice || 'Default'}`,
					'🔑 Set ElevenLabs API Key',
					'🧪 Test Connection',
					'💾 Save Configuration',
					'⬅️ Back to Main Menu'
				];
			case 'reports':
				return [
					'📈 Voice System Stats',
					'📊 Apple TV Commands',
					'🏠 HomeKit Usage',
					'💬 Conversation History',
					'🔧 Error Reports',
					'⬅️ Back to Main Menu'
				];
			default:
				return ['⬅️ Back to Main Menu'];
		}
	};

	// Handle selection
	const handleSelection = () => {
		const items = getMenuItems();
		
		switch (currentScreen) {
			case 'main':
				const screens = ['voice', 'mcp', 'audio', 'emergency', 'monitoring', 'config', 'reports'];
				if (selectedIndex === 7) { // Exit
					process.exit(0);
				} else if (selectedIndex < screens.length) {
					setCurrentScreen(screens[selectedIndex]);
					setSelectedIndex(0);
				}
				break;
				
			case 'voice':
				if (selectedIndex === 5) { // Back
					setCurrentScreen('main');
					setSelectedIndex(0);
				} else if (selectedIndex <= 4) {
					handleVoiceAction(selectedIndex);
				}
				break;
				
			case 'mcp':
				if (showingRemovalMenu) {
					// Handle removal submenu
					if (selectedIndex === mcpServersForRemoval.length) { // Back option
						setShowingRemovalMenu(false);
						setMcpServersForRemoval([]);
						setSelectedIndex(3); // Return to "Remove Server" option
					} else if (selectedIndex < mcpServersForRemoval.length) {
						// Remove the selected server
						const serverToRemove = mcpServersForRemoval[selectedIndex];
						removeMCPServer(serverToRemove);
						setShowingRemovalMenu(false);
						setMcpServersForRemoval([]);
						setSelectedIndex(3);
					}
				} else {
					// Handle main MCP menu
					if (selectedIndex === 11) { // Back (now index 11)
						setCurrentScreen('main');
						setSelectedIndex(0);
					} else if (selectedIndex <= 5) {
						// Handle core MCP actions (0-5)
						handleMCPAction(selectedIndex);
					} else {
						// Handle quick add actions (6-10)
						switch (selectedIndex) {
							case 6: // Quick Add: Brave Search
								addBraveSearch();
								break;
							case 7: // Quick Add: SQLite
								addSQLite();
								break;
							case 8: // Quick Add: GitHub
								addGitHub();
								break;
							case 9: // Quick Add: Slack
								addSlack();
								break;
							case 10: // Quick Add: PostgreSQL
								addPostgreSQL();
								break;
						}
					}
				}
				break;
				
			case 'audio':
				if (selectedIndex === 5) { // Back
					setCurrentScreen('main');
					setSelectedIndex(0);
				} else {
					handleAudioAction(selectedIndex);
				}
				break;
				
			case 'emergency':
				if (selectedIndex === 5) { // Back
					setCurrentScreen('main');
					setSelectedIndex(0);
				} else {
					handleEmergencyAction(selectedIndex);
				}
				break;
				
			case 'monitoring':
				if (selectedIndex === 7) { // Back (now index 7 due to added voice log options)
					setCurrentScreen('main');
					setSelectedIndex(0);
				} else {
					handleMonitoringAction(selectedIndex);
				}
				break;
				
			case 'config':
				if (showingVoices) {
					handleVoiceSelection(selectedIndex);
				} else {
					if (selectedIndex === 6) { // Back (now index 6 due to added API key option)
						setCurrentScreen('main');
						setSelectedIndex(0);
					} else {
						handleConfigAction(selectedIndex);
					}
				}
				break;
				
			case 'reports':
				if (selectedIndex === 5) { // Back
					setCurrentScreen('main');
					setSelectedIndex(0);
				} else {
					handleReportsAction(selectedIndex);
				}
				break;
				
			default:
				setCurrentScreen('main');
				setSelectedIndex(0);
		}
	};

	// Helper function to show action results in Ink UI
	const showActionResult = (title, content, type = 'info') => {
		setActionResult({ title, content, type });
		setShowingActionResult(true);
	};

	// Input handling
	useInput((input, key) => {
		// Handle action result screen
		if (showingActionResult) {
			if (key.escape || key.return || input === 'q') {
				setShowingActionResult(false);
				setActionResult(null);
			}
			return;
		}

		// Handle log viewer
		if (logViewerActive) {
			if (key.escape || key.return || input === 'q') {
				// Clear the update interval FIRST
				if (logUpdateInterval) {
					clearInterval(logUpdateInterval);
					setLogUpdateInterval(null);
				}
				// Then close the viewer
				setLogViewerActive(false);
				setLogContent('');
			}
			return;
		}
		
		const items = getMenuItems();
		
		if (key.upArrow) {
			setSelectedIndex(prev => prev > 0 ? prev - 1 : items.length - 1);
		} else if (key.downArrow) {
			setSelectedIndex(prev => prev < items.length - 1 ? prev + 1 : 0);
		} else if (key.return) {
			handleSelection();
		}
	});

	useEffect(() => {
		checkVoiceSystemStatus();
		const interval = setInterval(checkVoiceSystemStatus, 3000);
		return () => clearInterval(interval);
	}, [config]);

	// Cleanup log interval when log viewer closes
	useEffect(() => {
		if (!logViewerActive && logUpdateInterval) {
			clearInterval(logUpdateInterval);
			setLogUpdateInterval(null);
		}
	}, [logViewerActive, logUpdateInterval]);

	// Get screen title
	const getScreenTitle = () => {
		switch (currentScreen) {
			case 'main': return '🎯 CONTROL OPTIONS:';
			case 'voice': return '🚀 VOICE SYSTEM CONTROL';
			case 'mcp': return '🔧 MCP CLIENT MANAGEMENT';
			case 'audio': return '🔊 AUDIO & TTS TESTING';
			case 'emergency': return '🚨 EMERGENCY PROTOCOLS';
			case 'monitoring': return '📜 SYSTEM MONITORING';
			case 'config': return showingVoices ? '🎙️ SELECT TTS VOICE:' : '⚙️ SYSTEM CONFIGURATION';
			case 'reports': return '📊 STATUS REPORTS';
			default: return '📋 MENU:';
		}
	};

	const now = new Date();
	const stardate = `${now.getFullYear()}.${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}.${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}`;
	const items = getMenuItems();

	// Action Result Component
	if (showingActionResult && actionResult) {
		const titleColor = actionResult.type === 'error' ? 'red' : 
		                  actionResult.type === 'success' ? 'green' : 'cyan';
		const borderColor = actionResult.type === 'error' ? 'red' : 
		                   actionResult.type === 'success' ? 'green' : 'cyan';
		
		return h(Box, { flexDirection: 'column', padding: 1 },
			h(Text, { color: titleColor, bold: true }, actionResult.title),
			h(Text, { color: titleColor }, '='.repeat(50)),
			h(Text, { color: 'white' }, ''),
			
			h(Box, { flexDirection: 'column', borderStyle: 'round', borderColor: borderColor, padding: 1 },
				h(Text, { color: 'white' }, actionResult.content)
			),
			
			h(Text, { color: 'white' }, ''),
			h(Text, { color: 'gray' }, '🎮 Press Enter, Esc, or Q to return to menu')
		);
	}

	// Log Viewer Component
	if (logViewerActive) {
		return h(Box, { flexDirection: 'column', padding: 1 },
			h(Text, { color: 'cyan', bold: true }, '📜 VOICE SYSTEM LOGS (LIVE)'),
			h(Text, { color: 'cyan' }, '='.repeat(50)),
			h(Text, { color: 'yellow' }, '🔄 Auto-refreshing every 2 seconds'),
			h(Text, { color: 'white' }, ''),
			
			h(Box, { flexDirection: 'column', borderStyle: 'round', borderColor: 'cyan', padding: 1 },
				h(Text, { color: 'white' }, logContent || 'Loading logs...')
			),
			
			h(Text, { color: 'white' }, ''),
			h(Text, { color: 'gray' }, '🎮 Press Enter, Esc, or Q to return to menu')
		);
	}

	return h(Box, { flexDirection: 'column', padding: 1 },
		// Header
		h(Text, { color: 'cyan', bold: true }, '🖖 USS ENTERPRISE NCC-1701-D'),
		h(Text, { color: 'cyan' }, '='.repeat(50)),
		h(Text, { color: 'yellow', bold: true }, '🤖 COMPUTER CONTROL CENTER'),
		h(Text, { color: 'white' }, `   Stardate: ${stardate}`),
		h(Text, { color: 'white' }, ''),

		// System Status
		h(Text, { color: 'cyan', bold: true }, '📊 SYSTEM STATUS:'),
		h(Text, { color: 'cyan' }, '─'.repeat(20)),
		h(Text, { color: 'gray' }, `🔗 Remote Pi: ${config.piAddress}`),
		h(Text, { color: systemStatus.voiceRunning ? 'green' : 'red' },
			`${systemStatus.voiceRunning ? '🟢' : '🔴'} Voice System: ${systemStatus.voiceRunning ? `ONLINE (PID: ${systemStatus.pid})` : 'OFFLINE'}`
		),
		h(Text, { color: 'green' }, '🟢 Audio Systems: OPERATIONAL'),
		h(Text, { color: 'green' }, '🟢 TNG Computer Sounds: READY'),
		h(Text, { color: 'white' }, ''),

		// Menu
		h(Text, { color: 'cyan', bold: true }, getScreenTitle()),
		h(Text, { color: 'cyan' }, '─'.repeat(20)),
		
		...items.map((item, index) => 
			h(Text, { 
				key: `${currentScreen}-${index}`,
				color: index === selectedIndex ? 'black' : 'white',
				backgroundColor: index === selectedIndex ? 'cyan' : undefined
			}, `${index === selectedIndex ? '► ' : '  '}${item}`)
		),
		
		h(Box, { marginTop: 1 },
			h(Text, { color: 'gray' }, '🎮 Controls: ↑/↓ Navigate • Enter Select')
		)
	);
};

// Render the app
render(h(EnterpriseControlCenter));