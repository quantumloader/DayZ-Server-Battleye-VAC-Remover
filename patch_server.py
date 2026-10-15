import os
import re
import shutil
import sys

DEFAULT_TARGET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "DayZServer_x64.exe")
CONSOLE_TITLE = b"Patched version"

BE_INIT_PATTERN = "40 55 53 56 57 41 54 41 55 41 56 41 57 48 8D 6C 24 ? 48 81 EC ? ? ? ? 48 C7 44 24 ? FE FF FF FF 48 8B D9 45 33 ED"
VAC_CHECK_PATTERN = "74 44 0F B7 C8 E8 ? ? ? ? 8B 13 44 0F B7 C0 44 89 4C 24 ? 48"
CONSOLE_TITLE_PATTERN = "43 6F 6E 73 6F 6C 65 20 76"

RET_AL_1 = bytes([0xB0, 0x01, 0xC3])  # mov al, 1; ret
JMP_SHORT = 0xEB


def compile_pattern(pattern):
    parts = []
    for token in pattern.split():
        parts.append(b"." if token == "?" else re.escape(bytes([int(token, 16)])))
    return re.compile(b"".join(parts), re.DOTALL)


def scan(data, pattern):
    return [m.start() for m in compile_pattern(pattern).finditer(data)]


def fail(message):
    print(message)
    input("Press Enter to exit...")
    sys.exit(1)


def find_unique(data, pattern, name):
    hits = scan(data, pattern)
    if not hits:
        fail(f"Failed to find {name}.")
    if len(hits) > 1:
        fail(f"Pattern for {name} matched {len(hits)} times, refusing to patch.")
    return hits[0]


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TARGET
    if not os.path.isfile(target):
        fail("Start application with target file path.")

    backup = target + ".bak"

    with open(target, "rb") as f:
        data = bytearray(f.read())

    be_offset = find_unique(data, BE_INIT_PATTERN, "battleye init function")
    vac_offset = find_unique(data, VAC_CHECK_PATTERN, "VAC check")

    shutil.copy2(target, backup)
    print(f"Created backup: {backup}")

    data[be_offset:be_offset + len(RET_AL_1)] = RET_AL_1
    print(f"Patched battleye init function at file offset 0x{be_offset:X}.")

    data[vac_offset] = JMP_SHORT
    print(f"Patched VAC check at file offset 0x{vac_offset:X}.")

    title_hits = scan(data, CONSOLE_TITLE_PATTERN)
    if title_hits:
        offset = title_hits[0]
        data[offset:offset + len(CONSOLE_TITLE)] = CONSOLE_TITLE
        print("Patched console title.")
    else:
        print("Failed to find console title, skipping...")

    try:
        with open(target, "wb") as f:
            f.write(data)
    except OSError as e:
        fail(f"Failed to write patched file: {e}")

    print("Wrote patched dayz server back to original file.")
    input("Press Enter to exit...")


if __name__ == "__main__":
    main()
