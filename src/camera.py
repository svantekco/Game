from __future__ import annotations

from dataclasses import dataclass

from .constants import (
    VIEWPORT_WIDTH,
    VIEWPORT_HEIGHT,
    ZOOM_LEVELS,
    DEFAULT_ZOOM_INDEX,
)


@dataclass
class Camera:
    """Simple camera tracking an offset and zoom level."""

    x: int = 0
    y: int = 0
    zoom_index: int = DEFAULT_ZOOM_INDEX

    @property
    def zoom(self) -> int:
        """Current zoom scale."""
        return ZOOM_LEVELS[self.zoom_index]

    @property
    def visible_tiles_x(self) -> int:
        """Number of map tiles visible horizontally at the current zoom."""
        return VIEWPORT_WIDTH // self.zoom

    @property
    def visible_tiles_y(self) -> int:
        """Number of map tiles visible vertically at the current zoom."""
        return VIEWPORT_HEIGHT // self.zoom

    def move(self, dx: int, dy: int, map_width: int, map_height: int) -> None:
        """Move the camera, clamping to map bounds."""
        self.x += dx
        self.y += dy

        max_x = max(0, map_width - self.visible_tiles_x)
        max_y = max(0, map_height - self.visible_tiles_y)
        self.x = min(max(self.x, 0), max_x)
        self.y = min(max(self.y, 0), max_y)

    def zoom_in(self) -> None:
        """Zoom in if possible."""
        if self.zoom_index < len(ZOOM_LEVELS) - 1:
            self.zoom_index += 1

    def zoom_out(self) -> None:
        """Zoom out if possible."""
        if self.zoom_index > 0:
            self.zoom_index -= 1

    def world_to_screen(self, wx: int, wy: int) -> tuple[int, int]:
        """Translate world coordinates to screen coordinates."""
        sx = (wx - self.x) * self.zoom
        sy = (wy - self.y) * self.zoom
        return sx, sy
