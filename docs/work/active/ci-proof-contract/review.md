# 复核

> 本增量为 R0 CI 定义与治理工具改动,不触及产品运行代码、公开主张、Provider、
> 费用、持久化或部署门,按规则本可由自动化与主 Agent 关闭;用户已决定在冻结
> 候选上安排独立只读复核,复核关闭前不作最终收口。

## 复核范围

- 安全姿态变化只有一处:`npm audit` 从“每次 runtime 变更阻塞”改为“依赖文件变化时
  阻塞 + 本地定期审计入口”。该取舍已由用户在增量启动时明确批准。
- `tools/check_public_repo.py` 的容器冒烟钉定合同被修改:逐行比对确认新脚本保留
  全部原有安全不变量(非 root 断言、只读 / 降权 / tmpfs 容器、断网装配检查、
  15 次 × 1 秒有界就绪循环、`replay_only` 健康断言、四路由检查、EXIT 清理 trap),
  新增内容仅为失败 echo 码、状态累积和 proof 记录;失败语义从 `bash -e` 隐式中止
  改为显式 `exit "$status"`,扫描器对脚本的逐行钉定使任何放松篡改仍失败关闭,
  15 个篡改变异全部按预期拒绝。

## 验证证据

见 `result.md` 的验证一节:工具单测、公开仓库扫描、YAML 解析、主张一致性交叉检查、
本地三类归因模拟均通过。

## 收口结论

- 本地范围内收口;workflow 在真实 runner 上的首次执行是剩余未知,失败时归因
  类别与摘要会把问题指向具体检查。
- 若后续在 GitHub 上启用定期审计或调整 required checks,属于新的外部动作,需用户
  独立授权,不从本增量推断。

## 2026-07-26 续:定期审计 workflow 复核

- 用户已明确授权本轮新增 `.github/workflows/dependency-audit.yml`、推送分支与创建
  Draft PR。新 workflow 为只读姿态:无 secret、`permissions: contents: read`、
  全部 action 钉定 40 位 SHA、checkout 禁用 persist-credentials、无
  `pull_request_target`;schedule 只在默认分支运行,每周一次,消耗有界。
- pip-audit 钉定 `==2.10.1` 并以 `--disable-pip --no-deps` 运行,避免审计工具在
  runner 上执行未锁定的依赖解析;本机同版本实测两份锁文件通过。
- 审计发现的依赖漂移(npm 11 个 high、test 锁 2 个)不在本增量修复;定期审计
  上线后首次周跑预计变红,这是设计内的检测行为,不是回归。
- 真实 CI 结果与 Draft PR 回执见续三。

## 2026-07-26 续二:workflow 评估失败复核

- 根因复核成立:全仓库仅四处 job 级 `env` 使用 `runner` context,均为本增量引入;
  既有绿色 workflow 只在 step 级使用该 context;失败形态(0 秒、无 job、workflow
  file issue)与 GitHub context 位置限制完全吻合。
- 修复保持最小:不改变证明合同设计、不触碰扫描器钉定的安全不变量,仅把 proof 路径
  从 GitHub expression 改为 run 块内 shell 变量;扫描器钉定与夹具同步更新。
- 该事件本身验证了失败归因设计的必要性:workflow 评估失败发生在任何检查执行之前,
  摘要机制对此类启动失败无法记录,已在 quality.md 诚实登记该边界。

## 2026-07-26 续三:冻结候选与独立只读复核安排

- 最终真实 CI:run 30195106004 在 `ead0ba6` 上全绿(governance / web / api /
  containers 通过,publish 按 PR 语义跳过),用户已核对终态。
- 用户已决定安排独立只读复核:冻结候选为本次事实收口提交推送后的 PR head
  (Checks 全绿后冻结,主 Agent 停止写入);复核者只读。
- 复核建议关注:17 条主张与 evidence-map 的一致性、三类失败归因的准确性、
  `governance_only` 跳过语义、依赖审计门分离的安全取舍、扫描器钉定同步的正确性,
  以及续二记录的 workflow 评估失败与修复是否完整闭环。
- 复核结果与收口结论由复核回执决定;合并仍需用户显式授权,不从复核通过推断。

## 2026-07-26 续四:独立复核回执处置

- 回执:冻结候选 `2e544eeb9213d44feafb3cb61c1922570cb496b4`,结论不就绪;回执
  SHA-256 `0f02b9fb956dcee102793d18cfdaba52be1fd6f7c9e8f4e259bd18995bd1fdd6`。
- 冻结证据更正:续三中 run 30195106004 属于修复前提交 `ead0ba6`;冻结 SHA
  `2e544ee` 的验证 run 为 30195548284(四项 required Checks 全绿、publish 按 PR
  语义跳过)。记录歧义已在本节更正。
- 主 Agent 独立核对结论:阻断 1(测试 `::error` 泄漏为绿 Check 注解)、2(未执行
  不阻断)、4(审计退出码合同与 API 侧覆盖)、5(冻结证据与 ROADMAP 矛盾)成立;
  阻断 3 核心成立(静态 `external` 过度承诺、归因行位置与 spec 不符),其中
  checkout / setup / publish / workflow 评估纳入合同的要求超出当前合同声明范围,
  按声明边界处理。
- 修复全部在已批准边界内,无重构、无新工具链、无产品代码或锁文件改动;明细与
  本地验证见 `result.md` 续四。
- 新候选 SHA 的四项 Checks 全绿后,按回执建议只对 findings 与覆盖 diff 做针对性
  复核;是否启动该复核由用户决定,主 Agent 不自行安排。

## 2026-07-26 续五:针对性复核回执处置

- 回执:候选 `a19420dd81ef11564b6711de39a6e97875cf33a2`,结论仍不就绪;回执
  SHA-256 `99d887bf9f303fef5bf72f7e9ddf746c0c463009d0bd526b2fff9ecc1cee343d`。
- 回执确认已解决:虚假失败注解、缺失失败关闭(代码)、skip 语义真实证据、API
  候选级审计接线、旧冻结证据绑定。
- 主 Agent 独立核对:四项剩余 finding 全部成立(归因行未 flush 被真实 runner 否证、
  类别 guidance 与 claim 边界自相矛盾、审计摘要与权威文字不一致、主合同未收窄
  “每个红灯”宣称),修复明细见 `result.md` 续五;回执列出的合同外项(Node Action
  弃用 warning、checkout/setup/publish/workflow 评估包装)未纳入工作。
- 三个“待验证”项按回执建议保留,未制造失败或 governance-only run。
- 新候选 Checks 全绿后是否启动下一轮针对性复核由用户决定,主 Agent 不自行安排。
