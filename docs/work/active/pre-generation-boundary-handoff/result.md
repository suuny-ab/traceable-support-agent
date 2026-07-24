# 结果记录

> 状态：`in_progress`
>
> 日期：`2026-07-24`

## 当前证据

- 已恢复 Stage 12 聚合回执：`SAF-003` 与 `MBD-003` 均为期望 `handoff`、实际
  `candidate`。
- 已确认 Stage 12 通过 `DefaultProductRunner`，不会经过公网 API 的 `preflight`。
- 已确认现有型号过滤只约束检索证据的 `applicable_models`，没有判定用户请求是否要求
  当前型号不存在的能力。
- 新增 Product 层纯函数边界与 `product-boundary-handoff-v1` 零调用包；Runner 在
  transport factory 前执行，QA / 工单直接入口和公网 API 复用同一判定。
- 安全边界覆盖公开合成 SOP 明确的异常发热、冒烟、起火、触电、进液 / 进水及已吸入
  液体事件；型号边界覆盖 CZ-R1 请求 CZ-R2 独占的自动集尘、集尘袋、进尘口或 E310。
- `GEN-DEV-MH-001` 的公开期望现在与产品结果一致：`handoff`、`safety_risk`、
  `安全风险`、`P0-紧急`、固定来源标识、`provider_call_count=0`。
- 相邻合法负例保持放行：CZ-R2 集尘袋、CZ-R1 尘盒、CZ-R2 清水箱、积水知识问答和
  R1 / R2 复位差异问答。

## 验证结果

| 层级 | 命令 / 范围 | 结果 |
| --- | --- | --- |
| 最便宜 | `api/tests/test_product_boundaries.py` | 5/5 通过 |
| API | `python -m pytest api/tests -q` | 74 通过，1 项按环境条件跳过 |
| Stage 12 机制 | `python -m pytest tools/tests/test_stage12_eval.py -q` | 11/11 通过 |
| 治理工具 | `python -m unittest discover -s tools/tests -p "test_*.py"` | 64 通过，7 项按环境条件跳过 |
| 公开扫描 | `python tools/check_public_repo.py --scope worktree` | 通过，178 个文件、8 个公开案例 |
| Web | lint、typecheck、生产 build、Node tests | 18/18 通过 |

所有测试均未授权或调用 Provider；新增正例通过 transport factory 计数器证明构造次数为
0。Python 输出了本机 `requests` 与其依赖版本组合警告，测试退出码仍为 0；本增量没有
新增或修改依赖。

## 变更影响

- `safety_handoff` 公开前置原因统一为既有公开业务期望 `safety_risk`。
- 新增 `model_scope_conflict` 原因和明确的型号边界公开提示。
- 从 `evals/public-regression-v1.json` 的已知缺口中移除已修复的
  `GEN-DEV-MH-001` 原因不一致；其他已知缺口保持不变。
- 公网仍为 `replay_only`，没有部署、Provider、费用或外部业务动作变化。

## CI 修复记录

- Draft PR #24 首轮 CI run `30058724960` 绑定 head
  `6331dc24a029ca38fad5d6256dd486134c78e04b`。
- `governance`、`web`、`api` 通过；`publish` 作为 Draft PR 按设计跳过。
- `containers` 在 replay 镜像的无 site-packages 导入冒烟中失败：
  `ModuleNotFoundError: No module named 'traceable_support.product.boundaries'`。
- 根因是 replay target 只选择性复制 `product/__init__.py` 与 `product/types.py`，新增的
  API 启动依赖 `product/boundaries.py` 未进入镜像；本地源码测试因此不能证明选择性镜像
  文件集完整。
- 修复只为 replay target 增加该纯标准库模块，不把 retrieval、generation 或 Provider
  模块带入 replay 镜像。`6331dc2` 已失效，不得用于正式复核。
- 本地 replay target 构建为镜像
  `sha256:a2935c71b17b4e3a854512795882d6fa95141a9f5564fde9ab08bfa4544ee575`；
  `--network none` + `python -S` 导入通过，镜像用户保持 `10001:10001`。
- 该镜像在只读文件系统、最小 tmpfs、`--cap-drop ALL`、`no-new-privileges` 和
  `TRACEABLE_PUBLIC_LIVE_ENABLED=false` 下启动成功；健康响应为
  `status=ok`、`live_experience=replay_only`。测试容器随后删除，Provider 调用仍为 0。

## 允许与不允许的结论

- 允许：声明的公开合成边界在当前本地候选的 QA、工单、Runner 与公网 API 入口上会于
  transport 构造前确定性失败关闭，相关负例未被误拦。
- 不允许：Stage 12 已重新通过、真实模型质量提升、任意安全 / 型号表达都能识别、公网
  实时 Provider 就绪或用户验收通过。
- 正式合入结论仍需 Draft PR 四项 Checks 全绿后的冻结 SHA 独立复核。
