---
name: android-agent-onboarding
description: >
  重做/新建安卓客户端(安卓 agent)时的架构参考与踩坑 runbook。只要涉及安卓 agent 连中台、
  安卓客户端 APK 分发/下载、客户自助装机、无障碍(AccessibilityService)权限引导、深链(deeplink)
  扫码绑定、激活码/license 绑机、安卓 gradle 单测这些主题,都要先读本 skill——它记录了 ZenithJoy
  Line02 安卓自助装机绑定(PR#1154/#1155)沉淀的做法和血泪坑,能省掉重新踩一遍 android.net.Uri
  单测跑不了、无障碍不能静默开、APK 别甩 COS 直链、env 闸门、状态核实幻觉等一系列坑。
  即使用户没说"skill",只要在做安卓客户端相关的开发,就应该参考本 runbook。
---

# 安卓 Agent 客户端自助装机绑定 —— 架构参考 + 踩坑 runbook

> 这不是执行脚本,是**做安卓客户端时的地图和避坑指南**。ZenithJoy Line02 用它把"客户装 app
> 就全搞定"从 0 做到零命令行客户流程(PR#1154 深链扫码绑定 + PR#1155 APK 从自家域名直下)。
> 重做安卓客户端前先读一遍,能少走弯路。

## 核心心法

**产品形态 = 客户零命令行自助**。客户只在网页 + 手机上点/扫,绝不碰 adb/scrcpy/命令行。
adb 装包、adb 授权无障碍、手写 SharedPreferences 绑定——这些都是**开发者调试土办法,不是客户流程**。
凡是"让我教客户敲命令"的方案,一律推翻重想成"app 引导用户点几下"。

**四端各一薄片,复用现有件**。别从零搭:license 体系、`POST /api/agent/register` 绑机、心跳、
机器列表在线状态、桌面 AgentDownloadPage 下载页——安卓这一刀本质是给现有 agent 链加一个
`android` 分支 + 一个安卓下载页,不是新建一套。

---

## 架构:四端

### 1. 后端 —— APK 分发(从自家域名直下,不暴露 COS)

**关键决策:别把 COS 直链甩给客户**。客户点下载应走我们自己域名,COS 只是后端文件源、客户无感。

- `GET /api/agent/install-pack/android`(session 鉴权,无→401):返
  `{ apk_url, deeplink, license_key, version }`。`apk_url` = 下面 download 端点的**相对路径**
  (`/api/agent/install-pack/android/download`),不是 COS 直链。
- `GET /api/agent/install-pack/android/download`(session 鉴权):流式回传 APK。
  首次从 COS 拉一份缓存到本地,之后本地直出:
  ```
  cachePath = env.ANDROID_APK_CACHE_PATH || os.tmpdir()/zenithjoy-agent.apk
  若 !existsSync(cachePath):
    tmp = cachePath + '.tmp-' + pid           # 并发各写各的临时文件
    downloadFileToPath(COS_URL, tmp)          # 失败 → 502 APK_FETCH_FAILED
    fs.renameSync(tmp, cachePath)             # 原子落地,防并发半文件
  res.setHeader('Content-Type','application/vnd.android.package-archive')
  res.setHeader('Content-Disposition','attachment; filename="zenithjoy-agent.apk"')
  fs.createReadStream(cachePath).pipe(res)    # 记得挂 .on('error')(桌面 /download 有,别漏)
  ```
- 鉴权照抄桌面 `/download`:`auth.api.getSession({ headers: fromNodeHeaders(req.headers) })`,
  无 userId → 401 `{ok:false,code:'UNAUTHORIZED'}`。
- CI(`android-agent-ci.yml`)用 **coscmd** 把签名 Release APK 传 COS:
  bucket `zenithjoy-static-1333590468`,endpoint `cos.accelerate.myqcloud.com`,
  path `/install-pack/android/zenithjoy-agent.apk`,`--force` 覆盖,`if: github.ref=='refs/heads/main'`
  (PR 不传,避免污染)。secrets `COS_SECRET_ID`/`COS_SECRET_KEY` 已配。

### 2. 前端 —— 安卓下载页

照抄桌面 `AgentDownloadPage` 模式,精简为:
- 「下载 APK」按钮 `href={data.apk_url}`(后端改 apk_url 值前端自动跟随,**前端可零改**)。
- **绑定二维码**:`import { QRCodeSVG } from 'qrcode.react'`(dashboard 已有此依赖,**零新增**),
  `value={data.deeplink}`。
- 激活码明文 + 复制按钮(扫码扫不动/未装 app 的兜底,客户可 app 内手输)。
- 安装授权图文引导(下载→装→开无障碍→扫码绑定→登号)。
- 入口:AreaHub 磁贴「下载安卓客户端」→ `/dashboard/android`。

### 3. 安卓 app —— 无障碍引导 + 深链绑定

**① 无障碍权限(最大坑,见下方铁律)**:app 检测未开 → 首屏引导卡片 → 跳系统设置让用户开。
- 检测:`isServiceEnabled(enabledSetting, pkg, serviceClass)` **纯函数**,解析
  `Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES`(格式 `pkg/cls:pkg/cls`,按 `:` 拆比对)。
- 引导:未开 → 显眼卡片 + 按钮 `startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))`。
- `onResume` 复检刷新(用户从系统设置返回即更新状态)。

**② 深链扫码绑定(免手输激活码)**:
- 网页二维码编码 `zenithjoy://bind?license=<key>&api=<wss_url>`。
- 手机**系统相机/微信扫一扫**扫它 → 唤起 app(不用自己做相机扫码器)。
- `AndroidManifest.xml` 的 MainActivity 加 intent-filter:
  `action VIEW` + `category DEFAULT` + `category BROWSABLE` + `data scheme="zenithjoy" host="bind"`。
- `MainActivity.onCreate` 解析 `intent.data` → `parseBindDeepLink` 取 license/api →
  写 `config.licenseKey`/`config.apiUrl` → `startAgentService()` → 走现有 register 自动绑定。
- 深链的 `api` 参数传 **wss url**(安卓 `deriveHttpBase()` 会 `wss→https` 再做 register)。

**③ license 绑定(复用)**:输/灌 licenseKey → `POST /api/agent/register` → 绑租户。
`tenantId` **不信设备上报**,服务端按 agent_id 反查。

### 4. CI —— 见上方后端第 4 点(coscmd 上传 + smoke)

---

## 铁律 / 踩坑(血泪,重做时必看)

- **JVM 单测(`gradle testDebugUnitTest`)绝不能碰 Android framework 类**(`android.net.Uri`/
  `Settings` 等在 JVM 跑不了)。深链解析 `parseBindDeepLink` 必须**纯 Kotlin 字符串 +
  `java.net.URLDecoder`**;`Settings.Secure` 只放在带 `context` 的函数(不进单测),把可测的纯逻辑
  单独抽成函数。否则单测直接编译/运行失败。

- **无障碍权限是安卓硬限制**:任何 app 都不能静默开启 AccessibilityService(除非 root)。正常
  产品**只能引导用户去系统设置手动开一下**(抖音自动化/微信辅助类 app 都这么做)。别妄想 adb
  `settings put`/`pm grant` 自动开——那是开发者土办法,不是客户能走的路。

- **APK 别把 COS 直链甩客户**:后端端点缓存中转,客户全程自家域名(见后端第 1 点)。

- **env 接缝闸门**:`apps/api` 里任何新读的 `process.env.X` 必须在 `apps/api/src/env-registry.ts`
  三选一登记(`OPTIONAL_ENV` 附 reason / `REQUIRED_ENV` / `FRAMEWORK_ENV`),否则 `env-registry.test`
  红 → L4 Runtime(required)挂,合不进。新加缓存路径 env、COS url env 都要登记。

- **CI Config Audit**:改了 `.github/workflows/**` → **PR 标题**必须含 `[CONFIG]` 或 `[INFRA]`
  (是 PR 标题,不是 commit),否则 Config Audit fail。

- **8 位分支名**:worktree 脚本可能生成 10 位时间戳分支(`cp-0707214406-...`),CI Branch Name
  Check 拒。push 前 `git branch -m` 改成 8 位(`cp-07072144-...`)。

- **smoke 要真接进 required gate**:光建 smoke 文件不够——它可能只被 report-only 的 glob runner
  跑(`continue-on-error`,不挡合并)。必须**显式**写进 `ci-l4-e2e-smoke.yml` 的
  `smoke-api-contract` job(required gate),CI 红才能真挡。

- **状态核实死规矩(反复被自己的幻觉坑)**:查 PR/CI/push 状态**只信 `gh api` + python 解析**。
  `git push` 的"成功"回显、`gh pr checks` 文本、`git ls-remote` 都可能不可信或混新旧 run。
  push 后**必须** `gh api repos/<O>/<R>/git/refs/heads/<branch> --jq .object.sha` 复核 ref sha
  是否 = 本地 HEAD;查合并用 `gh api repos/<O>/<R>/pulls/<N>` 的 `merged` 字段;查某 commit 结论用
  `gh api repos/<O>/<R>/commits/<完整sha>/check-runs`。所有网络操作用 `dangerouslyDisableSandbox`。

- **真机验收前卸载旧包清数据**:测试机之前装过 debug 包 → 旧 `SharedPreferences` 里的
  `registerApiUrl` 残留会**盖过深链带来的新 api 地址** → 绑错环境。验收前先卸载清数据(全新装机前提)。

- **required 只 6 个 gate**:L3 Code / L4 E2E / L4 Runtime / Integration / L2 Consistency /
  WeChat CS Gate。L1 Process Gate(Config Audit / TDD Commit Order / gitleaks)**非 required**,
  fail 不挡 auto-merge。gitleaks 命中文档里的 "token"/"keystore" 字样 = 误报。TDD Commit Order
  在你删掉 RED test 文件(合并 sibling 测试)时会误判 —— 它要求 RED test 文件在 HEAD 仍存在。

---

## 代码位置(ZenithJoy repo 参考实现)

- 安卓:`services/agent-android/app/src/main/kotlin/com/zenithjoy/agent/`
  - `MainActivity.kt`(深链分支 + 无障碍 banner + onResume 复检)
  - `onboarding/BindDeepLink.kt`(parseBindDeepLink 纯字符串解析)
  - `onboarding/AccessibilityGuide.kt`(isServiceEnabled 纯函数 + collectServiceEnabled)
  - `AndroidManifest.xml`(MainActivity 深链 intent-filter)
- 后端:`apps/api/src/routes/agent-install-pack.ts`(/android + /android/download 端点)、
  `apps/api/src/env-registry.ts`(env 登记)、`apps/api/src/lib/download-file.ts`(downloadFileToPath)
- 前端:`apps/dashboard/src/pages/AndroidDownloadPage.tsx`
- CI:`.github/workflows/android-agent-ci.yml`(coscmd 上传)、
  `.github/workflows/scripts/smoke/android-onboarding-smoke.sh`
- 沉淀来源:PR#1154(深链扫码自助装机绑定)+ PR#1155(APK 从 staging 自家域名直下)
