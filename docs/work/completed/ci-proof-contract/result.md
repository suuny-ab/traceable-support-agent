# 结果

> 状态：作者侧事实收口完成。Draft PR #32 已推送，真实 CI 全绿；用户已决定在冻结候选上安排独立只读复核。合并与部署未授权。

## 实际交付

- `tools/ci_proof.py`：CI 证明合同运行器。登记 17 条主张(claim),每条含主张文本、
  诚实边界和处理入口;`run` 包装单命令、`record` 回传多行 shell 步骤结果、`skip`
  记录故意跳过、`summary` 渲染 Job Summary 表。失败时在命令输出前打印归因类别
  (`product` / `boundary` / `external`)、主张和处理入口,并发出 `::error` 注解。
- `tools/ci_impact.py`:新增 `dependency_files_changed` 输出,检测
  `web/package.json`、`web/package-lock.json` 与 `api/requirements-*.txt/.lock`;
  未知或无法分类路径失败关闭为 `true`(审计照跑)。
- `.github/workflows/ci-release.yml`:
  - 四个 job 的关键步骤全部绑定主张与归因类别;外部获取(npm ci、pip install、
    模型下载)归为 `external`,治理 / 公开安全 / 依赖审计归为 `boundary`;
  - `npm audit --audit-level=high` 只在 `dependency_files_changed == 'true'` 时
    阻塞执行,依赖未变化时记录“故意跳过: dependencies_unchanged”;
  - `governance_only` 变更下三个运行时 job 记录全部检查的“故意跳过: governance_only”;
  - 每个 job 末尾 `if: always()` 渲染证明摘要:通过 / 失败 / 跳过 / 未执行四类状态
    显式列出,未执行表示该检查本次没有证明任何东西;
  - Web 路由冒烟从仅断言 HTTP 200 升级为断言 `<html lang="zh-CN">` 页面标记和
    首页 H1 文案;容器冒烟改用状态累积 + 显式 `exit "$status"`,失败点输出稳定
    echo 码。
- `tools/dependency_audit.py`:本地定期依赖审计入口;`web/` npm audit 必跑,
  `pip-audit` 存在时对两份 API 锁定清单扫描;工具缺失记 skipped 不影响退出码,
  任一扫描发现 high+ advisory 退出码为 1。未在 GitHub 启用定时运行。
- `tools/check_public_repo.py`:容器冒烟钉定合同与 job 元数据更新为新脚本
  (含 `env:` 与 proof 记录行);`governance_only` 成功语义钉定从旧步骤名
  “Report governance-only impact” 更新为 “Record skipped runtime checks
  (governance-only change)”。钉定强度不变:任何对冒烟边界、就绪超时、路由
  检查或 proof 记录行的篡改仍失败关闭。
- `docs/engineering/quality.md`:新增“CI 证明合同与失败归因”一节;Web 本地检查
  移除常驻 npm audit,登记依赖审计分层与本地入口。
- `docs/status.md`:切换为 `developing`,链接本增量。

## 验证

- `python -m unittest discover -s tools/tests -p "test_*.py"`:全部通过(含新增
  ci_proof 14 例、ci_impact 依赖检测 1 例、dependency_audit 4 例,容器冒烟夹具与
  15 个变异全部按预期拒绝)。
- `python tools/check_public_repo.py --scope worktree`:通过。
- 两个 workflow YAML 均解析有效;全部 30 个 run 块通过 `bash -n` 语法检查;workflow
  引用的主张与登记册完全一致(无未知、无未用)。
- Fast 层:`test_package_boundaries.py`、`test_public_api.py`、`test_provider_usage.py`
  通过;`git diff --check HEAD` 无空白符问题。
- 本地模拟 `ci_proof.py run / record / skip / summary`:三类归因输出、JSONL 记录、
  Markdown 摘要(含未执行列出)符合预期。
- `test_stage12_eval.py` 与 `test_generation_contract_probe.py` 在本机报
  `embedding_model_file_inventory_invalid` 共 14 个 error;在基线提交上 stash 复测
  结果完全相同,确认是本 worktree 无本地模型的既有环境条件,与本增量无关(CI 中
  这些测试由 api job 带模型执行,与本增量的 workflow 改动路径一致)。

## 证据边界

- 本地验证证明工具行为、扫描器钉定和 YAML 有效性;不证明 GitHub Actions 上的真实
  运行结果(本轮不授权推送 / 重跑,workflow 变更尚未在 runner 上执行过)。
- `python3` 在 ubuntu-24.04 runner 基础镜像上可用是既有假设(原 containers job 已在
  无 setup-python 的情况下使用 `python`);首次真实运行若缺 `python3` 会在摘要步骤
  失败,归因清楚。
- 容器冒烟的 base image 拉取失败仍归 `containers.image-build`(product),其处理入口
  注明 pull / network 错误按外部依赖处理;自动区分需要预拉取步骤,本轮未实现。
- 定时冒烟的固定等待循环保持不变,flake 风险未被消除,只是失败时归因可读。

## 仍未解决

- 定期审计 workflow 已随 PR #32 提交;schedule 只在合并进默认分支后生效,合并与首次
  周跑未授权。
- required checks 名称与分支保护未动;新摘要只对点进 run 的读者可见,Checks 列表
  本身不变。
- README 无 CI 状态入口(与 Issue #29 重叠,留给用户决定)。
- 四个 job 的分类 shell 片段仍重复(低优先级)。
- 各 job 的 Job Summary 证明表内容未逐行核对;Checks 终态已经用户在 run 页面确认。

## 2026-07-26 续:定期审计接入 GitHub

用户授权后追加交付:

- `.github/workflows/dependency-audit.yml`:每周一 07:43 UTC 定期依赖审计
  (schedule 只在默认分支 `main` 运行;分支与 PR 只能 `workflow_dispatch` 手动
  触发),`pipx` 安装钉定的 `pip-audit==2.10.1` 后运行 `tools/dependency_audit.py`,
  完整输出写入 Job Summary,发现 high+ advisory 时 run 变红。
- `tools/dependency_audit.py`:pip 侧改为 `--disable-pip --no-deps`,直接审计锁定
  清单的固定版本;已在本机 venv(pip-audit 2.10.1)中对两份锁文件实测通过——
  原 `--requirement` 直跑会让 pip 重新解析并在哈希锁文件 + 平台标记依赖下失败。

追加验证:新 workflow YAML 解析有效、run 块通过 `bash -n`、`check_public_repo.py
--scope worktree` 通过、dependency_audit 单测更新后全绿、本机完整跑通
npm + pip 三路扫描(退出码 1,符合发现语义)。

审计在本机发现的真实依赖漂移(未修复,锁文件更新是独立依赖变更,留待用户决定):

- `web/` npm:11 个 high advisory(brace-expansion / minimatch 链来自 eslint 工具链,
  postcss 来自 next 构建链);
- `api/requirements-test.lock`:pygments 2.19.2(PYSEC-2026-2987,修复 2.20.0)、
  pytest 9.0.2(PYSEC-2026-1845,修复 9.0.3);
- `api/requirements-live.lock`:无已知漏洞。

上述漂移全部是开发 / 测试 / 构建工具链,live 运行时依赖干净;这同时意味着 main 上
旧的“每次 runtime 变更阻塞 audit”门今天就会因外部 advisory 变红,本增量的门分离
正是针对这类不可归因红灯。

## 2026-07-26 续二:首次真实 CI 暴露 workflow 语义缺陷并修复

Draft PR #32 的首次 push 触发 run 30194650726 在 0 秒失败、未创建任何 job,GitHub
报告 workflow file issue。根因:四个 job 的 job 级 `env` 绑定了 `${{ runner.temp }}`,
而 `runner` context 不允许出现在 job 级 `env`(该处在 runner 分配前求值)。本地
YAML 解析与 `bash -n` 都无法覆盖这类 GitHub 语义校验,属本增量引入的定义缺陷
(归因 `product`)。

最小修复(不重构):删除四个 job 级 `env`,proof 路径在 run 块内统一以 shell 变量
`"$RUNNER_TEMP/ci-proof.jsonl"` 引用(每个 job 独立 runner,无冲突);扫描器容器
冒烟钉定与测试夹具同步一行;`quality.md` 登记该验证边界。既有合法 step 级
`runner.temp` 用法(`TRACEABLE_MODEL_ROOT` 等)保持不变。

## 2026-07-26 续三:作者侧事实收口

- 最小修复(`ead0ba6`)推送后,`pull_request` 触发的 run 30195106004 全部通过:
  `governance` 14s、`web` 44s、`api` 59s、`containers` 1m19s;`publish` 按 PR 语义
  跳过(非 `main` push 不发布镜像)。各 Check 终态已经用户在 run 页面核对。
- 首次失败 run 30194650726(workflow 评估失败)与修复 run 构成完整因果链,见续二。
- 已知依赖漂移保持未处理:npm 11 个 high advisory(eslint / next 工具链)、test 锁
  pygments 2.19.2 与 pytest 9.0.2;live 运行时依赖无已知漏洞。锁文件修复是独立
  依赖工作,由用户决定是否立项。
- 仍未授权:合并 Draft PR #32(合并进 `main` 将触发 publish 与自动生产部署链)、
  分支保护或 required checks 变更、依赖漂移修复、README CI 入口(留待 Issue #29)。
- 用户已决定在冻结候选上安排独立只读复核;复核范围与冻结 SHA 见 `review.md` 续三。

## 2026-07-26 续四:独立复核 findings 的最小修复

冻结候选 `2e544ee` 的独立只读复核(回执 SHA-256
`0f02b9fb956dcee102793d18cfdaba52be1fd6f7c9e8f4e259bd18995bd1fdd6`)判定不就绪,
主 Agent 独立核对后确认五项阻断中四项半成立,按已批准边界修复:

1. 绿色 Check 虚假失败注解(成立):测试用 `contextlib.redirect_stderr` 隔离
   `::error` workflow command 并转为断言;测试套件 stderr 中 `::error` 行数降为 0。
2. “未执行”不阻断(成立):`summary` 在 `--expect` 存在缺失主张时失败关闭(exit 1),
   跳过不触发;绿色 required Check 不再能掩盖未执行的检查。
3. 红灯归因(核心成立):`run` 在命令执行前打印 `ci_check claim=… category=…` 归因行;
   `web.dependencies`、`api.dependencies`、`api.model-download` 的诚实边界改为承认
   候选修改(锁不一致、错误哈希、模型清单变更)同样在此失败,先核对 diff 再按外部
   依赖重试。checkout / setup / publish / workflow 评估失败维持合同外,属声明边界。
4. 依赖审计合同(成立):退出码语义按工具如实表述(npm=high+、pip=任意已知漏洞、
   非零亦可能是扫描环境错误);`ci_impact` 拆分 `web/api_dependency_files_changed`;
   api job 新增候选级阻塞 pip 审计(钉定 `pip-audit==2.10.1 --disable-pip --no-deps`),
   依赖未变化时记录跳过。
5. 冻结证据一致性(成立):冻结 SHA `2e544ee` 的验证 run 为 30195548284(四项 Checks
   全绿、publish 跳过),续三对 `ead0ba6` / run 30195106004 的引用仅为修复前历史;
   `ROADMAP.md` 当前一节已同步为本活动增量。

复核回执中不成立的部分:把 checkout / setup / publish / workflow 评估纳入证明合同
超出当前合同声明范围,按边界处理而非修复项。

本地验证:ci_proof 18 例、ci_impact 8 例、dependency_audit 4 例、扫描器 25 例全绿;
两个 workflow YAML 有效、35 个 run 块 `bash -n` 通过、主张交叉检查零偏差;
`check_public_repo.py --scope worktree` 通过。

## 2026-07-26 续五:针对性复核四项剩余 finding 的修复

候选 `a19420d` 的针对性复核(回执 SHA-256
`99d887bf9f303fef5bf72f7e9ddf746c0c463009d0bd526b2fff9ecc1cee343d`)确认上一轮多数
finding 已解决,剩余四项经主 Agent 独立核对全部成立并修复:

1. 归因行顺序(成立):`print` 在非 TTY 下块缓冲,子进程输出先于 `ci_check` 到达
   日志——真实 runner 否证了“命令输出前打印”。修复为 `flush=True`,并新增 fd 级
   顺序测试(`os.dup2` 重定向后断言 `ci_check` 先于子进程输出)。
2. 归因文字自相矛盾(成立):`CATEGORY_GUIDANCE` 的 `external` 旧文“候选 diff 不是
   原因”与三条安装 / 下载 claim 的边界矛盾;`product` 旧文与镜像构建 claim 的
   “拉取属外部”矛盾。两类 guidance 改为不自相矛盾的表述,处理入口保持按 claim
   区分;quality.md 类别条目同步。
3. 审计权威文字(成立):`dependency-audit.yml` 摘要改为“1 表示至少一路扫描未通过
   (npm=high+、pip=任意已知漏洞、亦可能是扫描环境错误,以输出为准)”;quality.md
   前段改为 web→npm audit、API 锁→pip-audit 的两侧描述;spec 证伪项与审计描述同步。
4. 合同外边界(成立):spec 用户结果与 quality.md 证明合同一节明确列出合同外四类
   (checkout、setup actions、artifact 上传、publish job、workflow 评估),不再无条件
   宣称“每个红灯”可归因。

本地验证:ci_proof 18 例(含新 fd 级顺序用例)等 55 例全绿;worktree 扫描通过;
workflow YAML 与 run 块语法、主张交叉检查通过。不改动已解决 findings,未制造失败
或 governance-only run;三个“待验证”项(缺失失败关闭真实红 run、完整
governance_only run、API 依赖变化的 pip 审计路径、定期审计首次周跑)继续保持。

## 2026-07-26 续六:审计失败归因的最终定向复核修复

候选 `811e7a1` 的最终定向复核(turn 0005 回执)确认输出顺序、合同范围、审计权威
文字均已解决,剩余一项阻断经主 Agent 独立核对成立:

- 候选级 npm / pip 审计固定标为 `boundary`,失败块只打印通用“修正内容或回退”与
  “更新依赖”,registry / 网络 / 工具环境故障会被错误归因给候选并给出错误行动建议;
  `api.audit-tool-install` 旧边界绝对排除候选(候选改钉定版本同样会导致安装失败)。

最小一致修复(不改类别体系、不加新类别):

- `boundary` guidance 改为按输出区分:内容或依赖问题修正内容或回退;扫描环境错误
  (registry / 网络 / 工具)按外部故障重试或等待;不得放松门。quality.md 类别条目同步。
- `web.dependency-advisory` / `api.dependency-advisory` 的边界承认 registry / 网络 /
  扫描环境错误同步骤失败,处理入口按输出分流(advisory→更新依赖或说明例外;环境
  错误→重试或等待)。
- `api.audit-tool-install` 边界改为“通常属 pipx / PyPI 外部故障;候选修改钉定版本
  同样会导致失败”,处理入口为先核对 diff 再按外部依赖重试。
- 顺带清理两处直接相关的过时 docstring:`ci_proof.py` 模块 docstring 的三类描述
  (旧的 external 绝对表述)与 `dependency_audit.py` 的“只有 npm audit 阻塞”描述。

本地验证:55 例相关工具测试全绿;`::error` 泄漏 0;worktree 扫描通过;workflow
YAML / run 块语法与主张交叉检查通过;`git diff --check` 干净。

## 2026-07-26 续七:失败输出保留 claim 边界

候选 `f82e563` 的单项复核(turn 0006 回执)确认续六的归因分流已解决,剩余一项
阻断经主 Agent 独立核对成立:`report_failure()` 把 claim 的 boundary 解构为
`_boundary` 丢弃,失败日志只打印主张 / 类别归因 / 处理入口;失败摘要行同样只显示
remediation。审计 claim 的决定性边界(如“pip-audit 无严重度阈值、扫描环境错误以
输出为准”)因此不会出现在真实失败输出中。

最小修复(类别体系与既有合同不变):

- `report_failure()` 失败块新增“边界： ”行,保留并显示 claim boundary。
- `render_summary` 失败行改为同时显示 boundary 与处理入口(通过行仍只显示边界,
  跳过 / 未执行行不变)。
- 新增两个针对性测试:审计失败 stderr 输出包含 pip-audit 边界全文与分流处理入口;
  失败摘要行包含 web 审计的触发边界与处理入口。既有失败输出测试补“边界： ”断言。
- `quality.md` 与 spec 证伪项同步为“失败块包含主张、类别归因、claim 边界与处理入口”。

本地验证:ci_proof 20 例(含 2 个新增 boundary 断言用例)等 55 例全绿;worktree
扫描通过;`git diff --check` 干净。

## 2026-07-26 终态:统一基线、部署与验收回执

- 独立复核:turn 0007 回执对候选 `c001e08` 结论 ready、剩余阻断为零;候选 SHA、
  PR head 与全绿 run 30212050262 一致。
- 合并:合并前实时复核(head、CLEAN、Checks、main 未前进)全部成立,PR #32 转
  Ready 后 squash 合并;统一基线为 `df81ccd81ee908f557c5896e1bbacfc859cc4ae7`。
- main CI:run 30212844769 四项 Checks 全绿;publish 成功,镜像
  `traceable-support-agent-web@sha256:358ae37b…07736fc` 与
  `traceable-support-agent-api-replay@sha256:e563ba91…b414981`(GHCR,带
  provenance / SBOM)。
- 生产部署:run 30212923995 自动触发,preflight 与 deploy 双成功,无回滚;
  release-manifest 经本地 `--verify` 绑定合并 SHA、run ID 与镜像摘要,
  `provider_enabled=false`、`provider_calls_during_build=0`。
- 公网健康:`/api/v1/health` 为 `replay_only`;/、/design、/app、/privacy 均 200。
- 用户线上体验验收(`user_confirmed_external`):用户本人于 2026-07-26 明确确认
  通过。外部回执坐标:Conversation `CONVERSATION-KIMI-TRACEABLE-CI-CONTRACT-20260726`,
  Turn `TURN-5cbcf680-b3da-41fd-bacf-bc4a2dbfc0b1`,message SHA-256
  `e39511443219e930401b188e1254a21e34f44c24a90710400e434cc1aa3cb3e5`,
  confirmation_ref
  `work:2026-07-27:user-confirmed-kimi-project-facts-closeout-research-message-13`。
  该回执可由本机个人 Work 控制记录核验;它不是 GitHub、CI、自动化或公开证据。
- 治理-only 真实运行证据:归档 PR #33 的 run 30213776085 分类为
  `classification=governance_only`,web / api / containers 各 5-6 秒显式跳过并记录
  `故意跳过: governance_only`(摘要失败关闭逻辑下,未记录的缺失会使 job 变红),
  publish 跳过,未触发任何部署运行。

## 保留的待验证边界(由未来自然事件提供证据,非已完成)

- 真实 advisory 红灯与环境故障(registry / 网络 / 工具)红灯的实际输出。
- 缺失主张导致真实 Actions 红灯的失败关闭。
- API 锁文件变化触发的候选级 pip-audit 真实路径(含 pipx 安装)。
- 定期 dependency-audit 的首次默认分支周跑(预计因已知漂移变红,属设计内检测)。
