# GUI-Pilot

GUI-Pilot 是一个面向移动端 GUI 自动操作任务的多模态 Agent。它不是纯 Prompt Demo，也不是按本地样例名称查表返回答案，而是一个 **高置信工作流先验 + 通用 VLM fallback + 窄后处理保护** 的混合式 GUI Agent。

项目来自“捧月初赛-智能代理”类任务：输入用户指令和当前手机截图，Agent 每一步输出一个合法动作：

- `OPEN(app_name)`
- `CLICK(point=[x, y])`
- `TYPE(text)`
- `SCROLL(start_point, end_point)`
- `COMPLETE()`

坐标是归一化到 `[0, 1000]` 的屏幕坐标。

## 核心设计目标

GUI 任务的难点不是单纯“看懂截图”，而是长链路中每一步都不能错。一次错误点击、一次过早 `TYPE`、一次多余 `CLICK` 都会导致整条任务失败。因此本项目的设计目标是：

1. **稳定路径确定化**：对搜索、播放、评论、外卖、地图、航班等高频移动端任务家族，用窄触发的状态机降低 VLM 抖动。
2. **未知场景仍交给 VLM**：没有命中高置信条件时，让视觉语言模型根据当前截图决策，避免把规则写死成样例答案。
3. **末步风险保护**：对“已输入文本后是否完成/是否还要发送”这类高风险状态做专门保护。
4. **控制提交风险**：依赖只保留 `openai` 和 `pillow`，不引入重型 OCR、本地 CV 模型或复杂 Agent 框架。

## Agent 架构

当前提交的核心代码在 [`submission/src/agent.py`](submission/src/agent.py)。

运行时决策顺序如下：

```text
用户指令 + 当前截图 + 历史动作
        │
        ▼
第 1 步：从指令抽取目标 App，直接 OPEN
        │
        ▼
文本后保护：刚 TYPE 后是否应该 COMPLETE 或点击发送/提交
        │
        ▼
提交后保护：刚点击发送/提交后是否可以 COMPLETE
        │
        ▼
高置信工作流先验：命中任务家族则走确定性动作表
        │
        ▼
通用 VLM fallback：观察当前截图，输出下一步动作
        │
        ▼
解析、校验、轻量后处理
```

### 1. 第一步直接 OPEN

如果用户指令中能识别目标应用，例如“爱奇艺”“美团”“百度地图”，Agent 第一步直接输出：

```text
OPEN(app_name="爱奇艺")
```

这一步不需要截图，也不调用 VLM，所以线上日志里会看到 `input: 0, output: 0`。这是正常现象，不是没有使用模型；只是这个动作本身可以确定。

### 2. 高置信工作流先验

部分移动端任务有稳定的交互骨架，例如：

- 视频类：打开 App -> 搜索 -> 点结果 -> 播放/收藏/评论
- 地图类：进入打车/语音包 -> 输入地点或关键词 -> 选择候选
- 外卖类：搜索店铺 -> 进店 -> 搜索商品 -> 加购/结算前完成
- 航班类：选择出发地/目的地/日期 -> 搜索 -> 查看列表
- 电商评价类：进入评价入口 -> 选择评分/文本框 -> 输入评价 -> 完成或提交

代码里为这些 **任务家族** 写了窄触发的工作流表。触发条件来自用户指令中的 App 名和自然语言意图，例如“爱奇艺 + 评论区 + 评论/发布”，而不是来自本地 case 名称，也不会读取本地测试数据或参考答案。

这样做的原因很现实：VLM 在长链路 GUI 上会有抖动。同一个截图，有时点搜索框，有时点历史记录，有时点结果卡片正文。对已经被验证稳定的通用交互骨架，用确定性动作可以显著降低随机失败。

### 3. 通用 VLM fallback

没有命中工作流时，Agent 调用 VLM。Prompt 不是只问“下一步点哪里”，而是先组织任务理解：

- 用户原始指令
- 任务类型：搜索、评论/留言、评价填写、内容播放、交易/出行表单等
- 目标 App
- 是否明确要求发布/提交
- 最近是否已经输入文本
- 是否有“第一个”“默认地址”“最便宜”等选择偏好
- 最近动作历史和失败反馈

历史上下文只用文本压缩，不重复发送历史截图。这样能保留“已经做过什么”，同时减少 token 和视觉干扰。当前截图会做轻量 JPEG 编码，并用 Pillow 做轻微对比度/锐度增强，帮助模型识别小按钮和输入框边界。

### 4. 文本后保护和提交保护

很多 GUI 任务失败发生在文本输入之后：

- 用户只要求“写评价”，输入完成后应该 `COMPLETE`，但模型又去点“提交”或乱滚动。
- 用户明确要求“发布评论”，输入完成后不能 `COMPLETE`，必须找发送按钮。
- 某些评价页需要先点评分，再点文本框，输入后还要点一个隐式发布按钮。

因此代码里有专门保护：

- 如果刚 `TYPE` 了评论/评价文本，且用户没有要求发布/发送/提交，优先 `COMPLETE`。
- 如果用户明确要求发布/发送/提交，而 VLM 想 `SCROLL` 或 `COMPLETE`，后处理会改成点击常见提交区域。
- 对“评分/星级 -> 文本框 -> TYPE”这类页面，使用一个很小的 VLM 分类器，只判断提交按钮的大致区域：`TOP_RIGHT`、`BOTTOM_RIGHT`、`BOTTOM_CENTER`、`NONE`。它不自由生成坐标，避免过拟合和乱点。

这部分是分数稳定性的关键：规则足够窄，只修高置信错误，避免影响已经稳定的 `TYPE -> COMPLETE` 场景。

### 5. 输出解析和容错

线上模型输出不一定总是严格 JSON。Agent 支持解析多种格式：

- 标准 `Thought / Action / Parameters`
- `CLICK:[[x, y]]`
- `TYPE:["文本"]`
- `click(point=[x,y])`
- `open(app_name="...")`

解析后还会做动作校验：

- 点击坐标 clamp 到 `[0,1000]`
- 空 `TYPE` 转为 `COMPLETE`
- 缺失滚动参数时给默认安全滚动
- 连续重复同一动作时做轻量恢复，避免卡死

## 为什么不是重型 ReAct / 多轮 Critic

项目迭代中尝试过更重的链路：多候选、critic、自检、前后图 assessment、reflection 等。它们本地有时有效，但线上分数并不稳定，主要问题是：

- 每步多轮调用增加延迟和失败面。
- 自评错误会污染后续上下文。
- critic 可能把本来正确的一步改错。
- GUI 评分是严格逐步检查，链路越重，自由度越高，越容易在某一步偏离。

当前版本保留的思路是更保守的：**确定性工作流负责稳定拿分，VLM 负责未知泛化，后处理只修已知高置信风险点。**

## `submit_log/` 是什么，为什么保留

[`submit_log/`](submit_log/) 不是运行依赖，Agent 不会读取这个目录。它是研发过程中的 **线上日志证据和回归约束**。

保留它有三个原因：

1. **解释设计来源**：很多规则不是拍脑袋写的，而是从线上日志中归纳出来的失败模式。
2. **防止回归**：例如京东/拼多多评价任务中，好的版本是 `TYPE -> COMPLETE`；如果后续改成输入后继续乱点，就会掉分。
3. **记录 case-family**：日志帮助把隐藏题目归纳成任务家族，比如视频搜索播放、地图打车、外卖购买、航班查询、电商评价。

当前只保留少量代表日志：

- `v7c_log.md`
- `v9_log.md`
- `v12a_log.md`
- `visible_case_regression.md`

这些文件不参与提交包，也不参与线上运行。如果只想保留最小源码仓库，可以删除 `submit_log/`；如果要继续迭代冲分，建议保留它，因为它是分析线上退化和制定回归边界的依据。

## 目录结构

```text
.
├── submission/              # 最终提交目录：doc/ 和 src/
│   ├── doc/
│   └── src/
│       ├── agent.py         # 当前 Agent 实现
│       ├── agent_base.py    # 官方基类
│       └── requirements.txt # 提交依赖
├── code-for-student/        # 官方参考代码和本地 runner
├── tools/                   # 提交包检查脚本
├── submit_log/              # 代表性线上日志和回归记录，不参与运行
├── submit_version/          # 本地提交包记录；zip 文件被 gitignore
├── task.md                  # 赛题说明
└── SUBMISSION_SOP.md        # 每次提交前的检查流程
```

## 不纳入 Git 的内容

这些内容只用于本地调试或包含私密信息，不上传：

- `.env`
- `code-for-student/test_data/`
- `code-for-student/output*/`
- `submit_version/*.zip`
- 本地 IDE/Agent 配置

## 运行环境

比赛提交目标为 Python 3.10.12。当前提交包依赖：

```text
openai
pillow
```

本地开发环境使用 `moon_zx` conda 环境。

复制环境变量模板：

```bash
cp .env.example .env
```

默认模型常量：

```python
DEFAULT_API_URL = "https://ark.cn-beijing.volces.com/api/v3"
DEFAULT_MODEL_ID = "doubao-seed-1-6-vision-250815"
```

## 本地验证

先打包，再检查提交结构：

```bash
conda activate moon_zx
cd submission
zip -qr ../submit_version/submission_local.zip doc src
cd ..
python tools/check_submission.py --submission-dir submission --zip submit_version/submission_local.zip
```

如果本地有官方测试数据：

```bash
conda activate moon_zx
cd code-for-student
python test_runner.py --data_dir ./test_data/offline --output_dir ./output_local --no_debug_test
```

`output*` 是生成物，不要提交。

## 提交包规范

最终提交 zip 只应包含：

```text
doc/
src/
```

每次打包前按 [`SUBMISSION_SOP.md`](SUBMISSION_SOP.md) 做自查。当前源码基准是 [`submission/src/agent.py`](submission/src/agent.py)。
