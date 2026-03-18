"""Glomph Maze entry point.

Usage:
    python -m glomph                     # Play with default maze
    python -m glomph path/to/maze.txt    # Play with specific maze
    python -m glomph --list              # List available mazes
    python -m glomph --speed slow        # Play at slower speed
"""

from __future__ import annotations

import argparse
import curses
import sys
import time
from pathlib import Path

from . import __version__
from .entities import Direction
from .game import GamePhase, GameState, SpeedConfig, create_game, tick
from .maze import find_mazes, load_maze
from .renderer import init_colors, render
from .sound import SoundEngine

SPEED_PRESETS = {
    "slow": SpeedConfig.slow,
    "normal": SpeedConfig.normal,
    "fast": SpeedConfig.fast,
}


def find_assets_dir() -> Path:
    """Locate the assets directory relative to the project."""
    project_root = Path(__file__).parent.parent.parent
    assets = project_root / "assets"
    if assets.exists():
        return assets
    cwd_assets = Path.cwd() / "assets"
    if cwd_assets.exists():
        return cwd_assets
    return assets


def list_mazes(assets_dir: Path) -> None:
    """Print available mazes."""
    mazes = find_mazes(assets_dir)
    if not mazes:
        print(f"No mazes found in {assets_dir / 'mazes'}")
        return

    print(f"Available mazes ({len(mazes)}):\n")
    for maze_path in mazes:
        try:
            levels = load_maze(maze_path)
            if levels:
                m = levels[0]
                about = m.metadata.about[:55] if m.metadata.about else ""
                print(f"  {maze_path.stem:<16} {m.width:>2}x{m.height:<2}  {len(levels):>2} lvl  {m.dot_count:>3} dots  {about}")
        except (ValueError, IndexError):
            print(f"  {maze_path.stem:<16} (parse error)")


def game_loop(stdscr: curses.window, state: GameState, sound: SoundEngine) -> int:
    """Main game loop. Returns final score."""
    stdscr.nodelay(True)
    stdscr.keypad(True)
    curses.curs_set(0)
    init_colors()

    paused = False
    last_tick = time.monotonic()

    while True:
        now = time.monotonic()

        # Input — drain all pending keys
        key = -1
        while True:
            try:
                k = stdscr.getch()
            except curses.error:
                break
            if k == -1:
                break
            key = k  # Keep the last key pressed

        if key == ord("q") or key == ord("Q"):
            return state.score

        if key == ord("p") or key == ord("P"):
            paused = not paused
            if paused:
                render(stdscr, state)
                max_y, max_x = stdscr.getmaxyx()
                msg = " PAUSED - P to resume, Q to quit "
                try:
                    stdscr.addstr(
                        max_y // 2,
                        (max_x - len(msg)) // 2,
                        msg,
                        curses.A_REVERSE | curses.A_BOLD,
                    )
                except curses.error:
                    pass
                stdscr.refresh()
            continue

        if paused:
            time.sleep(0.05)
            continue

        # Speed controls
        if key == ord("+") or key == ord("="):
            state.speed.hero_tick = max(0.04, state.speed.hero_tick - 0.02)
        elif key == ord("-") or key == ord("_"):
            state.speed.hero_tick = min(0.30, state.speed.hero_tick + 0.02)

        # Direction input
        if key == curses.KEY_UP or key == ord("k") or key == ord("w"):
            state.hero.next_direction = Direction.UP
        elif key == curses.KEY_DOWN or key == ord("j") or key == ord("s"):
            state.hero.next_direction = Direction.DOWN
        elif key == curses.KEY_LEFT or key == ord("h") or key == ord("a"):
            state.hero.next_direction = Direction.LEFT
        elif key == curses.KEY_RIGHT or key == ord("l") or key == ord("d"):
            state.hero.next_direction = Direction.RIGHT

        # Tick at the configured rate
        elapsed = now - last_tick
        if elapsed < state.tick_rate:
            time.sleep(0.01)  # Small sleep to avoid busy-wait
            continue

        last_tick = now

        # Update
        events = tick(state)

        # Sound
        for event in events:
            base_event = event.split(":")[0]
            sound.play(base_event)

        # Terminal states
        if state.phase == GamePhase.GAME_OVER:
            render(stdscr, state)
            sound.play("death")
            stdscr.nodelay(False)
            stdscr.getch()
            return state.score

        if state.phase == GamePhase.WON:
            render(stdscr, state)
            sound.play("won")
            stdscr.nodelay(False)
            stdscr.getch()
            return state.score

        # Render
        render(stdscr, state)


def run(stdscr: curses.window, maze_path: Path, speed: SpeedConfig, sound: SoundEngine) -> int:
    """Load maze and run the game."""
    try:
        levels = load_maze(maze_path)
    except (ValueError, OSError) as e:
        curses.endwin()
        print(f"Error loading maze: {e}", file=sys.stderr)
        sys.exit(1)

    if not levels:
        curses.endwin()
        print(f"No levels found in {maze_path}", file=sys.stderr)
        sys.exit(1)

    state = create_game(levels[0], speed=speed)
    sound.play("start")
    return game_loop(stdscr, state, sound)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="glomph",
        description="Glomph Maze - Terminal Pac-Man",
    )
    parser.add_argument("maze", nargs="?", help="Maze name or path (default: first available)")
    parser.add_argument("--list", action="store_true", help="List available mazes")
    parser.add_argument(
        "--speed",
        choices=["slow", "normal", "fast"],
        default="normal",
        help="Game speed preset (default: normal). Use +/- in-game to fine-tune.",
    )
    parser.add_argument("--no-sound", action="store_true", help="Disable sound effects")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args()

    assets_dir = find_assets_dir()

    if args.list:
        list_mazes(assets_dir)
        return

    if args.maze:
        maze_path = Path(args.maze)
        if not maze_path.exists():
            maze_path = assets_dir / "mazes" / f"{args.maze}.txt"
    else:
        mazes = find_mazes(assets_dir)
        if not mazes:
            print(f"No mazes found in {assets_dir / 'mazes'}", file=sys.stderr)
            sys.exit(1)
        maze_path = mazes[0]

    if not maze_path.exists():
        print(f"Maze not found: {maze_path}", file=sys.stderr)
        sys.exit(1)

    speed = SPEED_PRESETS[args.speed]()
    sound = SoundEngine(enabled=not args.no_sound)

    print(f"Loading {maze_path.stem}... (speed: {args.speed}, +/- to adjust in-game)")

    score = curses.wrapper(lambda stdscr: run(stdscr, maze_path, speed, sound))
    print(f"\nFinal score: {score}")


if __name__ == "__main__":
    main()
