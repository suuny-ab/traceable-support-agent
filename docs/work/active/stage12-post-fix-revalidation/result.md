# 结果

> 状态：`preflight`

## 执行前身份

- 候选：`night-20260802@df01968c56350626544ca4acc4ed88cf13dfd337`。
- runner：`tools/stage12_eval.py` 与 `origin/main` 为同一 Git blob
  `132328043321a550b3ff480f961644e11f7a9220`。
- 模型：`deepseek-v4-pro`；prompt 集合 SHA-256
  `108ab9aae60eb86806383cc2fea4511d358955f50503531e0da2e82be1ba8584`。
- 私有未见集：24 题，SHA-256
  `7d73073cd0227b0ced81398fcbadc7e5f85867a633a9654d82bd0b516c358ab0`；留在 Git 外。

## Provider 前预检

- 冻结检查通过：24 题与上述 SHA 精确一致。
- Stage 12 runner 定向测试：`13 passed`。首次测试因隔离 worktree 缺本地 BGE 缓存而在
  用例装配阶段失败；随后按模型清单逐文件大小 / SHA-256 核验主工作树 7 文件缓存并只读复用，
  未下载、未改代码或资产，Provider 调用 0。
- 旧响应离线回归完成 24 题，Provider 调用 0；它只证明当前装配可运行，不是本次真实复验结果。

真实复验尚未执行；本文件将在唯一一次运行后用聚合结果更新。
