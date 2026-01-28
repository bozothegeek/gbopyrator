import re
import json
import requests

def convert_libretro_dat_to_json(url):
    # 1. Fetch the DAT file
    print("Fetching DAT file...")
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Error: Could not download file (Status {response.status_code})")
        return
    
    content = response.text

    # 2. Split into blocks based on 'game ('
    # The first split index [0] is the header info, so we skip it
    game_blocks = content.split('game (')[1:]
    
    rom_database = {}

    for block in game_blocks:
        # Extract Serial (e.g., BJBJ)
        serial_match = re.search(r'serial\s+"?([A-Z0-9]{4})"?', block)
        if not serial_match:
            continue
        
        game_id = serial_match.group(1)

        # Extract Full Title
        name_match = re.search(r'name\s+"(.*?)"', block)
        full_title = name_match.group(1) if name_match else "Unknown"

        # Extract ROM Size (convert bytes to MiB)
        size_match = re.search(r'size\s+(\d+)', block)
        size_bytes = int(size_match.group(1)) if size_match else 0
        rom_size_mib = f"{size_bytes // (1024*1024)} MiB" if size_bytes else "Unknown"

        # Extract Region
        region_match = re.search(r'region\s+"(.*?)"', block)
        destination = region_match.group(1) if region_match else "Unknown"
        
        # NEW: Extract CRC for global_checksum
        crc_match = re.search(r'crc\s+([0-9A-F]{8})', block, re.IGNORECASE)
        crc_hex = crc_match.group(1).upper() if crc_match else None

        # Build the JSON object
        rom_database[game_id] = {
            "full_title": f"{full_title}.gba",
            "title": full_title.split('(')[0].strip().upper(),
            "CGB_support": False,
            "SGB_support": False,
            "cartridge_type": "GBA Standard",
            "ROM_size": rom_size_mib,
            "RAM_size": 0,
            "destination": destination,
            "ROM_version": "0x00",
            "header_checksum": None,
            "global_checksum": f"0x{crc_hex}" if crc_hex else None
        }

    return rom_database

# Execute
url = "https://raw.githubusercontent.com/libretro/libretro-database/master/metadat/no-intro/Nintendo%20-%20Game%20Boy%20Advance.dat"
gba_json = convert_libretro_dat_to_json(url)

if gba_json:
    with open('gba_roms_info.json', 'w', encoding='utf-8') as f:
        json.dump(gba_json, f, indent=4)
    print(f"Successfully created gba_rom_database.json with {len(gba_json)} entries.")
    