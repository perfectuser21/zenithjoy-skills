# 快手内容发布功能 — 分析与规划

## 现状摸底

快手发布其实**已经有相当多基础**，不是从零开始：

### 已有的部分

**publisher 脚本层**（`services/agent/publishers/kuaishou-publisher/`）：
- `publish-kuaishou-image.cjs` — 图文真发（CDP UI 自动化）
- `publish-kuaishou-image-dryrun.cjs` — 图文 dry-run（登录验证，不点发布）
- `publish-kuaishou-api.cjs` — 图文新 API 方案（CDP 提取 Cookie → HTTP 直调 API，更稳定）
- `publish-kuaishou-video.cjs` — 视频真发（CDP + SCP 到 Windows）
- `utils.cjs`, `check-kuaishou-session.cjs`

**Agent handler 层**（`services/agent/src/handlers/kuaishou-publish.ts`）：
- `handleKuaishouPublish` 已实现，但目前**只走图文 dryrun**，不支持视频路由

**API 路由层**（`apps/api/src/routes/agent.ts`）：
- `POST /api/agent/test-publish-kuaishou` 已注册
- agent 的 `publish_request` 消息已路由到 `handleKuaishouPublish`

**平台注册**：kuaishou 在 Dashboard 类型定义、平台列表、发布统计等多处已注册为合法平台。

### 缺口在哪里

对比抖音（已完整支持 image / video / article 三种类型），快手目前的 handler 有两个关键问题：

1. **handler 硬编码只走 image dryrun**：`kuaishou-publish.ts` 的 `SCRIPT_PATH` 写死了 `publish-kuaishou-image-dryrun.cjs`，没有按 `content_type` 路由到视频或真发脚本。
2. **没有 video dryrun 脚本**：`publish-kuaishou-video.cjs` 存在（真发版），但没有对应的 `publish-kuaishou-video-dryrun.cjs`（安全验证用）。
3. **handler 没有 `KuaishouPublishType` 类型区分**：不像 `douyin-publish.ts` 有 `type: 'video' | 'image'` 的分发逻辑。
4. **`resolveScriptPath` 有 bug**：用的是旧版 `beside || dev` 写法（非空字符串永远 truthy），不会正确 fallback，和抖音修复后的版本不一致。

---

## 要做什么

### 目标

让快手发布功能对齐抖音的完整度：
- 图文发布：dryrun（CI 验证）+ 真发（客户机）
- 视频发布：dryrun（CI 验证）+ 真发（客户机）
- 类型路由：handler 按 `content_type` 正确分发脚本

### 不在本次范围

- 快手文章（article）类型：快手创作者中心目前没有类似抖音图文文章的独立入口，暂不支持
- Dashboard UI 改动：`ContentFactoryPage` 等已有快手选项，不需要新增

---

## 实施计划

### commit-1：失败的 E2E smoke（定义"完成"）

新建 `.github/workflows/scripts/smoke/kuaishou-publish-smoke.sh`：

```bash
# 验证快手发布 handler 能正确路由 image / video 类型
# 验证 dryrun 模式不调真实发布 API
# 用 resolveKuaishouScriptPath 函数验证路径解析
```

同时新建 `services/agent/publishers/kuaishou-publisher/__tests__/kuaishou-publish-handler.test.ts`：
- type=image → `publish-kuaishou-image-dryrun.cjs`（dryrun 模式）
- type=image → `publish-kuaishou-image.cjs`（真发模式）
- type=video → `publish-kuaishou-video-dryrun.cjs`（dryrun 模式）
- type=video → `publish-kuaishou-video.cjs`（真发模式）

### commit-2：实现

**1. 新增 `publish-kuaishou-video-dryrun.cjs`**

参考 `publish-douyin-video-dryrun.cjs` 的结构：
- CDP 连接 Windows Chrome（端口 19223）
- 验证已登录快手创作者中心
- 截图当前发布页
- 拦截 `/rest/cp/works/v1/video/publish` 等真发 API
- 不上传视频，不点发布按钮

**2. 重构 `kuaishou-publish.ts`**

对齐 `douyin-publish.ts` 的结构：

```typescript
export type KuaishouPublishType = 'video' | 'image';

// 修复 resolveScriptPath（加 fs.existsSync 检查，对齐抖音修复版）
function resolveScriptPath(...segs: string[]): string {
  const explicit = process.env.ZENITHJOY_AGENT_ROOT;
  if (explicit) {
    const p = path.join(explicit, ...segs);
    if (fs.existsSync(p)) return p;
  }
  const beside = path.join(path.dirname(process.execPath), ...segs);
  if (fs.existsSync(beside)) return beside;
  const dev = path.resolve(__dirname, '..', '..', ...segs);
  if (fs.existsSync(dev)) return dev;
  return dev;
}

// 按 type + REAL_PUBLISH 选脚本
export function resolveKuaishouScriptPath(
  opts: { type: KuaishouPublishType },
  env = process.env,
): string {
  const isReal = env.ZENITHJOY_AGENT_REAL_PUBLISH === '1' || 
                 env.ZENITHJOY_AGENT_REAL_PUBLISH === 'true';
  if (opts.type === 'video') {
    return resolveScriptPath(
      'publishers', 'kuaishou-publisher',
      isReal ? 'publish-kuaishou-video.cjs' : 'publish-kuaishou-video-dryrun.cjs',
    );
  }
  // image（默认）
  return resolveScriptPath(
    'publishers', 'kuaishou-publisher',
    isReal ? 'publish-kuaishou-image.cjs' : 'publish-kuaishou-image-dryrun.cjs',
  );
}

// handleKuaishouPublish 从 content 读 type，路由到正确脚本
export async function handleKuaishouPublish(
  taskId: string,
  content: KuaishouContent & { type?: KuaishouPublishType },
  emit, makeMsg,
): Promise<void> {
  const type = content.type ?? 'image';
  const scriptPath = resolveKuaishouScriptPath({ type });
  // ... 其余 spawn 逻辑不变
}
```

**3. 更新 `services/agent/src/index.ts` 的消息路由**

确认 `publish_request` 携带的 `content.type` 能透传到 handler（目前已有，但需验证 type 字段是否在 payload 里正确传递）。

**4. 更新 `apps/api/src/routes/agent.ts` 的 test-publish-kuaishou 端点**

增加可选 `type` 参数（image / video），方便 Dashboard 调试页触发视频 dryrun：

```typescript
agentRouter.post('/test-publish-kuaishou', (req, res) => {
  const type = req.body?.type ?? 'image'; // 新增
  // ...
  const sent = sendToAgent(agent.agentId, makeMsg('publish_request', {
    platform: 'kuaishou',
    content: { ...content, type }, // 透传 type
    agent_id: agent.agentId,
  } as any, taskId));
```

---

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `services/agent/publishers/kuaishou-publisher/publish-kuaishou-video-dryrun.cjs` | 新增 | 视频 dryrun 脚本 |
| `services/agent/src/handlers/kuaishou-publish.ts` | 修改 | 类型路由 + resolveScriptPath 修复 |
| `apps/api/src/routes/agent.ts` | 修改 | test-publish-kuaishou 支持 type 参数 |
| `services/agent/publishers/kuaishou-publisher/__tests__/kuaishou-publish-handler.test.ts` | 新增（commit-1 先写）| 类型路由单元测试 |
| `.github/workflows/scripts/smoke/kuaishou-publish-smoke.sh` | 新增（commit-1 先写）| E2E smoke |

---

## 注意事项

1. **安全默认**：所有新脚本默认走 dryrun，`ZENITHJOY_AGENT_REAL_PUBLISH=1` 才真发，与抖音保持一致。
2. **API 方案 vs UI 方案**：图文有两个脚本（`publish-kuaishou-api.cjs` 更新方案，`publish-kuaishou-image.cjs` 旧 UI 方案）。handler 应优先用 API 方案（更稳定），但 dryrun 验证两者都要覆盖。建议本次先对齐 dryrun 脚本，API vs UI 的选择可以作为后续加厚（thickness 升级）。
3. **Windows 环境依赖**：视频发布需要 SCP 到 Windows + CDP 到 xian-rog，CI smoke 只能验证脚本路由逻辑，不能真实执行发布流程。

---

## 当前分支状态

当前在 `cp-20260525-article-dryrun-fix` 分支，该分支主要处理抖音 article dryrun 修复。快手功能应该开一个新分支 `cp-kuaishou-full-publish` 来做，避免与当前工作混合。

需要我开始动手写第一个 commit（失败的 E2E + 单元测试）吗？
