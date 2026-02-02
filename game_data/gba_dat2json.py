import re
import json
import requests

def convert_combined_databases(dat_url, flashgbx_url):
    print("Fetching databases...")
    fg_response = requests.get(flashgbx_url)
    fg_data = fg_response.json()
    
    dat_response = requests.get(dat_url)
    dat_content = dat_response.text
    
    save_types = {1: "SRAM/FLASH", 2: "EEPROM", 3: "FLASH (Alt)", 4: "None"}
    
    # We use a dictionary of lists to group by Game Code first for filtering
    grouped_entries = {}

    def add_entry(game_id, entry):
        if game_id not in grouped_entries:
            grouped_entries[game_id] = []
        # Avoid exact duplicates (same title and checksum)
        if not any(e['full_title'] == entry['full_title'] and e['global_checksum'] == entry['global_checksum'] for e in grouped_entries[game_id]):
            grouped_entries[game_id].append(entry)

    # --- PHASE 1: Process FlashGBX ---
    for info in fg_data.values():
        game_id = info.get("gc")
        crc_val = info.get('rc')
        if not game_id or crc_val is None: 
            continue

        crc_hex = f"0x{hex(crc_val)[2:].upper()}"
        
        # RAM Logic: ss / 1024
        val_ss = info.get("ss", 0)
        ram_val_kib = val_ss / 1024
        ram_size_str = f"{int(ram_val_kib) if ram_val_kib % 1 == 0 else ram_val_kib} KiB"
        
        gn = info.get('gn', 'Unknown')
        ne = info.get('ne', '')
        full_title = f"{gn} {ne}".strip()
        
        # Fixed: Calculate ROM size outside the f-string to avoid backslash error
        rs_bytes = info.get('rs', 0)
        rom_size_mib = f"{rs_bytes // (1024*1024)} MiB"

        entry = {
            "full_title": f"{full_title}.gba",
            "title": gn.split('(')[0].strip().upper(),
            "CGB_support": False,
            "SGB_support": False,
            "cartridge_type": f"GBA {save_types.get(info.get('st', 0), 'Standard')}",
            "ROM_size": rom_size_mib,
            "RAM_size": ram_size_str,
            "destination": info.get('rg', 'Unknown'),
            "ROM_version": "0x00",
            "header_checksum": None,
            "global_checksum": crc_hex
        }
        add_entry(game_id, entry)

    # --- PHASE 2: Process Libretro DAT ---
    game_blocks = dat_content.split('game (')[1:]
    for block in game_blocks:
        serial_match = re.search(r'serial\s+"?([A-Z0-9]{4})"?', block)
        crc_match = re.search(r'crc\s+([0-9A-F]{8})', block, re.IGNORECASE)
        if not serial_match or not crc_match: 
            continue
        
        game_id = serial_match.group(1)
        crc_hex = f"0x{crc_match.group(1).upper()}"
        
        name_match = re.search(r'name\s+"(.*?)"', block)
        dat_full_title = f"{name_match.group(1)}.gba"

        # Fixed: Move regex search and calculation outside the f-string
        size_match = re.search(r'size\s+(\d+)', block)
        size_bytes = int(size_match.group(1)) if size_match else 0
        rom_size_mib = f"{size_bytes // (1024*1024)} MiB"
        
        reg_match = re.search(r'region\s+"(.*?)"', block)
        destination = reg_match.group(1) if reg_match else "Unknown"

        entry = {
            "full_title": dat_full_title,
            "title": dat_full_title.replace('.gba', '').split('(')[0].strip().upper(),
            "CGB_support": False,
            "SGB_support": False,
            "cartridge_type": "GBA Standard",
            "ROM_size": rom_size_mib,
            "RAM_size": "0 KiB",
            "destination": destination,
            "ROM_version": "0x00",
            "header_checksum": None,
            "global_checksum": crc_hex
        }
        add_entry(game_id, entry)

    # --- PHASE 3: Filter Betas and Flatten ---
    final_list = []
    for game_id, entries in grouped_entries.items():
        # Check if any entry for this game_id is NOT a beta
        has_final_version = any("(Beta)" not in e["full_title"] for e in entries)
        
        for e in entries:
            # If a final version exists, skip this entry if it's a beta
            if has_final_version and "(Beta)" in e["full_title"]:
                continue
            final_list.append((game_id, e))

    # --- MANUAL STRING WRITING WITH 8-SPACE INDENTATION ---
    print(f"Writing {len(final_list)} entries to file...")
    with open('gba_roms_info.json', 'w', encoding='utf-8') as f:
        f.write("{\n")
        for i, (game_code, data) in enumerate(final_list):
            raw_json = json.dumps(data, indent=4, ensure_ascii=False)
            lines = raw_json.splitlines()
            
            f.write(f'    "{game_code}":\n')
            for j, line in enumerate(lines):
                if j == 0:
                    f.write('        {\n')
                elif j == len(lines) - 1:
                    f.write('        }')
                else:
                    # Content indented with 12 spaces (8 base + 4 nested)
                    f.write('            ' + line.strip() + '\n')
            
            if i < len(final_list) - 1:
                f.write(",\n")
            else:
                f.write("\n")
        f.write("}")

# Run
url_dat = "https://raw.githubusercontent.com/libretro/libretro-database/master/metadat/no-intro/Nintendo%20-%20Game%20Boy%20Advance.dat"
url_flash = "https://raw.githubusercontent.com/Lesserkuma/FlashGBX/master/FlashGBX/config/db_AGB.json"

convert_combined_databases(url_dat, url_flash)
print("Processing complete! Output saved to gba_roms_info.json")
