from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class FollowerConfig:
    port: str
    disable_torque_on_disconnect: bool = False
    joint_velocity_scaling: float = 0.2
    max_gripper_torque: float = 1.0

    def __post_init__(self) -> None:
        if not self.port:
            raise ValueError("Follower port must be configured")
        if not 0.0 < self.joint_velocity_scaling <= 1.0:
            raise ValueError("joint_velocity_scaling must be in (0, 1]")
        if self.max_gripper_torque <= 0.0:
            raise ValueError("max_gripper_torque must be greater than 0")


@dataclass(frozen=True)
class LeaderConfig:
    port: str
    gripper_open_pos: int = 2280
    gripper_closed_pos: int = 1670
    direction: tuple[int, ...] = (1, 1, 1, 1, 1, 1)
    offset: tuple[float, ...] = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    def __post_init__(self) -> None:
        if not self.port:
            raise ValueError("Leader port must be configured")
        if len(self.direction) != 6 or any(v not in (-1, 1) for v in self.direction):
            raise ValueError("direction must contain 6 values, each either -1 or 1")
        if len(self.offset) != 6:
            raise ValueError("offset must contain 6 values")
        if self.gripper_open_pos == self.gripper_closed_pos:
            raise ValueError("gripper_open_pos and gripper_closed_pos must be different")


@dataclass(frozen=True)
class ArmConfig:
    robot: FollowerConfig
    teleop: LeaderConfig

    def with_overrides(
        self,
        *,
        follower_port: str | None = None,
        leader_port: str | None = None,
        joint_velocity_scaling: float | None = None,
    ) -> "ArmConfig":
        robot = replace(
            self.robot,
            port=follower_port if follower_port is not None else self.robot.port,
            joint_velocity_scaling=(
                joint_velocity_scaling
                if joint_velocity_scaling is not None
                else self.robot.joint_velocity_scaling
            ),
        )
        teleop = replace(
            self.teleop,
            port=leader_port if leader_port is not None else self.teleop.port,
        )
        return ArmConfig(robot=robot, teleop=teleop)


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"Config section '{name}' must be a mapping")
    return value


def load_arm_config(config_path: str | Path) -> ArmConfig:
    path = Path(config_path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"Config file does not exist: {path}")
    with path.open("r", encoding="utf-8") as f:
        root = yaml.safe_load(f) or {}
    if not isinstance(root, dict):
        raise ValueError(f"Config root must be a mapping: {path}")

    robot = _mapping(root.get("robot"), "robot")
    teleop = _mapping(root.get("teleop"), "teleop")

    follower_cfg = FollowerConfig(
        port=robot.get("port"),
        disable_torque_on_disconnect=robot.get("disable_torque_on_disconnect", False),
        joint_velocity_scaling=float(robot.get("joint_velocity_scaling", 0.2)),
        max_gripper_torque=float(robot.get("max_gripper_torque", 1.0)),
    )
    leader_cfg = LeaderConfig(
        port=teleop.get("port"),
        gripper_open_pos=int(teleop.get("gripper_open_pos", 2280)),
        gripper_closed_pos=int(teleop.get("gripper_closed_pos", 1670)),
        direction=tuple(int(v) for v in teleop.get("direction", [1, 1, 1, 1, 1, 1])),
        offset=tuple(float(v) for v in teleop.get("offset", [0, 0, 0, 0, 0, 0])),
    )
    return ArmConfig(robot=follower_cfg, teleop=leader_cfg)
