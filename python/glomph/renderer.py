"""Curses-based terminal renderer.

Renders the maze, entities, score, and UI to a curses window.
Completely separated from game logic.
"""

from __future__ import annotations

import curses
from typing import TYPE_CHECKING

from .entities import GhostState
from .game import GamePhase, SpeedConfig

if TYPE_CHECKING:
    from .game import GameState

# Color pair IDs
COLOR_WALL = 1
COLOR_DOT = 2
COLOR_PELLET = 3
COLOR_HERO = 4
COLOR_GHOST_RED = 5
COLOR_GHOST_PINK = 6
COLOR_GHOST_CYAN = 7
COLOR_GHOST_ORANGE = 8
COLOR_GHOST_BLUE = 9
COLOR_GHOST_EYES = 10
COLOR_TEXT = 11
COLOR_SCORE = 12

GHOST_COLOR_MAP = {
    0: COLOR_GHOST_RED,
    1: COLOR_GHOST_PINK,
    2: COLOR_GHOST_CYAN,
    3: COLOR_GHOST_ORANGE,
}

HERO_CHARS = {
    "left": "<",
    "right": ">",
    "up": "V" if False else "^",  # noqa: SIM211
    "down": "v",
    "none": "●",
}


def init_colors() -> None:
    """Initialize color pairs for the terminal."""
    curses.start_color()
    curses.use_default_colors()

    curses.init_pair(COLOR_WALL, curses.COLOR_BLUE, -1)
    curses.init_pair(COLOR_DOT, curses.COLOR_WHITE, -1)
    curses.init_pair(COLOR_PELLET, curses.COLOR_WHITE, -1)
    curses.init_pair(COLOR_HERO, curses.COLOR_YELLOW, -1)
    curses.init_pair(COLOR_GHOST_RED, curses.COLOR_RED, -1)
    curses.init_pair(COLOR_GHOST_PINK, curses.COLOR_MAGENTA, -1)
    curses.init_pair(COLOR_GHOST_CYAN, curses.COLOR_CYAN, -1)
    curses.init_pair(COLOR_GHOST_ORANGE, curses.COLOR_RED, -1)  # No orange in basic curses
    curses.init_pair(COLOR_GHOST_BLUE, curses.COLOR_BLUE, -1)
    curses.init_pair(COLOR_GHOST_EYES, curses.COLOR_WHITE, -1)
    curses.init_pair(COLOR_TEXT, curses.COLOR_WHITE, -1)
    curses.init_pair(COLOR_SCORE, curses.COLOR_YELLOW, -1)


def render(stdscr: curses.window, state: GameState) -> None:
    """Render the complete game state to the terminal."""
    stdscr.erase()
    max_y, max_x = stdscr.getmaxyx()
    maze = state.maze

    # Calculate offset to center the maze
    offset_y = max(0, (max_y - maze.height - 3) // 2)
    offset_x = max(0, (max_x - maze.width) // 2)

    # Check terminal size
    if max_y < maze.height + 3 or max_x < maze.width:
        _draw_str(stdscr, 0, 0, f"Terminal too small ({max_x}x{max_y}). Need {maze.width}x{maze.height + 3}.", COLOR_TEXT)
        stdscr.refresh()
        return

    # Draw score bar
    score_text = f" SCORE: {state.score:>6}  LIVES: {'● ' * state.lives}  LEVEL: {state.level} "
    _draw_str(stdscr, offset_y, offset_x, score_text[:maze.width].ljust(maze.width), COLOR_SCORE)

    # Draw maze
    maze_y = offset_y + 2
    for row in range(maze.height):
        for col in range(maze.width):
            ch = maze.char_at(row, col)
            cell_type = maze.at(row, col)

            if cell_type == "wall":
                _draw_ch(stdscr, maze_y + row, offset_x + col, ch, COLOR_WALL)
            elif cell_type == "dot":
                _draw_ch(stdscr, maze_y + row, offset_x + col, "·", COLOR_DOT)
            elif cell_type == "pellet":
                _draw_ch(stdscr, maze_y + row, offset_x + col, "●", COLOR_PELLET | curses.A_BOLD)
            elif cell_type == "door":
                _draw_ch(stdscr, maze_y + row, offset_x + col, "─", COLOR_WALL)
            else:
                _draw_ch(stdscr, maze_y + row, offset_x + col, " ", COLOR_TEXT)

    # Draw ghosts
    for ghost in state.ghosts:
        gy, gx = maze_y + ghost.row, offset_x + ghost.col
        if 0 <= gy < max_y and 0 <= gx < max_x:
            if ghost.state == GhostState.SCATTER:
                color = GHOST_COLOR_MAP.get(ghost.color_index, COLOR_GHOST_RED)
                _draw_ch(stdscr, gy, gx, "Ω", color)  # Dimmer when scattering
            elif ghost.state == GhostState.FRIGHTENED:
                if ghost.frightened_timer < 8 and ghost.frightened_timer % 2 == 0:
                    # Flashing when about to end
                    _draw_ch(stdscr, gy, gx, "ω", COLOR_GHOST_EYES | curses.A_BOLD)
                else:
                    _draw_ch(stdscr, gy, gx, "ω", COLOR_GHOST_BLUE | curses.A_BOLD)
            elif ghost.state == GhostState.EYES:
                _draw_ch(stdscr, gy, gx, "\"", COLOR_GHOST_EYES)
            else:
                color = GHOST_COLOR_MAP.get(ghost.color_index, COLOR_GHOST_RED)
                _draw_ch(stdscr, gy, gx, "Ω", color | curses.A_BOLD)

    # Draw hero
    if state.hero.alive and state.phase != GamePhase.DYING:
        hy, hx = maze_y + state.hero.row, offset_x + state.hero.col
        if 0 <= hy < max_y and 0 <= hx < max_x:
            direction_name = state.hero.direction.name.lower()
            hero_ch = HERO_CHARS.get(direction_name, "●")
            _draw_ch(stdscr, hy, hx, hero_ch, COLOR_HERO | curses.A_BOLD)

    # Draw phase overlays
    if state.phase == GamePhase.READY:
        msg = state.maze.metadata.ready_text
        msg_row = state.maze.metadata.msg_row or maze.height // 2
        msg_col = (maze.width - len(msg)) // 2
        _draw_str(stdscr, maze_y + msg_row, offset_x + msg_col, msg, COLOR_HERO | curses.A_BOLD)

    elif state.phase == GamePhase.DYING:
        _draw_ch(stdscr, maze_y + state.hero.row, offset_x + state.hero.col, "X", COLOR_HERO | curses.A_BOLD)

    elif state.phase == GamePhase.GAME_OVER:
        msg = state.maze.metadata.gameover_text
        msg_row = state.maze.metadata.msg_row or maze.height // 2
        msg_col = (maze.width - len(msg)) // 2
        _draw_str(stdscr, maze_y + msg_row, offset_x + msg_col, msg, COLOR_GHOST_RED | curses.A_BOLD)

    elif state.phase == GamePhase.WON:
        msg = "LEVEL COMPLETE!"
        msg_row = maze.height // 2
        msg_col = (maze.width - len(msg)) // 2
        _draw_str(stdscr, maze_y + msg_row, offset_x + msg_col, msg, COLOR_HERO | curses.A_BOLD)

    # Draw bottom bar
    bottom_y = maze_y + maze.height + 1
    if bottom_y < max_y:
        speed_pct = int((1.0 - (state.speed.hero_tick - 0.04) / 0.26) * 100)
        dots_text = f" DOTS: {state.dots_eaten}/{state.total_dots}  SPD:{speed_pct:>3}%  Q=Quit P=Pause +/-=Speed "
        _draw_str(stdscr, bottom_y, offset_x, dots_text[:maze.width].ljust(maze.width), COLOR_TEXT)

    stdscr.refresh()


def _draw_ch(stdscr: curses.window, y: int, x: int, ch: str, color: int) -> None:
    """Safely draw a character at a position."""
    try:
        stdscr.addstr(y, x, ch, curses.color_pair(color & 0xFF) | (color & ~0xFF))
    except curses.error:
        pass  # Off-screen


def _draw_str(stdscr: curses.window, y: int, x: int, text: str, color: int) -> None:
    """Safely draw a string at a position."""
    try:
        stdscr.addstr(y, x, text, curses.color_pair(color & 0xFF) | (color & ~0xFF))
    except curses.error:
        pass
