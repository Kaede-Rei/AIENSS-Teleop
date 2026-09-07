#!/usr/bin/env python3
"""Read-only DM follower diagnostic: does not enable motors or home the gripper."""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from dm_arm_teleop.config import load_arm_config
from dm_arm_teleop.dm_control.DM_CAN import DM_variable, MotorControl
from dm_arm_teleop.follower import DMFollower


DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "config" / "arm.yaml"


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only DM follower diagnostic")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--follower_port", default=None)
    parser.add_argument("--freq", type=float, default=10.0)
    args = parser.parse_args()

    cfg = load_arm_config(args.config)
    if args.follower_port is not None:
        cfg = cfg.with_overrides(follower_port=args.follower_port)
    if args.freq <= 0:
        raise ValueError("--freq must be greater than 0")

    try:
        import serial
    except ImportError as exc:
        raise RuntimeError("pyserial is required for follower diagnostics") from exc

    follower = DMFollower(cfg.robot)
    serial_device = serial.Serial(cfg.robot.port, 115200, timeout=0.5)
    time.sleep(0.5)
    control = MotorControl(serial_device)
    for motor in follower.motors.values():
        control.addMotor(motor)

    print("Follower read-only diagnostic. Motors are NOT enabled; gripper homing is NOT run.")
    try:
        for name, motor in follower.motors.items():
            for _ in range(3):
                control.refresh_motor_status(motor)
                time.sleep(0.01)
            mode = control.read_motor_param(motor, DM_variable.CTRL_MODE)
            if mode is None:
                raise RuntimeError(f"No response from {name} ({motor.MotorType.name}, ID=0x{motor.SlaveID:02X})")
            print(f"PASS {name:8s} type={motor.MotorType.name:6s} id=0x{motor.SlaveID:02X} ctrl_mode={mode}")

        period = 1.0 / args.freq
        while True:
            parts = []
            for name, motor in follower.motors.items():
                control.refresh_motor_status(motor)
                parts.append(
                    f"{name}: q={motor.getPosition():+.3f} "
                    f"dq={motor.getVelocity():+.3f} tau={motor.getTorque():+.3f}"
                )
            print(" | ".join(parts))
            time.sleep(period)
    except KeyboardInterrupt:
        print("\nStopping follower diagnostic...")
    finally:
        if getattr(control.serial_, "is_open", False):
            control.serial_.close()


if __name__ == "__main__":
    main()
