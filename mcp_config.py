#!/usr/bin/env python3
"""MCP Configuration Management System for Voice Assistant"""

import json
import os
import subprocess
import sys
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class MCPServer:
    """Configuration for an MCP server"""
    name: str
    command: str
    args: List[str]
    description: str
    enabled: bool = True
    added_date: str = ""
    
    def __post_init__(self):
        if not self.added_date:
            self.added_date = datetime.now().isoformat()

class MCPManager:
    """Manages MCP server configurations and connections"""
    
    def __init__(self, config_file: str = "/home/dan/mcp_config.json"):
        self.config_file = config_file
        self.servers: Dict[str, MCPServer] = {}
        self.load_config()
    
    def load_config(self):
        """Load MCP configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.servers = {
                        name: MCPServer(**server_data) 
                        for name, server_data in data.get('servers', {}).items()
                    }
                print(f"✅ Loaded {len(self.servers)} MCP servers from config")
            else:
                print("📝 No existing MCP config found, starting fresh")
                self.servers = {}
        except Exception as e:
            print(f"❌ Error loading MCP config: {e}")
            self.servers = {}
    
    def save_config(self):
        """Save MCP configuration to file"""
        try:
            config_data = {
                "servers": {
                    name: asdict(server) 
                    for name, server in self.servers.items()
                },
                "last_updated": datetime.now().isoformat()
            }
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            print(f"✅ Saved MCP configuration to {self.config_file}")
            return True
        except Exception as e:
            print(f"❌ Error saving MCP config: {e}")
            return False
    
    def add_server(self, name: str, command: str, args: List[str], description: str):
        """Add a new MCP server"""
        if name in self.servers:
            print(f"⚠️ MCP server '{name}' already exists")
            return False
        
        server = MCPServer(
            name=name,
            command=command,
            args=args,
            description=description
        )
        
        self.servers[name] = server
        self.save_config()
        print(f"✅ Added MCP server: {name}")
        return True
    
    def remove_server(self, name: str):
        """Remove an MCP server"""
        if name not in self.servers:
            print(f"❌ MCP server '{name}' not found")
            return False
        
        del self.servers[name]
        self.save_config()
        print(f"✅ Removed MCP server: {name}")
        return True
    
    def enable_server(self, name: str):
        """Enable an MCP server"""
        if name not in self.servers:
            print(f"❌ MCP server '{name}' not found")
            return False
        
        self.servers[name].enabled = True
        self.save_config()
        print(f"✅ Enabled MCP server: {name}")
        return True
    
    def disable_server(self, name: str):
        """Disable an MCP server"""
        if name not in self.servers:
            print(f"❌ MCP server '{name}' not found")
            return False
        
        self.servers[name].enabled = False
        self.save_config()
        print(f"✅ Disabled MCP server: {name}")
        return True
    
    def list_servers(self):
        """List all configured MCP servers"""
        if not self.servers:
            print("📝 No MCP servers configured")
            return
        
        print("\n🔧 Configured MCP Servers:")
        print("=" * 60)
        
        for name, server in self.servers.items():
            status = "🟢 ENABLED" if server.enabled else "🔴 DISABLED"
            print(f"\n📦 {name} - {status}")
            print(f"   Command: {server.command} {' '.join(server.args)}")
            print(f"   Description: {server.description}")
            print(f"   Added: {server.added_date[:19]}")
    
    def test_server(self, name: str):
        """Test if an MCP server can be started"""
        if name not in self.servers:
            print(f"❌ MCP server '{name}' not found")
            return False
        
        server = self.servers[name]
        if not server.enabled:
            print(f"⚠️ MCP server '{name}' is disabled")
            return False
        
        try:
            print(f"🧪 Testing MCP server: {name}")
            
            # Try to start the MCP server process
            cmd = [server.command] + server.args
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait briefly to see if it starts successfully
            try:
                stdout, stderr = process.communicate(timeout=3)
                if process.returncode == 0:
                    print(f"✅ MCP server '{name}' started successfully")
                    return True
                else:
                    print(f"❌ MCP server '{name}' failed: {stderr}")
                    return False
            except subprocess.TimeoutExpired:
                process.terminate()
                print(f"✅ MCP server '{name}' appears to be running (timeout after 3s)")
                return True
                
        except Exception as e:
            print(f"❌ Error testing MCP server '{name}': {e}")
            return False
    
    def get_enabled_servers(self) -> Dict[str, MCPServer]:
        """Get all enabled MCP servers"""
        return {
            name: server 
            for name, server in self.servers.items() 
            if server.enabled
        }

def main():
    """CLI interface for MCP management"""
    manager = MCPManager()
    
    if len(sys.argv) < 2:
        print("\n🤖 MCP Configuration Manager for Voice Assistant")
        print("=" * 50)
        print("Usage: python3 mcp_config.py <command> [args]")
        print("\nCommands:")
        print("  list                     - List all MCP servers")
        print("  add <name> <cmd> <args>  - Add new MCP server")
        print("  remove <name>            - Remove MCP server")
        print("  enable <name>            - Enable MCP server")
        print("  disable <name>           - Disable MCP server")
        print("  test <name>              - Test MCP server connection")
        print("  test-all                 - Test all enabled servers")
        print("\nExample:")
        print("  python3 mcp_config.py add weather 'npx' '@modelcontextprotocol/server-weather'")
        return
    
    command = sys.argv[1].lower()
    
    if command == "list":
        manager.list_servers()
    
    elif command == "add":
        if len(sys.argv) < 5:
            print("❌ Usage: add <name> <command> <args...>")
            return
        
        name = sys.argv[2]
        cmd = sys.argv[3]
        args = sys.argv[4:]
        
        # Get description from user
        description = input(f"📝 Enter description for '{name}': ").strip()
        if not description:
            description = f"MCP server: {name}"
        
        manager.add_server(name, cmd, args, description)
    
    elif command == "remove":
        if len(sys.argv) < 3:
            print("❌ Usage: remove <name>")
            return
        
        name = sys.argv[2]
        confirm = input(f"⚠️ Remove MCP server '{name}'? (y/N): ").strip().lower()
        if confirm in ['y', 'yes']:
            manager.remove_server(name)
        else:
            print("❌ Cancelled")
    
    elif command == "enable":
        if len(sys.argv) < 3:
            print("❌ Usage: enable <name>")
            return
        manager.enable_server(sys.argv[2])
    
    elif command == "disable":
        if len(sys.argv) < 3:
            print("❌ Usage: disable <name>")
            return
        manager.disable_server(sys.argv[2])
    
    elif command == "test":
        if len(sys.argv) < 3:
            print("❌ Usage: test <name>")
            return
        manager.test_server(sys.argv[2])
    
    elif command == "test-all":
        print("🧪 Testing all enabled MCP servers...")
        enabled = manager.get_enabled_servers()
        if not enabled:
            print("📝 No enabled MCP servers to test")
            return
        
        for name in enabled:
            manager.test_server(name)
            print()
    
    else:
        print(f"❌ Unknown command: {command}")

if __name__ == "__main__":
    main()