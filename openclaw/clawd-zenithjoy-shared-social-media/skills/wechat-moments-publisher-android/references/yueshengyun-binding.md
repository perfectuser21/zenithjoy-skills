# 悦升云端绑定与发布合同

## 飞书

- profile：`opc-main`
- 内容运营 Base：`JmoHbcewuakBX1shqsPc46gEnwI`
- 朋友圈内容：`tbliA1rVh0RkyWKc`
- 发布执行 Base：`S5fUbPqsDaefXNsZWMrcgsXYnCf`
- 发布任务：`tbltj67AMlX5IDUF`
- 发布效果：`tblSorYDJeJKGdok`
- 发布系统配置：`tblPVWJMVspH487g`

每次执行必须读取发布执行中心配置记录 `配置ID=moments-publisher-v2`。只有 `配置状态=启用` 且 `微信发布器状态=启用` 才允许进入手机动作。

## OpenClaw 与设备

- tenant：`yueshengyun`（规范租户可映射为 `zenithjoy`）
- agent：`zenithjoy-shared-social-media`
- node：`XIAN-M1-PHONE`
- phone profile：`yueshengyun-work`
- 预期 serial：`e6c7ef34`
- 预期 model：`RMX3478`
- 微信专用控制器预期路径：`/Users/xx-macmini/.local/bin/wechat-moments-adb`

Node 在线不等于手机、微信账号或控制器已就绪；必须每次预检。专用控制器不存在时只报告缺口，不尝试抖音控制器或裸 ADB。

## 发布门槛

- 任务 `审核状态=已批准`。
- 任务 `发布状态=待发布`，且没有成功回执。
- 正文与附件已经冻结。
- 微信账号标识非空且不等于“待手机端核验”。
- 系统配置的 Node、phone profile 与本合同一致。
- 用户本次明确要求立即发布，或可信调度信封明确授权计划发布。

部署验收只允许读取飞书和检查能力存在性，不打开微信、不创建发布任务、不点击发布。
