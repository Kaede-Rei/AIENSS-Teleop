#!/usr/bin/env python3
from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Callable

from dm_arm_teleop.config import load_arm_config
from dm_arm_teleop.follower import DMFollower
from dm_arm_teleop.leader import DMLeader


DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "config" / "arm.yaml"
DEFAULT_FAULT_RETRY_INTERVAL = 0.1


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


def read_action_with_fault_hold(
    leader: DMLeader | object,
    *,
    retry_interval: float = DEFAULT_FAULT_RETRY_INTERVAL,
    sleep_fn: Callable[[float], None] = time.sleep,
    print_fn: Callable[[str], None] = print,
) -> dict[str, float]:
    """Retry leader reads while leaving the follower untouched on read faults."""
    fault_active = False
    while True:
        try:
            action = leader.read_action()
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            if not fault_active:
                print_fn(
                    f"[LEADER FAULT HOLD] {type(exc).__name__}: {exc} | "
                    "follower stays enabled and holds the last target"
                )
                fault_active = True
            sleep_fn(retry_interval)
            continue

        if fault_active:
            print_fn("[AIENSS-Teleop] Leader recovered | teleoperation resumed")
        return action


def prompt_disable_on_exit(*, input_fn: Callable[[str], str] = input) -> bool:
    """Return True only when the user explicitly requests follower disable."""
    try:
        answer = input_fn(
            "Disable follower motors before exit? This may allow the arm to drop [y/N]: "
        )
    except (EOFError, KeyboardInterrupt):
        return False
    return answer.strip().lower() in {"y", "yes"}


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
    explicit_disable = False

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
            action = read_action_with_fault_hold(leader)
            follower.send_action(action)
            time.sleep(period)
    except KeyboardInterrupt:
        print("\n[AIENSS-Teleop] Ctrl+C received")
        explicit_disable = follower_connected and prompt_disable_on_exit()
        if not explicit_disable:
            print("[AIENSS-Teleop] Follower remains enabled")
    except Exception as exc:
        print(f"\n[AIENSS-Teleop] Teleoperation stopped by error: {type(exc).__name__}: {exc}")
        print("[AIENSS-Teleop] Follower will NOT be disabled automatically")
        print("[AIENSS-Teleop] Use reset.sh or reset.bat when recovery is needed")
    finally:
        if follower_connected:
            if explicit_disable:
                try:
                    follower.disable_all()
                    print("[AIENSS-Teleop] Follower motors disabled by explicit user request")
                except Exception as exc:
                    print(f"[AIENSS-Teleop] Explicit disable failed: {type(exc).__name__}: {exc}")
            follower.disconnect()
        if leader_connected:
            leader.disconnect()


if __name__ == "__main__":
    main()
