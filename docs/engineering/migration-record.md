# 唯一权威仓库迁移记录

本记录标识私有来源基线，以及建立干净公开历史时采用的白名单。它有意不包含私有归档位置、本机路径、Provider 输出、凭据、请求头或已消费 HOLDOUT 正文。

## 来源身份

- 产品基线：`ab2c4b8a374937a8727e414991799dba490db30b`
- 方向 B Web 基线：`b1bcc94c5cf122a6c6dcff5d007eb6194d47dcc7`
- 新历史从白名单重建开始；旧仓库的 385 个提交均不是本仓库的祖先提交。

## 纳入规则

纳入：当前产品合同、公开控制面、合成知识、八个脱敏回归预期、方向 B Web 源码、当前治理、可复现部署文件和适合公开的迁移哈希。

排除：旧 evidence 与编号审计区、未精选规格/计划、已消费 HOLDOUT 材料、Provider 原始输出、执行信封、日志、SQLite 状态、归档、缓存、构建产物、模型二进制、凭据和本机专用路径。

## 合成知识清单

| 文件 | 字节数 | SHA-256 |
| --- | ---: | --- |
| `after-sales-policy.md` | 2047 | `0c30193d1dffec7ab37690883197e7e4314338f7bf2526a2ce3ffef3abe94d2e` |
| `common-faq.md` | 1890 | `06da5e5366603822d75cd090e4a797b2dc8e3cd49badf35f57082516fc363377` |
| `customer-service-sop.json` | 2545 | `373f813469c6f088bfcca9702ae8904a1bf962a16430f77b85bb4a5ed7e2c554` |
| `fault-codes.json` | 2746 | `1f8f8d1c675f7143d85a536cf89e79c2a993c31329fa67cd67391b88068885a8` |
| `manual-cz-r1.md` | 2120 | `076504c08e6ce81a001469a0bddc3bebae8620e9785fc30f5b58e276e0e3b06c` |
| `manual-cz-r2.md` | 2149 | `5a54c630d70716fba68d4ac988ecf1910a7ec655726adbef154528c7d26a84a8` |

六文件知识清单的整体哈希为 `41948be4be64f6e1aeb49db7a5be30c5b5570b8dbbf7ee6c1bfa74bddf0f3303`；解析后 27 个知识单元的清单哈希为 `714538ce5b649f3acf566ac53f93dc9201f6a80d13430c7e3e293436d7e55161`。

## 运行时等价性

`evals/migration-equivalence-v1.json` 冻结 API、prompt、Provider 和知识身份。`evals/fixtures/migration-retrieval-equivalence-v1.json` 只包含有序单元 ID、逻辑文档/章节标识和正文哈希。由旧包与新包生成的 fixture 字节完全一致，SHA-256 为 `81c9a483f541a452c49d4d6f5bbae26582b95c27b829d5f35c81f4afdd335ef7`。

这只证明冻结案例的抽取等价；不能证明 Stage 12 质量，也不能据此发布 `product/0.1.0`。

## 精选公开资产哈希

以下哈希标识迁入公开开发候选的小型、可审查资产。它们是内容身份，不是一次新 Provider 运行的证据。

| 资产 | 字节数 | SHA-256 |
| --- | ---: | --- |
| `api/contracts/public-api-v1.json` | 1090 | `288b43c683e4da2afc469d9f86c10679f9b6ce59395fe1b74adf662a0db4348e` |
| `evals/public-regression-v1.json` | 4632 | `fca1ac41f47edc1beec33d4fa0244a74120a038c57b4b101c949a051be932e32` |
| `evals/migration-equivalence-v1.json` | 1927 | `ef47d7385b95a8bb78cb6f2cff864dba08da4988fa61140b131c8f9a54b3cfc8` |
| `evals/fixtures/migration-retrieval-equivalence-v1.json` | 29935 | `81c9a483f541a452c49d4d6f5bbae26582b95c27b829d5f35c81f4afdd335ef7` |
| `web/app/lib/replay-presets.json` | 4310 | `c1b24b010eacb7be6c8a7ac5dce01c1184541b7b8793dd21004b9029b1b7f28f` |

发布清单生成器会在构建时再次绑定这些运行时身份。只有成功的 GitHub 发布运行产生镜像摘要后，记录中才会加入对应摘要。

## 本地候选验证

- 一个使用 `--no-local` 的全新克隆重现了预期的六个提交主题，并通过完整历史扫描。
- 在 Git 外下载并按字节验证清单绑定的 BGE 模型后，70 项 API 测试全部通过，其中包含 16 个子测试。
- 干净执行 `npm ci` 后，lint、类型检查、15 项 Web 测试、四路由 `standalone` 构建和零漏洞审计全部通过。
- 从全新克隆构建了 Web、回放 API 和离线 `live` 镜像。Web 与回放容器均以非 root 用户和只读根文件系统运行；四个 Web 路由返回 `200`，API 健康检查报告 `replay_only`。
- 回放镜像既不包含模型，也不包含 Provider 密钥。`live` 镜像在禁用网络时运行八个公开检索检查，并保持 `provider_calls=0`。
- 第一次无上下文冷启动获得 `9/10`，发现当前状态中有一句过期的下一步描述。修正后的候选在用户预览前重新读取并获得 `10/10`。
- 用户要求候选仓库文档使用中文后，39 份面向人的 Markdown 完成中文收口；固定快照复核、全新克隆扫描和最终中文冷启动 `10/10` 再次通过。四份参与知识哈希的 Markdown 保持字节不变。

公开源码仓库已建立在 <https://github.com/suuny-ab/traceable-support-agent>。这些检查只关闭本地候选检查门；GitHub 仓库公开本身不代表已经完成正式路径切换、生产部署或用户验收。
