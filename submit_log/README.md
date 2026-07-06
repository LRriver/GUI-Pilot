# submit_log

这个目录只保存研发证据，不参与 Agent 运行，也不会被放进比赛提交 zip。

当前保留的日志是少量代表版本：

- `v7c_log.md`
- `v9_log.md`
- `v12a_log.md`
- `visible_case_regression.md`

保留原因：

- 记录哪些任务家族在强版本中稳定通过。
- 记录线上失败模式，避免后续修改重新引入同类退化。
- 解释 `submission/src/agent.py` 中部分规则为什么必须写得很窄。

如果只需要最小源码仓库，可以安全删除这个目录。若还要继续冲榜或复盘 Agent 设计，建议保留它作为回归笔记。
