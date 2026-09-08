# AIENSS-Teleop

**AIENSS-Teleop** 是一个独立的单臂主从遥操作仓库

```text
Dynamixel XL330 Leader  →  Python standalone teleop  →  DaMiao DM Follower
```

仓库不依赖 LeRobot ROS 相机或 GUI

## 1 硬件与平台

### 1.1 Leader

| 关节 | 电机 | ID |
|---|---|---:|
| J1 | XL330-M288 | 1 |
| J2 | XL330-M288 | 2 |
| J3 | XL330-M288 | 3 |
| J4 | XL330-M288 | 4 |
| J5 | XL330-M077 | 5 |
| J6 | XL330-M077 | 6 |
| Gripper | XL330-M077 | 7 |

Leader 通信参数

- DYNAMIXEL Protocol 2.0
- 115200 baud
- 同步读取 7 个电机的 `Present_Position`

### 1.2 Follower

| 关节 | 电机 | Slave ID | Master ID |
|---|---|---:|---:|
| J1 | DM4340 | `0x01` | `0x11` |
| J2 | DM4340 | `0x02` | `0x12` |
| J3 | DM4340 | `0x03` | `0x13` |
| J4 | DM4310 | `0x04` | `0x14` |
| J5 | DM4310 | `0x05` | `0x15` |
| J6 | DM4310 | `0x06` | `0x16` |
| Gripper | DM4310 | `0x07` | `0x17` |

Follower 通过达妙 USB CAN 串口控制器连接

当前代码使用 115200 baud

### 1.3 平台支持

| 平台 | 状态 | 说明 |
|---|---|---|
| Linux Ubuntu | 已验证 推荐 | 使用 `install.sh` `launch.sh` `reset.sh` |
| Windows Native | 已完成实机验证 | 使用 `install.bat` `launch.bat` `reset.bat` |
| WSL | 不推荐 | USB 串口透传会增加排障成本 |
| macOS | 未验收 | 底层 SDK 支持但不是当前部署目标 |

软件要求

- Python `>= 3.10`
- `numpy`
- `pyserial`
- `PyYAML`
- `dynamixel-sdk`

## 2 Quick Start

### 2.1 Linux

安装

```bash
./install.sh
```

如果没有执行权限

```bash
chmod +x install.sh launch.sh reset.sh
./install.sh
```

只读检查

```bash
./.venv/bin/python scripts/leader_test.py
./.venv/bin/python scripts/follower_test.py
```

启动遥操作

```bash
./launch.sh
```

安全归零

```bash
./reset.sh
```

### 2.2 Windows Native

安装

```powershell
.\install.bat
```

只读检查

```powershell
.\.venv\Scripts\python.exe scripts\leader_test.py
.\.venv\Scripts\python.exe scripts\follower_test.py
```

启动遥操作

```powershell
.\launch.bat
```

安全归零

```powershell
.\reset.bat
```

## 3 配置 `config/arm.yaml`

默认核心配置

```yaml
robot:
  port: /dev/com-1.3-tty
  disable_torque_on_disconnect: false
  joint_velocity_scaling: 1.0
  max_gripper_torque: 1.0

teleop:
  port: /dev/com-1.4-tty
  gripper_open_pos: 2280
  gripper_closed_pos: 1670
  direction: [1, 1, 1, 1, 1, 1]
  offset: [0.0, 0.0, 1.64, 0.0, 0.0, 0.0]
```

### 3.1 `robot.port`

Linux 示例

```yaml
port: /dev/ttyUSB0
```

Windows 示例

```yaml
port: COM3
```

### 3.2 `teleop.port`

Linux 示例

```yaml
port: /dev/ttyUSB1
```

Windows 示例

```yaml
port: COM4
```

### 3.3 `disable_torque_on_disconnect`

该字段为了兼容旧配置继续保留

当前安全策略下 `DMFollower.disconnect()` 永远只关闭通信 不会自动失能

即使用户把该字段改成 `true` 也不会恢复旧的自动失能行为

整臂失能只能通过明确的用户确认触发

### 3.4 `joint_velocity_scaling`

允许范围

```text
0 < scaling <= 1.0
```

遥操作保持原实现 J1 到 J6 都使用 `joint_velocity_scaling × DM4340_SPEED`

### 3.5 `max_gripper_torque`

用于 Follower 夹爪 `Torque_Pos` 模式下的目标电流换算

### 3.6 `direction`

对应 J1 到 J6 的方向

允许值只有 `1` 和 `-1`

### 3.7 `offset`

默认配置

```yaml
offset: [0.0, 0.0, 1.64, 0.0, 0.0, 0.0]
```

当前 J3 保留 `+1.64 rad` 对齐偏置

## 4 Fault Hold 安全机制

运行时状态逻辑为：

```text
NORMAL
  Leader 读取成功
  ↓
  正常发送新 action

LEADER FAULT HOLD
  Leader 读取失败
  ↓
  不发送任何新 action
  ↓
  Follower 保持当前使能状态和最后目标
  ↓
  周期性重试 Leader 读取
  ├─ 恢复成功 → 自动回到 NORMAL
  └─ 持续失败 → 等待用户 Ctrl+C
```

Leader 读取失败时不会重发新的旧 action

Follower 依靠电机内部位置控制继续保持最后一次目标

Leader 恢复后遥操作自动继续

### 4.1 Ctrl+C

按下 `Ctrl+C` 后会询问是否失能 Follower

```text
Disable follower motors before exit? This may allow the arm to drop [y/N]
```

默认选择为 No

直接回车不会失能

输入 `n` 或 `no` 不会失能

只有明确输入 `y` 或 `yes` 才会调用整臂失能

### 4.2 普通异常

任何普通异常退出都不会自动失能 Follower

程序只关闭通信口并保留电机当前使能状态

发生异常后可以使用 `reset.sh` 或 `reset.bat` 归零

### 4.3 硬件 fault 的边界

软件可以避免程序异常路径主动发送 disable 命令

但如果 DM 驱动器自身进入过压 欠压 过流 过温 通信丢失或过载等硬件保护状态 电机固件本身仍可能停止输出

这种硬件保护行为无法通过本仓库的软件策略禁止

如果 DM 的 CAN TIMEOUT 已配置为非零 进程退出后停止通信仍可能触发驱动器通信丢失保护 因此需要按实际电机配置确认 TIMEOUT 行为

## 5 Safe Reset

reset 的目标是将 J1 到 J6 平滑移动到 `0 rad`

reset 不是修改编码器零点 也不会调用 DM 的 set zero position 命令

默认流程

```text
连接 Follower 但不改变使能状态
↓
读取 J1 到 J6 实际 DM 状态码
↓
状态 1 已使能
  直接使用
↓
状态 0 已失能
  确认控制模式
  必要时切换到 POS_VEL
  enable 对应关节
↓
状态 8 到 E 硬件 fault
  中止 reset
  不发送 disable
↓
读取当前位置
↓
时间插值 + 单步限幅
↓
平滑移动 J1 到 J6 到 0 rad
↓
保持使能并关闭通信
```

reset 不会操作夹爪

reset 不会执行夹爪 homing

reset 完成后不会失能

reset 被 Ctrl+C 中断后也不会失能

### 5.1 默认 reset 参数

```text
control_freq = 200 Hz
smooth_time = 2.0 s
max_step = 0.05 rad
tolerance = 0.02 rad
timeout = 30 s
joint_velocity_scaling = 0.2
```

Linux 参数示例

```bash
./reset.sh --smooth_time 4 --joint_velocity_scaling 0.1
```

Windows 参数示例

```powershell
.\reset.bat --smooth_time 4 --joint_velocity_scaling 0.1
```

完整参数

```bash
./reset.sh --help
```

```powershell
.\reset.bat --help
```

## 6 控制行为

Leader 映射

```text
rad = raw / 4096 × 2π - π
rad = rad × direction[i] + offset[i]
```

默认 J3

```text
J3 += 1.64 rad
```

Follower 限位

```text
J4 = ±100°
J5 = ±90°
```

Follower J1 到 J6 保留原有 POS_VEL 控制行为

Gripper 保留原有 Torque_Pos 控制和自动 homing 行为

夹爪 homing 中局部的 `disable → set zero → enable` 仍然保留

这一行为只作用于夹爪 不会导致整条机械臂失去支撑

## 7 常用命令

Linux

```bash
./launch.sh
./launch.sh --freq 100
./launch.sh --joint_velocity_scaling 0.3
./reset.sh
```

Windows

```powershell
.\launch.bat
.\launch.bat --freq 100
.\launch.bat --joint_velocity_scaling 0.3
.\reset.bat
```

## 8 仓库结构

```text
AIENSS-Teleop/
├── config/
│   └── arm.yaml
├── dm_arm_teleop/
│   ├── config.py
│   ├── dynamixel_bus.py
│   ├── follower.py
│   ├── leader.py
│   ├── mapping.py
│   └── dm_control/
├── scripts/
│   ├── teleop.py
│   ├── reset.py
│   ├── leader_test.py
│   └── follower_test.py
├── tests/
├── install.sh
├── launch.sh
├── reset.sh
├── install.bat
├── launch.bat
├── reset.bat
├── README.md
└── pyproject.toml
```

## 9 仓库历史

本仓库的单臂遥操作路径来自 `Kaede-Rei/Dual-DM-Arm-LeRobot`

原项目依赖 LeRobot 完成 Leader 与 Follower 封装

AIENSS-Teleop 将这条已经验证的硬件链路抽离为独立 Python 实现

## 10 许可证

仓库主体遵循根目录 `LICENSE`

`dm_arm_teleop/dm_control/DM_CAN.py` 来源及许可证信息见对应目录中的 `LICENSE`
