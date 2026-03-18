"""Maze loading and representation.

Parses the text-based maze format used by MyMan/Glomph.
Each maze file has a header line with dimensions and metadata,
followed by a grid of characters representing walls, dots, pellets, etc.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# Maze cell types
WALL = "wall"
DOT = "dot"
PELLET = "pellet"
EMPTY = "empty"
DOOR = "door"
TUNNEL = "tunnel"

# Characters that represent walls (box-drawing and block chars)
WALL_CHARS = set("═║╔╗╚╝╞╡╠╣╦╩╬╨╥╰╯╭╮─│■▌▐█▀▄╢╕╒╓╖╘╙╜╛┌┐└┘├┤┬┴┼")
DOT_CHARS = set("·.∙・")  # Includes U+30FB (Katakana middle dot)
PELLET_CHARS = set("oO●◉◆")
DOOR_CHARS = set("≡=")
TUNNEL_CHARS = set("~")
EMPTY_CHARS = set("\u3000")  # Fullwidth space (CJK mazes)


@dataclass
class MazeMetadata:
    """Metadata parsed from the maze header line."""

    about: str = ""
    ready_text: str = "READY!"
    gameover_text: str = "GAME OVER"
    hero_row: float = 0.0
    hero_col: float = 0.0
    ghost_row: float = 0.0
    ghost_col: float = 0.0
    ghost_row_offset: float = 0.0
    ghost_col_offset: float = 0.0
    fruit_row: float = 0.0
    fruit_col: float = 0.0
    msg_row: int = 0
    msg_col: int = 0


@dataclass
class Maze:
    """A single maze level."""

    width: int
    height: int
    grid: list[list[str]]  # Raw character grid
    cell_types: list[list[str]]  # Classified cell types
    dot_count: int = 0
    metadata: MazeMetadata = field(default_factory=MazeMetadata)

    def at(self, row: int, col: int) -> str:
        """Get cell type at position, wrapping for tunnels."""
        row = row % self.height
        col = col % self.width
        return self.cell_types[row][col]

    def char_at(self, row: int, col: int) -> str:
        """Get display character at position."""
        row = row % self.height
        col = col % self.width
        return self.grid[row][col]

    def is_passable(self, row: int, col: int) -> bool:
        """Check if a cell can be walked through."""
        cell = self.at(row, col)
        return cell != WALL

    def is_wall(self, row: int, col: int) -> bool:
        return self.at(row, col) == WALL

    def remove_dot(self, row: int, col: int) -> str | None:
        """Remove and return dot/pellet at position, or None."""
        cell = self.cell_types[row % self.height][col % self.width]
        if cell in (DOT, PELLET):
            self.cell_types[row % self.height][col % self.width] = EMPTY
            self.grid[row % self.height][col % self.width] = " "
            if cell == DOT:
                self.dot_count -= 1
            return cell
        return None


def _classify_char(ch: str) -> str:
    """Classify a maze character into a cell type."""
    if ch in WALL_CHARS:
        return WALL
    if ch in DOT_CHARS:
        return DOT
    if ch in PELLET_CHARS:
        return PELLET
    if ch in DOOR_CHARS:
        return DOOR
    if ch in TUNNEL_CHARS:
        return TUNNEL
    if ch in EMPTY_CHARS:
        return EMPTY
    return EMPTY


def _parse_metadata(header_rest: str) -> MazeMetadata:
    """Parse key=value pairs from the maze header."""
    meta = MazeMetadata()

    for match in re.finditer(r'(\w+)="([^"]*)"', header_rest):
        key, value = match.group(1).upper(), match.group(2)
        if key == "ABOUT":
            meta.about = value
        elif key == "READY":
            meta.ready_text = value
        elif key == "GAMEOVER":
            meta.gameover_text = value

    for match in re.finditer(r"(\w+)=([\d.]+)", header_rest):
        key, value = match.group(1).upper(), match.group(2)
        if key == "RHERO":
            meta.hero_row = float(value.split(",")[0])
        elif key == "CHERO":
            meta.hero_col = float(value.split(",")[0])
        elif key == "RGHOST":
            meta.ghost_row = float(value.split(",")[0])
        elif key == "CGHOST":
            meta.ghost_col = float(value.split(",")[0])
        elif key == "ROGHOST":
            meta.ghost_row_offset = float(value)
        elif key == "COGHOST":
            meta.ghost_col_offset = float(value)
        elif key == "RFRUIT":
            meta.fruit_row = float(value.split(",")[0])
        elif key == "CFRUIT":
            meta.fruit_col = float(value.split(",")[0])
        elif key == "RMSG":
            meta.msg_row = int(value)
        elif key == "CMSG":
            meta.msg_col = int(value)

    return meta


def load_maze(path: Path) -> list[Maze]:
    """Load maze levels from a file.

    Returns a list of Maze objects (one per level in the file).
    """
    text = path.read_text(encoding="utf-8-sig")  # Handle BOM
    lines = text.split("\n")

    if not lines:
        raise ValueError(f"Empty maze file: {path}")

    # Parse header
    header = lines[0].strip()
    header_match = re.match(r"(\d+)\s+(\d+)[xX](\d+)(.*)", header)
    if not header_match:
        raise ValueError(f"Invalid maze header: {header}")

    num_levels = int(header_match.group(1))
    width = int(header_match.group(2))
    height = int(header_match.group(3))
    header_rest = header_match.group(4)

    metadata = _parse_metadata(header_rest)

    # Parse grid data (starting from line 1)
    mazes: list[Maze] = []
    line_idx = 1

    for _ in range(num_levels):
        grid: list[list[str]] = []
        cell_types: list[list[str]] = []
        dot_count = 0

        for _row in range(height):
            if line_idx >= len(lines):
                break
            raw_line = lines[line_idx]
            line_idx += 1

            # Pad or truncate to width
            row_chars: list[str] = []
            i = 0
            for ch in raw_line:
                if i >= width:
                    break
                row_chars.append(ch)
                i += 1
            while len(row_chars) < width:
                row_chars.append(" ")

            row_types: list[str] = []
            for ch in row_chars:
                ct = _classify_char(ch)
                if ct == DOT:
                    dot_count += 1
                row_types.append(ct)

            grid.append(row_chars)
            cell_types.append(row_types)

        # Auto-detect hero position if not in metadata
        level_meta = MazeMetadata(
            about=metadata.about,
            ready_text=metadata.ready_text,
            gameover_text=metadata.gameover_text,
            hero_row=metadata.hero_row,
            hero_col=metadata.hero_col,
            ghost_row=metadata.ghost_row,
            ghost_col=metadata.ghost_col,
            ghost_row_offset=metadata.ghost_row_offset,
            ghost_col_offset=metadata.ghost_col_offset,
            fruit_row=metadata.fruit_row,
            fruit_col=metadata.fruit_col,
            msg_row=metadata.msg_row,
            msg_col=metadata.msg_col,
        )

        # If hero column not set, find one near the center of the hero's row
        if level_meta.hero_col == 0.0:
            hero_r = int(level_meta.hero_row) if level_meta.hero_row > 0 else height * 3 // 4
            # Search outward from center
            center = width // 2
            for offset in range(width):
                for c in (center + offset, center - offset):
                    if 0 <= c < width and hero_r < len(cell_types):
                        if cell_types[hero_r][c] in (DOT, EMPTY):
                            level_meta.hero_col = float(c)
                            break
                if level_meta.hero_col != 0.0:
                    break

        # If hero row not set either, search lower half
        if level_meta.hero_row == 0.0:
            for r in range(height - 1, height // 2, -1):
                for c in range(width):
                    if r < len(cell_types) and c < len(cell_types[r]):
                        if cell_types[r][c] in (DOT, EMPTY):
                            level_meta.hero_row = float(r)
                            level_meta.hero_col = float(c)
                            break
                if level_meta.hero_row != 0.0:
                    break

        # If ghost position not set, find the center
        if level_meta.ghost_row == 0.0:
            level_meta.ghost_row = float(height // 2)
        if level_meta.ghost_col == 0.0:
            level_meta.ghost_col = float(width // 2)

        mazes.append(
            Maze(
                width=width,
                height=height,
                grid=grid,
                cell_types=cell_types,
                dot_count=dot_count,
                metadata=level_meta,
            )
        )

    return mazes


def find_mazes(assets_dir: Path) -> list[Path]:
    """Find all .txt maze files in an assets directory."""
    maze_dir = assets_dir / "mazes"
    if not maze_dir.exists():
        return []
    return sorted(p for p in maze_dir.glob("*.txt") if p.stat().st_size > 0)
