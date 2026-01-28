# %%
import argparse
from .cartridge_utils import CartridgeReader
from pkg_resources import resource_filename
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

# %%
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dump-rom", type=str, default=None, help="Dump ROM to file")
    parser.add_argument("--dump-save", type=str, default=None, help="Dump save to file")
    parser.add_argument(
        "--write-save", type=str, default=None, help="Write save from file"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        default=False,
        help="Do not output anything to stdout",
    )
    args = parser.parse_args()

    # %%

    cr = CartridgeReader(quiet=args.quiet)

    cr.printer.greetings()

    if (args.dump_save is not None) and (args.write_save is not None):
        cr.printer.warning(
            "`dump-save` and `write-save` are both set. GBOpyrator will dump the save first and write it after."
        )
    cr.initialize_reader(blocking=True,timeout=10)

    #get epilogue id for GB/GBC or GBA
    rom_epilogue_id = cr.get_epilogue_id()
    
    #get rom info file for GB/GBC or GBA
    filename=resource_filename(__name__, cr.get_rom_info_file())
    with open(filename, "r") as file:
        roms_db = json.load(file)
    
    # Print cartridge info
    if rom_epilogue_id in roms_db:
        rom_info = roms_db[rom_epilogue_id]
        if rom_info['cartridge_type'] == "GBA Standard":
            #set cartridge rom size from rom info
            cr.set_cartridge_info("ROM_size",parse_size_to_bytes(rom_info['cartridge_type']))
        # Center "rom info" text on =80 chars
        cr.printer.print("")
        cr.printer.rule("[blue_violet]CARTRIDGE INFO")
        cr.printer.print(
            f"""Detected game:\t[blue_violet]{rom_info['full_title']}[/blue_violet]"""
        )
        if rom_info["SGB_support"]:
            cr.printer.print(f"""SGB support:\t[blue_violet]Yes[/blue_violet]""")
        if rom_info["CGB_support"]:
            cr.printer.print(f"""CGB support:\t[blue_violet]Yes[/blue_violet]""")
        cr.printer.print(
            f"""ROM size:\t[blue_violet]{rom_info['ROM_size']}[/blue_violet]"""
        )
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
            cr.dump_save(args.dump_save)

        if args.dump_rom is not None:
            cr.dump_rom(args.dump_rom)

        if args.write_save is not None:
            cr.write_save_from_file(args.write_save)

        cr.close()

    cr.printer.print("")


# %%

if __name__ == "__main__":
    main()
