import re
import json
import requests

def convert_libretro_dat_to_json(dat_url, flashgbx_url):
    # 1. Fetch and index FlashGBX database
    print("Fetching and indexing FlashGBX database...")
    fg_response = requests.get(flashgbx_url)
    flash_lookup = {}
    
    if fg_response.status_code == 200:
        flash_data = fg_response.json()
        for info in flash_data.values():
            game_code = info.get("gc")
            if game_code:
                flash_lookup[game_code] = info
    else:
        print("Warning: Could not fetch FlashGBX DB.")

    # 2. Fetch the Libretro DAT file
    print("Fetching Libretro DAT file...")
    response = requests.get(dat_url)
    if response.status_code != 200:
        print(f"Error: Could not download DAT")
        return
    
    content = response.text
    game_blocks = content.split('game (')[1:]
    rom_database = {}

    # FlashGBX Save Types Mapping
    save_types = {1: "SRAM/FLASH", 2: "EEPROM", 3: "FLASH (Alt)", 4: "None"}

    for block in game_blocks:
        # Extract Serial (e.g., "AZFE")
        serial_match = re.search(r'serial\s+"?([A-Z0-9]{4})"?', block)
        if not serial_match:
            continue
        
        game_id = serial_match.group(1)

        # Extract basic info from Libretro DAT
        name_match = re.search(r'name\s+"(.*?)"', block)
        full_title = name_match.group(1) if name_match else "Unknown"

        size_match = re.search(r'size\s+(\d+)', block)
        size_bytes = int(size_match.group(1)) if size_match else 0
        rom_size_mib = f"{size_bytes // (1024*1024)} MiB" if size_bytes else "Unknown"

        region_match = re.search(r'region\s+"(.*?)"', block)
        destination = region_match.group(1) if region_match else "Unknown"
        
        crc_match = re.search(r'crc\s+([0-9A-F]{8})', block, re.IGNORECASE)
        crc_hex = crc_match.group(1).upper() if crc_match else None

        # --- RAM CONVERSION LOGIC ---
        ram_size_str = "0 KiB"
        cart_type = "GBA Standard"
        
        if game_id in flash_lookup:
            fg_info = flash_lookup[game_id]
            val_ss = fg_info.get("ss", 0) # Raw value from FlashGBX
            st_type = fg_info.get("st", 0)
            
            # Per your requirement: 512 results in 0.5 KiB
            # This implies val_ss is in bytes: val_ss / 1024 = KiB
            if val_ss > 0:
                ram_val_kib = val_ss / 1024
                # Clean formatting: remove .0 if it's an integer
                if ram_val_kib % 1 == 0:
                    ram_size_str = f"{int(ram_val_kib)} KiB"
                else:
                    ram_size_str = f"{ram_val_kib} KiB"
            
            cart_type = f"GBA {save_types.get(st_type, 'Standard')}"

        # Build the final JSON object
        rom_database[game_id] = {
            "full_title": f"{full_title}.gba",
            "title": full_title.split('(')[0].strip().upper(),
            "CGB_support": False,
            "SGB_support": False,
            "cartridge_type": cart_type,
            "ROM_size": rom_size_mib,
            "RAM_size": ram_size_str, 
            "destination": destination,
            "ROM_version": "0x00",
            "header_checksum": None,
            "global_checksum": f"0x{crc_hex}" if crc_hex else None
        }

    return rom_database

# URLs
url_dat = "https://raw.githubusercontent.com/libretro/libretro-database/master/metadat/no-intro/Nintendo%20-%20Game%20Boy%20Advance.dat"
url_flash = "https://raw.githubusercontent.com/Lesserkuma/FlashGBX/master/FlashGBX/config/db_AGB.json"

gba_json = convert_libretro_dat_to_json(url_dat, url_flash)

if gba_json:
    with open('gba_roms_info.json', 'w', encoding='utf-8') as f:
        json.dump(gba_json, f, indent=4)
    print(f"Success! {len(gba_json)} entries processed. RAM calculated as ss/1024.")
    