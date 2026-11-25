# Analog_Design_Test_OPAMP
运放的前后仿测试仿真

## 三轮 OTA 设计

[五页设计报告](report/ota.pdf) · [三轮指标对照](round3/改进记录.md) · [原始附件](REF/) · [审核原始数据](audit/nominal.zip)

| 阶段 | 可复核的内容 |
|---|---|
| 第一遍 | [冻结网表与测量](round1/)，提交 dca5841，早于首次查阅答案 |
| 第二遍 | [参考报告对照及精度差异](round2/对照.md) |
| 第三遍 | [改进网表、测量和扫描](round3/)，[报告源文件与画图脚本](report/) |

`audit/nominal.zip` 保存冻结初版、同台复测初版和最终版的 ngspice 测试网表、日志和原始数值。`round3/pvt.csv`、`mismatch.csv` 按行给出测量结果；同名 `_waves.npz` 用 `<case>_t`、`<case>_v` 保存每个样本的完整时间（秒）和差分输出（伏）。两份原始压缩包和 180 nm 模型的校验值在 `audit/inputs.sha256`。

云端复跑使用 ngspice 44.2、Python 3 和 NumPy。在仓库根目录执行 `sha256sum -c audit/inputs.sha256` 和 `python3 sim/review.py /tmp/ota-replay`。图表使用 Matplotlib，PDF 用 IEEEtran、pdfLaTeX 编译，完整命令见 [Actions 工作流](.github/workflows/ota.yml)。`NGSPICE` 可指定仿真器路径。
