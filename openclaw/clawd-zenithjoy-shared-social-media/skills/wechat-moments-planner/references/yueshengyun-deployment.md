# 悦升云端部门隔离部署绑定

- tenant：`yueshengyun`（规范租户可映射为 `zenithjoy`）
- Feishu profile：`opc-main`

## 企业资料中心

- Base：`ZQG7bLznUaqMYKsGYsyc4k70n2f`
- 企业档案：`tbl0EzVTEO146Vmp`
- 产品服务：`tblK35zSZ0mhCN2C`
- 目标客户画像：`tblS6c0nVO3AcIfz`

## 销售 CRM

- Base：`BDmIbprBnaN6mjsNi48cOZpznRe`
- 客户 CRM：`tblaH9GqaES7PBVs`
- 沟通分析记录：`tblJtzX3ESrR98hL`
- CRM 统计快照：`tblVHZFx5vebX44S`

客户姓名、微信昵称、联系方式和沟通摘要只保存在销售 CRM。传给内容运营的快照必须聚合并脱敏，不得包含可识别个人的信息。

## 内容运营中心

- Base：`JmoHbcewuakBX1shqsPc46gEnwI`
- 客户洞察快照（脱敏）：`tblfDzj2Ihk0sUTd`
- 朋友圈内容：`tbliA1rVh0RkyWKc`
- 内容规划配置：`tblDDS5pmhpte3OY`
- 有效配置：`配置ID=moments-content-v2`

## 发布执行中心

- Base：`S5fUbPqsDaefXNsZWMrcgsXYnCf`
- 发布任务：`tbltj67AMlX5IDUF`
- 发布效果：`tblSorYDJeJKGdok`
- 发布系统配置（管理员）：`tblPVWJMVspH487g`
- 有效配置：`配置ID=moments-publisher-v2`

每次运行先按业务域读取对应 Base 和字段 schema。正式文案只写入内容运营中心。只有审核状态为“已批准”且用户明确要求移交发布时，才把冻结正文和附件写入发布执行中心。微信账号仍为“待手机端核验”或发布器状态不是“启用”时，只允许生成、保存和审核，禁止手机动作。实际手机发布由 `$wechat-moments-publisher-android` 执行。
