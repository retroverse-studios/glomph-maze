"""Game engine: state management, scoring, scatter/chase waves, and speed control."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .entities import Direction, Ghost, GhostState, Hero
from .maze import DOT, PELLET, Maze

NUM_GHOSTS = 4
PELLET_DURATION = 40  # Ticks of frightened mode
GHOST_SCORE_SEQUENCE = [200, 400, 800, 1600]
EXTRA_LIFE_SCORES = [10000, 50000]

# Scatter/chase wave timing (in ticks): scatter, chase, scatter, chase, ...
# Classic Pac-Man: 7s scatter, 20s chase, 7s, 20s, 5s, 20s, 5s, then chase forever
SCATTER_CHASE_WAVES = [
    (70, 200),   # 7s scatter, 20s chase
    (70, 200),
    (50, 200),
    (50, 0),     # Final: 5s scatter then permanent chase
]


class GamePhase(Enum):
    READY = "ready"
    PLAYING = "playing"
    DYING = "dying"
    WON = "won"
    GAME_OVER = "game_over"


@dataclass
class SpeedConfig:
    """Game speed settings. All values in seconds per tick."""

    hero_tick: float = 0.12    # How often hero moves (higher = slower)
    ghost_base: float = 0.14   # Ghost base tick rate
    fright_tick: float = 0.18  # Ghost speed when frightened
    eyes_tick: float = 0.06    # Ghost eyes speed (fast return)

    @classmethod
    def slow(cls) -> SpeedConfig:
        return cls(hero_tick=0.16, ghost_base=0.18, fright_tick=0.22, eyes_tick=0.08)

    @classmethod
    def normal(cls) -> SpeedConfig:
        return cls()

    @classmethod
    def fast(cls) -> SpeedConfig:
        return cls(hero_tick=0.09, ghost_base=0.11, fright_tick=0.14, eyes_tick=0.04)


@dataclass
class GameState:
    """Complete game state."""

    maze: Maze
    hero: Hero
    ghosts: list[Ghost]
    score: int = 0
    lives: int = 3
    level: int = 1
    phase: GamePhase = GamePhase.READY
    phase_timer: int = 0
    ghosts_eaten_combo: int = 0
    dots_eaten: int = 0
    total_dots: int = 0
    ready_timer: int = 30
    tick_number: int = 0
    speed: SpeedConfig = field(default_factory=SpeedConfig)

    # Scatter/chase wave tracking
    wave_index: int = 0
    wave_timer: int = 0
    in_scatter: bool = True  # Start in scatter mode

    @property
    def dots_remaining(self) -> int:
        return self.maze.dot_count

    @property
    def tick_rate(self) -> float:
        """Current tick rate in seconds (for the main loop)."""
        return self.speed.hero_tick


def create_game(maze: Maze, speed: SpeedConfig | None = None) -> GameState:
    """Create a new game from a maze."""
    meta = maze.metadata

    hero = Hero(
        row=int(meta.hero_row),
        col=int(meta.hero_col),
    )

    ghosts: list[Ghost] = []
    ghost_row = int(meta.ghost_row)
    ghost_col = int(meta.ghost_col)

    for i in range(NUM_GHOSTS):
        g = Ghost(
            row=ghost_row + int(meta.ghost_row_offset) * (i % 2),
            col=ghost_col + int(meta.ghost_col_offset) * (i // 2),
            home_row=ghost_row,
            home_col=ghost_col,
            color_index=i,
        )
        ghosts.append(g)

    state = GameState(
        maze=maze,
        hero=hero,
        ghosts=ghosts,
        total_dots=maze.dot_count,
        phase=GamePhase.READY,
        speed=speed or SpeedConfig(),
    )

    # Start first scatter wave
    if SCATTER_CHASE_WAVES:
        state.wave_timer = SCATTER_CHASE_WAVES[0][0]
        state.in_scatter = True
        for g in ghosts:
            g.make_scatter(state.wave_timer)

    return state


def tick(state: GameState) -> list[str]:
    """Advance the game by one tick. Returns list of events."""
    events: list[str] = []
    state.tick_number += 1

    if state.phase == GamePhase.READY:
        state.ready_timer -= 1
        if state.ready_timer <= 0:
            state.phase = GamePhase.PLAYING
            events.append("start")
        return events

    if state.phase == GamePhase.DYING:
        state.phase_timer -= 1
        if state.phase_timer <= 0:
            if state.lives > 0:
                _reset_positions(state)
                state.phase = GamePhase.READY
                state.ready_timer = 30
                events.append("respawn")
            else:
                state.phase = GamePhase.GAME_OVER
                events.append("game_over")
        return events

    if state.phase in (GamePhase.WON, GamePhase.GAME_OVER):
        return events

    # ── Playing phase ──

    # Move hero
    state.hero.update(state.maze)

    # Check dot/pellet collection
    collected = state.maze.remove_dot(state.hero.row, state.hero.col)
    if collected == DOT:
        state.score += 10
        state.dots_eaten += 1
        events.append("dot")
    elif collected == PELLET:
        state.score += 50
        state.dots_eaten += 1
        state.ghosts_eaten_combo = 0
        for ghost in state.ghosts:
            ghost.make_frightened(PELLET_DURATION)
        events.append("pellet")

    # Check win condition
    if state.maze.dot_count <= 0:
        state.phase = GamePhase.WON
        events.append("won")
        return events

    # Update scatter/chase waves
    _update_scatter_chase(state)

    # Move ghosts with personality AI
    blinky = state.ghosts[0] if state.ghosts else None
    for ghost in state.ghosts:
        ghost.update(
            state.maze,
            state.hero.row,
            state.hero.col,
            state.hero.direction,
            blinky=blinky,
            tick_number=state.tick_number,
        )

    # Check collisions
    for ghost in state.ghosts:
        if ghost.row == state.hero.row and ghost.col == state.hero.col:
            if ghost.state == GhostState.FRIGHTENED:
                ghost.state = GhostState.EYES
                idx = min(state.ghosts_eaten_combo, len(GHOST_SCORE_SEQUENCE) - 1)
                points = GHOST_SCORE_SEQUENCE[idx]
                state.score += points
                state.ghosts_eaten_combo += 1
                events.append(f"eat_ghost:{points}")
            elif ghost.state == GhostState.HUNTING:
                state.lives -= 1
                state.hero.alive = False
                state.phase = GamePhase.DYING
                state.phase_timer = 15
                events.append("death")
                return events

    # Check extra lives
    for threshold in EXTRA_LIFE_SCORES:
        if state.score >= threshold > state.score - 10:
            state.lives += 1
            events.append("extra_life")

    return events


def _update_scatter_chase(state: GameState) -> None:
    """Manage scatter/chase wave transitions."""
    if state.wave_index >= len(SCATTER_CHASE_WAVES):
        return  # Permanent chase after all waves

    state.wave_timer -= 1
    if state.wave_timer > 0:
        return

    scatter_dur, chase_dur = SCATTER_CHASE_WAVES[state.wave_index]

    if state.in_scatter:
        # Transition to chase
        state.in_scatter = False
        state.wave_timer = chase_dur
        for g in state.ghosts:
            if g.state == GhostState.SCATTER:
                g.state = GhostState.HUNTING
                g.direction = Direction.NONE  # Allow direction recalc
    else:
        # Transition to scatter (advance to next wave)
        state.wave_index += 1
        if state.wave_index < len(SCATTER_CHASE_WAVES):
            scatter_dur, _ = SCATTER_CHASE_WAVES[state.wave_index]
            state.in_scatter = True
            state.wave_timer = scatter_dur
            for g in state.ghosts:
                if g.state == GhostState.HUNTING:
                    g.make_scatter(scatter_dur)


def _reset_positions(state: GameState) -> None:
    """Reset hero and ghost positions after a death."""
    meta = state.maze.metadata
    state.hero.row = int(meta.hero_row)
    state.hero.col = int(meta.hero_col)
    state.hero.direction = Direction.NONE
    state.hero.next_direction = Direction.NONE
    state.hero.alive = True

    ghost_row = int(meta.ghost_row)
    ghost_col = int(meta.ghost_col)
    for i, ghost in enumerate(state.ghosts):
        ghost.row = ghost_row + int(meta.ghost_row_offset) * (i % 2)
        ghost.col = ghost_col + int(meta.ghost_col_offset) * (i // 2)
        ghost.state = GhostState.HUNTING
        ghost.direction = Direction.UP
        ghost.frightened_timer = 0
        ghost.move_counter = 0
