# 云上 GPU 租金价格监控台

一个面向个人投研的轻量静态 dashboard，用于按 GPU 型号观察租金变化。

当前版本只使用 **一个统一主数据源**：`Mercatus GPU Index`。

## 当前能力

- 同一来源覆盖：`H100`、`H200`、`B200`、`B300`、`A100 80GB`、`L40S`、`RTX 4090`、`RTX 5090`
- 同一口径：`USD / GPU-hour`
- 同一来源公开窗口：当前接口提供 `90D` 日线
- 前端会优先请求 Mercatus 最新公开数据，失败时回退到仓库静态快照
- 本地历史会在定时刷新后持续累积，不再只保留最近 90 天
- 首页直接展示每个 GPU 型号的一张历史图
- 支持 `7D / 30D / 90D / MAX` 区间切换
- 点击任一型号卡片，可进入该型号的独立详情页
- 提供跨型号比较：
  - 型号价格比较图
  - 区间涨幅排行
  - `B200 / H100`、`B300 / H100`、`H200 / H100`、`RTX 5090 / RTX 4090` 等相对溢价
- 详情页提供：
  - 更大的单型号走势图
  - 最新价、区间涨跌、高低点、均价
  - 数据口径、样本点数、相对 H100 溢价
  - 最近 10 个观测日变化表

## 数据源

- 主数据源：`Mercatus GPU Index`
- 公开接口：`/api/gpu/trend?range=90D&baseModel=...`
- 说明：Mercatus 页面公开说明其价格来自 50+ 云厂商，并统一归一到 `USD / GPU-hour`。

## 本地运行

```bash
cd gpu-rental-monitor
python3 -m pip install -r requirements.txt
python3 scripts/refresh_data.py
./start-site.sh 4176
```

打开：`http://127.0.0.1:4176`

## 刷新数据

```bash
python3 scripts/refresh_data.py
```

## 准实时与自动更新

仓库内置两层更新机制：

- 前端打开页面时，优先直接请求 `Mercatus GPU Index` 最新 `90D` 日线数据，并与仓库已累积历史合并
- 如果实时请求失败，页面自动回退到 `data/aggregated/prices.json` 静态快照
- GitHub Actions 文件：`.github/workflows/daily-refresh.yml`
- 频率：每小时一次，UTC 每小时 `:20` 左右触发；实际运行时间可能受 GitHub Actions 排队影响
- 行为：
  - 安装依赖
  - 运行 `python3 scripts/refresh_data.py`
  - 当数据有变化时，自动提交 `data/raw` 与 `data/aggregated`
  - 将新抓取的滚动 `90D` 数据与仓库中已有历史合并，按日期去重并持续累积，作为实时请求失败时的兜底数据
  - 所有正常刷新与恢复刷新共用一个并发锁，延迟到达的任务不会同时写入 `main`
  - 数据推送遇到瞬时网络故障时最多重试 3 次，并在重试前同步最新的 `main`
- 自动恢复文件：`.github/workflows/refresh-recovery.yml`
  - 定时刷新失败后自动触发一次恢复检查
  - 如果已有更新的成功运行则直接跳过，避免重复刷新
  - 如果仍未恢复则补跑刷新；因此 GitHub 托管 Runner 暂时不可用时，Runner 恢复后可自动补偿

> GitHub 托管 Runner 在任务开始前发生的平台故障时，原失败记录仍会保留；仓库内的恢复流程负责降低数据停更影响，但无法消除 GitHub 平台自身的故障记录。

## 目录结构

```text
gpu-rental-monitor/
  index.html
  app.js
  styles.css
  data/
    aggregated/prices.json
  scripts/
    refresh_data.py
    rebuild_aggregates.py
  src/gpu_monitor/
  tests/
```

## 测试

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## 当前边界

- 免费公开接口目前稳定提供的是滚动 `90D` 历史，而不是多年历史。
- 本版本会从上线日起持续累积自有历史，但不会回填接口当前无法复核的更早日期。
- 本版本刻意不再混入其他来源来延长时间轴，以保证横向比较口径完全一致。
