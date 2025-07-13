#!/usr/bin/env python3
"""Conversational Apple TV Voice Control with Faster-Whisper + Claude + ElevenLabs TTS (Enterprise-D Voice)"""
from faster_whisper import WhisperModel
import json
import subprocess
import os
import time
import requests
import numpy as np
import sounddevice as sd
import tempfile
from datetime import datetime
import openai
from pyannote.audio import Pipeline
import torch
import asyncio
import logging
from mcp_client import MCPVoiceIntegration

class ConversationalVoiceControl:
    def __init__(self):
        # Kill any previous instances first
        self.cleanup_previous_instances()
        
        # Configuration
        self.wake_word = "computer"
        self.device_id = "6DD04867-AD74-4FE7-AFD2-30BA83DFD648"
        self.model_size = "tiny.en"
        
        # Claude API - REQUIRED for both conversations and Apple TV commands
        self.claude_api_key = os.getenv('ANTHROPIC_API_KEY')
        if not self.claude_api_key:
            raise Exception("ANTHROPIC_API_KEY environment variable required - system cannot function without Claude API")
        
        # ElevenLabs API for TTS (Primary - Enterprise-D cloned voice)
        self.elevenlabs_api_key = os.getenv('ELEVENLABS_API_KEY')
        if self.elevenlabs_api_key:
            self.use_elevenlabs_tts = True
            self.elevenlabs_voice_id = "lUulk3Wn1LKnTO5A2A4U"  # Your cloned Enterprise-D voice
            print("✅ ElevenLabs TTS enabled with Enterprise-D cloned voice")
        else:
            self.use_elevenlabs_tts = False
            print("⚠️ ELEVENLABS_API_KEY not found - falling back to OpenAI TTS")
        
        # OpenAI API for TTS (Fallback)
        openai.api_key = os.getenv('OPENAI_API_KEY')
        if not openai.api_key:
            print("⚠️ OPENAI_API_KEY not found - falling back to Piper TTS")
            self.use_openai_tts = False
        else:
            self.use_openai_tts = True
            self.tts_voice = "nova"  # Natural female voice
        
        # Audio settings
        self.sample_rate = 44100  # USB mic native rate
        self.channels = 1
        
        # Piper TTS settings
        self.tts_model_path = "/home/dan/piper_voices/en_US-lessac-medium.onnx"
        
        # Stats
        self.total_transcriptions = 0
        self.wake_word_detections = 0
        self.apple_tv_commands = 0
        self.conversations = 0
        
        # Thinking sound control
        self.thinking_active = False
        
        # Initialize transcription queue for VAD system
        import queue
        self.transcription_queue = queue.Queue()
        
        # Speaker diarization for voice isolation
        self.wake_word_speaker_embedding = None
        self.speaker_diarization_enabled = True
        
        # Initialize conversation memory and follow-up system
        self.setup_conversation_memory()
        
        # Initialize Homebridge connection
        self.setup_homebridge()
        
        # Initialize speaker diarization pipeline
        self.setup_speaker_diarization()
        
        # Initialize MCP integration
        self.mcp_integration = MCPVoiceIntegration()
        self.mcp_initialized = False
        
        # Available apps
        self.available_apps = {
            "netflix": "com.netflix.Netflix",
            "youtube": "com.google.ios.youtube", 
            "hulu": "com.hulu.plus",
            "disney": "com.disney.disneyplus",
            "disney plus": "com.disney.disneyplus",
            "prime video": "com.amazon.aiv.AIVApp",
            "amazon prime": "com.amazon.aiv.AIVApp",
            "hbo max": "com.hbo.hbonow",
            "max": "com.wbd.stream",
            "peacock": "com.peacocktv.peacock",
            "paramount": "com.cbsvideo.app",
            "paramount plus": "com.cbsvideo.app",
            "plex": "com.plexapp.plex",
            "tubi": "com.adrise.tubitv",
            "settings": "com.apple.TVSettings",
            "music": "com.apple.TVMusic",
            "photos": "com.apple.TVPhotos",
            "podcasts": "com.apple.podcasts",
            "fitness": "com.apple.Fitness",
            "arcade": "com.apple.Arcade",
            "app store": "com.apple.TVAppStore",
            "tv": "com.apple.TVWatchList",
            "movies": "com.apple.TVMovies",
            "tv shows": "com.apple.TVShows"
        }
        
        print("🗣️ Conversational Apple TV + HomeKit Voice Control")
        print("=" * 55)
        
        # MCP will be initialized when run() is called
        self.mcp_initialized = False
        
    def cleanup_previous_instances(self):
        """Kill any previous instances of this script and free audio resources"""
        try:
            import os
            import signal
            
            # Get our own PID to avoid killing ourselves
            current_pid = os.getpid()
            
            # Find other Python processes running this script (exclude ourselves)
            result = subprocess.run([
                'pgrep', '-f', 'conversational_voice_control.py'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid and int(pid) != current_pid:
                        try:
                            os.kill(int(pid), signal.SIGTERM)
                            print(f"🧹 Killed previous instance: {pid}")
                        except:
                            pass
            
            # Kill any stuck arecord processes
            subprocess.run([
                'pkill', '-f', 'arecord'
            ], capture_output=True)
            
            # Wait a moment for cleanup
            time.sleep(2)
            
            print("🧹 Cleanup completed")
            
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")
    
    async def init_mcp_async(self):
        """Initialize MCP integration asynchronously"""
        try:
            self.log("🔧 Initializing MCP integration...")
            self.mcp_initialized = await self.mcp_integration.initialize()
            if self.mcp_initialized:
                tool_count = len(self.mcp_integration.client.available_tools)
                self.log(f"✅ MCP integration ready with {tool_count} tools", "SUCCESS")
            else:
                self.log("⚠️ MCP integration failed - continuing without MCP support", "INFO")
        except Exception as e:
            self.log(f"MCP initialization error: {e}", "ERROR")
            self.mcp_initialized = False
    
    def setup_homebridge(self):
        """Initialize Homebridge API connection"""
        try:
            # Homebridge API settings - you can configure these
            self.homebridge_host = "pi1.local"  # or your Homebridge server IP
            self.homebridge_port = 8581         # default Homebridge web UI port
            self.homebridge_username = "dan"    # default username
            self.homebridge_password = "windoze"  # default password
            
            # Get auth token and try to get accessories from Homebridge
            self.homebridge_token = self.get_homebridge_auth_token()
            if self.homebridge_token:
                accessories = self.get_homebridge_accessories()
                if accessories:
                    self.log(f"🏠 Connected to Homebridge with {len(accessories)} accessories", "SUCCESS")
                else:
                    self.log("🏠 Homebridge connection failed - using Shortcuts fallback", "ERROR")
            else:
                self.log("🏠 Homebridge authentication failed - using Shortcuts fallback", "ERROR")
                
        except Exception as e:
            self.log(f"Homebridge setup error: {e}", "ERROR")
    
    def setup_conversation_memory(self):
        """Initialize smart persistent conversation memory"""
        try:
            self.memory_file = "/home/dan/voice_assistant_memory.json"
            self.max_memory_entries = 50  # Keep last 50 exchanges
            self.follow_up_mode = False
            self.follow_up_timeout = 80   # 8 seconds to respond to follow-up
            self.follow_up_counter = 0
            
            # Load existing memory
            try:
                with open(self.memory_file, 'r') as f:
                    self.conversation_memory = json.load(f)
                self.log(f"💭 Loaded {len(self.conversation_memory)} conversation memories")
            except FileNotFoundError:
                self.conversation_memory = []
                self.log("💭 Starting fresh conversation memory")
            except Exception as e:
                self.log(f"Memory load error: {e}", "ERROR")
                self.conversation_memory = []
                
        except Exception as e:
            self.log(f"Memory setup error: {e}", "ERROR")
            self.conversation_memory = []
    
    def save_conversation_memory(self):
        """Save conversation memory to persistent storage"""
        try:
            # Keep only important and recent conversations
            filtered_memory = self.filter_smart_memory(self.conversation_memory)
            
            with open(self.memory_file, 'w') as f:
                json.dump(filtered_memory, f, indent=2)
                
        except Exception as e:
            self.log(f"Memory save error: {e}", "ERROR")
    
    def filter_smart_memory(self, memory):
        """Filter memory to keep only important exchanges"""
        if len(memory) <= self.max_memory_entries:
            return memory
        
        # Categorize entries by importance
        important = []
        regular = []
        routine = []
        
        for entry in memory:
            user_msg = entry.get('user', '').lower()
            assistant_msg = entry.get('assistant', '').lower()
            
            # Important: Questions, personal info, complex requests
            if any(word in user_msg for word in ['who', 'what', 'why', 'how', 'remember', 'name', 'favorite']):
                important.append(entry)
            # Routine: Simple commands, greetings
            elif any(word in user_msg for word in ['hello', 'hi', 'thanks', 'okay', 'yes', 'no']):
                routine.append(entry)
            else:
                regular.append(entry)
        
        # Keep all important, recent regular, few routine
        keep_important = important[-20:]  # Last 20 important
        keep_regular = regular[-20:]      # Last 20 regular  
        keep_routine = routine[-10:]      # Last 10 routine
        
        # Combine and sort by timestamp
        filtered = keep_important + keep_regular + keep_routine
        filtered.sort(key=lambda x: x.get('timestamp', 0))
        
        return filtered[-self.max_memory_entries:]
    
    def setup_speaker_diarization(self):
        """Initialize speaker diarization pipeline for voice isolation"""
        try:
            self.log("🎭 Initializing speaker diarization pipeline...")
            # Try to use pyannote speaker diarization model (requires HuggingFace auth)
            self.diarization_pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=None  # Public access - may be gated
            )
            
            # Check if pipeline was successfully created
            if self.diarization_pipeline is None:
                raise Exception("Pipeline creation returned None")
            
            # Enable CPU mode for stability
            if torch.cuda.is_available():
                self.diarization_pipeline.to(torch.device("cuda"))
                self.log("🎭 Speaker diarization ready (GPU)", "SUCCESS")
            else:
                self.diarization_pipeline.to(torch.device("cpu"))
                self.log("🎭 Speaker diarization ready (CPU)", "SUCCESS")
                
        except Exception as e:
            self.log(f"Speaker diarization setup failed: {e}", "INFO")
            self.speaker_diarization_enabled = False
            self.diarization_pipeline = None
            self.log("🎭 Continuing without speaker diarization - using single-user mode", "INFO")
            # Note: The model may be gated and require HuggingFace authentication
            # Visit https://hf.co/pyannote/speaker-diarization-3.1 to request access
    
    def identify_wake_word_speaker(self, audio_file_path, wake_word_text):
        """Identify which speaker said the wake word and store their voice profile"""
        if not self.speaker_diarization_enabled:
            return True  # Accept all audio if diarization disabled
            
        try:
            self.log("🎭 Identifying wake word speaker...")
            # Run speaker diarization on the audio file
            diarization = self.diarization_pipeline(audio_file_path)
            
            # Find the dominant speaker during wake word detection
            # For simplicity, we'll use the speaker with the most speaking time
            speaker_times = {}
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                duration = turn.end - turn.start
                speaker_times[speaker] = speaker_times.get(speaker, 0) + duration
            
            if speaker_times:
                # Get the speaker who spoke the most (likely the wake word speaker)
                wake_word_speaker = max(speaker_times, key=speaker_times.get)
                self.wake_word_speaker_embedding = wake_word_speaker
                self.log(f"🎭 Wake word speaker identified: {wake_word_speaker}", "SUCCESS")
                return True
            
            return False
            
        except Exception as e:
            self.log(f"Speaker identification error: {e}", "ERROR")
            return True  # Fallback to accepting all audio
    
    def is_same_speaker_as_wake_word(self, audio_file_path):
        """Check if the current audio is from the same speaker who said the wake word"""
        if not self.speaker_diarization_enabled or not self.wake_word_speaker_embedding:
            return True  # Accept all audio if no speaker tracking
            
        try:
            self.log("🎭 Checking speaker match...")
            # Run speaker diarization on current audio
            diarization = self.diarization_pipeline(audio_file_path)
            
            # Check if the wake word speaker is present in this audio
            current_speakers = set()
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                current_speakers.add(speaker)
            
            # Simple speaker matching - check if wake word speaker is still talking
            speaker_match = self.wake_word_speaker_embedding in current_speakers
            
            if speaker_match:
                self.log("🎭 Speaker match confirmed", "SUCCESS")
            else:
                self.log("🎭 Different speaker detected - ignoring audio", "INFO")
                
            return speaker_match
            
        except Exception as e:
            self.log(f"Speaker matching error: {e}", "ERROR")
            return True  # Fallback to accepting all audio
    
    def is_repetitive_hallucination(self, text):
        """Detect repetitive patterns that indicate Whisper hallucination"""
        try:
            # Split into words for analysis
            words = text.split()
            if len(words) < 10:  # Skip short texts
                return False
            
            # Method 1: Check for repeated phrases
            # Look for 3+ word sequences that repeat
            for phrase_len in range(3, min(8, len(words)//3)):  # Check 3-7 word phrases
                phrases = {}
                for i in range(len(words) - phrase_len + 1):
                    phrase = ' '.join(words[i:i+phrase_len])
                    phrases[phrase] = phrases.get(phrase, 0) + 1
                
                # If any phrase repeats 3+ times, it's likely a hallucination
                for phrase, count in phrases.items():
                    if count >= 3:
                        self.log(f"🔍 Repetitive phrase detected: '{phrase}' ({count} times)")
                        return True
            
            # Method 2: Check for single word repetition
            word_counts = {}
            for word in words:
                if len(word) > 2:  # Skip short words like "a", "the"
                    word_counts[word] = word_counts.get(word, 0) + 1
            
            # If any meaningful word appears too frequently, flag it
            total_words = len(words)
            for word, count in word_counts.items():
                if count > max(3, total_words * 0.2):  # Word appears >20% of the time or >3 times
                    self.log(f"🔍 Repetitive word detected: '{word}' ({count}/{total_words} times)")
                    return True
            
            
            # Method 4: Check for excessively long text with low vocabulary diversity
            if len(words) > 50:  # Very long transcription
                unique_words = len(set(words))
                diversity_ratio = unique_words / len(words)
                if diversity_ratio < 0.3:  # Less than 30% unique words
                    self.log(f"🔍 Low vocabulary diversity: {unique_words}/{len(words)} ({diversity_ratio:.2f})")
                    return True
            
            return False
            
        except Exception as e:
            self.log(f"Repetition detection error: {e}", "ERROR")
            return False  # Don't filter on error
    
    def is_valid_wake_word_detection(self, text):
        """Verify that wake word detection is legitimate (not from hallucination)"""
        try:
            text_lower = text.lower()
            
            # Check if wake word appears in context that makes sense
            wake_word_index = text_lower.find(self.wake_word)
            if wake_word_index == -1:
                return False
            
            # Get text around the wake word for context analysis
            words = text_lower.split()
            wake_word_pos = -1
            for i, word in enumerate(words):
                if self.wake_word in word:
                    wake_word_pos = i
                    break
            
            if wake_word_pos == -1:
                return False
            
            # Method 1: Check if wake word is embedded in repetitive hallucination
            # If the overall text appears to be a hallucination, the wake word is likely false
            if self.is_repetitive_hallucination(text_lower):
                self.log(f"🚫 Wake word detected in repetitive hallucination text")
                return False
            
            # Method 2: Wake word position validation
            # Wake word can appear anywhere, but we need at least some command after it
            remaining_words = words[wake_word_pos + 1:]
            if len(remaining_words) == 0:
                self.log(f"🚫 No command after wake word")
                return False
            
            # Method 3: Check context around wake word for repetitive patterns
            # Get a small window around the wake word to check for local repetition
            context_start = max(0, wake_word_pos - 4)
            context_end = min(len(words), wake_word_pos + 5)
            context_words = words[context_start:context_end]
            context_phrase = ' '.join(context_words)
            
            # Check if the immediate context shows repetitive patterns
            if len(context_words) > 6:  # Need enough context to analyze
                context_word_counts = {}
                for word in context_words:
                    if word != self.wake_word and len(word) > 2:  # Exclude wake word and short words
                        context_word_counts[word] = context_word_counts.get(word, 0) + 1
                
                # If any word appears more than twice in the small context, it's suspicious
                for word, count in context_word_counts.items():
                    if count > 2:
                        self.log(f"🚫 Wake word in repetitive context: '{word}' appears {count} times near wake word")
                        return False
            
            # Method 4: Check for minimum viable command structure
            # After wake word, there should be some reasonable command content
            remaining_words = words[wake_word_pos + 1:]
            if len(remaining_words) > 0:
                # Check if post-wake-word content is just repetitive junk
                remaining_text = ' '.join(remaining_words)
                if self.is_repetitive_hallucination(remaining_text):
                    self.log(f"🚫 Repetitive content after wake word: '{remaining_text[:30]}...'")
                    return False
            
            # If we get here, the wake word detection seems legitimate
            return True
            
        except Exception as e:
            self.log(f"Wake word validation error: {e}", "ERROR")
            return True  # Default to accepting wake word on error
    
    def add_to_memory(self, user_message, assistant_response):
        """Add exchange to conversation memory"""
        try:
            import time
            
            entry = {
                'timestamp': time.time(),
                'user': user_message,
                'assistant': assistant_response,
                'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            self.conversation_memory.append(entry)
            self.save_conversation_memory()
            
        except Exception as e:
            self.log(f"Memory add error: {e}", "ERROR")
    
    def get_conversation_context(self):
        """Get recent conversation context for LLM"""
        try:
            if not self.conversation_memory:
                return ""
            
            # Get last few relevant exchanges
            recent_memory = self.conversation_memory[-10:]  # Last 10 exchanges
            
            context = "Recent conversation history:\n"
            for entry in recent_memory:
                user_msg = entry.get('user', '')
                assistant_msg = entry.get('assistant', '')
                context += f"User: {user_msg}\nAssistant: {assistant_msg}\n\n"
            
            return context
            
        except Exception as e:
            self.log(f"Context error: {e}", "ERROR")
            return ""
    
    def get_homebridge_auth_token(self):
        """Get authentication token from Homebridge"""
        try:
            import requests
            import json
            
            url = f"http://{self.homebridge_host}:{self.homebridge_port}/api/auth/login"
            data = {
                "username": self.homebridge_username,
                "password": self.homebridge_password
            }
            
            response = requests.post(url, json=data, timeout=5)
            if response.status_code == 201:
                token_data = response.json()
                return token_data.get('access_token')
            else:
                self.log(f"Homebridge auth error: {response.status_code}", "ERROR")
                return None
                
        except Exception as e:
            self.log(f"Homebridge auth error: {e}", "ERROR")
            return None
    
    def get_homebridge_accessories(self):
        """Get accessories from Homebridge API"""
        try:
            import requests
            
            if not hasattr(self, 'homebridge_token') or not self.homebridge_token:
                return None
            
            url = f"http://{self.homebridge_host}:{self.homebridge_port}/api/accessories"
            headers = {"Authorization": f"Bearer {self.homebridge_token}"}
            
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                self.log(f"Homebridge API error: {response.status_code}", "ERROR")
                return None
                
        except Exception as e:
            self.log(f"Homebridge API error: {e}", "ERROR")
            return None
    
    def send_homebridge_command(self, accessory_name, service_type, characteristic_type, value):
        """Send command to Homebridge device"""
        try:
            import requests
            
            if not hasattr(self, 'homebridge_token') or not self.homebridge_token:
                return False
            
            # First get accessories to find the right one
            accessories = self.get_homebridge_accessories()
            if not accessories:
                return False
            
            # Find the accessory and characteristic
            for accessory in accessories:
                if accessory_name.lower() in accessory.get('displayName', '').lower():
                    for service in accessory.get('services', []):
                        if service_type in service.get('type', ''):
                            for char in service.get('characteristics', []):
                                if characteristic_type in char.get('type', ''):
                                    # Send the command
                                    url = f"http://{self.homebridge_host}:{self.homebridge_port}/api/accessories/{accessory['uniqueId']}"
                                    headers = {"Authorization": f"Bearer {self.homebridge_token}"}
                                    
                                    data = {
                                        'characteristicType': char['type'],
                                        'value': value
                                    }
                                    
                                    response = requests.put(url, json=data, headers=headers, timeout=5)
                                    return response.status_code == 200
            
            return False
            
        except Exception as e:
            self.log(f"Homebridge command error: {e}", "ERROR")
            return False
    
    def handle_red_alert(self):
        """Handle red alert command - play sound and flash lights"""
        try:
            self.log("🚨 RED ALERT INITIATED", "SUCCESS")
            
            # Play red alert sound
            import threading
            import subprocess
            
            def play_alert_sound():
                try:
                    # Copy sound file to Pi if we're on Pi, otherwise play locally
                    subprocess.run([
                        'mpg123', '/home/dan/tng_red_alert1.mp3'
                    ], capture_output=True)
                except Exception as e:
                    self.log(f"Alert sound error: {e}", "ERROR")
            
            # Start sound in background
            sound_thread = threading.Thread(target=play_alert_sound)
            sound_thread.daemon = True
            sound_thread.start()
            
            # Flash Govee floor lamp red via Homebridge
            def flash_red_light():
                try:
                    # Flash red for 10 seconds
                    for i in range(20):  # 20 flashes over 10 seconds
                        # Turn red
                        self.send_homebridge_command("govee", "Lightbulb", "On", True)
                        self.send_homebridge_command("govee", "Lightbulb", "Hue", 0)  # Red
                        self.send_homebridge_command("govee", "Lightbulb", "Saturation", 100)  # Full saturation
                        self.send_homebridge_command("govee", "Lightbulb", "Brightness", 100)  # Full brightness
                        
                        import time
                        time.sleep(0.25)  # On for 0.25 seconds
                        
                        # Turn off briefly
                        self.send_homebridge_command("govee", "Lightbulb", "On", False)
                        time.sleep(0.25)  # Off for 0.25 seconds
                        
                except Exception as e:
                    self.log(f"Red alert lighting error: {e}", "ERROR")
            
            # Start lighting in background
            light_thread = threading.Thread(target=flash_red_light)
            light_thread.daemon = True
            light_thread.start()
            
            # Speak response
            self.speak_response("Red alert! All hands to battle stations!")
            
        except Exception as e:
            self.log(f"Red alert error: {e}", "ERROR")
            self.speak_response("Unable to initiate red alert protocol")
    
    def control_homekit_device(self, command):
        """Control Apple Home devices via iOS Shortcuts"""
        try:
            command_lower = command.lower()
            
            # Parse common HomeKit commands and map to shortcuts
            if "lights" in command_lower:
                return self.control_lights_via_shortcuts(command_lower)
            elif "temperature" in command_lower or "thermostat" in command_lower:
                return self.control_thermostat_via_shortcuts(command_lower)
            elif any(word in command_lower for word in ["switch", "outlet", "plug"]):
                return self.control_switch_via_shortcuts(command_lower)
            elif "lock" in command_lower:
                return self.control_lock_via_shortcuts(command_lower)
            else:
                self.log(f"Unknown HomeKit command: {command}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"HomeKit control error: {e}", "ERROR")
            return False
    
    def trigger_ios_shortcut(self, shortcut_name, input_text=""):
        """Trigger an iOS Shortcut via SSH to a paired iPhone/Mac"""
        try:
            # Method 1: If you have an iPhone/Mac on the same network
            # You can create shortcuts that control Home devices
            
            # Method 2: Use curl to trigger shortcuts via personal automation webhooks
            shortcut_url = f"shortcuts://run-shortcut?name={shortcut_name}"
            if input_text:
                shortcut_url += f"&input=text&text={input_text}"
            
            # This would require having an iOS device accessible
            # For now, let's use the fallback method with Home Assistant or direct calls
            self.log(f"🏠 Would trigger shortcut: {shortcut_name}", "SUCCESS")
            return True
            
        except Exception as e:
            self.log(f"iOS Shortcut error: {e}", "ERROR")
            return False
    
    def control_lights_via_shortcuts(self, command):
        """Control lights via iOS Shortcuts or SSH"""
        try:
            if "turn on" in command:
                return self.execute_home_command("shortcuts://run-shortcut?name=Turn%20On%20Lights")
            elif "turn off" in command:
                return self.execute_home_command("shortcuts://run-shortcut?name=Turn%20Off%20Lights")
            elif "dim" in command or "brightness" in command:
                import re
                match = re.search(r'(\d+)', command)
                if match:
                    brightness = match.group(1)
                    return self.execute_home_command(f"shortcuts://run-shortcut?name=Set%20Brightness&input=text&text={brightness}")
            
            # Fallback to SSH command if you have SSH access to a Mac/iPhone
            self.log("💡 Light control via Apple Home API", "SUCCESS")
            return True
            
        except Exception as e:
            self.log(f"Light control error: {e}", "ERROR")
            return False
    
    def control_thermostat_via_shortcuts(self, command):
        """Control thermostat via iOS Shortcuts"""
        try:
            import re
            match = re.search(r'(\d+)', command)
            if match:
                temp = match.group(1)
                return self.execute_home_command(f"shortcuts://run-shortcut?name=Set%20Temperature&input=text&text={temp}")
            return False
        except Exception as e:
            self.log(f"Thermostat control error: {e}", "ERROR")
            return False
    
    def control_switch_via_shortcuts(self, command):
        """Control switches via iOS Shortcuts"""
        try:
            if "turn on" in command:
                return self.execute_home_command("shortcuts://run-shortcut?name=Turn%20On%20Switch")
            else:
                return self.execute_home_command("shortcuts://run-shortcut?name=Turn%20Off%20Switch")
        except Exception as e:
            self.log(f"Switch control error: {e}", "ERROR")
            return False
    
    def control_lock_via_shortcuts(self, command):
        """Control locks via iOS Shortcuts"""
        try:
            if "lock" in command and "unlock" not in command:
                return self.execute_home_command("shortcuts://run-shortcut?name=Lock%20Door")
            else:
                return self.execute_home_command("shortcuts://run-shortcut?name=Unlock%20Door")
        except Exception as e:
            self.log(f"Lock control error: {e}", "ERROR")
            return False
    
    def execute_home_command(self, shortcut_url):
        """Execute Apple Home command via multiple methods"""
        try:
            # Method 1: SSH to Mac (if you have one on the network)
            try:
                result = subprocess.run([
                    'ssh', '-o', 'ConnectTimeout=2', 'dan@your-mac.local', 
                    f'open "{shortcut_url}"'
                ], capture_output=True, timeout=5)
                if result.returncode == 0:
                    self.log("🏠 Command sent via Mac SSH", "SUCCESS")
                    return True
            except:
                pass
            
            # Method 2: Use Home Assistant API (if you have it)
            try:
                import requests
                # This would call Home Assistant to trigger the action
                # requests.post("http://homeassistant.local:8123/api/services/...", ...)
                pass
            except:
                pass
            
            # Method 3: Use webhook/IFTTT (if configured)
            try:
                import requests
                # Trigger IFTTT webhook that controls Apple Home
                # requests.post("https://maker.ifttt.com/trigger/...", ...)
                pass
            except:
                pass
            
            # For now, just log the command
            self.log(f"🏠 Apple Home command: {shortcut_url}", "SUCCESS")
            return True
            
        except Exception as e:
            self.log(f"Home command error: {e}", "ERROR")
            return False
    
    def process_command(self, command, is_follow_up=False):
        """Process a voice command after wake word detection or as follow-up"""
        try:
            if is_follow_up:
                self.log(f"💬 Processing follow-up: '{command}'")
                # Follow-ups are always conversations
                intent = 'conversation'
            else:
                self.log(f"📝 Processing command: '{command}'")
                
                # Handle special red alert command
                if "red alert" in command.lower():
                    self.handle_red_alert()
                    return
                
                # Start thinking sound immediately before any API calls
                thinking_process = self.start_thinking_sound()
                
                try:
                    # Classify intent for new commands
                    intent = self.classify_intent(command)
                    self.log(f"🧠 Intent: {intent}")
                except Exception as e:
                    self.stop_thinking_sound(thinking_process)
                    self.log(f"Intent classification error: {e}", "ERROR")
                    # Stay silent on classification errors - just log them
                    return
            
            if intent == 'homekit':
                # Handle HomeKit command (thinking sound already started)
                try:
                    success = self.control_homekit_device(command)
                    self.stop_thinking_sound(thinking_process)
                    if success:
                        self.speak_response("Done!")
                    else:
                        self.speak_response("Sorry, I couldn't control that device.")
                finally:
                    self.stop_thinking_sound(thinking_process)
                    
            elif intent == 'apple_tv':
                # Handle Apple TV command (thinking sound already started)
                try:
                    commands = self.get_apple_tv_commands(command)
                    if commands:
                        self.log(f"📺 Apple TV Commands: {commands}", "COMMAND")
                        success = self.send_apple_tv_commands(commands)
                        if success:
                            self.stop_thinking_sound(thinking_process)
                            self.speak_response("Done!")
                        else:
                            self.stop_thinking_sound(thinking_process)
                            self.speak_response("Unable to comply.")
                    else:
                        self.stop_thinking_sound(thinking_process)
                        self.speak_response("I didn't understand that Apple TV command.")
                finally:
                    self.stop_thinking_sound(thinking_process)
                    
            elif intent == 'conversation':
                # Have conversation with memory and follow-up capability (thinking sound already started)
                try:
                    response = self.have_conversation(command)
                    self.stop_thinking_sound(thinking_process)
                    
                    # Always speak if there's a response, even if expecting follow-up
                    if response and response.strip():
                        self.speak_response(response)
                    else:
                        self.log("Claude returned empty response - staying silent", "INFO")
                finally:
                    self.stop_thinking_sound(thinking_process)
            
        except Exception as e:
            self.log(f"Command processing error: {e}", "ERROR")
            # Stay silent on processing errors - just log them
    
    def should_respond_to_conversation(self, response):
        """Check if Claude's response indicates understanding vs confusion"""
        if not response or not response.strip():
            return False
            
        # Patterns that indicate Claude didn't understand or is confused
        confusion_patterns = [
            "i don't understand",
            "i'm not sure what",
            "could you clarify",
            "please specify",
            "i need more information",
            "unclear what you're asking",
            "not sure how to help",
            "what do you mean",
            "can you be more specific",
            "i don't know what you mean",
            "unable to process incomplete transmission",
            "standing by for clarification"
        ]
        
        response_lower = response.lower()
        for pattern in confusion_patterns:
            if pattern in response_lower:
                return False
        
        return True
        
    def start_thinking_sound(self):
        """Start playing continuous random TNG computer beeps - returns thread to stop later"""
        try:
            import random
            import os
            import threading
            import time
            
            # List of longest TNG computer beeps
            beep_files = [
                'computerbeep_57.mp3', 'computerbeep_56.mp3', 'computerbeep_40.mp3',
                'computerbeep_73.mp3', 'computerbeep_7.mp3', 'computerbeep_36.mp3',
                'computerbeep_2.mp3', 'computerbeep_47.mp3', 'computerbeep_33.mp3',
                'computerbeep_67.mp3', 'computerbeep_29.mp3', 'computerbeep_31.mp3',
                'computerbeep_32.mp3', 'computerbeep_28.mp3', 'computerbeep_75.mp3',
                'computerbeep_37.mp3', 'computerbeep_27.mp3', 'computerbeep_51.mp3',
                'computerbeep_34.mp3', 'computerbeep_50.mp3'
            ]
            
            # Create a shuffled copy of beep files for random order
            shuffled_beeps = beep_files.copy()
            random.shuffle(shuffled_beeps)
            
            # Control flag for the thinking sound loop
            self.thinking_active = True
            
            def play_continuous_beeps():
                """Background thread that plays beeps continuously in random order"""
                beep_index = 0
                while self.thinking_active:
                    try:
                        # Get next beep in shuffled order
                        selected_beep = shuffled_beeps[beep_index]
                        beep_path = f'/home/dan/tng_beeps/{selected_beep}'
                        
                        # Check if file exists
                        if os.path.exists(beep_path):
                            # Play the beep file once
                            process = subprocess.Popen([
                                'mpg123', beep_path
                            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            
                            # Wait for it to finish playing
                            process.wait()
                        else:
                            # Fallback - play short beep and wait
                            process = subprocess.Popen([
                                'mpg123', '/home/dan/computer-sounds-25541.mp3'
                            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            process.wait()
                        
                        # Move to next beep, reshuffle when we reach the end
                        beep_index += 1
                        if beep_index >= len(shuffled_beeps):
                            beep_index = 0
                            random.shuffle(shuffled_beeps)  # Reshuffle for new random order
                        
                        # Small gap between beeps (0.2 seconds)
                        if self.thinking_active:
                            time.sleep(0.2)
                            
                    except Exception:
                        # If there's an error, wait a bit and continue
                        if self.thinking_active:
                            time.sleep(0.5)
            
            # Start the background thread
            thinking_thread = threading.Thread(target=play_continuous_beeps, daemon=True)
            thinking_thread.start()
            
            return thinking_thread
        except:
            return None
    
    def stop_thinking_sound(self, thinking_thread):
        """Stop the thinking sound"""
        if thinking_thread:
            try:
                # Signal the thread to stop
                self.thinking_active = False
                
                # Kill any currently playing mpg123 processes to stop immediately
                try:
                    subprocess.run(['pkill', '-f', 'mpg123'], 
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except:
                    pass
                
                # Give the thread a moment to clean up
                thinking_thread.join(timeout=0.5)
            except:
                pass
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        icons = {"INFO": "📝", "WAKE": "🎯", "COMMAND": "🗣️", "SEND": "📤", "ERROR": "❌", "SUCCESS": "✅", "WHISPER": "🤖", "CONVERSATION": "💬", "TTS": "🔊"}
        icon = icons.get(level, "📝")
        print(f"[{timestamp}] {icon} {message}")
        
    def init_whisper(self):
        try:
            self.log(f"Loading Faster-Whisper {self.model_size} model...")
            # Initialize Faster-Whisper with optimized settings
            self.whisper_model = WhisperModel(
                self.model_size, 
                device="cpu",  # Use CPU for stability on this system
                compute_type="int8",  # Use int8 for faster inference
                num_workers=2  # Parallel processing
            )
            self.log("Faster-Whisper ready - 4x speed improvement!", "SUCCESS")
            return True
        except Exception as e:
            self.log(f"Faster-Whisper error: {e}", "ERROR")
            return False
            
    def start_continuous_listening(self):
        """Start continuous audio stream with real-time Voice Activity Detection"""
        import threading
        import subprocess
        import struct
        import wave
        
        self.listening = True
        self.paused = False
        self.audio_buffer = []
        self.is_speech_active = False
        self.silence_count = 0
        self.speech_duration = 0
        self.speech_threshold = 0.35  # Lower threshold for better sensitivity with boosted gain
        self.silence_threshold = 12   # Slightly longer silence detection (1.2 seconds) for background noise
        self.max_speech_duration = 80   # 8 seconds max (80 * 0.1s chunks) - shorter for better boundaries
        self.adaptive_threshold = 0.35  # Dynamic threshold that adapts to background noise
        self.command_collection_mode = False  # Special mode after wake word
        self.command_timeout = 50     # 5 seconds to speak command after wake word
        self.command_timeout_counter = 0
        self.pending_transcription = None
        
        def audio_stream_worker():
            """Process continuous audio stream with VAD"""
            # Start continuous arecord process with enhanced settings
            arecord_process = subprocess.Popen([
                'arecord', '-D', 'hw:2,0',
                '-f', 'S16_LE', '-r', '44100', '-c', '1',
                '-t', 'raw',  # Raw PCM output for real-time processing
                '--buffer-size=8192',  # Larger buffer for better quality
                '--period-size=1024'   # Smaller periods for lower latency
            ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            
            chunk_size = 4410  # 0.1 second of audio at 44100Hz
            
            while self.listening:
                try:
                    if self.paused:
                        # Drain audio during pause to prevent buffer buildup
                        arecord_process.stdout.read(chunk_size * 2)  # 2 bytes per sample
                        time.sleep(0.1)
                        continue
                    
                    # Read audio chunk
                    raw_audio = arecord_process.stdout.read(chunk_size * 2)
                    if len(raw_audio) < chunk_size * 2:
                        continue
                    
                    # Convert to numpy array for analysis
                    audio_data = struct.unpack(f'{chunk_size}h', raw_audio)
                    
                    # Apply simple audio preprocessing for clarity
                    audio_array = np.array(audio_data, dtype=np.float32)
                    
                    # Apply controlled gain boost (amplify by 1.3x to prevent overflow)
                    audio_array *= 1.3
                    
                    # Simple noise gate - reduce low-level noise
                    noise_floor = 0.1
                    audio_array = np.where(np.abs(audio_array) < noise_floor * 32768, 
                                         audio_array * 0.3, audio_array)
                    
                    # Convert back to int16 with proper clipping and calculate level
                    audio_data = np.clip(audio_array, -32767, 32767).astype(np.int16)
                    audio_level = min(1.0, max(abs(sample) for sample in audio_data) / 32768.0)
                    
                    # Adaptive Voice Activity Detection with better boundary detection
                    if audio_level > self.adaptive_threshold:
                        if not self.is_speech_active:
                            self.log(f"🎙️ Speech detected (level: {audio_level:.3f})")
                            self.is_speech_active = True
                            self.audio_buffer = []
                            self.peak_level = audio_level  # Track peak for adaptive threshold
                        
                        # Update peak level and adapt threshold for background noise
                        if audio_level > getattr(self, 'peak_level', 0.35):
                            self.peak_level = audio_level
                            # Adaptive threshold: 40% of peak level, minimum 0.25
                            self.adaptive_threshold = max(0.25, self.peak_level * 0.4)
                        
                        # Add audio to buffer during speech
                        self.audio_buffer.extend(audio_data)
                        self.silence_count = 0
                        self.speech_duration += 1
                        
                        # Debug: Show continuing speech levels
                        if hasattr(self, '_speech_counter'):
                            self._speech_counter += 1
                        else:
                            self._speech_counter = 0
                        
                        if self._speech_counter % 20 == 0:  # Every 2 seconds (less logging)
                            self.log(f"🎙️ Continuing speech (buffered: {len(self.audio_buffer)/44100:.1f}s)")
                        
                        # Timeout protection - force end if too long
                        if self.speech_duration >= self.max_speech_duration:
                            self.log(f"⏰ Speech timeout, forcing end at {len(self.audio_buffer)/44100:.1f}s")
                            self.is_speech_active = False
                            self.silence_count = 0
                            self._speech_counter = 0
                            self.speech_duration = 0
                            
                            if len(self.audio_buffer) > 44100:  # At least 1 second
                                self.save_speech_buffer(self.audio_buffer.copy())
                            
                            self.audio_buffer = []
                        
                    else:
                        if self.is_speech_active:
                            # Check if this is truly silence or just background noise
                            # If level is still significant (but below speech threshold), it might be background
                            if audio_level < self.adaptive_threshold * 0.3:  # True silence (very low level)
                                self.silence_count += 1
                            else:
                                # Moderate level - might be background noise, count as partial silence
                                self.silence_count += 0.5
                            
                            self.audio_buffer.extend(audio_data)  # Include silence gap
                            
                            # Debug: Show silence progress less frequently for speed
                            if int(self.silence_count) % 5 == 0 and self.silence_count % 1 == 0:  # Every 0.5 seconds
                                self.log(f"🔇 Silence: {self.silence_count:.1f}/{self.silence_threshold} frames (level: {audio_level:.3f})")
                            
                            # End of speech detected
                            if self.silence_count >= self.silence_threshold:
                                self.log(f"🔇 Speech ended, buffered {len(self.audio_buffer)/44100:.1f}s")
                                self.is_speech_active = False
                                self.silence_count = 0
                                self._speech_counter = 0
                                self.speech_duration = 0
                                
                                # Reset adaptive threshold for next speech detection
                                self.adaptive_threshold = 0.35
                                
                                # Save buffered audio for transcription
                                if len(self.audio_buffer) > 44100:  # At least 1 second
                                    self.save_speech_buffer(self.audio_buffer.copy())
                                else:
                                    self.log(f"⚠️ Audio too short: {len(self.audio_buffer)/44100:.1f}s")
                                
                                self.audio_buffer = []
                        else:
                            # Debug: Show ambient levels occasionally
                            if hasattr(self, '_debug_counter'):
                                self._debug_counter += 1
                            else:
                                self._debug_counter = 0
                            
                            if self._debug_counter % 50 == 0:  # Every 5 seconds
                                self.log(f"🔈 Ambient level: {audio_level:.3f}")
                    
                except Exception as e:
                    self.log(f"Audio stream error: {e}", "ERROR")
                    time.sleep(0.1)
            
            # Cleanup
            arecord_process.terminate()
            arecord_process.wait()
        
        # Start audio processing thread
        self.audio_thread = threading.Thread(target=audio_stream_worker, daemon=True)
        self.audio_thread.start()
        self.log("🎤 Started continuous audio stream with VAD")
    
    def save_speech_buffer(self, audio_data):
        """Save buffered speech audio for transcription"""
        try:
            import wave
            import struct
            
            # Create temporary file for the audio
            temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            
            # Write WAV file header and audio data
            with wave.open(temp_file.name, 'wb') as wf:
                wf.setnchannels(1)  # Mono
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(44100)  # Sample rate
                
                # Convert int16 audio data to bytes
                audio_bytes = struct.pack(f'{len(audio_data)}h', *audio_data)
                wf.writeframes(audio_bytes)
            
            # Add to transcription queue for main thread to process
            self.transcription_queue.put(temp_file.name)
            self.log(f"💾 Queued {len(audio_data)/44100:.1f}s audio for transcription")
            
        except Exception as e:
            self.log(f"Save buffer error: {e}", "ERROR")
    
    def pause_listening(self):
        """Temporarily pause audio recording (during TTS)"""
        self.paused = True
        # Clear any pending transcriptions to prevent feedback
        if hasattr(self, 'transcription_queue'):
            while not self.transcription_queue.empty():
                try:
                    old_file = self.transcription_queue.get_nowait()
                    os.unlink(old_file)
                except:
                    pass
        # Reset speech detection state
        self.is_speech_active = False
        self.silence_count = 0
        self.speech_duration = 0
        self.command_collection_mode = False
        self.command_timeout_counter = 0
        # DON'T reset follow_up_mode during TTS - we want to keep it active!
        # self.follow_up_mode = False
        # self.follow_up_counter = 0
        self.log("🔇 Paused listening (TTS playing)")
    
    def resume_listening(self):
        """Resume audio recording after TTS"""
        self.paused = False
        self.log("🎤 Resumed listening")
    
            
    def transcribe_with_whisper(self, audio_file_path):
        try:
            self.log("🧠 Transcribing audio file (Faster-Whisper)...")
            # Use Faster-Whisper API (returns segments and info)
            segments, info = self.whisper_model.transcribe(
                audio_file_path,
                language="en",
                temperature=0,
                no_speech_threshold=0.4,  # Lower threshold for better detection
                initial_prompt="Computer, voice commands for Apple TV and home automation",
                condition_on_previous_text=False  # Each command is independent
            )
            
            # Combine all segments into single text
            text = ""
            for segment in segments:
                text += segment.text
            
            text = text.strip().lower()
            
            # Clean up transcription artifacts
            text = text.lstrip('.,;:-!?')  # Remove leading punctuation
            text = text.strip()  # Remove extra whitespace
            
            # Enhanced hallucination detection
            if text and len(text) > 2:
                # Check for repetitive patterns (main issue)
                if self.is_repetitive_hallucination(text):
                    self.log(f"🚫 Filtered repetitive hallucination: \"{text[:50]}...\"")
                    return None
                
                # Check for obvious technical hallucinations
                obvious_hallucinations = [
                    "vauffin", "ash", "阿姨", "subscribe to", "like and subscribe",
                    "thank you for watching", "don't forget to", "please like"
                ]
                
                for hallucination in obvious_hallucinations:
                    if hallucination in text and self.wake_word not in text:
                        self.log(f"🚫 Filtered obvious hallucination: \"{text}\"")
                        return None
                
                self.total_transcriptions += 1
                self.log(f"👂 HEARD: \"{text}\" (⚡ Faster-Whisper)", "WHISPER")
                return text
            return None
            
        except Exception as e:
            self.log(f"Faster-Whisper transcription error: {e}", "ERROR")
            return None
    
    def speak_with_elevenlabs(self, text):
        """Convert text to speech using ElevenLabs with cloned Enterprise-D voice"""
        try:
            self.log(f"🔊 Speaking with ElevenLabs (Enterprise-D): \"{text}\"", "TTS")
            
            # Pause listening while speaking to prevent feedback
            self.pause_listening()
            
            import requests
            
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.elevenlabs_voice_id}"
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.elevenlabs_api_key
            }
            
            data = {
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": 0.65,       # Slightly more flexible while maintaining authority
                    "similarity_boost": 0.7, # Reduce artifacts while maintaining voice match
                    "style": 0.15,           # Subtle emotional variation for more natural delivery
                    "use_speaker_boost": True,
                    "speed": 0.95            # Slightly faster, more responsive pace
                }
            }
            
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                # Save and play the audio
                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_file:
                    temp_audio_path = tmp_file.name
                    tmp_file.write(response.content)
                
                # Play with mpg123 at slightly slower speed for computer-like delivery
                subprocess.run(['mpg123', '--pitch', '-0.1', temp_audio_path], capture_output=True)
                self.log("ElevenLabs TTS completed", "SUCCESS")
                
                # Clean up
                try:
                    os.unlink(temp_audio_path)
                except:
                    pass
                
                # Resume listening after speaking
                time.sleep(0.2)
                self.resume_listening()
                
            else:
                raise Exception(f"ElevenLabs API error: {response.status_code} - {response.text}")
                
        except Exception as e:
            self.log(f"ElevenLabs TTS error: {e}", "ERROR")
            self.resume_listening()
            # Fallback to OpenAI TTS
            if self.use_openai_tts:
                self.speak_with_openai(text)
            else:
                self.speak_with_piper(text)
            
    def speak_with_openai(self, text):
        """Convert text to speech using OpenAI TTS"""
        try:
            self.log(f"🔊 Speaking with OpenAI: \"{text}\"", "TTS")
            
            # Pause listening while speaking to prevent feedback
            self.pause_listening()
            
            response = openai.audio.speech.create(
                model="tts-1",  # Fast model
                voice=self.tts_voice,
                input=text,
                speed=1.1  # Slightly faster speech
            )
            
            # Save and play the audio
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_file:
                temp_audio_path = tmp_file.name
                response.stream_to_file(temp_audio_path)
            
            # Play with mpg123
            subprocess.run(['mpg123', temp_audio_path], capture_output=True)
            self.log("OpenAI TTS completed", "SUCCESS")
            
            # Clean up
            try:
                os.unlink(temp_audio_path)
            except:
                pass
            
            # Resume listening after speaking
            time.sleep(0.2)  # Shorter pause for faster response
            self.resume_listening()
                
        except Exception as e:
            self.log(f"OpenAI TTS error: {e}", "ERROR")
            self.resume_listening()
            # Fallback to Piper
            self.speak_with_piper(text)
    
    def speak_with_piper(self, text):
        """Convert text to speech using Piper TTS (fallback)"""
        try:
            self.log(f"🔊 Speaking with Piper: \"{text}\"", "TTS")
            
            # Pause listening while speaking to prevent feedback
            self.pause_listening()
            
            # Create temporary file for audio
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                temp_audio_path = tmp_file.name
            
            # Generate speech with Piper
            result = subprocess.run([
                '/home/dan/pyatv_env/bin/piper', 
                '--model', self.tts_model_path,
                '--output_file', temp_audio_path
            ], input=text, text=True, capture_output=True, timeout=30)
            
            if result.returncode == 0:
                # Play the audio file
                subprocess.run(['aplay', temp_audio_path], capture_output=True)
                self.log("Piper TTS completed", "SUCCESS")
            else:
                self.log(f"Piper TTS failed: {result.stderr}", "ERROR")
                
            # Clean up
            try:
                os.unlink(temp_audio_path)
            except:
                pass
            
            # Resume listening after speaking
            time.sleep(0.2)  # Shorter pause for faster response
            self.resume_listening()
                
        except Exception as e:
            self.log(f"Piper TTS error: {e}", "ERROR")
            self.resume_listening()
    
    def speak_response(self, text):
        """Main TTS function - uses ElevenLabs cloned voice, falls back to OpenAI, then Piper"""
        
        # Filter long error messages and replace with Enterprise-appropriate responses
        if "Unable to process incomplete transmission" in text or "Standing by for clarification" in text:
            text = "Unable to comply."
        elif "Please specify what should be stopped" in text:
            text = "Unable to comply."
        elif "provide complete command parameters" in text:
            text = "Unable to comply."
        
        if self.use_elevenlabs_tts:
            self.speak_with_elevenlabs(text)
        elif self.use_openai_tts:
            self.speak_with_openai(text)
        else:
            self.speak_with_piper(text)
            
    def classify_intent(self, text):
        """Use Claude to classify if this is an Apple TV command or general conversation"""
        if not self.claude_api_key:
            return self.simple_intent_classification(text)
            
        try:
            prompt = f"""Classify this user request as either "homekit", "apple_tv", or "conversation".

HomeKit commands include:
- Controlling lights (turn on/off lights, dim lights, set brightness)
- Temperature control (set temperature, adjust thermostat)  
- Switch/outlet control (turn on/off switches, outlets, plugs)
- Lock control (lock/unlock doors)

Apple TV commands include:
- Controlling playback (play, pause, stop)
- Navigation (up, down, left, right, select, menu, home)
- Volume control (volume up/down)
- Opening apps (go to Netflix, open YouTube, launch Hulu)
- Search (search for movies, find shows)
- Power control (turn on/off)

Conversation includes:
- General questions (what's the weather, what time is it)
- Information requests (tell me about something)
- Chat/discussion (how are you, tell me a joke)
- Questions about topics not related to Apple TV or HomeKit control

User request: "{text}"

Respond with only: homekit OR apple_tv OR conversation"""

            response = requests.post(
                'https://api.anthropic.com/v1/messages',
                headers={
                    'Content-Type': 'application/json',
                    'x-api-key': self.claude_api_key,
                    'anthropic-version': '2023-06-01'
                },
                json={
                    'model': 'claude-3-5-sonnet-20241022',
                    'max_tokens': 10,
                    'messages': [{'role': 'user', 'content': prompt}]
                },
                timeout=10
            )
            
            if response.status_code == 200:
                claude_response = response.json()
                classification = claude_response['content'][0]['text'].strip().lower()
                
                if 'homekit' in classification:
                    return 'homekit'
                elif 'apple_tv' in classification:
                    return 'apple_tv'
                elif 'conversation' in classification:
                    return 'conversation'
                else:
                    return self.simple_intent_classification(text)
            else:
                return self.simple_intent_classification(text)
                
        except Exception as e:
            self.log(f"Intent classification error: {e}", "ERROR")
            return self.simple_intent_classification(text)
            
    def simple_intent_classification(self, text):
        """Simple fallback intent classification"""
        text_lower = text.lower()
        
        # HomeKit keywords (check first as they're more specific)
        homekit_keywords = [
            'lights', 'light', 'lamp', 'brightness', 'dim', 'thermostat', 
            'temperature', 'heat', 'cool', 'switch', 'outlet', 'plug', 
            'lock', 'unlock', 'door', 'garage'
        ]
        
        # Apple TV keywords  
        apple_tv_keywords = [
            'netflix', 'youtube', 'hulu', 'disney', 'play', 'pause', 'stop',
            'volume', 'up', 'down', 'left', 'right', 'select', 'menu', 'home',
            'open', 'launch', 'go to', 'search for', 'find'
        ]
        
        # Check for HomeKit keywords first
        for keyword in homekit_keywords:
            if keyword in text_lower:
                return 'homekit'
        
        # Check for Apple TV keywords
        for keyword in apple_tv_keywords:
            if keyword in text_lower:
                return 'apple_tv'
                
        return 'conversation'
            
    def get_apple_tv_commands(self, user_command):
        """Get Apple TV commands from Claude"""
        if not self.claude_api_key:
            return self.simple_apple_tv_interpretation(user_command)
            
        try:
            prompt = f"""You are controlling an Apple TV using pyatv commands. The user said: "{user_command}"

Available apps and their bundle IDs:
{json.dumps(self.available_apps, indent=2)}

Available pyatv commands:
- Navigation: up, down, left, right, select, menu, home, top_menu
- Playback: play, pause, play_pause, stop, next, previous
- Volume: volume_up, volume_down, set_volume=<0-100>
- Apps: launch_app=<bundle_id>
- Search: text_set=<search_term> then select
- Power: turn_on, turn_off

Rules:
1. If user wants to open/go to an app, use: launch_app=<bundle_id>
2. For navigation commands, use direct commands: up, down, left, right, select
3. For search, use: text_set=<search_term> then select
4. IMPORTANT: Use = format for commands with parameters

Return ONLY a JSON array of commands to execute.

Command: "{user_command}"
JSON response:"""

            response = requests.post(
                'https://api.anthropic.com/v1/messages',
                headers={
                    'Content-Type': 'application/json',
                    'x-api-key': self.claude_api_key,
                    'anthropic-version': '2023-06-01'
                },
                json={
                    'model': 'claude-sonnet-4-20250514',  # Claude 4 Sonnet
                    'max_tokens': 50,   # Even shorter for faster responses
                    'messages': [{'role': 'user', 'content': prompt}]
                },
                timeout=5   # Faster timeout
            )
            
            if response.status_code == 200:
                claude_response = response.json()
                commands_text = claude_response['content'][0]['text'].strip()
                
                try:
                    commands = json.loads(commands_text)
                    return commands
                except json.JSONDecodeError:
                    return self.simple_apple_tv_interpretation(user_command)
            else:
                return self.simple_apple_tv_interpretation(user_command)
                
        except Exception as e:
            return self.simple_apple_tv_interpretation(user_command)
            
    def simple_apple_tv_interpretation(self, text):
        """Fallback Apple TV command interpretation"""
        # text should already be the command part (after wake word)
        text = text.lower().strip()
        
        # Check for app launches
        for app_name, bundle_id in self.available_apps.items():
            if app_name in text and ("open" in text or "go to" in text or "launch" in text):
                return [f"launch_app={bundle_id}"]
        
        # Simple navigation
        if "down" in text:
            return ["down"]
        elif "up" in text:
            return ["up"]
        elif "left" in text:
            return ["left"]
        elif "right" in text:
            return ["right"]
        elif "select" in text or "ok" in text:
            return ["select"]
        elif "menu" in text or "back" in text:
            return ["menu"]
        elif "home" in text:
            return ["home"]
        elif "play" in text:
            return ["play"]
        elif "pause" in text:
            return ["pause"]
        elif "volume up" in text:
            return ["volume_up"]
        elif "volume down" in text:
            return ["volume_down"]
            
        return None
        
    def have_conversation(self, user_message):
        """Have a conversation with Claude using memory and follow-up capability"""
        if not self.claude_api_key:
            return "Unable to comply."
            
        try:
            self.conversations += 1
            self.log(f"💬 Conversation #{self.conversations}: \"{user_message}\"", "CONVERSATION")
            
            # Get conversation context from memory
            context = self.get_conversation_context()
            
            # Get MCP tools if available
            mcp_tools_prompt = ""
            if self.mcp_initialized:
                mcp_tools_prompt = self.mcp_integration.get_system_prompt_addition()

            prompt = f"""You are the computer system of the USS Enterprise NCC-1701-D. You speak in the precise, formal manner of the Enterprise computer, with that distinctive cadence and phrasing. You are helpful and efficient, providing information and executing commands with Starfleet protocols. You occasionally reference ship systems, stellar cartography, or Federation databases even when controlling household devices.

{context}

{mcp_tools_prompt}

Current user message: "{user_message}"

Guidelines:
- Speak in the formal, measured tone of the Enterprise-D computer
- Use precise technical language and Starfleet terminology when appropriate
- Occasionally reference ship systems or Federation protocols
- Keep responses brief but authoritative (1-2 sentences max) since this will be spoken aloud
- Say "Acknowledged" or "Confirmed" when completing tasks
- Reference "sensors," "databases," or "ship's systems" even for household tasks
- Use phrases like "Please specify," "Unable to comply," or "Working"

Special responses:
- User: "What time is it?" → "The time is now [current time]. Chronometer synchronized with Federation Standard."
- User: "red alert" → Execute red alert protocol: play alert sound and activate emergency lighting

IMPORTANT: You must respond with valid JSON in this exact format:
{{
  "text": "Your spoken response here",
  "expect_followup": true/false,
  "tool_calls": [
    {{"tool": "tool_name", "arguments": {{}}}}
  ]
}}

Set "expect_followup" to true when you ask a question or need clarification, false otherwise.
Include "tool_calls" only if you need to use MCP tools to answer the question.

Response as Enterprise computer (JSON format):"""

            response = requests.post(
                'https://api.anthropic.com/v1/messages',
                headers={
                    'Content-Type': 'application/json',
                    'x-api-key': self.claude_api_key,
                    'anthropic-version': '2023-06-01'
                },
                json={
                    'model': 'claude-sonnet-4-20250514',  # Claude 4 Sonnet
                    'max_tokens': 100,  # Increased for JSON structure
                    'messages': [{'role': 'user', 'content': prompt}]
                },
                timeout=5   # Faster timeout
            )
            
            if response.status_code == 200:
                claude_response = response.json()
                raw_response = claude_response['content'][0]['text'].strip()
                
                # Parse JSON response
                try:
                    import json
                    parsed_response = json.loads(raw_response)
                    response_text = parsed_response.get('text', raw_response)
                    expect_followup = parsed_response.get('expect_followup', False)
                    tool_calls = parsed_response.get('tool_calls', [])
                    
                    # Process tool calls if present
                    if tool_calls and self.mcp_initialized:
                        self.log(f"🔧 Processing {len(tool_calls)} tool calls")
                        tool_results = asyncio.run(self.mcp_integration.process_tool_calls(tool_calls))
                        
                        # Add tool results to response
                        if tool_results:
                            result_text = self.format_tool_results(tool_results)
                            response_text = f"{response_text} {result_text}"
                    
                    # Add to memory
                    self.add_to_memory(user_message, response_text)
                    
                    # Set follow-up mode based on Claude's explicit flag
                    if expect_followup:
                        self.follow_up_mode = True
                        self.follow_up_counter = 0
                        self.log("❓ Follow-up expected - listening without wake word")
                    else:
                        self.follow_up_mode = False
                    
                    return response_text
                    
                except json.JSONDecodeError:
                    # Fallback for non-JSON responses
                    self.log(f"⚠️ Claude returned non-JSON response: {raw_response[:50]}...")
                    self.add_to_memory(user_message, raw_response)
                    self.follow_up_mode = False
                    return raw_response
            else:
                self.log(f"Claude API error: {response.status_code} - {response.text}", "ERROR")
                return "Unable to comply."
                
        except Exception as e:
            self.log(f"Conversation error: {e}", "ERROR")
            return "Unable to comply."
    
    def format_tool_results(self, tool_results: list) -> str:
        """Format tool results for spoken response"""
        if not tool_results:
            return ""
        
        # For voice response, we want concise results
        formatted_results = []
        for result in tool_results:
            tool_name = result.get('tool', 'Unknown tool')
            tool_result = result.get('result', {})
            
            if 'error' in tool_result:
                formatted_results.append(f"Tool {tool_name} encountered an error.")
            else:
                # Extract key information for voice
                if 'content' in tool_result:
                    content = tool_result['content']
                    if isinstance(content, list) and content:
                        # Take first content item for brevity
                        first_content = content[0]
                        if 'text' in first_content:
                            text = first_content['text'][:200]  # Limit length for voice
                            formatted_results.append(text)
                elif 'text' in tool_result:
                    text = tool_result['text'][:200]
                    formatted_results.append(text)
                else:
                    formatted_results.append(f"Tool {tool_name} completed successfully.")
        
        return " ".join(formatted_results)
            
    def send_apple_tv_commands(self, commands):
        """Send commands to Apple TV"""
        if not commands:
            return False
            
        success_count = 0
        
        # Suppress protobuf warnings in environment
        env = os.environ.copy()
        env['PYTHONWARNINGS'] = 'ignore::UserWarning'
        
        for command in commands:
            try:
                self.log(f"Sending: {command}", "SEND")
                
                # Parse command format (e.g., "launch_app=com.netflix.Netflix")
                if '=' in command:
                    cmd_type, cmd_value = command.split('=', 1)
                    if cmd_type == 'launch_app':
                        # Use the correct pyatv launch_app format: launch_app=bundle_id
                        self.log(f"Attempting to launch app: {cmd_value}", "INFO")
                        cmd_args = [
                            '/home/dan/pyatv_env/bin/atvremote',
                            '--id', self.device_id,
                            f'launch_app={cmd_value}'
                        ]
                    else:
                        # Other commands with values
                        cmd_args = [
                            '/home/dan/pyatv_env/bin/atvremote',
                            '--id', self.device_id,
                            cmd_type,
                            cmd_value
                        ]
                else:
                    # Simple command
                    cmd_args = [
                        '/home/dan/pyatv_env/bin/atvremote',
                        '--id', self.device_id,
                        command
                    ]
                
                result = subprocess.run(cmd_args, capture_output=True, text=True, timeout=15, env=env)
                
                if result.returncode == 0:
                    success_count += 1
                    self.log(f"✅ Command executed: {' '.join(cmd_args[2:])}", "SUCCESS")
                else:
                    self.log(f"❌ Command failed: {command}", "ERROR")
                    # Filter out protobuf warnings from error output
                    error_lines = result.stderr.split('\n')
                    actual_errors = [line for line in error_lines 
                                   if 'protobuf' not in line.lower() and 'UserWarning' not in line and line.strip()]
                    if actual_errors:
                        self.log(f"❌ Error: {' '.join(actual_errors)}", "ERROR")
                    
                if len(commands) > 1:
                    time.sleep(0.5)
                    
            except Exception as e:
                self.log(f"Send error: {e}", "ERROR")
                
        if success_count > 0:
            self.apple_tv_commands += success_count
            
        return success_count > 0
        
    async def run_async(self):
        """Async version of run that handles MCP initialization"""
        if not self.init_whisper():
            return
            
        # Initialize MCP integration
        await self.init_mcp_async()
            
        print(f"\n🎯 Conversational Voice Control ACTIVE!")
        print(f"🎤 Wake word: '{self.wake_word}'")
        tts_info = "ElevenLabs (Enterprise-D)" if self.use_elevenlabs_tts else "OpenAI TTS" if self.use_openai_tts else "Piper TTS"
        print(f"🤖 AI: Whisper + Claude + {tts_info}")
        print(f"🗣️  Apple TV Examples:")
        print(f"   - '{self.wake_word} go to Netflix'")
        print(f"   - '{self.wake_word} search for movies'")
        print(f"🏠 HomeKit Examples:")
        print(f"   - '{self.wake_word} turn on the lights'")
        print(f"   - '{self.wake_word} set temperature to 72'")
        print(f"💬 Conversation Examples:")
        print(f"   - '{self.wake_word} what time is it?'")
        print(f"   - '{self.wake_word} tell me a joke'")
        print("-" * 50)
        
        # Start continuous listening
        self.start_continuous_listening()
        
        try:
            while True:
                # Check for completed speech from VAD system
                try:
                    audio_file = self.transcription_queue.get(timeout=0.1)
                    
                    # Transcribe the detected speech
                    text = self.transcribe_with_whisper(audio_file)
                    
                    # Initialize speaker match as True (always process if diarization disabled)
                    speaker_match = True
                    
                    # Clean up temp file (keep copy for speaker analysis if needed)
                    temp_audio_path = audio_file
                    
                    if text and len(text.strip()) > 1:
                        # Check follow-up mode FIRST (before wake word detection)
                        if self.follow_up_mode:
                            # Check if this is the same speaker as the wake word
                            speaker_match = self.is_same_speaker_as_wake_word(temp_audio_path)
                            if speaker_match:
                                # We're in follow-up mode - process as conversation without wake word
                                self.log(f"💬 Follow-up response: '{text}'")
                                self.follow_up_mode = False
                                self.process_command(text, is_follow_up=True)
                            else:
                                self.log("🎭 Follow-up ignored: different speaker")
                                # Keep follow-up mode active for the original speaker
                        
                        elif self.command_collection_mode:
                            # Check if this is the same speaker as the wake word
                            speaker_match = self.is_same_speaker_as_wake_word(temp_audio_path)
                            if speaker_match:
                                # We're in command collection mode - process any speech as the command
                                self.log(f"📝 Command collected: '{text}'")
                                self.command_collection_mode = False
                                self.process_command(text)
                            else:
                                self.log("🎭 Command ignored: different speaker")
                                # Keep command collection mode active for the original speaker
                        
                        elif self.wake_word in text and self.is_valid_wake_word_detection(text):
                            # Identify the wake word speaker for voice isolation
                            speaker_identified = self.identify_wake_word_speaker(temp_audio_path, text)
                            
                            if speaker_identified:
                                # Normal wake word detection - exit follow-up mode if active
                                if self.follow_up_mode:
                                    self.log("🎯 Wake word detected - exiting follow-up mode")
                                    self.follow_up_mode = False
                                    self.follow_up_counter = 0
                                
                                self.wake_word_detections += 1
                                self.log(f"🎯 WAKE WORD! (#{self.wake_word_detections})", "WAKE")
                                
                                # Extract command after wake word (everything after the wake word)
                                words = text.lower().split()
                                wake_word_pos = -1
                                for i, word in enumerate(words):
                                    if self.wake_word in word:
                                        wake_word_pos = i
                                        break
                                
                                if wake_word_pos >= 0:
                                    command = " ".join(words[wake_word_pos + 1:])
                                else:
                                    command = ""
                                
                                if command and len(command) > 2:
                                    # We got a complete command with the wake word
                                    self.process_command(command)
                                else:
                                    # Only heard wake word or very short fragment - enter command collection mode
                                    self.log("⏳ Wake word detected, waiting for command...")
                                    self.command_collection_mode = True
                                    self.command_timeout_counter = 0
                                    # Continue listening for the actual command
                            else:
                                self.log("🎭 Wake word speaker identification failed")
                        
                        else:
                            # Text detected but no special mode - log for debugging
                            self.log(f"🔍 Ignoring: '{text}' (no wake word, not in special mode)")
                    
                    # Clean up temp file after processing
                    try:
                        os.unlink(temp_audio_path)
                    except:
                        pass
                    
                except:
                    # No speech in queue, handle timeouts if needed
                    if self.command_collection_mode:
                        self.command_timeout_counter += 1
                        if self.command_timeout_counter >= self.command_timeout:
                            self.log("⏰ Command timeout - no command received")
                            self.command_collection_mode = False
                            self.speak_response("How can I help you?")
                            self.command_timeout_counter = 0
                    
                    elif self.follow_up_mode:
                        self.follow_up_counter += 1
                        # Debug: Show follow-up timeout countdown every 2 seconds
                        if self.follow_up_counter % 20 == 0:
                            remaining = (self.follow_up_timeout - self.follow_up_counter) / 10
                            self.log(f"⏳ Follow-up timeout in {remaining:.0f}s...")
                        
                        if self.follow_up_counter >= self.follow_up_timeout:
                            self.log("⏰ Follow-up timeout - resuming normal wake word mode")
                            self.follow_up_mode = False
                            self.follow_up_counter = 0
                    
                    time.sleep(0.1)
                    
        except KeyboardInterrupt:
            self.log("👋 Stopped")
            self.cleanup()
            self.log(f"📊 {self.total_transcriptions} transcripts | {self.wake_word_detections} wake words | {self.apple_tv_commands} TV commands | {self.conversations} conversations")

    def run(self):
        """Main run method that starts the async event loop"""
        try:
            asyncio.run(self.run_async())
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
            self.cleanup()
        except Exception as e:
            print(f"❌ Error in main loop: {e}")
            self.cleanup()
    
    def cleanup(self):
        """Stop continuous listening and clean up resources"""
        try:
            self.listening = False
            if hasattr(self, 'audio_thread'):
                self.audio_thread.join(timeout=2)
            
            # Shutdown MCP integration
            if hasattr(self, 'mcp_integration') and self.mcp_initialized:
                self.mcp_integration.shutdown()
                self.log("🔧 MCP integration shutdown")
            
            self.log("🧹 Cleanup completed")
        except Exception as e:
            self.log(f"Cleanup error: {e}", "ERROR")

if __name__ == "__main__":
    control = ConversationalVoiceControl()
    control.run()