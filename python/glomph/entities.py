"""Game entities: Hero (player) and Ghosts with distinct AI personalities.

Ghost AI based on the original Pac-Man design:
  - Blinky (red):   Directly chases the hero
  - Pinky (pink):   Targets 4 tiles ahead of the hero
  - Inky (cyan):    Uses Blinky's position to calculate ambush point
  - Clyde (orange): Chases when far, scatters when close
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum

from .maze import Maze


class Direction(Enum):
    UP = (-1, 0)
    DOWN = (1, 0)
    LEFT = (0, -1)
    RIGHT = (0, 1)
    NONE = (0, 0)


class GhostState(Enum):
    HUNTING = "hunting"
    SCATTER = "scatter"
    FRIGHTENED = "frightened"
    EYES = "eyes"


# Scatter targets — corners of the maze
SCATTER_TARGETS = [
    (0, -2),     # Blinky: top-right (offset from width)
    (0, 2),      # Pinky: top-left
    (-2, -2),    # Inky: bottom-right (offset from height/width)
    (-2, 2),     # Clyde: bottom-left
]


def _opposite(d: Direction) -> Direction:
    if d == Direction.UP:
        return Direction.DOWN
    if d == Direction.DOWN:
        return Direction.UP
    if d == Direction.LEFT:
        return Direction.RIGHT
    if d == Direction.RIGHT:
        return Direction.LEFT
    return Direction.NONE


def _distance_sq(r1: int, c1: int, r2: int, c2: int) -> int:
    """Squared Euclidean distance (avoids sqrt)."""
    return (r1 - r2) ** 2 + (c1 - c2) ** 2


@dataclass
class Entity:
    row: int
    col: int

    def move(self, direction: Direction, maze: Maze) -> bool:
        """Try to move in a direction. Returns True if moved."""
        dr, dc = direction.value
        new_row = (self.row + dr) % maze.height
        new_col = (self.col + dc) % maze.width
        if maze.is_passable(new_row, new_col):
            self.row = new_row
            self.col = new_col
            return True
        return False


@dataclass
class Hero(Entity):
    direction: Direction = Direction.NONE
    next_direction: Direction = Direction.NONE
    alive: bool = True

    def update(self, maze: Maze) -> None:
        """Move hero, trying queued direction first."""
        if self.next_direction != Direction.NONE:
            dr, dc = self.next_direction.value
            new_row = (self.row + dr) % maze.height
            new_col = (self.col + dc) % maze.width
            if maze.is_passable(new_row, new_col):
                self.direction = self.next_direction
                self.next_direction = Direction.NONE

        if self.direction != Direction.NONE:
            self.move(self.direction, maze)


@dataclass
class Ghost(Entity):
    state: GhostState = GhostState.HUNTING
    direction: Direction = Direction.UP
    home_row: int = 0
    home_col: int = 0
    frightened_timer: int = 0
    color_index: int = 0  # 0=Blinky(red), 1=Pinky(pink), 2=Inky(cyan), 3=Clyde(orange)
    move_counter: int = 0  # For speed control — ghosts move every N ticks
    scatter_timer: int = 0

    def update(
        self,
        maze: Maze,
        hero_row: int,
        hero_col: int,
        hero_direction: Direction,
        blinky: Ghost | None = None,
        tick_number: int = 0,
    ) -> None:
        """Move ghost based on its current AI personality and state."""
        # Ghosts are slower than hero — skip every other tick
        self.move_counter += 1
        if self.move_counter % 2 != 0 and self.state != GhostState.EYES:
            return

        if self.state == GhostState.FRIGHTENED:
            self.frightened_timer -= 1
            if self.frightened_timer <= 0:
                self.state = GhostState.HUNTING
            self._move_random(maze)

        elif self.state == GhostState.EYES:
            self._move_toward(maze, self.home_row, self.home_col)
            if self.row == self.home_row and self.col == self.home_col:
                self.state = GhostState.HUNTING

        elif self.state == GhostState.SCATTER:
            self.scatter_timer -= 1
            if self.scatter_timer <= 0:
                self.state = GhostState.HUNTING
            # Move toward scatter corner
            sr, sc = SCATTER_TARGETS[self.color_index % 4]
            target_r = sr if sr >= 0 else maze.height + sr
            target_c = sc if sc >= 0 else maze.width + sc
            self._move_toward(maze, target_r, target_c)

        else:
            # HUNTING — each ghost has a unique targeting strategy
            target_r, target_c = self._get_chase_target(
                maze, hero_row, hero_col, hero_direction, blinky
            )
            self._move_toward(maze, target_r, target_c)

    def _get_chase_target(
        self,
        maze: Maze,
        hero_row: int,
        hero_col: int,
        hero_direction: Direction,
        blinky: Ghost | None,
    ) -> tuple[int, int]:
        """Get target position based on ghost personality."""
        if self.color_index == 0:
            # Blinky (red): Direct chase — always targets hero's current position
            return hero_row, hero_col

        elif self.color_index == 1:
            # Pinky (pink): Ambush — targets 4 tiles ahead of hero
            dr, dc = hero_direction.value
            return (hero_row + dr * 4) % maze.height, (hero_col + dc * 4) % maze.width

        elif self.color_index == 2:
            # Inky (cyan): Flanking — uses vector from Blinky to 2-ahead-of-hero, doubled
            if blinky:
                dr, dc = hero_direction.value
                pivot_r = (hero_row + dr * 2) % maze.height
                pivot_c = (hero_col + dc * 2) % maze.width
                # Double the vector from Blinky to the pivot
                target_r = (2 * pivot_r - blinky.row) % maze.height
                target_c = (2 * pivot_c - blinky.col) % maze.width
                return target_r, target_c
            return hero_row, hero_col

        else:
            # Clyde (orange): Shy — chases when far (>8 tiles), scatters when close
            dist = _distance_sq(self.row, self.col, hero_row, hero_col)
            if dist > 64:  # 8^2
                return hero_row, hero_col
            # Scatter to home corner
            sr, sc = SCATTER_TARGETS[self.color_index % 4]
            return (
                sr if sr >= 0 else maze.height + sr,
                sc if sc >= 0 else maze.width + sc,
            )

    def make_frightened(self, duration: int) -> None:
        """Enter frightened state (power pellet eaten)."""
        if self.state != GhostState.EYES:
            self.state = GhostState.FRIGHTENED
            self.frightened_timer = duration
            # Reverse direction on becoming frightened
            self.direction = _opposite(self.direction)

    def make_scatter(self, duration: int) -> None:
        """Enter scatter mode (ghosts retreat to corners)."""
        if self.state == GhostState.HUNTING:
            self.state = GhostState.SCATTER
            self.scatter_timer = duration
            self.direction = _opposite(self.direction)

    def _move_toward(self, maze: Maze, target_row: int, target_col: int) -> None:
        """Move toward a target, avoiding reversals (classic Pac-Man pathfinding)."""
        opposite = _opposite(self.direction)
        candidates: list[tuple[Direction, int]] = []

        for d in (Direction.UP, Direction.LEFT, Direction.DOWN, Direction.RIGHT):
            if d == opposite:
                continue
            dr, dc = d.value
            new_row = (self.row + dr) % maze.height
            new_col = (self.col + dc) % maze.width
            if maze.is_passable(new_row, new_col):
                dist = _distance_sq(new_row, new_col, target_row, target_col)
                candidates.append((d, dist))

        if not candidates:
            # Dead end — must reverse
            candidates.append((opposite, 0))

        # Choose direction closest to target (tie-break: UP > LEFT > DOWN > RIGHT)
        candidates.sort(key=lambda x: x[1])
        chosen = candidates[0][0]
        self.direction = chosen
        self.move(chosen, maze)

    def _move_random(self, maze: Maze) -> None:
        """Move in a random valid direction, avoiding reversals."""
        opposite = _opposite(self.direction)
        options = []

        for d in (Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT):
            if d == opposite:
                continue
            dr, dc = d.value
            new_row = (self.row + dr) % maze.height
            new_col = (self.col + dc) % maze.width
            if maze.is_passable(new_row, new_col):
                options.append(d)

        if not options:
            options = [opposite]

        chosen = random.choice(options)
        self.direction = chosen
        self.move(chosen, maze)
