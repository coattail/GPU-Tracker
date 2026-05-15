# 云上 GPU 租金价格监控台

一个面向个人投研的轻量静态 dashboard，用于按 GPU 型号观察租金变化。

当前版本只使用 **一个统一主数据源**：`Mercatus GPU Index`。

## 当前能力

- 同一来源覆盖：`H100`、`H200`、`B200`、`B300`、`A100 80GB`、`L40S`
- 同一口径：`USD / GPU-hour`
- 同一历史窗口：公开 `90D` 日线
- 首页直接展示每个 GPU 型号的一张历史图
- 支持 `7D / 30D / 90D` 区间切换
- 点击任一型号卡片，可进入该型号的独立详情页
- 提供跨型号比较：
  - 型号价格比较图
  - 区间涨幅排行
  - `B200 / H100`、`B300 / H100`、`H200 / H100` 等相对溢价
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

## 每日自动更新

仓库内置 GitHub Actions 工作流：

- 文件：`.github/workflows/daily-refresh.yml`
- 频率：每天一次
- 时间：UTC `01:20`（北京时间 `09:20`）
- 行为：
  - 安装依赖
  - 运行 `python3 scripts/refresh_data.py`
  - 当数据有变化时，自动提交 `data/raw` 与 `data/aggregated`

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

- 免费公开接口目前稳定提供的是 `90D` 历史，而不是多年历史。
- 本版本刻意不再混入其他来源来延长时间轴，以保证横向比较口径完全一致。
