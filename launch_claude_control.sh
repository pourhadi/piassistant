#!/bin/bash
# Launch Enterprise Voice Control System

cd /home/dan

# Load API keys from environment
source ~/.bashrc

# Ensure we have the required API keys
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ ANTHROPIC_API_KEY not found in environment"
    echo "Please add your Claude API key to ~/.bashrc:"
    echo "echo 'export ANTHROPIC_API_KEY=your_key_here' >> ~/.bashrc"
    exit 1
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ OPENAI_API_KEY not found in environment"
    echo "Please add your OpenAI API key to ~/.bashrc:"
    echo "echo 'export OPENAI_API_KEY=your_key_here' >> ~/.bashrc"
    exit 1
fi

# Activate Python environment
source pyatv_env/bin/activate

echo "🚀 Starting Enterprise Voice Control System..."
echo "🖖 Computer systems online. Ready for voice commands."
python3 conversational_voice_control.py