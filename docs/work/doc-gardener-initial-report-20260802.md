# 文档园丁首次扫描报告

> 日期：`2026-08-02`
>
> 基线：`origin/main@3c981c6d2c1aa711048b8638e78041ff4cd7ae50`
>
> 性质：治理工具首次结果；只对活动文档作启发式扫描，不是产品质量或生产健康证明。

## 扫描合同

命令：

```powershell
python tools/doc_gardener.py --format markdown
```

园丁以 `PROJECT.md` 和 `docs/status.md` 为 canonical 输入，扫描 `README.md`、
`PUBLIC_CONTEXT.md`、`ROADMAP.md`、`docs/engineering/`、`docs/product/` 与
`docs/work/README.md`。状态月报、已完成工作和 ADR 等历史材料不作为活动文档扫描面；
`migration-record.md` 虽是历史记录，但仍在工程规则族中，因此只把没有时间锚的相对措辞列为
人工判断项。

默认模式只读、只告警且退出成功；`--fail-on stale` / `--fail-on any` 仅供治理专项使用。

## 首次结果（修复前）

canonical：

- `release_sha=3c981c6d2c1aa711048b8638e78041ff4cd7ae50`
- `live_experience=available`
- `product/0.1.0=not_released`
- `state=candidate`

扫描 18 个活动文档，得到 `stale=2`、`review=1`：

| 级别 | 规则 | 首次位置 | 处理 |
| --- | --- | --- | --- |
| stale | `stale_release_sha` | `README.md:11` | 已修：移除会随每次部署腐坏的旧短 SHA，保留实时健康入口 |
| stale | `delivered_work_described_as_future` | `PUBLIC_CONTEXT.md:13` | 已修：按 `PROJECT.md` 改为四页、固定示例、公开实时演示和仓库展示均已交付 |
| review | `ambiguous_current_in_historical_doc` | `docs/engineering/migration-record.md:13` | 未改：迁移范围中的“当前产品合同”可能指迁移时点，也可能指保留范围；机器不能无损裁决 |

## 修复后复扫

同一命令在修复后仍扫描 18 个活动文档，结果为 `stale=0`、`review=1`。保留的 review 项不会
阻断构建，也不会被工具自动改写；若以后修改迁移记录，应由人确认后改成“迁移时产品合同”
或“现行产品合同”之一，并明确时间语义。

## 能证明与不能证明

本结果证明：已登记的精确 SHA 漂移、当前公网 live / replay 冲突和一个已交付事项仍被写成
未来工作时，工具能稳定列出；两处确定腐坏已按 canonical 来源修复。

本结果不证明：`PROJECT.md` / `docs/status.md` 自身一定及时，也不理解任意自然语言矛盾；默认
非阻断 CI 只提供持续可见性。生产身份仍须通过公网 `/api/v1/health` 独立核验。
