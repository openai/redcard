from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from time import sleep

from .local_overlay import _ensure_overlay_executable


SPRITE_WIDTH = 161
SPRITE_HEIGHT = 198


class DemoReferee:
    def __init__(self, config: dict) -> None:
        sprite_root = Path(config.get("sprite_root", "assets/sprites"))
        if not sprite_root.is_absolute():
            sprite_root = Path.cwd() / sprite_root
        if not sprite_root.exists():
            raise RuntimeError(f"Referee sprite root not found: {sprite_root}")

        self.sprite_root = sprite_root
        self.scale = float(config.get("sprite_scale", 1.2))
        self.state_path = Path(tempfile.NamedTemporaryFile("w", suffix=".json", delete=False).name)
        self.process: subprocess.Popen | None = None
        self.x = float(config.get("x", 40))
        self.y = float(config.get("y", 520))
        self.current_scale = self.scale
        self.facing = "right"
        self._write_state(visible=False, x=self.x, y=self.y, animation="waiting")

    def start(self) -> None:
        if self.process is not None and self.process.poll() is None:
            return
        self._write_state(visible=False, x=self.x, y=self.y, animation="waiting")
        executable = _ensure_overlay_executable()
        self.process = subprocess.Popen(
            [str(executable), str(self.sprite_root), "600", "demo", str(self.state_path), str(os.getpid())]
        )
        sleep(0.25)
        if self.process.poll() is not None:
            return_code = self.process.returncode
            self.process = None
            raise RuntimeError(f"Referee overlay could not start (exit code {return_code}).")

    def show(
        self,
        x: float | None = None,
        y: float | None = None,
        animation: str = "waving",
        scale: float | None = None,
        facing: str | None = None,
    ) -> None:
        if x is not None:
            self.x = float(x)
        if y is not None:
            self.y = float(y)
        if scale is not None:
            self.current_scale = float(scale)
        if facing is not None:
            self.facing = facing
        self._write_state(
            visible=True,
            x=self.x,
            y=self.y,
            animation=animation,
            scale=self.current_scale,
            facing=self.facing,
        )

    def show_feet_at(
        self,
        feet_x: float,
        feet_y: float,
        animation: str = "waving",
        scale: float | None = None,
        facing: str | None = None,
        foot_anchor_x: float = 0.5,
    ) -> None:
        target_scale = float(scale) if scale is not None else self.current_scale
        self.show(
            feet_x - SPRITE_WIDTH * target_scale * foot_anchor_x,
            feet_y - SPRITE_HEIGHT * target_scale,
            animation=animation,
            scale=target_scale,
            facing=facing,
        )

    def move_to(
        self,
        x: float,
        y: float,
        duration: float = 1.0,
        animation: str = "running",
        final_animation: str = "waving",
        scale: float | None = None,
        facing: str | None = None,
        final_facing: str | None = None,
    ) -> None:
        start_x, start_y = self.x, self.y
        start_scale = self.current_scale
        target_scale = float(scale) if scale is not None else self.current_scale
        move_facing = facing or ("left" if x < start_x else "right")
        steps = max(1, int(duration * 30))
        for step in range(1, steps + 1):
            t = step / steps
            eased = t * t * (3 - 2 * t)
            self.x = start_x + (x - start_x) * eased
            self.y = start_y + (y - start_y) * eased
            self.current_scale = start_scale + (target_scale - start_scale) * eased
            self.facing = move_facing
            self._write_state(
                visible=True,
                x=self.x,
                y=self.y,
                animation=animation,
                scale=self.current_scale,
                facing=self.facing,
            )
            sleep(duration / steps)
        self.current_scale = target_scale
        self.facing = final_facing or move_facing
        self._write_state(
            visible=True,
            x=x,
            y=y,
            animation=final_animation,
            scale=self.current_scale,
            facing=self.facing,
        )

    def move_feet_to(
        self,
        feet_x: float,
        feet_y: float,
        duration: float = 1.0,
        animation: str = "running",
        final_animation: str = "waving",
        scale: float | None = None,
        facing: str | None = None,
        final_facing: str | None = None,
        foot_anchor_x: float = 0.5,
    ) -> None:
        target_scale = float(scale) if scale is not None else self.current_scale
        self.move_to(
            feet_x - SPRITE_WIDTH * target_scale * foot_anchor_x,
            feet_y - SPRITE_HEIGHT * target_scale,
            duration=duration,
            animation=animation,
            final_animation=final_animation,
            scale=target_scale,
            facing=facing,
            final_facing=final_facing,
        )

    def animate(
        self,
        animation: str,
        seconds: float,
        scale: float | None = None,
        facing: str | None = None,
    ) -> None:
        if scale is not None:
            self.current_scale = float(scale)
        if facing is not None:
            self.facing = facing
        self._write_state(
            visible=True,
            x=self.x,
            y=self.y,
            animation=animation,
            scale=self.current_scale,
            facing=self.facing,
        )
        sleep(seconds)

    def stop(self) -> None:
        self._write_state(visible=False, x=self.x, y=self.y, animation="waiting", quit=True)
        process = self.process
        self.process = None
        if process:
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=1)
        self.state_path.unlink(missing_ok=True)

    def _write_state(self, **state: object) -> None:
        state.setdefault("scale", self.current_scale)
        state.setdefault("facing", self.facing)
        tmp_path = self.state_path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(state), encoding="utf-8")
        tmp_path.replace(self.state_path)
