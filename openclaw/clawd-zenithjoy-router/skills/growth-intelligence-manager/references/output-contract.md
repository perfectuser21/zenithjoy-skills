# 情报流水与日报契约

## 飞书资源

- 企业 Base：`H3OrbAH49aLNebs7XvOcpS1enec`
- 企业档案：`ZomPdBBrPo1LPOxCxqCcPCV3nHh`
- 情报流水表：`tblf0fWMbQQOR9Tf`
- 日报文档：`I9Z0dTcA4o79JMxSz5OczZtinOe`

## 已验证的读写路径

当前租户通过秋米 bot 使用飞书官方 Bitable v1 接口：

- 读：`GET /open-apis/bitable/v1/apps/H3OrbAH49aLNebs7XvOcpS1enec/tables/tblf0fWMbQQOR9Tf/records`
- 批量写：`POST /open-apis/bitable/v1/apps/H3OrbAH49aLNebs7XvOcpS1enec/tables/tblf0fWMbQQOR9Tf/records/batch_create`

不要改走新版 `lark-cli base +record-list`：当前应用没有该命令要求的 `base:record:read` scope，而 v1 读写已经实测成功。这是接口兼容选择，不是登录问题。

## 去重键

优先使用标准化原文 URL；URL 缺失时使用“来源名称 + 原文标题 + 发布日期”。重复信息保留权威度最高、最接近一手来源的一条。

## 日报结构

1. 今日结论：三条以内。
2. 国内重点。
3. 国际重点。
4. 候选关键词。
5. 与产品、客户或内容的连接。
6. 建议动作与接收 Agent。
7. 来源统计、企业资料版本和生成时间。

## 状态

- `候选`：已核验但未进入日报。
- `入选日报`：进入当天正式日报。
- `待核验`：缺少一手来源或日期。
- `已归档`：重复、过期或不再相关。

公开网络信息不得直接更新企业档案中的“已确认事实”。
