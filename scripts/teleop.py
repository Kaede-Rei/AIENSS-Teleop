#!/usr/bin/env python3
from __future__ import annotations

import argparse
import time
from pathlib import Path

from dm_arm_teleop.config import load_arm_config
from dm_arm_teleop.follower import DMFollower
from dm_arm_teleop.leader import DMLeader


DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "config" / "arm.yaml"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Standalone single-arm Dynamixel leader -> DM follower teleoperation"
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--follower_port", default=None)
    parser.add_argument("--leader_port", default=None)
    parser.add_argument("--freq", type=float, default=200.0)
    parser.add_argument("--joint_velocity_scaling", type=float, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.freq <= 0:
        raise ValueError("--freq must be greater than 0")

    cfg = load_arm_config(args.config).with_overrides(
        follower_port=args.follower_port,
        leader_port=args.leader_port,
        joint_velocity_scaling=args.joint_velocity_scaling,
    )

    leader = DMLeader(cfg.teleop)
    follower = DMFollower(cfg.robot)
    leader_connected = False
    follower_connected = False

    try:
        leader.connect()
        leader_connected = True
        follower.connect()
        follower_connected = True

        period = 1.0 / args.freq
        print(
            f"Starting standalone teleoperation at target {args.freq:g} Hz "
            "(no LeRobot, no cameras, no GUI)..."
        )
        while True:
            action = leader.read_action()
            follower.send_action(action)
            time.sleep(period)
    except KeyboardInterrupt:
        print("\nStopping teleoperation...")
    finally:
        if follower_connected:
            follower.disconnect()
        if leader_connected:
            leader.disconnect()


if __name__ == "__main__":
    main()
