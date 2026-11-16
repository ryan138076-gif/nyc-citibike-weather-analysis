# SI 618 Milestone 1 — Citi Bike × Weather 项目需求文档

> **版本**：v1.0 · 2026-10-14  
> **项目**：NYC Citi Bike Ridership and Weather Analysis  
> **当前范围**：仅 Milestone 1（M1）。为后续 GitHub Portfolio 保留可维护结构，但**不在 M1 做假设检验或建模**。  
> **截止**：2026-10-14，Project Studio 结束时（以课程页面为准）。  
> **执行方式**：拆为三个独立 Session；每个 Session 结束必须有可检查的成果，后一 Session 依赖前一 Session 的验收结果。

## 0. 项目背景与目标

研究 **2024 年纽约市 Citi Bike 每日骑行需求** 与 **降水量、温度及工作日/周末** 的描述性关联。将 Citi Bike 逐次骑行记录按开始日期汇总，与 NOAA Central Park 气象站日观测按 `date` 合并，生成一份每日粒度的 tidy dataset，并用至少三张图支持三个研究问题。

### 成功定义

- 使用至少两个来源不同且可追溯的数据集；说明合并带来的新分析能力。
- 通过可运行 Python 代码完成读取、清洗、汇总、合并、缺失值核查、行数追踪。
- 给出 **3 个 Research Questions**：每题包括问题、合并表中实际字段、何种比较/关系构成回答，以及若未发现关系时的解释。
- 生成 **至少 3 张**带标题、坐标轴标签和真实数据解释的图。
- 完成 **3 条 Decision Log**，每条含 Decision / Alternative / Evidence / Consequence，至少 **1 条**通过运行替代方案展示差异。
- 提交 **marimo `.py` Notebook + 其 HTML export**；HTML 能正确显示分析结果。

### 非目标（M1 不做）

- 不进行 p-value、显著性检验、回归系数推断或机器学习训练。
- 不做小时级实时天气、精确线路地理匹配或复杂可视化 Dashboard。
- 不为了 GitHub 美观牺牲课程交付与可复现性。

## 1. 研究设计（冻结的初版）

| 维度 | 需求 |
|---|---|
| 研究区域 | NYC Citi Bike（避免混入 `JC-` Jersey City 文件） |
| 研究期间 | **目标** 2024-01-01 至 2024-12-31；先跑 2024 年 1–3 月验证 |
| 观测单位 | 每行 = 一个日期（daily） |
| Bike 来源 | Citi Bike Trip Histories: <https://citibikenyc.com/system-data> |
| Weather 来源 | NOAA NCEI Daily Summaries，Central Park，station `USW00094728` |
| NOAA 下载参数 | `PRCP`,`TMAX`,`TMIN`，metric；样例链接见 README |
| Join key | 从 `started_at` 提取的纽约本地骑行开始日期 ↔ NOAA `DATE` |
| 主要结果变量 | `daily_rides`；保留 `member_rides`、`casual_rides` 供描述/扩展 |
| 天气变量 | `prcp_mm`, `tmax_c`, `tmin_c`, `avg_temp_c=(tmax_c+tmin_c)/2`（仅代理日均温） |
| 日期变量 | `date`, `is_weekend`, `month` |

### 三个研究问题

1. **RQ1 — How is daily precipitation associated with Citi Bike ridership?**  
   字段：`prcp_mm`, `daily_rides`。回答方式：无雨/小雨/较大降雨的分布或降水量与骑行次数趋势；若无关联，应看到分布高度重叠或无稳定方向。阈值需在 Notebook 定义并说明。
2. **RQ2 — Is the relationship between temperature and daily ridership nonlinear?**  
   字段：`avg_temp_c`, `daily_rides`。回答方式：散点及描述性趋势是否体现弯曲/峰值；若无非线性模式，可表现为近似线性或无清晰变化。
3. **RQ3 — Does the precipitation–ridership relationship differ between weekdays and weekends?**  
   字段：`prcp_mm`, `daily_rides`, `is_weekend`。回答方式：分组散点/趋势或雨天与非雨天的描述性比较；若无差别，两组的模式相近。

> **解释边界**：仅做相关/描述性观察，不声称天气造成需求变化。单一 Central Park 站点并不等于全市每个起点的真实天气；系统规模、节假日、季节均可能混杂。

## 2. 已有项目基础与真实状态

当前 Starter ZIP：`SI618_CitiBike_M1_starter.zip`，包含：

```text
nyc-citibike-weather-analysis/
├── src/pipeline.py
├── notebooks/SI618_M1_CitiBike.py
├── data/raw/citibike/
├── data/raw/weather/
├── data/processed/
├── reports/
├── README.md
├── requirements.txt
└── .gitignore
```

**已完成**：Pipeline 和 marimo Notebook 骨架已编写，并通过小型**模拟数据**测试。  
**未完成**：在当前工作环境中尚未成功下载、检查并分析真实的 Citi Bike / NOAA 数据，因此**不得**写入虚构的行数、匹配率或发现。  
**已知问题**：现有 Notebook 中 `Data manipulation` 先于 `Data description`，必须改成课程要求的顺序；跨 CSV/chunk 的 `ride_id` 重复检查尚未实现；HTML 数据路径与依赖需要验证。

---

# Session 1 — 数据获取与可行性验证（Data Feasibility）

**目标**：证明两套真实数据可正常读取，具备足够日期覆盖，且存在可解释的 join key；为后续工作准备可靠的文件与审计结果。

### 输入

- Starter Repo 中 `src/pipeline.py` 与依赖文件。
- Citi Bike 2024 年 1、2、3 月的官方 ZIP；ZIP 可能包含多个 CSV，**必须读取全部**。
- NOAA 2024 年 Central Park 日观测 CSV（尽量下载全年，便于后续扩展）。

### 工作任务

- [ ] 创建环境，执行 `python -m pip install -r requirements.txt`。
- [ ] 检查官方链接是否可用；按月下载 Bike，下载 NOAA CSV；记录实际访问/下载日期。
- [ ] 读取 Bike 文件列表与字段名，识别 ZIP 中多 CSV 情况。
- [ ] 核查 `ride_id`,`started_at`,`ended_at`,`member_casual` 是否存在；检查 timestamps 的解释及本地日期归属。
- [ ] 核查 NOAA `DATE`,`PRCP`,`TMAX`,`TMIN`、单位、缺失标记/质量标记、重复日期。
- [ ] 统计每月文件/CSV 数量、原始行数、有效时间比例、日期范围与缺失情况。
- [ ] 先运行 `python src/pipeline.py --months 1 2 3 --download`（若数据已下载，可去掉 `--download`）；保存日志。
- [ ] 核实读入、日级汇总、天气 Merge 都可运行；排查空值和异常大/小骑行天数。

### 交付物

- `data/raw/citibike/` 中测试月份的原始文件、`data/raw/weather/noaa_2024.csv`（原始大文件本地保留即可）。
- 可复现的下载和来源记录（`README.md` 或独立 source notes）。
- 初版 `data/processed/daily_bike_weather_2024.csv`、`trip_cleaning_audit.csv`、`merge_audit.csv`。
- 一份简短 Feasibility Notes，记录字段、日期覆盖、实际错误和待修复问题。

### 验收标准 / Gate 1

- [ ] 两个数据源都由**真实文件**加载，且 Notebook/脚本不需要私人 API key。
- [ ] 每个 Bike ZIP 中的全部 CSV 均被处理（未遗漏）。
- [ ] 可以精确说明三个数据粒度：trip、weather-station-day、merged-day。
- [ ] 有实际的 matched / unmatched 日期数量，不能只写“merge successful”。
- [ ] 如果只跑 1–3 月，报告不得提前声称得到全年结论。

**阻塞处理**：若全年数据过大，保留 1–3 月验证结果，优先修复流程；但 RQ2 温度非线性及季节变化的完整回答仍以全年为目标。

---

# Session 2 — 数据清洗、合并与 EDA（Data Engineering + Visualisation）

**目标**：完成最终 tidy table、透明的清洗审计、3 张与 RQ 对应的真实图表，并尽可能扩展到全年。

### 输入

- Session 1 验收通过的真实源文件和审计结果。
- 研究问题的最终字段定义。

### 工作任务

- [ ] 按月/分块读取大文件，保留全部月度 CSV；扩展至 2024 全年（资源允许情况下）。
- [ ] 解析时间，过滤无法解析时间、`ended_at <= started_at` 等无效记录；明确计数规则。
- [ ] 加入或明确限制**跨 chunk/跨 CSV `ride_id` 去重审计**；避免仅 chunk 内去重却误称全局去重。
- [ ] 按 `started_at` 的日历日期汇总 `daily_rides`,`member_rides`,`casual_rides`。
- [ ] 清洗天气日期与数值字段，确认 `PRCP` 毫米、气温摄氏度；区分 0 降水与缺失降水。
- [ ] 构建日历日期索引，区分“无骑行观测”和“确实 0 次骑行”，不得无依据填 0。
- [ ] 用 `date` 进行一对一验证的 merge；保留匹配标志和 matched/unmatched 数量。
- [ ] 自动输出原始数据、天气数据和最终数据的 rows、columns、row grain、字段类型、单位、missingness。
- [ ] 制作三张图并写实际观察：①降雨类别 vs 日骑行量；②温度 vs 日骑行量；③降雨与需求，按 weekend 分组。
- [ ] 检查可视化样本过滤逻辑：缺失 `daily_rides` 或相应天气变量的日期应清楚说明是否排除。

### 交付物

- 更新后的 `src/pipeline.py`。
- 经验证的 `data/processed/daily_bike_weather_2024.csv` 与 audit 文件。
- Notebook 中的数据描述表与至少 3 张**来自真实数据**的图。
- 每张图 1–2 句客观解释（不是模板占位句）。

### 验收标准 / Gate 2

- [ ] 每行唯一表示一个 date；没有意外的一对多 join。
- [ ] 清洗前后总行数与每步损失数量可以从代码运行结果追踪。
- [ ] 实际观察期有记录且未匹配日期原因可解释。
- [ ] 三个 RQ 依赖字段均出现在最终 merged dataset。
- [ ] 三张图有标题、带单位的轴标签及解读，图表与 RQ 一一对应。
- [ ] 不执行统计显著性检验或模型训练。

---

# Session 3 — 写作、决策证据、Marimo 与提交（M1 Delivery）

**目标**：将真实结果组织成老师要求的 marimo notebook，完成 Decision Log，验证 HTML，准备 Canvas 提交与后续 GitHub 复用。

### 必须遵守的 Notebook 章节顺序

1. `Title and group`
2. `Overview`
3. `Research questions`
4. `Data sources`
5. `Data description`
6. `Data manipulation`
7. `Data visualisation`
8. `Decision log`

> **修复要求**：当前 Starter 的 `Data description` / `Data manipulation` 顺序与课程不一致，必须调整。

### 工作任务

- [ ] 填写所有小组成员姓名和 uniqname；概述合并数据带来的额外研究价值。
- [ ] 三个 Research Questions 每题提供字段名、观察标准和“若没有关系会怎样”。
- [ ] 每个数据集注明发布者、URL、实际下载日期、许可/使用条款；解释合并列为何合理。
- [ ] 数据描述表**通过 Notebook 代码生成**，涵盖 merge 前和 merge 后行列数、粒度、变量类型/单位/缺失率。
- [ ] Data manipulation 中对每步清洗、汇总、merge 增加简短 Markdown；展示存活/损失行数。
- [ ] 完成三张图的实际解读，不引入因果结论。
- [ ] 编写 **3 条 Decision Log**，每条四段：Decision / Alternative / Evidence / Consequence。
- [ ] 选择至少一条决策，**真正运行 alternative**，计算并呈现与正式方案的数字/表格/图形差异。
- [ ] 不要使用没有数据影响的“装饰性决策”；优先使用真实发生的清洗、缺失值、join、去重选择。
- [ ] 按课程指定命名规则，以**真实 group name** 生成 `SI618_M1_<group name>.py`。
- [ ] HTML 导出，检查页面而非只检查命令退出码；确认图表、表格、动态数值不是错误堆栈或空白。
- [ ] GitHub README 标明数据获取方法、复现方法、使用条款与已知限制；大数据不强制上传仓库。

### 导出命令（文件名替换为实际小组名）

```bash
uvx marimo export html --sandbox SI618_M1_<group name>.py -o SI618_M1_<group name>.html
```

如果文件位于 `notebooks/`，可传入对应相对路径，但最终提交文件名须与老师要求一致。需要确保 HTML 导出时能访问数据和依赖。

### 交付物

- `SI618_M1_<group name>.py`：完整 marimo Notebook。
- `SI618_M1_<group name>.html`：可正常打开、完整展示实际结果的导出文件。
- 完整的 README、处理脚本及审计文件（供团队/GitHub 长期维护；课程必交只有以上两个文件）。

### 验收标准 / Gate 3

- [ ] 按老师规定的章节顺序组织并可运行。
- [ ] 数据源、类型、单位、缺失值、匹配数都由**真实数据**支持。
- [ ] 至少 3 个 RQ、至少 3 张图、3 条完整 Decision Log。
- [ ] 至少 1 条 Decision Log 的 consequence 有**实际替代方案运行证据**。
- [ ] HTML 文件人工打开检查通过，且没有缺数据引起的级联错误。
- [ ] Canvas 上按小组只提交 `.py` 和 `.html` 两个文件。

---

## 3. 评分映射与优先级

| 章节 | 分数 | 本项目验收重点 |
|---|---:|---|
| Overview | 10 | 阐明 Bike + Weather 合并的意义 |
| Research questions | 10 | 3 个 RQ、字段名、可观察回答与无效应情形 |
| Data sources | 20 | 发布者、URL、下载日期、条款与日期匹配依据 |
| Data description | 40 | 原始与合并数据的行列数、粒度、类型、单位和缺失率，由代码计算 |
| Data manipulation | 50 | 可运行处理流程，明确各步骤行数变化、matched/unmatched |
| Data visualisation | 50 | 3+ 标签完整、解释清晰、对应 RQ 的真实图 |
| Decision log | 20 | 三条完整记录，至少一条替代方案实测 |
| **Total** | **200** | 优先保障 140 分的数据描述、处理与可视化 |

## 4. 风险登记与处理原则

| 风险 | 影响 | 处理原则 |
|---|---|---|
| Citi Bike 年度大文件下载/内存压力 | 处理耗时、内存溢出 | 按月 ZIP、CSV chunk 读取，尽早汇总到日粒度 |
| 数据日期覆盖不足 | 会影响 RQ2 和全年结论 | 明确实际时间覆盖；优先扩展至完整 2024 年 |
| `ride_id` 重复 | `daily_rides` 可能重复计数 | 补充跨 chunk/文件审计，报告清洗口径 |
| 气象站有缺测 | Rain/temperature 图样本偏移 | 展示 unmatched 与 missingness，不把 NA 填成 0 |
| NOAA 数据质量标记/单位 | 不可信天气数值 | 核对官方字段、单位及质量标记 |
| 气象与系统运营因素混杂 | 易把相关误读为因果 | 限制到描述性关系，注明季节与系统规模因素 |
| HTML 读取外部路径失败 | 导出看似成功但空白/报错 | 使用稳定路径，人工检查最终 HTML |
| 复用课程数据与条款 | 来源披露不完整 | README 与 Notebook 明确发布者、条款和数据下载日期 |

## 5. Session 交接模板

每个 Session 结束时，填写下面的内容，供下一个 Session 延续：

```markdown
### Session [1/2/3] Handoff
- 完成事项：
- 生成/修改文件：
- 实际数据行数与日期范围：
- 发现的数据质量问题：
- 尚未解决的阻塞：
- 下一 Session 的首要任务：
- 证据文件/截图/日志位置：
```

## 6. 官方依据及工作文件

- SI618 [Milestone 1](https://github.com/cteplovs/si618-fa2026-student/blob/main/project/milestone-1.md)
- SI618 [Decision Log](https://github.com/cteplovs/si618-fa2026-student/blob/main/project/decision-log.md)
- [Citi Bike System Data](https://citibikenyc.com/system-data)
- [NOAA NCEI Daily Summaries](https://www.ncei.noaa.gov/access/services/data/v1)
- 当前项目 Starter：`SI618_CitiBike_M1_starter.zip`（不是完整验证过的 M1 作业）

> **事实状态声明**：此文档是基于已读课程要求、既定研究设计和 Starter 代码状态整理的实施需求。所有真实数据统计、图表结果、matched/unmatched 计数与实验性决策证据，必须在执行三个 Session 后以真实输出填写，不得预设。
