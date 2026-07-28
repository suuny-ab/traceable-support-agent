# 实施计划

> 状态：`closed_not_planned`（随 Issue #28 于 2026-07-28 关闭归档）

## 已完成：设计研究

1. 建立 Issue #28 的唯一活动工作，固定用户结果、最便宜证伪、复用、投入和外部风险边界。
2. 把本轮对话中已经确认的主页、Moonshot 首屏参考、`Evidence Lens` 和文案方向写入
   `spec.md` 的前端设计合同。
3. 研究 7 个公开参考网站，分别记录首屏叙事、真实过程展示、结果层级、动效、移动端处理、
   可借鉴机制和不采用内容。
4. 根据研究结果把主页结构稿从 v0 更新为 v1；结构稿不冻结具体配色、字体或材质。
5. 形成首页文案初稿，明确保留、重写与删除的现有内容。
6. 复核设计简报、参考矩阵、结构稿和文案是否一致；运行公开仓库扫描与文档状态检查。
7. 把参考矩阵与研究结果写入 `result.md`，停在用户设计检查点，不开始高保真页面、
   Provider 或部署。

用户已经确认主页结构 v1 与产品命题；首屏具体文字层级在原型阶段继续调整。

## 已完成：最小动效原型迭代

1. 冻结只验证叙事、运动、响应式和降级的原型合同。
2. 在 `web/prototypes/evidence-lens/` 实现独立 Canvas 2D 原型，不进入生产路由、不增加依赖。
3. 验证桌面、手机、`prefers-reduced-motion`、强制失败降级、离屏暂停和控制台状态。
4. v1 因解释文字过多、主视觉不足而被用户否决。
5. v2 只保留静态短品牌、一句短定位和简化流程，因视觉及产品解释过度简化而被用户否决。
6. v3 复现参考站的滚动品牌字带、圆形压缩折射和月牙高光；恢复原定位句，把第二屏改成
   一个具体 run 的五阶段来路、来源绑定、候选回复和检查结果。
7. 用户判断 v3 仍存在方向、动态和布局差距，明确未通过。

## 已完成：首屏参考对齐

1. 只读测量 Moonshot 当前桌面 `1280 × 720` 与手机 `390 × 844` 首屏。
2. 用双帧像素位移确认品牌字带向右约 `86px/s`，不再凭视觉印象判断方向。
3. 固定画布、透镜、定位句、入口和手机裁切的目标位置与容差。
4. 在 `alignment.html` 中并排呈现参考观测与 Traceable 目标帧。
5. 用户确认需要继续提高透镜与文字运动的参考一致性，并同意用 K3 视频能力处理动态视觉。

## 后续阶段

1. 用户确认原型叙事与运动方向后，完成首页高保真设计，再设计工作台真实状态与结果层级。
2. 实现固定示例公共合同、持久化 trace、恢复与预算 / 队列 / 健康门。
3. 先运行 Fast、Web Product 与离线 live 验证；涉及公共合同、费用、持久化和生产的候选
   按独立复核门处理。
4. 只有冻结 Provider / model / prompt / schema / 示例 / 预算 / 停止条件并获得授权后，
   才执行两个 candidate 示例的有界真实验证。
5. 推送、Draft PR、正式复核、合并、自动部署后的生产验证和用户验收分别形成证据。

---

## 本轮计划：live 主路径工作台（2026-07-24 · Worker Kimi K3）

1. 后端边界：在 `product/boundaries.py` 增加 `unsupported_claim` 确定性规则（2.4GHz /
   5GHz / 频段 / 双频等无线网络频段能力不在批准来源内）；在 `api/projection.py`
   `blocked_result` 增加对应文案分支（证据不足转人工、0 调用、不猜测）。
2. 后端装配：`api/http.py main()` 增加 env 门控 live 装配——`TRACEABLE_PUBLIC_LIVE_ENABLED`
   为真且依赖（合成语料、嵌入模型文件）与凭据占位（仅检查环境变量存在性，不读取值）
   齐备时注入 `DefaultProductRunner(default_qa_transport, MODE_AUTHORIZED_REAL)`；
   否则保持 `product_runner=None`，健康状态继续 `replay_only`。生产配置不改。
3. 本地验收工具：`tools/local_live_workbench.py`（dev-only，不进产品路径）以检索派生的
   `OfflineInjectedTransport` 装配同一 `PublicRunService`，供本地浏览器端到端验收。
4. 前端数据层：`web/app/lib/demo-data.ts` 增加三个默认 live 案例 + 边界挑战案例 +
   推荐问法；`replay-presets.json` 更新 IE-001 note 并继续只承担显式回放。
5. 前端路由：`replay-routing.mjs` 改为 live 优先——案例 / 自由输入只走 live 或 blocked，
   回放仅由显式按钮触发。
6. 前端工作台：重构 `DemoWorkbench.tsx` 信息层级（运行身份 → 案例卡 → 自由探索 →
   回放入口），结果视图补充 Provider 调用次数与 `handoff_reason` 的诚实展示；
   `app/page.tsx` 简介改为 live 主路径表述，状态由检测决定而非写死。
7. 测试：更新 / 新增 web 测试（路由、预设、渲染 HTML）与 api 测试（边界、投影、装配）；
   运行 web `npm test`、api Fast 子集、公开仓库扫描。
8. 文档：更新活动工作 `result.md`、`docs/status.md`；隐私边界无变化，仅在结果中记录评估。
9. 本地端到端验收与截图自验后提交边界清楚的 checkpoint commit，输出交接回执。

以上 1–9 全部执行完成：后端边界、装配、本地工具、前端数据 / 路由 / 工作台、测试、
文档、本地端到端验收与截图自验均已落地；细节与证据见 `result.md` 本轮结果段。
