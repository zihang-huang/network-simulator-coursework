# Omega Network Simulator

本实验模拟了一个 8x8 Omega 网络，用于分析给定的置换是否会发生阻塞，并计算完成该置换所需的最小传输周期（Cycles）。

## 功能

-   **阻塞检测**: 判断给定的置换在 Omega 网络中是否是阻塞的。
-   **调度算法**: 如果发生阻塞，使用冲突图着色算法计算无冲突传输所需的最小周期数。
-   **开关状态计算**: 输出每个周期中所有开关的状态（Straight/直连 或 Cross/交叉）。

## 运行环境

-   Python 3.x
-   无需安装额外的第三方库（使用标准库 `re` 和 `itertools`）。

## 如何运行

### 1. 运行默认测试案例

如果不传递任何参数，脚本将运行作业中预设的 5 个置换 (`pi1` - `pi5`)：

```bash
python omega_sim.py
```

### 2. 运行自定义置换

您可以通过命令行参数传递一个或多个置换（使用**轮换表示法**）。
**注意**：由于包含空格和括号，请务必用引号将每个置换字符串括起来。

```bash
# 运行单个自定义置换
python omega_sim.py "(1 2) (3 4)"

# 运行多个自定义置换
python omega_sim.py "(1 2) (3 4)" "(0 7 6)"
```

## 输出结果 (Output)

程序运行后会在终端直接输出实验结果，包括：

-   **Status**: `NON-BLOCKING` (无阻塞) 或 `BLOCKING` (阻塞)。
-   **Minimum Cycles**: 完成置换所需的最少时间周期。
-   **Schedule**: 每个周期的传输计划。
    -   `Transmissions`: 当前周期进行的传输对 (`源->目的`)。
    -   `Switch Settings`: 每一级开关的状态。
        -   `0`: 直连 (Straight)
        -   `1`: 交叉 (Cross)
        -   `-`: 未使用 (Unused)

### 输出示例

```text
--- Analysis for pi1 ---
Permutation: (7 0 6 5 2) (4 3) (1)
Status: BLOCKING
Minimum Cycles: 3
  Cycle 1:
    Transmissions: 0->6, 6->5, 2->7
    Switch Settings:
      Stage 0: 1  -  -  0
      Stage 1: -  0  1  -
      Stage 2: 0  -  1  1
  ...
```
