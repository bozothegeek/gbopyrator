# %%
import argparse
from .cartridge_utils import CartridgeReader
from importlib.resources import files
import json

def parse_size_to_bytes(size_str):
    """
    Convert a string as '4 MiB' or '128 KiB' in 'bytes' number (int).
    """
    if not size_str:
        return 0
        
    # clean string (remove space and upper case)
    size_str = size_str.upper().replace(' ', '')
    
    try:
        if "MIB" in size_str:
            number = float(size_str.replace("MIB", ""))
            return int(number * 1024 * 1024)
        elif "KIB" in size_str:
            number = float(size_str.replace("KIB", ""))
            return int(number * 1024)
        elif "MB" in size_str: # Security if the 'i' is forgotten
            number = float(size_str.replace("MB", ""))
            return int(number * 1024 * 1024)
    except ValueError:
        print(f"Error : Impossible to read size '{size_str}'")
        return 0
    
    return 0

def detect_gba_ram_size(rom_data):
    # Common strings used by GBA libraries (AgbSram, AgbFlash, etc.)
    if b"SRAM_V" in rom_data:
        return "32 KiB"
    elif b"FLASH_V" in rom_data or b"FLASH512_V" in rom_data:
        return "64 KiB"
    elif b"FLASH1M_V" in rom_data:
        return "128 KiB"
    elif b"EEPROM_V" in rom_data:
        # EEPROM is tricky; it can be 0.5 KiB or 8 KiB. 
        # Most databases default to 8 KiB for compatibility.
        return "8 KiB"
    return "0 KiB"
    
# %%
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dump-rom", type=str, default=None, help="Dump ROM to file")
    parser.add_argument("--dump-save", type=str, default=None, help="Dump save to file")
    parser.add_argument("--rom-source", type=str, default=None, help="Get ram size from rom (GBA only)")
    parser.add_argument(
        "--write-save", type=str, default=None, help="Write save from file"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        default=False,
        help="Do not output anything to stdout",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Display 'debug' info as hexdump",
    )
    args = parser.parse_args()

    # %%

    cr = CartridgeReader(quiet=args.quiet, debug=args.debug)

    cr.printer.greetings()

    if (args.dump_save is not None) and (args.write_save is not None):
        cr.printer.warning(
            "`dump-save` and `write-save` are both set. GBOpyrator will dump the save first and write it after."
        )
    cr.initialize_reader(blocking=True,timeout=10)

    #get epilogue id for GB/GBC or GBA
    rom_epilogue_id, rom_info_file = cr.get_epilogue_id_and_rom_info_file()
    if(args.debug):
        print("rom_epilogue_id: " + rom_epilogue_id)
        print("rom_info_file use: " + rom_info_file)
    #get rom info file for GB/GBC or GBA
    filename = str(files("gbopyrator").joinpath(rom_info_file))
    with open(filename, "r") as file:
        roms_db = json.load(file)
        
    # Print cartridge info
    if rom_epilogue_id in roms_db:
        rom_info = roms_db[rom_epilogue_id]
    else:
        # Fallback: Search for the first game with the same 3-character prefix
        prefix = rom_epilogue_id[:3]
        # Find the first key in the DB that starts with the prefix
        fallback_key = next((key for key in roms_db if key.startswith(prefix)), None)
        
        if fallback_key:
            rom_info = roms_db[fallback_key]
            cr.printer.print(f"[orange]Warning: Exact region match not found. Using info from {fallback_key}[/orange]")
        else:
            rom_info = None # Truly not in the database
    if rom_info != None:
        # Center "rom info" text on =80 chars
        cr.printer.print("")
        cr.printer.rule("[blue_violet]CARTRIDGE INFO")
        #using simple print to stay on one line in all cases
        cr.printer.print(f"Detected game: {rom_info['full_title']}")
        if(args.debug and args.quiet):
            print(f"Detected game: {rom_info['full_title']}")
        if rom_info["SGB_support"]:
            cr.printer.print(f"""SGB support:\t[blue_violet]Yes[/blue_violet]""")
        if rom_info["CGB_support"]:
            cr.printer.print(f"""CGB support:\t[blue_violet]Yes[/blue_violet]""")
        cr.printer.print(
            f"""ROM size:\t[blue_violet]{rom_info['ROM_size']}[/blue_violet]"""
        )
        if(args.debug and args.quiet):
            print(f"ROM size: {rom_info['ROM_size']}")
        cr.printer.print(
            f"""ROM checksum:\t[blue_violet]{rom_info['global_checksum']}[/blue_violet]"""
        )
        if(args.debug and args.quiet):
            print(f"ROM checksum: {rom_info['global_checksum']}")
        if rom_info["RAM_size"] != 0:
            cr.printer.print(
                f"""RAM size:\t[blue_violet]{rom_info['RAM_size']}[/blue_violet]"""
            )
    else:
        cr.printer.warning(
            f"ROM epilogue ID not found in the database. If you know the game, please add it to the database."
        )

    # Print dumping/writing info
    if (
        args.dump_save is not None
        or args.dump_rom is not None
        or args.write_save is not None
    ):
        cr.printer.print("")
        cr.printer.rule("[blue_violet]ROM AND SAVE OPERATIONS")

        if args.dump_save is not None:
            if rom_info['cartridge_type'] == "GBA Standard":
                #set cartridge ram size from rom content in this case and not from cartridge info
                if args.rom_source is not None:
                    with open(args.rom_source, "rb") as f:
                        rom_data = f.read()
                    rom_info['RAM_size'] = detect_gba_ram_size(rom_data)
                    cr.printer.success(f"RAM size (detected):\t[dark_cyan]{rom_info['RAM_size']}[/dark_cyan]")
                cr.dump_save(args.dump_save, parse_size_to_bytes(rom_info['RAM_size']))
            else:
                cr.dump_save(args.dump_save)

        if args.dump_rom is not None:
            if rom_info['cartridge_type'] == "GBA Standard":
                #set cartridge rom size from rom info in this case and not from cartridge info
                cr.dump_rom(args.dump_rom, parse_size_to_bytes(rom_info['ROM_size']))
            else:
                cr.dump_rom(args.dump_rom)
        if args.write_save is not None:
            cr.write_save_from_file(args.write_save)

        cr.close()

    cr.printer.print("")


# %%

if __name__ == "__main__":
    main()
