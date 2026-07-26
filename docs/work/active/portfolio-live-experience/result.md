# 结果记录

> 状态：`developing`

## 当前阶段

Issue #28 已启动。用户已确认主页结构 v1 和产品命题，但 v1–v3 均未达到首屏预期。
Moonshot 首屏的可测量参考对齐已经形成；用户进一步确认动态网页应由具备视频视觉能力的
Worker 主导，而不默认由个人 Work 前台验收。当前开发协作按项目工程规则执行。

生产继续保持 `replay_only`，未启用产品 Provider，未读取产品凭据，未修改生产开关或部署
状态。Kimi Code CLI 的公开参考视觉分析来自当前会话中的 Git 外明确授权，不构成产品
Provider 授权，也不由本文件延续授权。

## 已形成

- `spec.md`：设计简报、主页结构稿、首页文案、工作台文案方向和手机顺序已经收敛为 v1；
- 本文件：完成 Moonshot、Linear、Vercel、Resend、Langfuse、Braintrust、Sentry 的
  桌面 / 手机对照；
- `Evidence Lens` 已形成独立 Canvas 2D 原型与静态 / 失败降级，不进入生产路由。

本轮 K3 已完成一次只读视觉分析：读取 5 秒、50 帧的公开参考录屏和用户截图，进一步裁切
字带、透镜内部与月牙光环；约 13 分钟后输出结构化诊断，未修改仓库。该过程确认了向右约
`86px/s`、圆外吸引形变、圆内非均匀压缩、外部扫描线 / RGB 色散和移动亮弧等关键机制，
并逐项解释 v3 的方向、形变、扫描线、月牙与手机缩放差距。这证明 K3 能承担本候选所需的
动态视觉分析。

## Checkpoint 验证

- 公开仓库扫描：`passed`，worktree 共检查 `196` 个文件；
- 稳定 API Fast 子集：`54 passed`、`20 subtests passed`；
- 工具单测：首次 `30s` 上限超时后按详细模式重跑，`78 tests` 全部通过、`7 skipped`，
  实际耗时 `46.813s`；这证明不是失败，但已超过 Fast 的 `<=10s` 目标；
- `alignment.html`：桌面 `1280 × 720` 为 `scrollWidth 1265 <= 1280`，手机
  `390 × 844` 为 `375 <= 390`；
- v3 原型：桌面和手机均为 `renderState=animated`，Canvas 帧持续增长且无横向溢出；
- `motion=reduce`：两次间隔检查均保持 `frame=2 / renderState=static`；
- `fallback=1`：根节点进入 `fallback`，Canvas `display:none`、HTML 降级
  `display:flex`，手机无横向溢出。

这些检查只证明当前 checkpoint 可恢复、原型和对齐稿能在本机运行，不代表 v3 视觉通过。

## 参考网站对照

| 网站 | 关键观察 | 本项目采用 | 本项目不采用 |
| --- | --- | --- | --- |
| [Moonshot AI](https://www.moonshot.cn/) | 首屏近一整屏留白；全宽 Canvas 以横向文字带、透镜、扫描线和色散分段显现；产品入口延后 | 只把主页第一屏做成沉浸品牌空间；原创 `Evidence Lens`；采用先图形、后定位、再入口的节奏 | 不复制月食、品牌文字、输入框、代码或抽象使命句；不把全站做成大留白 |
| [Linear](https://linear.app/) | 类别定位清楚，真实产品 UI 在首屏下缘出现；手机重新编排内容而不是压缩双栏 | 第二屏尽快展示真实运行轨迹；采用安静、精确的产品语气 | 不采用超长主页、泛化 “AI era” 文案或无关多团队场景 |
| [Vercel](https://vercel.com/) | 大类别名、一个强品牌对象、明确行动；手机改变图形与文字顺序 | 首屏只允许一个主视觉对象；手机允许改变阅读顺序 | 不制造客户 Logo 或宽泛 “Agentic Infrastructure” 定位 |
| [Resend](https://resend.com/) | “Email for developers” 用三个词说明产品，一个 3D 对象承担记忆点 | 用具体类别 / 结果表达替代 AI 形容词；动态对象必须具有产品含义 | 不放与证据产品无关的 3D 装饰或用材质炫技代替运行证明 |
| [Langfuse](https://langfuse.com/) | 高密度编辑部 / 仪表盘网格，很快进入 trace 产品界面；手机移除侧栏 | 工程证据页可用结构化网格；运行轨迹成为最强产品证据 | 不使用无法证明的企业规模数字；主页首屏不复制高密度侧栏 |
| [Braintrust](https://www.braintrust.dev/) | 简短结果承诺，第二段以大面积真实 trace UI 证明产品 | 主页第二屏使用大面积真实运行轨迹；以动作和结果写产品过程 | 不采用通用 AI 规模文案、虚构客户或空泛规模主张 |
| [Sentry](https://sentry.io/) | 文案直接且有人味，产品面板在首屏下缘可见；手机重排并保留主要行动 | 使用“查看一次运行”而非“了解更多”；优先表达结果层级 | 不采用吉祥物、营销开关和与信任气质冲突的高饱和装饰 |

## 跨样本结论

1. 首屏只完成类别 / 结果定位，不同时解释架构、限制、版本、状态和全部功能。
2. 一个有产品含义的对象胜过一组能力卡；本项目使用证据透镜，不使用通用 AI 球体或粒子。
3. 真实产品证据需要在首屏下缘或第二段出现；主页用一个代表性公开合成 run。
4. 主页不承担完整 Demo；三个示例、运行恢复、终态和决定归工作台。
5. 手机端必须重新编排；`Evidence Lens` 降低密度且不能挤占文案。
6. 品牌动效和运行状态分开；工作台阶段只能来自服务端持久化状态。
7. 本项目没有企业客户证明，以公开源码和可验证工程边界替代 Logo 墙与规模统计。

## 对现有网站的直接修正

保留产品目的、来源回查、失败关闭、人工决定、代表性合成 run 和现有真实 / 回放路由。

移动：

- 五阶段轨迹从首页功能卡移到主页 run 预览和工作台；
- Provider / 回放状态从全站导航移到工作台运行身份；
- API、预算、留存、评测与版本事实移到工程证据或边界页；
- 三个固定示例全部由工作台负责，主页只预览一个。

从首页删除：

- `公开 Beta` 眉题；
- 三张同权结果卡；
- `Replay only`、API 数量、产品路径等统计卡；
- 重复 CTA；
- `Product workbench`、`Input contract` 等不承担必要语义的英文微标签；
- `product/0.1.0` 和历史候选治理文字。

## 研究改变了什么

- 主页从“三个示例陈列”收敛为“一个代表性 run 证明定位”；三个示例归工作台；
- 首屏之后尽快出现真实运行轨迹，不再使用静态答案卡或三组同权能力卡；
- 手机端明确采用重新编排，而不是桌面布局压缩；
- 客户 Logo 与规模统计不适用于本项目，改用公开源码与可验证工程边界；
- “让每一条客服回复，都能回到它的依据。”作为产品命题已确认，但不再默认以两行长句占据
  首屏核心位置。

## `Evidence Lens` 最小原型

原型位于：

- `web/prototypes/evidence-lens/index.html`
- `web/prototypes/evidence-lens/prototype.css`
- `web/prototypes/evidence-lens/prototype.js`

v1 使用原生 Canvas 2D 在透镜内显示来源—绑定—回复关系，同时在下方展示两行定位与入口。
用户判断解释文字过多、焦点分散，而且透镜视觉效果没有达到产品首屏要求，因此 v1 明确
未通过。

v2 删除所有透镜内解释文字，改为分散光线穿过玻璃后收敛，并只显示临时短品牌
`TRACEABLE`。透镜下只保留“客服回复，有据可查。”和一个弱入口。深色背景、短品牌、字体、
线条与具体色值均为原型候选，不是最终决定。

用户判断 v2 仍未达到要求：`TRACEABLE` 缺少参考站的动态滚动效果，短定位不如原定位句，
第二屏只有四个标签，无法解释产品。

v3 按参考站的可见机制重写主视觉：

- 超大 `TRACEABLE` 品牌字带持续横向滚动；
- 中央圆形透镜重新绘制字带并进行横向压缩，形成折射感；
- 月牙高光沿圆周缓慢变化，成为唯一视觉焦点；
- 恢复“让每一条客服回复，都能回到它的依据。”；
- 第二屏使用 `CZ-R1 怎么开始局部清扫？` 串起问题进入、批准来源、处理要求、客户回复、
  机械检查、来源绑定和人工确认；
- 可见机制接近参考站，但 Canvas 代码、品牌文字、流程内容与素材均为项目独立实现。

实现边界：

- 不注册 Next.js 路由、不导入现有产品代码、不增加前端依赖；
- 不连接 Provider、公共 API、真实 run 或生产数据；
- 桌面与手机使用同一滚动 / 折射机制，手机缩小字带并放大圆形焦点；
- `prefers-reduced-motion` 固定为静态关键帧；
- Canvas 不可用时保留 HTML 降级图形与完整定位文字；
- `IntersectionObserver` 与页面可见性状态共同控制暂停，像素密度封顶。

## v3 原型浏览器检查

| 场景 | 结果 |
| --- | --- |
| 桌面 `1280 × 720` | Canvas 持续渲染，定位文案可读；`scrollWidth 1265 ≤ innerWidth 1280` |
| 手机 `390 × 844` | 滚动字带、圆形折射、原定位句和入口保持分层；`scrollWidth 375 ≤ innerWidth 390` |
| 第二屏 | 桌面三栏展示问题 / 五阶段 / 候选结果；手机按同一顺序纵向重排 |
| 减少动态 | 强制 `motion=reduce` 后帧计数保持 `2`，只显示静态关键帧 |
| 渲染失败 | 强制 `fallback=1` 后 Canvas 隐藏，HTML 降级可见且无横向溢出 |
| 离屏暂停 | 首屏离开视口后帧计数在 700 ms 检查窗口内不再增长 |
| 控制台 | 最终桌面复核无 warning 或 error |

桌面与手机动画在浏览器截图采样期间持续推进；这只能证明本机原型能够工作，不是正式的
跨设备性能基准。

## 首屏参考对齐

用户判断 v3 的文字方向、动态效果和页面布局仍与预期差距明显，因此 v3 明确未通过。当前
没有继续修改动画，而是新增：

- `web/prototypes/evidence-lens/alignment.html`
- `web/prototypes/evidence-lens/alignment.css`

公开参考站只读测量结果：

| 项目 | 桌面 `1280 × 720` | 手机 `390 × 844` |
| --- | --- | --- |
| 导航 | 高 `72px` | 高 `72px` |
| 动态画布 | `x 0 / y 144.5 / 1276 × 400` | `x -287 / y 72 / 960 × 400` |
| 品牌字带 | 向右约 `86px/s` | 同一方向与节奏 |
| 透镜 | 核心直径约 `216px` | 保持近似物理尺寸 |
| 定位句 | `y 518.3`，单行 | `x 20 / y 452 / w 346 / h 69.3`，两行 |
| 入口面板 | `x 268.3 / y 605 / 739.5 × 139.3` | `x 20 / y 573.3 / 346 × 115.3` |

对齐页包含桌面与手机的参考观测 / Traceable 目标帧、四条已确认差异和九项测量合同。桌面
`1280 × 720` 与手机 `390 × 844` 检查均无横向溢出。它不修改 v3，不代表 v4 已实现。

## 当前证据边界

v1 证明“把产品原理塞进主视觉”不可接受；v2 证明过度简化也无法形成产品理解；v3 虽能
运行，但方向、动态和布局仍未满足用户预期。当前只允许形成首屏参考对齐结论，不能声称 v4、
高保真、工作台行为或生产实时能力已经完成。

## 下一检查点

Worker 候选 `71104ee` 已由 Integrator 集成到 `codex/integrate-live-llm-workbench`；
Provider、推送、合并与部署边界保持不变。下一步：推送集成分支并创建 Draft PR。

---

## 本轮结果：live 主路径工作台候选（2026-07-24 · Worker Kimi K3）

### 已完成

1. **确定性证据不足边界**：`product/boundaries.py` 新增 `unsupported_claim` 规则
   （2.4GHz / 5GHz / 无线频段 / 双频等批准来源未覆盖的能力主张），经 preflight →
   `_insert_blocked_run` 形成新 run、`provider_call_count=0`、不存原文；runner 与
   `run_qa` / `run_ticket` 内层自动获得同一拦截。`projection.blocked_result` 新增对应
   文案。`evals/public-regression-v1.json` 的 `GEN-DEV-IE-001` 已知差距关闭（
   `GEN-DEV-MH-003` 仍未实现，保持登记）。
2. **公网 live 装配点**：`api/live_assembly.py` 在 `TRACEABLE_PUBLIC_LIVE_ENABLED=true`
   时构建 `DefaultProductRunner`；健康门要求嵌入模型清单校验、六份合成语料、检索依赖
   可导入、凭据占位存在（只查存在性，不读值）。任一缺失则 `is_ready=False`，健康状态
   继续 `replay_only`。装配在 `http.py main()` 中惰性导入，回放镜像无 live 依赖（
   `python -S` 导入证明保持）。生产 compose / Dockerfile 未改，`provider_enabled=false`。
3. **live-only 工作台**：`DemoWorkbench.tsx` 重排信息层级为 运行身份（健康检测）→
   三个默认案例 + 一个边界挑战（每次点击创建新 run）→ 受约束自由探索（推荐问法 +
   500 字 + 型号 + QA/工单）→ 已验证回放次要入口（显式点击，绝不自动替代 live）。
   案例数据收敛到 `web/app/lib/live-cases.json`；路由改为 live 或 blocked 两种，
   边界挑战因 preflight 在 live 门前持久化，live 关闭时仍可创建 0 调用 handoff run。
4. **诚实状态**：结果视图新增 Provider 调用行（`N 次 · 零自动重试` /
   `0 次 · 模型调用前停止` / `未知` / `回放不调用模型`）与 `handoff_reason` chip；
   超时 / 断连 / 协议错误 / 503 的诚实 handoff 文案保留；阶段轨迹仍只来自服务端
   状态轮询，无任何”模型思考”动画或 Chain of Thought。
5. **本地验收工具**：`tools/local_live_workbench.py`（dev-only）用检索派生的离线注入
   transport 启动同一 `PublicRunService`，不调 Provider、不读凭据。

### 验证结果

- API 全量：`pytest api/tests` 110 项全部通过（含新 `test_live_assembly.py` 5 项、
  `test_product_boundaries.py` 新增 IE-001 期望与反例、预检新增 unsupported_claim case）；
  首次运行前按项目脚本下载固定 BGE 模型到 gitignored `artifacts/`。
- 工具测试：`pytest tools/tests` 71 passed、7 skipped、117 subtests passed（47.7s）。
- Web：`npm test`（next build + node tests）23 项全部通过；`tsc --noEmit` 与
  `eslint .` 干净。
- 公开仓库扫描：`check_public_repo.py` passed，187 个文件。
- 本地端到端（离线注入 transport，非真实模型）：QA 局部清扫、工单地毯、QA E310
  均形成 candidate、clause 绑定来源正确（`CZ-R1-MANUAL · 清扫模式`、
  `CZ-R2-MANUAL · 扫拖模式`、`FAULT-CODES · E310 CZ-R2 集尘通道`）、
  `provider_call_count=2`；IE-001 handoff、`provider_call_count=0`、
  `handoff_reason=unsupported_claim`；自由输入出范围被预检拦截；人工批准写入服务端。

### 隐私 / 安全评估

自由输入面未扩大：同一 500 字上限、同一敏感正则 + 短语预检、同一出范围词表、同一
浏览器软限 / 队列 / 预算、同一 30 天原文保留与清理。推荐问法只是前端填充，不绕过
任何服务端检查。不构成新的隐私 / 安全边界变化，无需停止升级。

### 证据边界

离线注入 transport 只证明服务端链、合同、投影与工作台行为，不证明真实模型质量；
真实 Provider 仍需独立冻结与授权。生产保持 `replay_only`，本候选未部署、未改变任何
公开主张。

---

## 本轮结果：三 worktree 基线收敛（2026-07-26 · 项目集成会话）

### 收敛动作

1. **无损备份**：收敛前主 worktree 的 8 个未提交修改固化为本地分支
   `backup/portfolio-experience-wip-20260726`（`a683dff`），备份树与当时工作区逐文件一致
   （`git diff` 为空）；恢复方式：`git restore --source=backup/portfolio-experience-wip-20260726 .`。
2. **D1 `487cec9`**：新多 CLI Conversation 协作规则（`AGENTS.md` 与三个 engineering 文档）
   单独提交；与集成提交零文件重叠。
3. **M `edd9044`**：`git merge --no-ff codex/integrate-live-llm-workbench`，零冲突；
   `e3fc2a5` 与 `71104ee` 两个候选 SHA 原样进入基线祖先链，未重写。
4. **结构核验**：`git diff e3fc2a5 edd9044` 只含 D1 的 4 个规则文件；
   `git diff 71104ee edd9044 -- web api` 为空，候选产品代码完整进入基线。
5. **D2（本提交）**：备份中的 Conversation 措辞回填到集成事实底座；`docs/status.md`
   更新为收敛后状态。过时的"待集成"状态未重新进入当前事实。

### 收敛后验证（主 worktree 本机复跑，R0，未调 Provider）

- 公开仓库扫描：`check_public_repo.py --scope worktree` passed，177 个文件；
- API 完整套件（本地固定 BGE 模型，`artifacts/models/fastembed/fast-bge-small-zh-v1.5`）：
  `106 passed, 20 subtests passed`，无失败；Worker 报告为 110 项，本次收集数为 106，
  差 4 项原因 `待确认`（无失败、无跳过，疑为计数口径差异）；
- 工具测试：`71 passed, 7 skipped, 117 subtests passed`（50.2s），与 Worker 报告一致；
  主 worktree 本机有模型，未复现 Integrator 记录的 23 项缺模型失败；
- Web：`npm test`（next build + node tests）23/23 通过；`tsc --noEmit` 与 `eslint .`
  均退出码 0。

### 证据边界

本轮只证明汇合树在本机通过 Fast / Candidate 层检查与结构核验；不构成候选成熟度、
发布或部署主张。Worker 的本地端到端记录（离线注入 transport）未在本轮复跑，保持
`待验证`。推送、Draft PR、正式复核、合并与部署仍需用户逐项授权。

### 两个旧 worktree 的退出条件

- `traceable-support-agent-live-workbench`（`71104ee`）：产品代码 diff 为空且验证全绿，
  **退出条件已满足**，分支保留为历史引用；
- `traceable-support-agent-live-integration`（`e3fc2a5`）：已原样并入基线历史且验证全绿，
  **退出条件已满足**。物理移除 worktree / 删除分支是独立的破坏性动作，需单独授权。
