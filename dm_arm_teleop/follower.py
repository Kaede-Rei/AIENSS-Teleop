from __future__ import annotations

import math
import time
from collections.abc import Iterable
from typing import Any

import numpy as np

from .config import FollowerConfig
from .dm_control.DM_CAN import (
    Control_Type,
    DM_Motor,
    DM_Motor_Type,
    DM_variable,
    MotorControl,
)
from .mapping import map_range


class DMFollower:
    """Standalone wrapper preserving the original DM follower behavior."""

    DM4310_TORQUE_CONSTANT = 0.945
    EMIT_VELOCITY_SCALE = 100
    EMIT_CURRENT_SCALE = 1000

    JOINT_NAMES = tuple(f"joint_{i}" for i in range(1, 7))
    JOINT_LIMITS = {
        "joint_4": (-100 / 180 * math.pi, 100 / 180 * math.pi),
        "joint_5": (-90 / 180 * math.pi, 90 / 180 * math.pi),
    }

    DM4310_SPEED = 200 / 60 * 2 * math.pi
    DM4340_SPEED = 52.5 / 60 * 2 * math.pi

    def __init__(self, config: FollowerConfig):
        self.config = config
        self.motors = {
            "joint_1": DM_Motor(DM_Motor_Type.DM4340, 0x01, 0x11),
            "joint_2": DM_Motor(DM_Motor_Type.DM4340, 0x02, 0x12),
            "joint_3": DM_Motor(DM_Motor_Type.DM4340, 0x03, 0x13),
            "joint_4": DM_Motor(DM_Motor_Type.DM4310, 0x04, 0x14),
            "joint_5": DM_Motor(DM_Motor_Type.DM4310, 0x05, 0x15),
            "joint_6": DM_Motor(DM_Motor_Type.DM4310, 0x06, 0x16),
            "gripper": DM_Motor(DM_Motor_Type.DM4310, 0x07, 0x17),
        }
        self.control: MotorControl | Any | None = None
        self.serial_device = None
        self.bus_connected = False
        self.gripper_open_pos = 0.0
        self.gripper_closed_pos = -5.23

    @property
    def is_connected(self) -> bool:
        return self.bus_connected

    def _open_bus(self) -> None:
        if self.is_connected:
            raise RuntimeError("Follower already connected")
        try:
            import serial
        except ImportError as exc:
            raise RuntimeError("pyserial is required for follower hardware access") from exc

        self.serial_device = serial.Serial(self.config.port, 115200, timeout=0.5)
        time.sleep(0.5)
        self.control = MotorControl(self.serial_device)
        self.bus_connected = True

    def connect(self) -> None:
        """Connect and perform the original teleoperation configuration sequence."""
        self._open_bus()
        try:
            self.configure()
        except Exception:
            self._close_serial()
            self.bus_connected = False
            raise

    def connect_passive(self) -> None:
        """Connect without enabling, disabling, homing, or changing motor modes."""
        self._open_bus()
        try:
            if self.control is None:
                raise RuntimeError("Follower control is not initialized")
            for key, motor in self.motors.items():
                self.control.addMotor(motor)
                for _ in range(3):
                    self.control.refresh_motor_status(motor)
                    time.sleep(0.01)
                mode = self.control.read_motor_param(motor, DM_variable.CTRL_MODE)
                if mode is None:
                    raise RuntimeError(f"Unable to read control mode from {key} ({motor.MotorType.name})")
                try:
                    motor.NowControlMode = Control_Type(int(mode))
                except ValueError:
                    raise RuntimeError(f"Unsupported control mode {mode!r} on {key}") from None
                if getattr(motor, "status_code", None) is None:
                    self.control.refresh_motor_status(motor)
                if getattr(motor, "status_code", None) is None:
                    raise RuntimeError(f"Unable to read status from {key} ({motor.MotorType.name})")
                print(
                    f"  {key} ({motor.MotorType.name}) status=0x{motor.status_code:X} "
                    f"mode={motor.NowControlMode.name}"
                )
        except Exception:
            self._close_serial()
            self.bus_connected = False
            raise

    def configure(self) -> None:
        if self.control is None:
            raise RuntimeError("Follower control is not initialized")

        for key, motor in self.motors.items():
            self.control.addMotor(motor)
            for _ in range(3):
                self.control.refresh_motor_status(motor)
                time.sleep(0.01)
            if self.control.read_motor_param(motor, DM_variable.CTRL_MODE) is None:
                raise RuntimeError(f"Unable to read from {key} ({motor.MotorType.name})")
            print(f"  {key} ({motor.MotorType.name}) is connected")
            self.control.switchControlMode(motor, Control_Type.POS_VEL)
            motor.NowControlMode = Control_Type.POS_VEL
            self.control.enable(motor)

        for joint in ("joint_1", "joint_2", "joint_3"):
            self.control.change_motor_param(self.motors[joint], DM_variable.ACC, 10.0)
            self.control.change_motor_param(self.motors[joint], DM_variable.DEC, -10.0)
            self.control.change_motor_param(self.motors[joint], DM_variable.KP_APR, 200)
            self.control.change_motor_param(self.motors[joint], DM_variable.KI_APR, 10)

        self.control.change_motor_param(self.motors["gripper"], DM_variable.KP_APR, 100)
        self._home_gripper()

    def _home_gripper(self) -> None:
        if self.control is None:
            raise RuntimeError("Follower control is not initialized")
        motor = self.motors["gripper"]
        self.control.switchControlMode(motor, Control_Type.VEL)
        motor.NowControlMode = Control_Type.VEL
        self.control.control_Vel(motor, 10.0)
        while True:
            self.control.refresh_motor_status(motor)
            if motor.getTorque() > 1.2:
                self.control.control_Vel(motor, 0.0)
                # Local gripper-only disable is intentionally preserved for zeroing
                self.control.disable(motor)
                self.control.set_zero_position(motor)
                time.sleep(0.2)
                self.control.enable(motor)
                break
            time.sleep(0.01)
        self.control.switchControlMode(motor, Control_Type.Torque_Pos)
        motor.NowControlMode = Control_Type.Torque_Pos

    def read_state(self) -> dict[str, float]:
        if not self.is_connected or self.control is None:
            raise RuntimeError("Follower is not connected")
        state: dict[str, float] = {}
        for key, motor in self.motors.items():
            self.control.refresh_motor_status(motor)
            if key == "gripper":
                state[f"{key}.pos"] = map_range(
                    motor.getPosition(),
                    self.gripper_open_pos,
                    self.gripper_closed_pos,
                    0.0,
                    1.0,
                )
            else:
                state[f"{key}.pos"] = float(motor.getPosition())
        return state

    def read_joint_positions(self) -> dict[str, float]:
        if not self.is_connected or self.control is None:
            raise RuntimeError("Follower is not connected")
        state: dict[str, float] = {}
        for key in self.JOINT_NAMES:
            motor = self.motors[key]
            self.control.refresh_motor_status(motor)
            state[f"{key}.pos"] = float(motor.getPosition())
        return state

    def _joint_goals(self, action: dict[str, Any]) -> dict[str, float]:
        goals = {
            key.removesuffix(".pos"): float(val)
            for key, val in action.items()
            if key.endswith(".pos") and key.removesuffix(".pos") in self.JOINT_NAMES
        }
        missing = set(self.JOINT_NAMES) - set(goals)
        if missing:
            raise KeyError(f"Missing joint action fields: {sorted(missing)}")
        return goals

    def send_joint_positions(self, action: dict[str, Any]) -> dict[str, float]:
        """Send J1..J6 only, leaving gripper state untouched."""
        if not self.is_connected or self.control is None:
            raise RuntimeError("Follower is not connected")
        goal_pos = self._joint_goals(action)
        for key in self.JOINT_NAMES:
            motor = self.motors[key]
            if key in self.JOINT_LIMITS:
                goal_pos[key] = float(np.clip(goal_pos[key], *self.JOINT_LIMITS[key]))
            # Preserve original implementation: all J1..J6 use DM4340_SPEED
            self.control.control_Pos_Vel(
                motor,
                goal_pos[key],
                self.config.joint_velocity_scaling * self.DM4340_SPEED,
            )
        return {f"{key}.pos": value for key, value in goal_pos.items()}

    def send_action(self, action: dict[str, Any]) -> dict[str, float]:
        if not self.is_connected or self.control is None:
            raise RuntimeError("Follower is not connected")

        sent = self.send_joint_positions(action)
        if "gripper.pos" not in action:
            raise KeyError("Missing action fields: ['gripper']")
        gripper_goal = float(action["gripper.pos"])
        motor = self.motors["gripper"]
        self.control.refresh_motor_status(motor)
        mapped = map_range(
            gripper_goal,
            0.0,
            1.0,
            self.gripper_open_pos,
            self.gripper_closed_pos,
        )
        self.control.control_pos_force(
            motor,
            mapped,
            self.DM4310_SPEED * self.EMIT_VELOCITY_SCALE,
            i_des=(
                self.config.max_gripper_torque
                / self.DM4310_TORQUE_CONSTANT
                * self.EMIT_CURRENT_SCALE
            ),
        )
        sent["gripper.pos"] = gripper_goal
        return sent

    def motor_statuses(
        self,
        *,
        motor_names: Iterable[str] | None = None,
        refresh: bool = True,
    ) -> dict[str, int | None]:
        if not self.is_connected or self.control is None:
            raise RuntimeError("Follower is not connected")
        names = tuple(self.motors) if motor_names is None else tuple(motor_names)
        statuses: dict[str, int | None] = {}
        for key in names:
            motor = self.motors[key]
            if refresh:
                self.control.refresh_motor_status(motor)
            statuses[key] = getattr(motor, "status_code", None)
        return statuses

    @staticmethod
    def _format_statuses(statuses: dict[str, int | None]) -> str:
        return ", ".join(
            f"{key}=0x{status:X}" if status is not None else f"{key}=unknown"
            for key, status in statuses.items()
        )

    def enable_disabled_motors(
        self,
        *,
        motor_names: Iterable[str] | None = None,
        refresh: bool = True,
    ) -> list[str]:
        if not self.is_connected or self.control is None:
            raise RuntimeError("Follower is not connected")
        names = tuple(self.motors) if motor_names is None else tuple(motor_names)
        statuses = self.motor_statuses(motor_names=names, refresh=refresh)
        faults = {key: status for key, status in statuses.items() if status not in (0, 1)}
        if faults:
            raise RuntimeError(
                f"Follower motor status is not safe to enable: {self._format_statuses(faults)}"
            )

        enabled: list[str] = []
        for key in names:
            if statuses[key] == 0:
                motor = self.motors[key]
                self.control.enable(motor)
                self.control.refresh_motor_status(motor)
                if getattr(motor, "status_code", None) != 1:
                    raise RuntimeError(
                        f"Failed to enable {key}, status="
                        f"{self._format_statuses({key: getattr(motor, 'status_code', None)})}"
                    )
                enabled.append(key)
        return enabled

    def prepare_reset_joints(self, *, refresh: bool = True) -> list[str]:
        """Ensure J1..J6 are enabled in POS_VEL without touching the gripper."""
        if not self.is_connected or self.control is None:
            raise RuntimeError("Follower is not connected")
        statuses = self.motor_statuses(motor_names=self.JOINT_NAMES, refresh=refresh)
        faults = {key: status for key, status in statuses.items() if status not in (0, 1)}
        if faults:
            raise RuntimeError(
                f"Follower joint fault blocks reset: {self._format_statuses(faults)}"
            )

        enabled: list[str] = []
        for key in self.JOINT_NAMES:
            motor = self.motors[key]
            status = statuses[key]
            if status == 1:
                if motor.NowControlMode != Control_Type.POS_VEL:
                    raise RuntimeError(
                        f"{key} is enabled in {motor.NowControlMode.name}, expected POS_VEL; "
                        "refusing to change mode while loaded"
                    )
                continue

            if motor.NowControlMode != Control_Type.POS_VEL:
                if not self.control.switchControlMode(motor, Control_Type.POS_VEL):
                    raise RuntimeError(f"Failed to switch {key} to POS_VEL before enable")
                motor.NowControlMode = Control_Type.POS_VEL
            self.control.enable(motor)
            self.control.refresh_motor_status(motor)
            if getattr(motor, "status_code", None) != 1:
                raise RuntimeError(
                    f"Failed to enable {key}: {self._format_statuses({key: getattr(motor, 'status_code', None)})}"
                )
            enabled.append(key)
        return enabled

    def disable_all(self) -> None:
        """Explicit whole-arm disable, never called implicitly by disconnect."""
        if not self.is_connected or self.control is None:
            return
        for motor in self.motors.values():
            self.control.disable(motor)

    def disconnect(self) -> None:
        """Close follower communication without changing motor enable state."""
        if not self.is_connected:
            return
        self._close_serial()
        self.bus_connected = False

    def _close_serial(self) -> None:
        serial_obj = None
        if self.control is not None:
            serial_obj = getattr(self.control, "serial_", None)
        if serial_obj is None:
            serial_obj = self.serial_device
        if serial_obj is not None and getattr(serial_obj, "is_open", False):
            serial_obj.close()
