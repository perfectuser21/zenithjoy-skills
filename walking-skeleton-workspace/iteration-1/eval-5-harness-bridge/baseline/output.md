# 关于"直接调 sprint-planner"的建议

不建议直接进 sprint-planner，先做 walking skeleton。

## 为什么先别开 sprint

你描述的是"4 个 ws 并行推进 license 系统"，但 license 这件事本身在 ZenithJoy 现在的代码里还**没有一条端到端跑通的最小链路**。从 git log 看，最近的 PR 是 admin-users（PR-A）、free-tier-onboarding（PR-B）、credits-foundation（PR-C），都是基础件，license 的 API → DB → Dashboard → admin 后台 → CI smoke 这条整链没人走过。

这种状态下直接拆 4 个 workstream 并行，会出现两个典型问题：

1. **集成假设错位**：后端 API ws 假定的 license schema、Dashboard ws 假定的字段、admin 后台假定的权限模型，三方在 sprint 中段才发现对不上，返工成本极高。
2. **CI 部署 ws 没东西可部署**：CI ws 通常需要前面三个 ws 各产出一个可冒烟的产物，并行启动的话 CI ws 前两周基本空转。

## 推荐顺序

**先 walking skeleton（1-2 天，单人）**：

- 一个最小 license 表（id / tenant_id / plan / status / expires_at）
- 一个 `GET /api/licenses/me` 端点，返回当前 tenant 的 license
- Dashboard 一个只读卡片显示 plan + 到期日
- admin 后台一行表格能看到所有 tenant 的 license
- 一个 smoke.sh：注册 → 拿 license → 卡片渲染 → admin 可见

这条链路跑通后，schema、字段名、权限边界、smoke 形态都被钉死，**再开 sprint 拆 4 个 ws 才有共同基线**。

## 然后再 sprint-planner

skeleton 落地后，调 sprint-planner 拆：
- 后端 API ws：补 CRUD、续费、降级、webhook
- Dashboard ws：升级流程、发票、用量
- admin ws：批量操作、license 调整审计
- CI ws：迁移自动化、灰度发布、回滚演练

每个 ws 都在 skeleton 上长肌肉，而不是在空地上盖楼。这样 sprint 才不会在第二周陷入"等对方接口"的瘫痪。

**结论**：先花 1-2 天做 walking skeleton，再调 sprint-planner，整体反而更快。
