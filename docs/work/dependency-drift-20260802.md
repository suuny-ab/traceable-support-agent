# 依赖漂移快照（2026-08-02）

> 基线：`origin/main@31541cfaca4f71c507fbda6f4774ed8e7c8b4a7f`
>
> 结论边界：本报告是 `2026-08-02` 的注册表与 advisory 快照，只提出下一切片优先级；没有修改任何依赖、锁文件、代码、生产或 Provider。

## 结论

| 分级 | 结论 |
| --- | --- |
| 建议立即升级 / 修正 | Web 锁中有 **3 个 high 级包 finding、对应 2 个唯一 advisory**：生产闭包中的 `postcss==8.5.14`，以及开发 / 构建工具链中的两份 `brace-expansion`。另有 `pyproject.toml` 声明 `pytest==9.0.2`、需求源与锁为 `9.0.3` 的声明漂移。两类问题应分别用可独立回滚的小切片处理。 |
| 可观察 | Python 有 5 个同主版本漂移；Web 有若干 patch / minor 漂移，并有 ESLint 与 TypeScript 的 major 迁移。它们没有进入本次“立即升级”结论，应按耦合关系拆批验证。 |
| 无需动 | Python 三份完整锁经钉定 `pip-audit==2.10.1` 扫描均未发现已知漏洞；多个直接依赖已经是注册表 latest。 |

没有证据表明公网当前存在可利用路径。本报告只证明锁图命中 advisory：`postcss` 位于生产依赖闭包，但其已知问题发生在 source map 自动加载；`brace-expansion` 位于开发 / 构建工具链。是否可达需要在升级切片中另做输入路径核对，不能把“没有已证明可达”写成“安全”。

## 范围与方法

- Python：3 份锁共解析 13 / 34 / 5 个包，去重后 46 个；版本漂移表覆盖 11 个直接根依赖。
- Web：`package-lock.json` lockfile v3 共 437 个 package entry（含根项目，依赖 entry 436 个）；版本漂移表覆盖 11 个声明依赖和 2 个显式 override。
- 漏洞：Python 使用仓库 CI 同版 `pip-audit==2.10.1 --disable-pip --no-deps` 扫三份完整锁；Web 使用官方 npm registry 分别扫描完整闭包和 `--omit=dev` 生产闭包。
- 版本与发布日期：读取官方 PyPI JSON 与 npm registry 元数据；“年龄”按首次发布 UTC 日期到 `2026-08-02` 粗略计算。
- 主版本差距只按版本号表面比较。`0.x` 的 minor 变化可能包含破坏性变化，仍需按 major 迁移对待。

## 声明与锁一致性

| 声明族 | 结果 | 分级 |
| --- | --- | --- |
| Python base | `pyproject.toml` 与 `requirements-base.txt` 的 `fastapi` / `uvicorn` 精确一致 | 无需动 |
| Python live | 8 个 `pyproject.toml` optional dependency 与 `requirements-live.txt` 精确一致 | 无需动 |
| Python test | `pyproject.toml` 为 `pytest==9.0.2`，`requirements-test.txt` 与锁为 `9.0.3` | **建议立即修正**；不同安装入口会得到不同测试版本，但本任务不改声明 |
| Web root | `package.json` 与 `package-lock.json` 根 entry 的 dependencies / devDependencies / engines 精确一致 | 无需动 |

## 安全公告

### 扫描结果

| 锁 / 闭包 | 结果 | 能证明什么 |
| --- | --- | --- |
| `requirements-base.lock`（13 包） | 0 个已知漏洞 | `pip-audit` 当前数据源没有命中；不是未来安全保证 |
| `requirements-live.lock`（34 包） | 0 个已知漏洞 | 同上；完整 live 解析锁已扫描 |
| `requirements-test.lock`（5 包） | 0 个已知漏洞 | 同上；测试闭包已扫描 |
| `package-lock.json` 完整闭包 | high 3、critical 0 | 3 个受影响包 finding，实际对应 2 个唯一 advisory |
| `package-lock.json --omit=dev` | high 2、critical 0 | `postcss` 及受它影响的直接包 `next` 位于生产闭包；`brace-expansion` 不在生产闭包 |

### 建议立即升级

| Advisory | 当前命中 | 已知影响范围 / 安全边界 | 下一切片最小动作 |
| --- | --- | --- | --- |
| [`GHSA-r28c-9q8g-f849`](https://github.com/advisories/GHSA-r28c-9q8g-f849) | 显式 override `postcss==8.5.14`；Next / Tailwind 构建链使用该节点 | high，`<=8.5.17`；Previous Source Map 自动加载可造成路径穿越与 `.map` 文件泄露。生产闭包命中不等于公网请求可达。 | 把 override 至少提升到 `8.5.18`，优先评估当前 latest `8.5.25`；刷新锁后跑 Web 全量、容器和两种 npm audit。不要采用 npm 自动建议的 Next 9 降级。 |
| [`GHSA-mh99-v99m-4gvg`](https://github.com/advisories/GHSA-mh99-v99m-4gvg) | `brace-expansion==1.1.16`（`minimatch@3.1.5`）与 `5.0.7`（`@typescript-eslint/.../minimatch@10.2.5`） | high，恶意超大 expansion 可导致 OOM DoS；本仓命中仅在开发 / 构建闭包。1.x 需 `>=1.1.17`，5.x 需 `>=5.0.8`。 | 只刷新满足现有父依赖范围的传递锁，目标至少 `1.1.17` / `5.0.8`（registry 当前 5.x latest 为 `5.0.9`）；不借机做工具链 major 升级。 |

`npm audit` 还把 `next` 列成 high，是 `postcss` finding 的 effect，不是第三个唯一 advisory。自动修复建议将 Next 降到 `9.3.3`，与当前 `16.2.11` 不兼容，也没有消除本仓显式 `postcss` override 的根因，因此不能执行。

## Python 直接依赖漂移

| 包 | 锁定版本（发布 / 年龄） | 注册表 latest（发布） | 版本差距 | 分级与理由 |
| --- | --- | --- | --- | --- |
| [`fastapi`](https://pypi.org/project/fastapi/) | `0.141.1`（07-29 / 4 天） | `0.141.1`（07-29） | 无 | 无需动；latest，锁审计无命中 |
| [`uvicorn`](https://pypi.org/project/uvicorn/) | `0.52.0`（07-29 / 4 天） | `0.52.1`（08-01） | patch | 可观察；新 patch 仅 1 天，等单独升级切片验证 |
| [`fastembed`](https://pypi.org/project/fastembed/) | `0.8.0`（03-23 / 132 天） | `0.8.0`（03-23） | 无 | 无需动；latest |
| [`numpy`](https://pypi.org/project/numpy/) | `2.4.2`（01-31 / 183 天） | `2.5.1`（07-04） | 同 major、1 minor | 可观察；需与 FastEmbed / ONNX Runtime 一起验证 ABI 与检索回归 |
| [`onnxruntime`](https://pypi.org/project/onnxruntime/) | `1.24.2`（02-19 / 164 天） | `1.28.0`（07-25） | 同 major、4 minor | 可观察；模型加载与平台 wheel 是主要兼容门 |
| [`pgvector`](https://pypi.org/project/pgvector/) | `0.5.0`（07-06 / 27 天） | `0.5.0`（07-06） | 无 | 无需动；latest |
| [`psycopg`](https://pypi.org/project/psycopg/) | `3.3.4`（05-01 / 93 天） | `3.3.4`（05-01） | 无 | 无需动；latest |
| [`psycopg-binary`](https://pypi.org/project/psycopg-binary/) | `3.3.4`（05-01 / 93 天） | `3.3.4`（05-01） | 无 | 无需动；与 `psycopg` 精确同版 |
| [`rank-bm25`](https://pypi.org/project/rank-bm25/) | `0.2.2`（2022-02-16 / 约 4.5 年） | `0.2.2`（2022-02-16） | 无可升级版本 | 可观察；当前无 advisory，但长期无新发布，应保留现有回归并观察维护状态 |
| [`tokenizers`](https://pypi.org/project/tokenizers/) | `0.22.2`（01-05 / 209 天） | `0.23.1`（04-27） | `0.x` minor | 可观察；按潜在破坏性变化处理，并与 FastEmbed 一起升级 |
| [`pytest`](https://pypi.org/project/pytest/) | `9.0.3`（04-07 / 117 天） | `9.1.1`（06-19） | 同 major、1 minor | 可观察；纯测试工具，单独升级成本低但无安全紧迫性 |

Python 侧没有直接依赖跨 major 落后；当前最明显的是 ONNX Runtime 的同 major 多 minor 漂移，以及 `rank-bm25` 的长期无新发布。两者都不是本次安全修复门。

## Web 直接依赖与 override 漂移

| 包 | 锁定版本（发布 / 年龄） | 注册表 latest（发布） | 版本差距 | 分级与理由 |
| --- | --- | --- | --- | --- |
| [`next`](https://www.npmjs.com/package/next) | `16.2.11`（07-21 / 12 天） | `16.2.12`（07-25） | patch | 可观察；与 `eslint-config-next` 同批 |
| [`react`](https://www.npmjs.com/package/react) | `19.2.6`（05-06 / 88 天） | `19.2.8`（07-21） | patch | 可观察；与 `react-dom` 同批 |
| [`react-dom`](https://www.npmjs.com/package/react-dom) | `19.2.6`（05-06 / 88 天） | `19.2.8`（07-21） | patch | 可观察；保持 React 精确同版 |
| [`@tailwindcss/postcss`](https://www.npmjs.com/package/@tailwindcss/postcss) | `4.2.1`（02-23 / 160 天） | `4.3.3`（07-16） | 同 major、1 minor | 可观察；与 Tailwind 同批，不与安全 patch 强绑 |
| [`@types/node`](https://www.npmjs.com/package/@types/node) | `22.19.19`（05-11 / 83 天） | `26.1.2`（07-27） | 4 major | 可观察；CI 是 Node `24.13.0`，下一切片应先对齐 24.x（registry 当前 `24.13.3`），不能盲追 26 |
| [`@types/react`](https://www.npmjs.com/package/@types/react) | `19.2.14`（02-11 / 172 天） | `19.2.18`（07-30） | patch | 可观察；与 React 类型同批 |
| [`@types/react-dom`](https://www.npmjs.com/package/@types/react-dom) | `19.2.3`（2025-11-12 / 263 天） | `19.2.4`（07-30） | patch | 可观察；与 React DOM 类型同批 |
| [`eslint`](https://www.npmjs.com/package/eslint) | `9.39.4`（03-06 / 149 天） | `10.8.0`（07-24） | 1 major | 可观察；`eslint-config-next@16.2.11` 接受 `eslint>=9`，但 major 迁移仍需独立验证规则输出 |
| [`eslint-config-next`](https://www.npmjs.com/package/eslint-config-next) | `16.2.11`（07-21 / 12 天） | `16.2.12`（07-25） | patch | 可观察；与 Next 同批 |
| [`tailwindcss`](https://www.npmjs.com/package/tailwindcss) | `4.2.1`（02-23 / 160 天） | `4.3.3`（07-16） | 同 major、1 minor | 可观察；与 PostCSS 插件同批评估 |
| [`typescript`](https://www.npmjs.com/package/typescript) | `5.9.3`（2025-09-30 / 306 天） | `7.0.2`（07-08） | 2 major | 可观察；迁移面大，不能与安全 patch 混做 |
| [`postcss`](https://www.npmjs.com/package/postcss) override | `8.5.14`（05-04 / 90 天） | `8.5.25`（07-29） | 同 major、11 patch | **建议立即升级**；当前版本命中 high advisory |
| [`sharp`](https://www.npmjs.com/package/sharp) override | `0.35.3`（07-01 / 32 天） | `0.35.3`（07-01） | 无 | 无需动；latest |

## 建议的后续切片与停止线

1. **Web 安全补丁切片（优先）**：只处理 `postcss` 与两份 `brace-expansion`，不混入 Next / React / Tailwind / ESLint / TypeScript 功能升级。验收至少包含完整与 production-only npm audit、Web lint / typecheck / build / tests、容器冒烟和锁文件差异审计。
2. **Python 声明同步切片（优先但独立）**：只把 `pyproject.toml` 的 test extra 与已生效的 `pytest==9.0.3` 需求源 / 锁对齐，并新增声明一致性机器检查；不借机升级 pytest。
3. **常规同主版本刷新（可观察）**：Next + eslint-config-next、React + React DOM、Python 数值 / 推理栈分别拆批；每批必须有对应产品回归。
4. **major 迁移（后置）**：ESLint 10、TypeScript 7、`@types/node` 对齐运行时单列，不以“latest”本身作为收益。
5. **停止线**：本报告不修改任何依赖；是否启动升级、如何分批和是否部署均由新任务与新授权决定。

## 本任务验证

- 治理工具：113 passed / 8 skipped。
- API 全集：138 passed / 2 skipped，24 subtests passed。
- Web：clean install 后 lint、typecheck、production build 与 36 tests 全部通过。
- `package-lock.json` 在审计、clean install 与测试前后 SHA-256 均未变化；候选差异不含任何依赖、锁或产品文件。
- 上述绿灯证明现有锁在当前测试面没有退化；它不抵消已命中的 advisory，也不证明未来升级兼容。

## 可重复证据

```powershell
uvx --python 3.13 --from pip-audit==2.10.1 pip-audit --disable-pip --no-deps --requirement api/requirements-base.lock
uvx --python 3.13 --from pip-audit==2.10.1 pip-audit --disable-pip --no-deps --requirement api/requirements-live.lock
uvx --python 3.13 --from pip-audit==2.10.1 pip-audit --disable-pip --no-deps --requirement api/requirements-test.lock
npm audit --package-lock-only --audit-level=low --registry=https://registry.npmjs.org
npm audit --package-lock-only --omit=dev --audit-level=low --registry=https://registry.npmjs.org
```

版本元数据来自官方 [`PyPI JSON API`](https://docs.pypi.org/api/json/) 与 [`npm registry`](https://registry.npmjs.org/)；安全详情以报告中链接的 GitHub Advisory Database 页面为准。`npm audit` 前后 `package-lock.json` SHA-256 未变化。
