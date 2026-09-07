from __future__ import annotations

import math
from collections.abc import Mapping, Sequence


def map_range(x: float, in_min: float, in_max: float, out_min: float, out_max: float) -> float:
    if in_max == in_min:
        raise ValueError("input range must be non-zero")
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


def normalize_gripper(raw: float, open_pos: int, closed_pos: int) -> float:
    # Exact algebra used by the original DMLeader.get_action().
    gripper_range = open_pos - closed_pos
    if gripper_range == 0:
        raise ValueError("gripper open/closed positions must differ")
    return 1.0 - (raw - closed_pos) / gripper_range


def leader_ticks_to_action(
    raw_positions: Mapping[str, float],
    *,
    direction: Sequence[int],
    offset: Sequence[float],
    gripper_open_pos: int,
    gripper_closed_pos: int,
) -> dict[str, float]:
    if len(direction) != 6 or len(offset) != 6:
        raise ValueError("direction and offset must each contain 6 values")

    action: dict[str, float] = {}
    for i in range(6):
        name = f"joint_{i + 1}"
        raw = float(raw_positions[name])
        radians = raw / 4096.0 * 2.0 * math.pi - math.pi
        action[f"{name}.pos"] = radians * direction[i] + offset[i]

    action["gripper.pos"] = normalize_gripper(
        float(raw_positions["gripper"]),
        gripper_open_pos,
        gripper_closed_pos,
    )
    return action
