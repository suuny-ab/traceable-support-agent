# 复核

> 本增量为 R0 CI 定义与治理工具改动,不触及产品运行代码、公开主张、Provider、
> 费用、持久化或部署门,按规则由自动化与主 Agent 关闭,不强制正式独立复核。

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
- 真实 CI 结果与 Draft PR 回执在下一轮用户确认后记录。
