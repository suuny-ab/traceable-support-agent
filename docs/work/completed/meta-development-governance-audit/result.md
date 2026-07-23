# 结果记录

> 状态：`completed`
>
> 完成日期：`2026-07-23`

## 产品与治理结果

- Issue #7 是唯一活动入口；#5、#6 作为子问题统一裁决，没有建立并行活动增量。
- 抽样 PR #4、#8/#9、#10/#11 的周期、CI attempt、复核轮次、候选失效、有效 findings、
  平台噪声和逃逸缺陷已规范化到 `docs/meta/governance-audit-2026-07.md`。
- GitHub 已建立最小 Issue 表单、PR 模板、标签和 #12–#15 路线 Issue；未来任务、候选
  diff、Checks 与外部回执归 GitHub，活动事实和长期决定归仓库。
- 正式复核门缩减到元规则、S2/S3、生产 / 发布、安全、隐私、认证、费用、持久化、公共
  合同和公开主张；普通 R0/R1 UI 与缺陷修复不再强制独立复核。
- CI 影响分类对空集合、未知路径、异常 Git 路径、工作流、工具、Web、API、部署和公共
  事实全部失败关闭到 `runtime`。四个 required job 始终出现。
- `release-decision` 绑定 schema、SHA、run ID / attempt、分类、部署布尔值和路径哈希。
  手动恢复只允许可信同仓 `ci-release` main push；缺少 decision 的兼容固定到旧成功 run
  `29999870811`，且在进入 production 前核验唯一未过期 manifest。
- 四页与共享导航完成明亮商业 SaaS 重设计；真实 GitHub 链接、移动导航、键盘焦点、
  44px 触控目标、减少动态效果和 AA 文本配色已落地，公共 API 和产品边界未改变。

## 候选、复核与 GitHub Checks

- Draft PR #16 的首个冻结候选为 `c61c5a67b0b7afd04e6d3d26a4874d6fb5246ce5`；
  run `30005142238` 的 `governance`、`web`、`api`、`containers` 全部成功。
- 一次完整只读复核发现两个 P2：异常 Git 路径可误归治理类、手动 legacy 恢复身份过宽。
- 修复候选 `bd3f9e6323e8d790a56d2453e0dc53ca917034a9` 的 run `30006093699`
  全绿；第一次针对性复核关闭路径 finding，并发现 legacy finding 的直接残余：只校验
  workflow 显示名、未固定 workflow path。
- 最终候选 `8bd15ffca60cbbed6bc44e8d249dd0affb8209ae` 固定
  `.github/workflows/ci-release.yml`；run `30006413918` 全绿，第二次针对性复核关闭
  原 findings，未发现新的 P0–P3。
- 实施期间正式复核为零；绿色 Draft PR 后只发生一次完整复核。后续两次均由 finding
  触发且只覆盖 finding 与覆盖 diff，没有重复全量复核。

## 发布、生产与用户验收

- PR #16 squash merge 为 `4b9a31feee6fb929631ba5b0b5db97b10a895c52`。
- 主线 run `30006589718` 的四项检查、两个 GHCR 镜像发布和不可变 manifest 全部成功。
- 自动生产 run `30006746612` 无人工批准、无自动重试；preflight 与 deploy 成功，来源
  run ID、SHA 和 attempt 绑定正确。
- 公网 `/`、`/design`、`/app`、`/privacy`、`/api/v1/health` 均为 `200`；健康合同为
  `status=ok`、`live_experience=replay_only`。
- 生产浏览器验证通过移动导航、无横向溢出、最小 44px 控件、回放四段轨迹、来源、机械
  门和人工编辑决定；浏览器错误 / 警告日志为空。
- 用户于 `2026-07-23` 实际体验并明确验收通过。Provider 全程保持关闭，没有调用、费用
  或外部业务动作。

## 结论与限制

本次真实产品增量证明：把正式复核推迟到绿色冻结候选、只对 finding 做针对性复核、用
GitHub 管候选与回执，以及对治理类路径跳过运行发布，可以减少治理等待，同时仍由自动化
和一次完整复核发现并关闭真实生产边界问题。因此本次最小治理变化保留。

这不证明产品已达到 S2/S3、`product/0.1.0`、生产级高可用或 SLA，也不授权 Stage 12、
实时 Provider、费用、真实数据或外部业务动作。
