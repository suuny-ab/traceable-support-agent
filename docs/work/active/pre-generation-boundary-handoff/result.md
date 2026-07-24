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
- 安全边界只覆盖当前规则来源明确支持的异常发热、冒烟、进液 / 进水及已吸入液体事件；
  型号边界覆盖 CZ-R1 的自动集尘、集尘袋、进尘口或 E310 操作 / 故障请求。
- `GEN-DEV-MH-001` 的公开期望现在与产品结果一致：`handoff`、`safety_risk`、
  `安全风险`、`P0-紧急`、固定来源标识、`provider_call_count=0`。
- 相邻合法负例保持放行：CZ-R2 集尘袋、CZ-R1 尘盒、CZ-R2 清水箱、积水知识问答和
  R1 / R2 复位差异问答。

## 验证结果

| 层级 | 命令 / 范围 | 结果 |
| --- | --- | --- |
| 最便宜 | `api/tests/test_product_boundaries.py` | 7/7 通过 |
| API | `python -m pytest api/tests -q` | 77 通过，1 项按环境条件跳过 |
| Stage 12 机制 | `python -m pytest tools/tests/test_stage12_eval.py -q` | 12/12 通过 |
| 治理工具 | `python -m unittest discover -s tools/tests -p "test_*.py"` | 65 通过，7 项按环境条件跳过 |
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

## 正式复核修复

- CI run `30058941904` 在候选
  `8b50618de0f59b623de8e7314201931d2310c6a8` 上四项必需 Checks 全绿后执行首轮只读
  正式复核；复核结论为 `failed`，候选随即失效。
- 修复范围固定为四项 finding：校验正文单一明确型号与所选型号的一致性；放行明确的
  能力存在 / 双型号差异知识问答并继续阻断操作和故障请求；让 Stage 12 评分器读取合法
  handoff 的 `boundary_sources`；删除当前公开来源未支持的 `起火`、`触电` 安全词。
- 修复不修改公开合成语料、不伪造 `answer` / `proposal`、不扩展安全词或 Provider 范围。
- 修复后 replay 镜像
  `sha256:7524dbe354b46ddd5924e596e5514d20af4c8e17a27879579ce4ee6dd4a877eb`
  的 `python -S` 无网络导入、`10001:10001` 用户、只读最小权限启动与
  `status=ok` / `live_experience=replay_only` 健康检查通过；测试容器已删除。
- 首轮候选 `8b50618` 不得合入；修复后的新候选需重新通过四项 Checks，并由同一复核者
  仅复核 finding 与覆盖 diff。
- 第二轮候选 `46c753773795d8ae97a8239bbb9fc1f185cc3c09` 在 CI run
  `30059598825` 四项必需 Checks 全绿后仍被聚焦复核判为 `failed`：双型号操作请求可在
  所选型号为 CZ-R2 时绕过，且“可以 / 可不可以 / 会不会”能力问法仍被误拦。
- 第二轮修复使正文明确包含 CZ-R1、R2 独占能力和操作 / 故障标记时不再因同时提到两个
  型号而豁免；同时补齐上述能力存在问法，并以“可以怎么更换”作为相邻操作负例。
- 第二轮修复后的受影响 API、治理、公开扫描和 replay 镜像检查全部通过；Provider 调用
  保持 0。
- `46c7537` 已失效，不得合入；新候选仍需重新通过四项 Checks 与同一复核者的聚焦复核。
- 第三轮候选 `497f10cb2236b4760ed13368373d889522dbc661` 在 CI run
  `30059878623` 四项必需 Checks 全绿后仍因 1 项聚焦 finding 判为 `failed`：
  `开启 / 启动 / 设置` 等歧义动作词优先于明确能力问法，造成合法知识问答误拦。
- 第三轮修复把判定顺序固定为明确操作 / 故障上下文、明确能力问法、单独动作词；因此
  “是否支持开启……”和“……可以设置吗”放行，而“怎么更换”、已满 / 故障请求仍阻断。
- 第三轮修复后的完整 API、公开扫描与 replay 镜像检查通过；Provider 调用保持 0。
- `497f10c` 已失效，不得合入；新候选仍需重新通过四项 Checks 与同一复核者聚焦复核。
- 第四轮候选 `dbd2941f104fef2e6c5ad55523baa6b4a98142ec` 在 CI run
  `30060109472` 四项必需 Checks 全绿后仍因 1 项聚焦 finding 判为 `failed`：
  `E310 可以重置吗` 与“集尘袋已满可以重置吗”被宽泛能力模式误放行。
- 第四轮修复在能力模式前识别“已满”等明确状态，并把更换、清理、重置、恢复、测试、
  维修等高风险动作前置；开启、启动、设置仍允许进入明确能力问法判定。
- 第四轮修复后的完整 API、公开扫描与 replay 镜像检查通过；Provider 调用保持 0。
- `dbd2941` 已失效，不得合入；新候选仍需重新通过四项 Checks 与同一复核者聚焦复核。
- 第五轮候选 `b2d3c099dcd8d15c4c1a316a33bbc81e6609c16b` 在 CI run
  `30060312783` 四项必需 Checks 全绿后通过同一复核者的 findings-only 正式复核；
  findings 为 0，工作树在复核结束时保持干净，SHA 未变化。
- 第五轮确认裸 E310 / 已满与高风险动作组合在公开 API 和 Runner 均为零 transport
  handoff；指定能力问答继续进入 Runner，相邻操作负例继续转人工。
- 正式复核总计 5 轮：1 次完整复核与 4 次 findings-only 复核；阻断 finding 数依次为
  4、2、1、1、0，四个候选因真实可达 finding 失效。复核避免了型号绕过、评分误判与
  能力问答误拦，但也证明继续扩充短语规则的成本较高。
- 后续语义分类改进已登记为 Issue #25：只评估受控外部 API 与确定性硬门的混合边界，
  不采用本地小模型；该 Issue 不授权 Provider、费用、凭据或生产开关。
- 本次写入最终回执会形成新的纯文档收口候选；它仍需四项 Checks 与同一复核者的文档
  diff 复核，不能沿用 `b2d3c09` 的候选身份直接合并。

## 允许与不允许的结论

- 允许：声明的公开合成边界在当前本地候选的 QA、工单、Runner 与公网 API 入口上会于
  transport 构造前确定性失败关闭；明确的能力存在与双型号差异知识问答不因排他词本身
  被误拦。
- 不允许：Stage 12 已重新通过、真实模型质量提升、任意安全 / 型号表达都能识别、公网
  实时 Provider 就绪或用户验收通过。
- 正式合入结论仍需纯文档收口 head 的四项 Checks 全绿与文档 diff 复核；随后还需用户
  单独授权 Ready、合并及由 `main` 触发的自动生产部署。
