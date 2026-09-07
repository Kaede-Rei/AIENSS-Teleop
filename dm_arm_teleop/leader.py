from __future__ import annotations

from .config import LeaderConfig
from .dynamixel_bus import (
    ADDR_CURRENT_LIMIT,
    ADDR_GOAL_POSITION,
    ADDR_OPERATING_MODE,
    ADDR_RETURN_DELAY_TIME,
    ADDR_TORQUE_ENABLE,
    MOTOR_IDS,
    DynamixelBus,
)
from .mapping import leader_ticks_to_action


class DMLeader:
    """Standalone XL330 leader arm with the same mapping/config as the LeRobot version."""

    GRIPPER_ID = 7
    OPERATING_MODE_CURRENT_POSITION = 5

    def __init__(self, config: LeaderConfig, *, bus: DynamixelBus | object | None = None):
        self.config = config
        self.bus = bus if bus is not None else DynamixelBus(config.port)
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self) -> None:
        if self._connected:
            raise RuntimeError("Leader already connected")
        self.bus.open()
        try:
            self.configure()
        except Exception:
            self.bus.close()
            raise
        self._connected = True

    def configure(self) -> None:
        # Mirrors the original sequence:
        # bus.disable_torque(); bus.configure_motors(); then gripper setup.
        for motor_id in MOTOR_IDS:
            self.bus.write_register(motor_id, ADDR_TORQUE_ENABLE, 1, 0)
        for motor_id in MOTOR_IDS:
            self.bus.write_register(motor_id, ADDR_RETURN_DELAY_TIME, 1, 0)

        self.bus.write_register(self.GRIPPER_ID, ADDR_TORQUE_ENABLE, 1, 0)
        self.bus.write_register(
            self.GRIPPER_ID,
            ADDR_OPERATING_MODE,
            1,
            self.OPERATING_MODE_CURRENT_POSITION,
        )
        self.bus.write_register(self.GRIPPER_ID, ADDR_CURRENT_LIMIT, 2, 100)
        self.bus.write_register(self.GRIPPER_ID, ADDR_TORQUE_ENABLE, 1, 1)
        self.bus.write_register(
            self.GRIPPER_ID,
            ADDR_GOAL_POSITION,
            4,
            self.config.gripper_open_pos,
        )

    def read_action(self) -> dict[str, float]:
        if not self._connected:
            raise RuntimeError("Leader is not connected")
        raw_by_id = self.bus.read_positions()
        raw = {f"joint_{i}": raw_by_id[i] for i in range(1, 7)}
        raw["gripper"] = raw_by_id[self.GRIPPER_ID]
        return leader_ticks_to_action(
            raw,
            direction=self.config.direction,
            offset=self.config.offset,
            gripper_open_pos=self.config.gripper_open_pos,
            gripper_closed_pos=self.config.gripper_closed_pos,
        )

    def disconnect(self) -> None:
        if not self._connected:
            return
        self.bus.close()
        self._connected = False
