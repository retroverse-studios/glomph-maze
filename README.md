# Glomph Maze

<!-- BADGES:START -->
[![c](https://img.shields.io/badge/-c-blue?style=flat-square)](https://github.com/topics/c) [![cli-game](https://img.shields.io/badge/-cli-game-blue?style=flat-square)](https://github.com/topics/cli-game) [![cmake](https://img.shields.io/badge/-cmake-blue?style=flat-square)](https://github.com/topics/cmake) [![console-game](https://img.shields.io/badge/-console-game-blue?style=flat-square)](https://github.com/topics/console-game) [![cross-platform](https://img.shields.io/badge/-cross-platform-blue?style=flat-square)](https://github.com/topics/cross-platform) [![maze-game](https://img.shields.io/badge/-maze-game-blue?style=flat-square)](https://github.com/topics/maze-game) [![ncurses](https://img.shields.io/badge/-ncurses-blue?style=flat-square)](https://github.com/topics/ncurses) [![pacman](https://img.shields.io/badge/-pacman-blue?style=flat-square)](https://github.com/topics/pacman) [![retro-gaming](https://img.shields.io/badge/-retro-gaming-blue?style=flat-square)](https://github.com/topics/retro-gaming) [![terminal](https://img.shields.io/badge/-terminal-blue?style=flat-square)](https://github.com/topics/terminal)
<!-- BADGES:END -->

![Glomph Mascot](images/glomph-mascot.png)

A revived and renamed fork of [MyMan](http://myman.sourceforge.net/), an unofficial text-based clone of the classic Pac-Man game. Designed for terminal and console environments, with no GUI support. Integrated into a collection of minimal text-based projects.

## Description

Glomph Maze is a fast-paced, curses-based game where you navigate mazes, collect dots, and avoid ghosts. It supports multiple platforms including modern Unix-like systems, DOS, and VMS, emphasizing portability and legacy compatibility.

Original project last updated in 2009; this fork adds modern maintenance while preserving the text-based ethos.

### History
- **1998**: Original MyMan by Benjamin Sittler—public domain, basic ncurses Pac-Man clone (742 lines, large tiles, maze/color support).
- **1998-2003**: Expanded portability (cygwin/DOS/VMS), small tiles, variants (e.g., pacmanic). Data files public domain.
- **Nov 2003 (v0.4/0.5)**: Switched to BSD 2-Clause license for attribution.
- **2003-2009**: Added backends (PDCurses/SDL/GTK/Allegro/libcaca/EFI/Mac Carbon), sizes/variants (quackman/small/square), UX (pager/help/snapshots/MIDI). Last update: 2009 (DOS fixes). v0.7.0 final.
- **2025 Fork (Glomph Maze)**: Renamed/revived; Makefile/UX tweaks (license in help, no startup prompt); focus on text portability. Data/original code under BSD; mazes/tiles public domain.

## Features

- Text-mode rendering using ncurses or alternatives (PDCurses, SDL, etc.).
- Modular data files for mazes, tiles, and sprites (customizable variants).
- Color and attribute support (toggleable).
- Optional audio support: SDL2_mixer (MIDI/tracker music) or terminal beep fallback.
- Command-line options for mazes, sizes, ghosts, etc. (e.g., `glomph -m pac` for Pac-Man layout).

## Installation

### Prerequisites
- ANSI C compiler (e.g., GCC or Clang)
- CMake 3.15 or higher
- Curses library (e.g., ncurses on Unix, PDCurses on Windows)
- Optional: SDL2 + SDL2_mixer for audio support (MIDI/tracker music)

### Build from Source

**Basic build (terminal beep audio):**
```bash
git clone git@github.com:michaelborck-dev/glomph-maze.git
cd glomph-maze
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
./build/glomph
```

**Build with SDL audio (recommended for music):**
```bash
# Install SDL2 libraries first
brew install sdl2 sdl2_mixer              # macOS
sudo apt install libsdl2-dev libsdl2-mixer-dev  # Ubuntu/Debian

# Build with audio enabled
cmake -B build -DCMAKE_BUILD_TYPE=Release -DENABLE_AUDIO=ON
cmake --build build
./build/glomph -b  # -b enables sound
```

See [CMAKE_SETUP.md](CMAKE_SETUP.md) for detailed build instructions and options.

## Usage

Run the game:
```
glomph-maze  # Or 'myman' if not renamed in binary
```

Controls (case-insensitive):
- Arrow keys / HJKL: Move (left/down/up/right).
- Q: Quit.
- P/ESC: Pause.
- C: Toggle color.
- S: Toggle sound on/off.
- ?: Help.

Full options: `glomph-maze -h`.

Environment variables for fine-tuning rendering (see original README notes).

## Building and Renaming Note

This fork renames binaries/docs from \"MyMan\" to \"Glomph Maze\". The CMake build produces four size variants:

- **`glomph`** (default) - 4×4 filled bitmap characters, best balance of detail and compatibility
- **`glomph-xlarge`** - 5×3 ASCII-art outlined characters, largest and most detailed
- **`glomph-small`** - 2×1 Unicode symbols, compact display fits more on screen
- **`glomph-tiny`** - 1×1 single characters, minimal display for small terminals

All variants play identically; only the visual rendering differs.

## Future Plans

- Update curses support to modern ncurses.
- Explore MIDI alternatives without breaking legacy.
- Refactoring for clarity while maintaining portability.
- No GUI development; focus on text environments.

## License

Modified from original BSD license. See [LICENSE](LICENSE) for details.

Original author: Benjamin C. Wiley Sittler <bsittler@gmail.com>. Fork maintainer: Michael Borck.

## Acknowledgements

This project is a fork of the original MyMan game, originally developed by Benjamin C. Wiley Sittler.

Original Sources:
- Original author's homepage: [https://xent.com/~bsittler/geocities/#myman](https://xent.com/~bsittler/geocities/#myman)
- SourceForge project: [https://sourceforge.net/projects/myman/](https://sourceforge.net/projects/myman/)
- GitHub mirror (CVS to Git conversion): [https://github.com/kragen/myman](https://github.com/kragen/myman)

Based on MyMan (public domain/BSD). Inspired by Pac-Man (Namco). Thanks to contributors for ports and variants.