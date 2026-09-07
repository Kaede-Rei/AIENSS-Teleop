from __future__ import annotations

import math
import time
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

    def connect(self) -> None:
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
        try:
            self.configure()
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
                raise RuntimeError(f"Unable to read from {key} ({motor.MotorType.name}).")
            print(f"  {key} ({motor.MotorType.name}) is connected.")
            self.control.switchControlMode(motor, Control_Type.POS_VEL)
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
        self.control.control_Vel(motor, 10.0)
        while True:
            self.control.refresh_motor_status(motor)
            if motor.getTorque() > 1.2:
                self.control.control_Vel(motor, 0.0)
                self.control.disable(motor)
                self.control.set_zero_position(motor)
                time.sleep(0.2)
                self.control.enable(motor)
                break
            time.sleep(0.01)
        self.control.switchControlMode(motor, Control_Type.Torque_Pos)

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

    def send_action(self, action: dict[str, Any]) -> dict[str, float]:
        if not self.is_connected or self.control is None:
            raise RuntimeError("Follower is not connected")

        goal_pos = {
            key.removesuffix(".pos"): float(val)
            for key, val in action.items()
            if key.endswith(".pos")
        }
        required = set(self.motors)
        missing = required - set(goal_pos)
        if missing:
            raise KeyError(f"Missing action fields: {sorted(missing)}")

        for key, motor in self.motors.items():
            if key == "gripper":
                self.control.refresh_motor_status(motor)
                mapped = map_range(
                    goal_pos[key],
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
            else:
                if key in self.JOINT_LIMITS:
                    goal_pos[key] = float(np.clip(goal_pos[key], *self.JOINT_LIMITS[key]))
                # Intentionally preserve the original implementation: J1..J6
                # all use DM4340_SPEED, even J4..J6 which are DM4310 motors.
                self.control.control_Pos_Vel(
                    motor,
                    goal_pos[key],
                    self.config.joint_velocity_scaling * self.DM4340_SPEED,
                )

        return {f"{motor}.pos": val for motor, val in goal_pos.items()}

    def disconnect(self) -> None:
        if not self.is_connected:
            return
        if self.control is not None and self.config.disable_torque_on_disconnect:
            for motor in self.motors.values():
                try:
                    self.control.disable(motor)
                except Exception:
                    pass
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
