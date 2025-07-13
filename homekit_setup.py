#!/usr/bin/env python3
"""HomeKit Device Discovery and Pairing Tool"""

import json
import time
from homekit.controller import Controller

def discover_devices():
    """Discover available HomeKit devices"""
    print("🔍 Discovering HomeKit devices...")
    controller = Controller()
    
    try:
        devices = controller.discover(timeout=15)
        
        if not devices:
            print("❌ No HomeKit devices found")
            print("\nTroubleshooting:")
            print("1. Make sure devices are in pairing mode")
            print("2. Check if devices are already paired to another controller")
            print("3. Ensure devices are on the same network")
            return []
        
        print(f"\n✅ Found {len(devices)} HomeKit device(s):")
        for i, device in enumerate(devices):
            print(f"{i+1}. {device.name} (ID: {device.device_id})")
            print(f"   Category: {device.category}")
            print(f"   Can Pair: {device.can_pair}")
            print()
        
        return devices
        
    except Exception as e:
        print(f"❌ Discovery error: {e}")
        return []

def pair_device(device_id, pin):
    """Pair with a HomeKit device"""
    controller = Controller()
    
    try:
        print(f"🔗 Pairing with device {device_id}...")
        pairing = controller.perform_pairing(device_id, device_id, pin)
        
        # Save pairing data
        pairing_data = {device_id: pairing.pairing_data}
        
        # Load existing pairings if any
        try:
            with open('/home/dan/homekit_pairings.json', 'r') as f:
                existing = json.load(f)
            existing.update(pairing_data)
            pairing_data = existing
        except FileNotFoundError:
            pass
        
        # Save updated pairings
        with open('/home/dan/homekit_pairings.json', 'w') as f:
            json.dump(pairing_data, f, indent=2)
        
        print(f"✅ Successfully paired with {device_id}")
        
        # List device characteristics
        try:
            accessories = pairing.list_accessories_and_characteristics()
            print(f"\n📱 Device capabilities:")
            for accessory in accessories:
                print(f"  Accessory {accessory['aid']}:")
                for service in accessory['services']:
                    service_type = service.get('type', 'Unknown')
                    print(f"    Service: {service_type}")
                    for char in service['characteristics']:
                        char_type = char.get('type', 'Unknown')
                        print(f"      - {char_type}")
        except Exception as e:
            print(f"⚠️ Could not list capabilities: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Pairing failed: {e}")
        return False

def list_paired_devices():
    """List already paired devices"""
    try:
        with open('/home/dan/homekit_pairings.json', 'r') as f:
            pairings = json.load(f)
        
        if not pairings:
            print("📱 No paired devices found")
            return
        
        print(f"📱 Paired devices ({len(pairings)}):")
        for device_id in pairings.keys():
            print(f"  - {device_id}")
            
    except FileNotFoundError:
        print("📱 No paired devices found")
    except Exception as e:
        print(f"❌ Error reading pairings: {e}")

def main():
    print("🏠 HomeKit Setup Tool")
    print("=" * 30)
    
    while True:
        print("\nOptions:")
        print("1. Discover devices")
        print("2. Pair device")
        print("3. List paired devices")
        print("4. Exit")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == "1":
            devices = discover_devices()
            
        elif choice == "2":
            device_id = input("Enter device ID: ").strip()
            pin = input("Enter 8-digit PIN from device: ").strip()
            
            if len(pin) != 8 or not pin.isdigit():
                print("❌ PIN must be 8 digits")
                continue
                
            pair_device(device_id, pin)
            
        elif choice == "3":
            list_paired_devices()
            
        elif choice == "4":
            print("👋 Goodbye!")
            break
            
        else:
            print("❌ Invalid option")

if __name__ == "__main__":
    main()