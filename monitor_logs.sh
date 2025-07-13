#!/bin/bash
# Live monitor voice control logs on Raspberry Pi

echo "🎤 Starting voice control with live logging..."
echo "Press Ctrl+C to stop"
echo "=" * 50

ssh -o StrictHostKeyChecking=no dan@pi5.local "cd /home/dan && source pyatv_env/bin/activate && python3 conversational_voice_control.py 2>&1 | tee -a voice_control.log"