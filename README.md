# AIENSS-Teleop

**AIENSS-Teleop** 是一个不依赖 LeRobot ROS 相机或 GUI 的单臂主从遥操作仓库

```text
Dynamixel XL330 Leader  →  Python standalone teleop  →  DaMiao DM Follower
```

仓库目标是把原 `Dual-DM-Arm-LeRobot` 中已经验证过的单臂遥操作链路独立出来

保留原有电机配置 关节映射 夹爪逻辑 限位和控制参数

运行时只保留机械臂遥操作真正需要的 Python 依赖

---

## 1 硬件与平台

### 1.1 Leader Dynamixel 示教臂

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
- 读取 `Present_Position`
- 7 个电机同步读取

### 1.2 Follower 达妙 DM 六轴臂和夹爪

| 关节 | 电机 | Slave ID | Master ID |
|---|---|---:|---:|
| J1 | DM4340 | `0x01` | `0x11` |
| J2 | DM4340 | `0x02` | `0x12` |
| J3 | DM4340 | `0x03` | `0x13` |
| J4 | DM4310 | `0x04` | `0x14` |
| J5 | DM4310 | `0x05` | `0x15` |
| J6 | DM4310 | `0x06` | `0x16` |
| Gripper | DM4310 | `0x07` | `0x17` |

Follower 通过串口连接达妙 USB-CAN 或对应串口控制器

当前代码固定使用 `115200` baud

### 1.3 操作系统支持

| 平台 | 状态 | 说明 |
|---|---|---|
| **Linux / Ubuntu** | **已实机验证** | 使用 `install.sh` 和 `launch.sh` |
| **Windows Native** | **已实机验证** | 使用 `install.bat` 和 `launch.bat` |
| WSL | 不推荐 | USB 和串口透传会增加额外排障成本 |
| macOS | 未验证 | 底层 DYNAMIXEL SDK 具备支持基础 但当前仓库没有实机测试 |

Windows Native 已在当前硬件环境完成安装和运行测试

本次成功测试环境包含 Python `3.14.3`

Linux 和 Windows 使用同一套 Python 控制代码

平台差异主要集中在串口设备名 虚拟环境路径 驱动安装和启动脚本

### 1.4 软件要求

- Python `>= 3.10`
- `numpy`
- `pyserial`
- `PyYAML`
- `dynamixel-sdk`

不需要安装以下框架

- LeRobot
- PyTorch
- Hugging Face
- ROS 或 ROS 2
- OpenCV
- Rerun
- 相机驱动

---

## 2 Quick Start

### 2.1 Linux

#### 安装

在仓库根目录运行

```bash
./install.sh
```

脚本会完成以下操作

1. 检查 Python `>= 3.10`
2. 创建 `.venv`
3. 准备 Python 安装环境
4. 安装本项目和运行时依赖

如果脚本没有执行权限

```bash
chmod +x install.sh launch.sh
./install.sh
```

如果系统存在多个 Python 可以显式指定

```bash
PYTHON_BIN=python3.11 ./install.sh
```

#### 配置串口

修改

```text
config/arm.yaml
```

Linux 示例

```yaml
robot:
  port: /dev/ttyUSB0

teleop:
  port: /dev/ttyUSB1
```

当前配置中的 `/dev/com-*` 属于特定机器上的稳定设备名

换机器后请按照实际设备路径修改

#### 首次只读检查

Leader

```bash
./.venv/bin/python scripts/leader_test.py
```

Follower

```bash
./.venv/bin/python scripts/follower_test.py
```

两侧读取正常后再启动遥操作

#### 启动

```bash
./launch.sh
```

停止使用 `Ctrl-C`

---

### 2.2 Windows Native

#### 安装

在 PowerShell 或 CMD 中进入仓库根目录

推荐运行

```powershell
.\install.bat
```

也可以直接双击 `install.bat`

Windows 安装脚本会完成以下操作

1. 优先使用 Windows Python Launcher `py -3`
2. 找不到 Launcher 时尝试 `python`
3. 检查 Python `>= 3.10`
4. 创建 `.venv`
5. 检查虚拟环境中的 pip
6. 检测异常的 `~ip*` 残留
7. 在 pip 损坏时自动重建 `.venv`
8. 直接执行 `pip install -e .`

Windows 安装脚本不会在刚创建的虚拟环境中升级 pip 自身

这样可以避免 Windows 文件占用导致的 `WinError 32`

本次 Windows 实测使用 Python `3.14.3` 安装成功

#### 配置串口

修改

```text
config/arm.yaml
```

Windows 示例

```yaml
robot:
  port: COM3

teleop:
  port: COM4
```

`COM3` 和 `COM4` 只是示例

实际端口请在 Windows 设备管理器中确认

Leader 和 Follower 对应的 USB 转接器驱动需要提前正常安装

#### 首次只读检查

Leader

```powershell
.\.venv\Scripts\python.exe scripts\leader_test.py
```

Follower

```powershell
.\.venv\Scripts\python.exe scripts\follower_test.py
```

两侧读取正常后再启动遥操作

#### 启动

```powershell
.\launch.bat
```

停止使用 `Ctrl-C`

Windows 当前已经完成实机运行测试

---

## 3 配置 `config/arm.yaml`

默认配置

```yaml
robot:
  port: /dev/com-1.3-tty
  disable_torque_on_disconnect: true
  joint_velocity_scaling: 1.0
  max_gripper_torque: 1.0

  cameras:
    end:
      type: opencv
      index_or_path: /dev/com-1.2-video
      width: 640
      height: 480
      fps: 30
    eye:
      type: opencv
      index_or_path: 4
      width: 1280
      height: 720
      fps: 30

teleop:
  port: /dev/com-1.4-tty
  gripper_open_pos: 2280
  gripper_closed_pos: 1670
  direction: [1, 1, 1, 1, 1, 1]
  offset: [0.0, 0.0, 1.64, 0.0, 0.0, 0.0]
```

### 3.1 `robot` DM Follower

#### `robot.port`

Follower 的串口设备

Linux 示例

```yaml
port: /dev/ttyUSB0
```

Windows 示例

```yaml
port: COM3
```

#### `disable_torque_on_disconnect`

```yaml
disable_torque_on_disconnect: true
```

为 `true` 时 正常退出遥操作后会尝试失能全部 DM 电机

建议保持 `true`

#### `joint_velocity_scaling`

```yaml
joint_velocity_scaling: 1.0
```

允许范围

```text
0 < scaling <= 1.0
```

首次调试可以先降低到

```yaml
joint_velocity_scaling: 0.3
```

当前版本为保持原仓库行为 J1 到 J6 都使用同一个速度基准

```text
joint_velocity_scaling × DM4340_SPEED
```

即使 J4 到 J6 实际使用 DM4310 当前版本也暂时不按型号拆分速度上限

#### `max_gripper_torque`

```yaml
max_gripper_torque: 1.0
```

该参数用于计算 Follower 夹爪 `Torque_Pos` 模式下的目标电流

#### `cameras`

该字段仅用于兼容原 `Dual-DM-Arm-LeRobot` 配置

本仓库不会读取 初始化或显示任何相机

可以保留该字段 也可以删除整个 `cameras` 配置块

### 3.2 `teleop` Dynamixel Leader

#### `teleop.port`

Leader 的 DYNAMIXEL 串口设备

Linux 示例

```yaml
port: /dev/ttyUSB1
```

Windows 示例

```yaml
port: COM4
```

#### `gripper_open_pos` 和 `gripper_closed_pos`

```yaml
gripper_open_pos: 2280
gripper_closed_pos: 1670
```

这两个值是 Leader 夹爪的 DYNAMIXEL encoder tick

当前映射

```text
2280 → 0.0 → Follower open
1670 → 1.0 → Follower closed
```

如果更换 Leader 夹爪结构或零点 需要重新测量这两个值

#### `direction`

```yaml
direction: [1, 1, 1, 1, 1, 1]
```

对应 J1 到 J6 的关节方向

允许值只有 `1` 和 `-1`

例如反转 J2

```yaml
direction: [1, -1, 1, 1, 1, 1]
```

#### `offset`

```yaml
offset: [0.0, 0.0, 1.64, 0.0, 0.0, 0.0]
```

对应 J1 到 J6 的弧度偏置

当前配置中 J3 使用 `+1.64 rad`

这是现有 Leader 和 Follower 对齐的一部分

没有重新标定时不建议修改

---

## 4 启动脚本与运行参数

### 4.1 Linux

```bash
./launch.sh
```

### 4.2 Windows

```powershell
.\launch.bat
```

两个启动脚本都会把额外参数透传给 `scripts/teleop.py`

### 临时覆盖串口

Linux

```bash
./launch.sh \
  --leader_port /dev/ttyUSB1 \
  --follower_port /dev/ttyUSB0
```

Windows

```powershell
.\launch.bat --leader_port COM4 --follower_port COM3
```

### 临时降低速度

Linux

```bash
./launch.sh --joint_velocity_scaling 0.3
```

Windows

```powershell
.\launch.bat --joint_velocity_scaling 0.3
```

### 修改目标循环频率

默认值

```text
200 Hz
```

Linux 示例

```bash
./launch.sh --freq 100
```

Windows 示例

```powershell
.\launch.bat --freq 100
```

查看完整参数

Linux

```bash
./launch.sh --help
```

Windows

```powershell
.\launch.bat --help
```

---

## 5 首次硬件检查与安全

### 5.1 Leader 只读检查

Linux

```bash
./.venv/bin/python scripts/leader_test.py
```

Windows

```powershell
.\.venv\Scripts\python.exe scripts\leader_test.py
```

该脚本会读取 7 个 Dynamixel 的 `Present_Position`

该脚本不会使能主臂关节扭矩

该脚本不会发送目标位置

### 5.2 Follower 只读检查

Linux

```bash
./.venv/bin/python scripts/follower_test.py
```

Windows

```powershell
.\.venv\Scripts\python.exe scripts\follower_test.py
```

该脚本会探测 7 个 DM 电机并读取状态

该脚本不会 enable 电机

该脚本不会执行夹爪 homing

### 5.3 正式遥操作启动行为

正式启动后 Follower 会按照原仓库行为执行以下流程

1. 检查 J1 到 J6 和 Gripper
2. 切换到对应控制模式
3. enable DM 电机
4. 写入原控制参数
5. 执行夹爪自动找零
6. 进入 Leader 到 Follower 实时映射循环

夹爪自动找零会主动运动夹爪

检测条件

```text
torque > 1.2
```

达到条件后会停止 失能 设置零位 重新使能并进入 `Torque_Pos`

首次启动前必须保证夹爪运动方向没有手指 线缆 工具或硬物阻挡

---

## 6 控制行为与数据流

```text
XL330 Leader
ID 1..7 / 115200 / Protocol 2.0
        ↓
Present_Position
        ↓
raw tick → rad
        ↓
direction + offset
        ↓
gripper normalize 0..1
        ↓
DM Follower
J1..J6: POS_VEL
Gripper: Torque_Pos
```

### 6.1 Leader 映射

J1 到 J6

```text
rad = raw / 4096 × 2π - π
rad = rad × direction[i] + offset[i]
```

默认 J3 偏置

```text
J3 += 1.64 rad
```

Gripper

```text
open tick   = 2280 → 0.0
closed tick = 1670 → 1.0
```

### 6.2 Follower 限位

```text
J4: -100° ~ +100°
J5:  -90° ~  +90°
```

夹爪映射

```text
Leader 0..1
     ↓
Follower 0 .. -5.23 rad
```

### 6.3 Follower 原始控制参数

J1 到 J3

```text
ACC    = 10
DEC    = -10
KP_APR = 200
KI_APR = 10
```

Gripper

```text
KP_APR = 100
```

---

## 7 开发与测试

Linux 安装开发依赖

```bash
./.venv/bin/python -m pip install -e '.[dev]'
```

Windows 安装开发依赖

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Linux 运行测试

```bash
./.venv/bin/python -m pytest -q
```

Windows 运行测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

语法检查

```bash
./.venv/bin/python -m compileall -q dm_arm_teleop scripts
bash -n install.sh
bash -n launch.sh
```

软件测试覆盖以下内容

- 配置加载与覆盖
- Leader tick 到 rad
- direction 和 offset
- J3 `+1.64 rad`
- Gripper 归一化
- J4 和 J5 限位
- 统一 DM4340 速度缩放兼容行为
- Gripper 位置和电流换算
- DYNAMIXEL Protocol 2.0 寄存器访问
- Leader 配置顺序
- 仓库无 LeRobot runtime import 和 dependency
- Linux Bash 启动入口
- Windows Batch 安装和启动入口

---

## 8 仓库结构

```text
AIENSS-Teleop/
├── install.sh
├── launch.sh
├── install.bat
├── launch.bat
├── config/
│   └── arm.yaml
├── dm_arm_teleop/
│   ├── config.py
│   ├── mapping.py
│   ├── dynamixel_bus.py
│   ├── leader.py
│   ├── follower.py
│   └── dm_control/
│       ├── DM_CAN.py
│       └── LICENSE
├── scripts/
│   ├── teleop.py
│   ├── leader_test.py
│   └── follower_test.py
├── tests/
├── pyproject.toml
├── requirements.txt
├── NOTICE.md
└── LICENSE
```

---

## 9 仓库历史

本仓库的单臂遥操作逻辑最初来自 `Kaede-Rei/Dual-DM-Arm-LeRobot`

原实现面向 LeRobot 集成

其中同时包含 DM Follower Dynamixel Leader LeRobot Robot LeRobot Teleoperator Camera config `lerobot-teleoperate` 和 Rerun GUI

对于单纯的机械臂主从遥操作 这些上层框架会引入大量与实际运动控制无关的依赖

因此 AIENSS-Teleop 将已经使用过的单臂链路独立出来

原来的数据链路

```text
Leader → LeRobot Teleoperator → LeRobot teleop runtime → Robot → DM
```

现在的数据链路

```text
Leader → standalone Python → DM
```

独立过程中刻意保持以下行为不变

- Leader 7 个 XL330 ID 与型号
- Protocol 2.0 和 115200 baud
- J3 `+1.64 rad`
- `direction` 和 `offset`
- Gripper 2280 和 1670
- DM 电机 ID 与类型
- J4 和 J5 限位
- Gripper 自动找零
- Gripper Torque Position
- J1 到 J6 共用原 `DM4340_SPEED` 的兼容行为

仓库目标是去掉框架依赖 而不是改变机械臂控制表现

后续如果需要接入 LeRobot Isaac Sim ROS 2 或 SerialArm-Core 建议继续把本仓库视为底层硬件遥操作 baseline

---

## 10 来源与许可证

DM 底层协议实现来源和许可证见以下文件

```text
NOTICE.md
dm_arm_teleop/dm_control/LICENSE
```

本仓库其余新增代码使用根目录 `MIT License`
