# Analog_Design_Test_OPAMP
运放的前后仿测试仿真

## 三轮 OTA 设计

[五页设计报告](report/ota.pdf) · [三轮指标对照](round3/改进记录.md) · [原始附件](REF/) · [审核原始数据](audit/nominal.zip)

### 最终网表与原理图

[在 RNL Viewer 打开 OTA](https://rich-netlist.github.io/rnl/viewer/?url=https%3A%2F%2Fraw.githubusercontent.com%2FDestinySky1%2FAnalog_Design_Test_OPAMP%2Fmain%2Fround3%2Fota.rnl.sp&level=ota) · [RNL 源文件](round3/ota.rnl.sp) · [SVG 矢量原理图](round3/ota.rnl.svg) · [高清 PNG](round3/ota.rnl.png) · [仿真用 SPICE 网表](round3/ota.cir)

RNL 文件在原始 SPICE 网表中用注释保存符号、位置和布线。也可以在 Viewer 中选择 **File → Open File** 打开下载的 `ota.rnl.sp`，选择 `ota` 层。SVG 适合放大查看，PNG 为 3078 × 2428 像素。

图中采用 RNL 0.4 的 `rnl-std-all` 标准库，可按下面的方法读图或绘制同类单元。[官方中文指南](https://rich-netlist.github.io/rnl/zh/)

| 单元 | 画法及本图对应器件 |
|---|---|
| 差分输入对 | M1、M2 左右镜像，栅极朝外，公共源节点 `t` 向下接居中的 Mtail。PMOS 源极朝上接 `vdd`。 |
| 偏置电流镜 | Mref、Mtail 同高，两栅沿水平线 `b` 相连。Mref 漏极经短支线接到栅线上，交点用实心点标记。 |
| 共模检测、补偿 | 两组共模检测桥分别画出取样点 `a` 和 `s`。两条串联 RC 补偿支路上下对齐，按 `xp → op`、`xm → om` 读；同名网络标签与上方主电路相连。 |
| 衬底 | 图中统一注明 NMOS 体端接 `0`、PMOS 体端接 `vdd`。每只 MOS 的四个端子均可在 RNL 的 SPICE 行中按 D、G、S、B 顺序核对。 |

[七项测试台补测与原始数据](audit/bias/README.md) 包括逐管偏置、输出共模阶跃、失配电流和三个共模环路探针。假设 SS、85 °C、1.1 V 下尾管饱和余量为 −3.28 mV。

### 三轮记录

| 阶段 | 可复核的内容 |
|---|---|
| 第一遍 | [冻结网表与测量](round1/)，提交 dca5841，早于首次查阅答案 |
| 第二遍 | [参考报告对照及精度差异](round2/对照.md) |
| 第三遍 | [改进网表、测量和扫描](round3/)，[报告源文件与画图脚本](report/) |

`audit/nominal.zip` 保存冻结初版、同台复测初版和最终版的 ngspice 测试网表、日志和原始数值。`round3/pvt.csv`、`mismatch.csv` 按行给出测量结果；同名 `_waves.npz` 用 `<case>_t`、`<case>_v` 保存每个样本的完整时间（秒）和差分输出（伏）。两份原始压缩包和 180 nm 模型的校验值在 `audit/inputs.sha256`。

云端复跑使用 ngspice 44.2、Python 3 和 NumPy。在仓库根目录执行 `sha256sum -c audit/inputs.sha256` 和 `python3 sim/review.py /tmp/ota-replay`。图表使用 Matplotlib，PDF 用 IEEEtran、pdfLaTeX 编译，完整命令见 [Actions 工作流](.github/workflows/ota.yml)。`NGSPICE` 可指定仿真器路径。
