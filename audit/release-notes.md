在指定 180 nm 模型上完成三轮全差分 OTA 设计和复测。标称静差 0.3974%，0.5% 上升和下降建立分别为 4.76、4.78 ns，功耗 353.49 µW。

PDF 为五页设计报告。nominal.zip 提供审核用网表、操作点、瞬态和频域数据。actions-replay.zip 保存发布时由 GitHub Actions 重新运行的仿真数据和报告。版本源码包还包含 REF 的两个原始附件、所用模型、三轮记录、30 组敏感性数据、20 个失配样本及其波形。初版冻结点为 dca5841。

模型仅含标称卡。附加的工艺和失配扰动采用报告列明的假设。交付物为前仿网表与数据。复现初版可运行 round1 网表或检出冻结点，无数据迁移步骤。

[设计需求 #2](https://github.com/DestinySky1/Analog_Design_Test_OPAMP/issues/2) · [设计与复核 PR #3](https://github.com/DestinySky1/Analog_Design_Test_OPAMP/pull/3)
