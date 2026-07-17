/**
 * TDD Red Phase Tests — staging 预览闸进合同法律
 * Sprint: 07171650-staging-preview-gate
 * Task: 8589b916-9b71-4dd8-a986-76670229b06d
 *
 * 这些测试在 generator 改动 SKILL.md 之前必须 FAIL（TDD Red）。
 * 改完 SKILL.md 之后全部通过（TDD Green）。
 *
 * 执行方式（在 /workspace 根目录）:
 *   npx tsx --test sprints/07171650-staging-preview-gate/tests/skill-changes.test.ts
 * 或者直接用 bash 运行对应的 grep 断言。
 */

import * as fs from "fs";
import * as path from "path";
import { describe, it } from "node:test";
import assert from "node:assert/strict";

const WORKSPACE = path.resolve(__dirname, "../../..");
const PROPOSER_SKILL = path.join(
  WORKSPACE,
  "harness-contract-proposer",
  "SKILL.md"
);
const REPORT_SKILL = path.join(WORKSPACE, "harness-report", "SKILL.md");

function readSkill(filePath: string): string {
  return fs.readFileSync(filePath, "utf8");
}

// ================================================================
// B-1: harness-contract-proposer 版本 bump 至 9.16.0
// ================================================================
describe("B-1: proposer SKILL.md 版本 bump", () => {
  it("version 字段应为 9.16.0（改前 FAIL，改后 PASS）", () => {
    const content = readSkill(PROPOSER_SKILL);
    assert.match(
      content,
      /^version: 9\.16\.0/m,
      "FAIL B-1: harness-contract-proposer/SKILL.md version 字段不是 9.16.0，请 bump 版本"
    );
  });

  it("changelog 应含 9.16.0 条目", () => {
    const content = readSkill(PROPOSER_SKILL);
    assert.match(
      content,
      /9\.16\.0/,
      "FAIL B-1b: changelog 缺少 9.16.0 条目"
    );
  });
});

// ================================================================
// B-2: proposer SKILL.md 含 staging 预览闸段及三步逻辑
// ================================================================
describe("B-2: proposer SKILL.md 含 staging 预览闸段", () => {
  it("应含「staging 预览闸」段标题", () => {
    const content = readSkill(PROPOSER_SKILL);
    assert.ok(
      content.includes("staging 预览闸"),
      "FAIL B-2a: 无「staging 预览闸」段，请新增 ## staging 预览闸 段"
    );
  });

  it("应含「通知式」关键字（Cecelia 仓模式）", () => {
    const content = readSkill(PROPOSER_SKILL);
    assert.ok(
      content.includes("通知式"),
      "FAIL B-2b: 无「通知式」条款，请补充 Cecelia 仓通知式描述"
    );
  });

  it("应含「阻塞式」关键字（ZJ 仓模式）", () => {
    const content = readSkill(PROPOSER_SKILL);
    assert.ok(
      content.includes("阻塞式"),
      "FAIL B-2c: 无「阻塞式」条款，请补充 ZJ 仓阻塞式描述"
    );
  });

  it("应含「promote_after」字段（Cecelia 通知式时间戳）", () => {
    const content = readSkill(PROPOSER_SKILL);
    assert.ok(
      content.includes("promote_after"),
      "FAIL B-2d: 无 promote_after 字段引用"
    );
  });

  it("应含 BARK_URL 引用（步骤 C Bark 推送）", () => {
    const content = readSkill(PROPOSER_SKILL);
    assert.ok(
      content.includes("BARK_URL"),
      "FAIL B-2e: 无 BARK_URL 引用，请补充 Bark 推送步骤"
    );
  });
});

// ================================================================
// B-3: proposer SKILL.md 明确 autonomous 豁免，不被错误纳入
// ================================================================
describe("B-3: proposer SKILL.md autonomous 豁免", () => {
  it("应含 autonomous 豁免声明（正向）", () => {
    const content = readSkill(PROPOSER_SKILL);
    const hasExemption =
      /autonomous.*不受本规则|autonomous.*零回归|autonomous.*不强制|autonomous.*不受约束|dev_pipeline.*不受|不受.*autonomous/i.test(
        content
      );
    assert.ok(
      hasExemption,
      "FAIL B-3a: 无 autonomous 豁免声明，请在 staging 预览闸段明确写出豁免类型"
    );
  });

  it("不应含「autonomous 必须执行 staging」类强制语句（负向）", () => {
    const content = readSkill(PROPOSER_SKILL);
    const hasWrongRule =
      /autonomous.*必须.*staging|autonomous.*强制.*staging/.test(content);
    assert.ok(
      !hasWrongRule,
      "FAIL B-3b: autonomous 被错误纳入 staging 强制流程，请移除相关语句"
    );
  });
});

// ================================================================
// B-4: harness-report SKILL.md 版本 bump 至 6.9.0 且含 Step 5.5
// ================================================================
describe("B-4: harness-report SKILL.md 版本 bump + Step 5.5", () => {
  it("version 字段应为 6.9.0（改前 FAIL，改后 PASS）", () => {
    const content = readSkill(REPORT_SKILL);
    assert.match(
      content,
      /^version: 6\.9\.0/m,
      "FAIL B-4a: harness-report/SKILL.md version 字段不是 6.9.0，请 bump 版本"
    );
  });

  it("应含 Step 5.5（Phase A 飞书通知之后的新步骤）", () => {
    const content = readSkill(REPORT_SKILL);
    assert.ok(
      /5\.5/.test(content),
      "FAIL B-4b: harness-report 缺少 Step 5.5，请在 Phase A Step 5 之后新增"
    );
  });

  it("应含「promote_after」（Cecelia 仓写时间戳）", () => {
    const content = readSkill(REPORT_SKILL);
    assert.ok(
      content.includes("promote_after"),
      "FAIL B-4c: harness-report 无 promote_after 字段"
    );
  });

  it("应含「approval_required」（ZJ 仓写审批标记）", () => {
    const content = readSkill(REPORT_SKILL);
    assert.ok(
      content.includes("approval_required"),
      "FAIL B-4d: harness-report 无 approval_required 字段"
    );
  });

  it("应含 BARK_URL 引用（Step 5.5 Bark 推送）", () => {
    const content = readSkill(REPORT_SKILL);
    assert.ok(
      content.includes("BARK_URL"),
      "FAIL B-4e: harness-report Step 5.5 无 BARK_URL 引用"
    );
  });
});

// ================================================================
// B-5: harness-report Phase B db-update 调用不变（INV-4 回归）
// ================================================================
describe("B-5: harness-report Phase B 不变量（INV-4）", () => {
  it("Phase B 应仍含 db-update 调用", () => {
    const content = readSkill(REPORT_SKILL);
    assert.ok(
      content.includes("db-update"),
      "FAIL B-5: harness-report Phase B db-update 调用丢失，请检查是否误删"
    );
  });
});
