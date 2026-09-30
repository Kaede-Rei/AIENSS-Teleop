#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import time
from pathlib import Path
from typing import Callable

from dm_arm_teleop.config import load_arm_config
from dm_arm_teleop.follower import DMFollower


DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "config" / "arm.yaml"
JOINT_KEYS = tuple(f"joint_{i}.pos" for i in range(1, 7))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Safely move DM follower J1..J6 to zero")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--follower_port", default=None)
    parser.add_argument("--joint_velocity_scaling", type=float, default=0.2)
    parser.add_argument("--control_freq", type=float, default=200.0)
    parser.add_argument("--smooth_time", type=float, default=2.0)
    parser.add_argument("--max_step", type=float, default=0.05)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--tolerance", type=float, default=0.02)
    return parser.parse_args()


def compute_reset_action(
    start_positions: dict[str, float],
    current_positions: dict[str, float],
    *,
    alpha: float,
    max_step: float,
) -> dict[str, float]:
    alpha = min(max(float(alpha), 0.0), 1.0)
    action: dict[str, float] = {}
    for key in JOINT_KEYS:
        q_start = float(start_positions[key])
        q_now = float(current_positions[key])
        q_ref = (1.0 - alpha) * q_start
        delta = q_ref - q_now
        if abs(delta) > max_step:
            q_cmd = q_now + math.copysign(max_step, delta)
        else:
            q_cmd = q_ref
        action[key] = q_cmd
    return action


def smooth_reset(
    follower: DMFollower,
    *,
    control_freq: float,
    smooth_time: float,
    max_step: float,
    timeout: float,
    tolerance: float,
    clock: Callable[[], float] = time.monotonic,
    sleep_fn: Callable[[float], None] = time.sleep,
    print_fn: Callable[[str], None] = print,
) -> None:
    if control_freq <= 0 or smooth_time <= 0 or max_step <= 0 or timeout <= 0 or tolerance <= 0:
        raise ValueError("reset timing, step, timeout, and tolerance values must be greater than 0")

    enabled_now = follower.prepare_reset_joints(refresh=True)
    if enabled_now:
        print_fn(f"[reset] Enabled previously disabled joints: {', '.join(enabled_now)}")
    else:
        print_fn("[reset] J1..J6 already enabled | no extra enable command sent")

    start_positions = follower.read_joint_positions()
    print_fn("[reset] Current joint positions")
    for key in JOINT_KEYS:
        q = start_positions[key]
        print_fn(f"  {key.removesuffix('.pos')}: {q:+.4f} rad")

    period = 1.0 / control_freq
    start_time = clock()
    last_print = start_time

    while True:
        loop_start = clock()
        elapsed = loop_start - start_time
        if elapsed > timeout:
            raise TimeoutError(f"Reset timed out after {timeout:g} s")

        current = follower.read_joint_positions()
        max_error = max(abs(current[key]) for key in JOINT_KEYS)
        if max_error <= tolerance:
            zero_action = {key: 0.0 for key in JOINT_KEYS}
            follower.send_joint_positions(zero_action)
            print_fn(f"[reset] Reset complete | max error {max_error:.4f} rad")
            return

        alpha = min(elapsed / smooth_time, 1.0)
        action = compute_reset_action(
            start_positions,
            current,
            alpha=alpha,
            max_step=max_step,
        )
        follower.send_joint_positions(action)

        if loop_start - last_print >= 1.0:
            print_fn(f"[reset] {elapsed:5.1f}s | max error {max_error:.4f} rad")
            last_print = loop_start

        sleep_time = period - (clock() - loop_start)
        if sleep_time > 0:
            sleep_fn(sleep_time)


def main() -> int:
    args = parse_args()
    cfg = load_arm_config(args.config).with_overrides(
        follower_port=args.follower_port,
        joint_velocity_scaling=args.joint_velocity_scaling,
    )
    follower = DMFollower(cfg.robot)
    connected = False

    print("[AIENSS-Teleop] Safe follower reset")
    print(f"[reset] port={cfg.robot.port}")
    print(f"[reset] velocity scaling={cfg.robot.joint_velocity_scaling:g}")

    try:
        follower.connect_passive()
        connected = True
        smooth_reset(
            follower,
            control_freq=args.control_freq,
            smooth_time=args.smooth_time,
            max_step=args.max_step,
            timeout=args.timeout,
            tolerance=args.tolerance,
        )
        print("[reset] Motors remain enabled after reset")
        return 0
    except KeyboardInterrupt:
        print("\n[reset] Ctrl+C received | reset stopped | motors remain enabled")
        return 130
    except Exception as exc:
        print(f"\n[reset] Reset aborted: {type(exc).__name__}: {exc}")
        print("[reset] No automatic disable command was sent")
        return 1
    finally:
        if connected:
            follower.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())
