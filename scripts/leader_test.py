#!/usr/bin/env python3
"""Read-only leader diagnostic: no torque enable and no position commands."""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from dm_arm_teleop.config import load_arm_config
from dm_arm_teleop.dynamixel_bus import DynamixelBus
from dm_arm_teleop.mapping import leader_ticks_to_action


DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "config" / "arm.yaml"


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only Dynamixel leader diagnostic")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--leader_port", default=None)
    parser.add_argument("--freq", type=float, default=20.0)
    args = parser.parse_args()

    cfg = load_arm_config(args.config)
    if args.leader_port is not None:
        cfg = cfg.with_overrides(leader_port=args.leader_port)
    if args.freq <= 0:
        raise ValueError("--freq must be greater than 0")

    bus = DynamixelBus(cfg.teleop.port)
    bus.open()
    period = 1.0 / args.freq
    print("Leader read-only diagnostic. Ctrl-C to stop.")
    try:
        while True:
            raw_by_id = bus.read_positions()
            raw = {f"joint_{i}": raw_by_id[i] for i in range(1, 7)}
            raw["gripper"] = raw_by_id[7]
            action = leader_ticks_to_action(
                raw,
                direction=cfg.teleop.direction,
                offset=cfg.teleop.offset,
                gripper_open_pos=cfg.teleop.gripper_open_pos,
                gripper_closed_pos=cfg.teleop.gripper_closed_pos,
            )
            raw_text = " ".join(f"ID{i}={raw_by_id[i]:5d}" for i in range(1, 8))
            mapped_text = " ".join(
                f"J{i}={action[f'joint_{i}.pos']:+.3f}" for i in range(1, 7)
            )
            print(f"{raw_text} | {mapped_text} G={action['gripper.pos']:+.3f}")
            time.sleep(period)
    except KeyboardInterrupt:
        print("\nStopping leader diagnostic...")
    finally:
        bus.close()


if __name__ == "__main__":
    main()
