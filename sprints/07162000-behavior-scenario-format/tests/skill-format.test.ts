import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join } from 'path';

const REPO_ROOT = join(__dirname, '../../..');
const PROPOSER_SKILL = join(REPO_ROOT, 'harness-contract-proposer/SKILL.md');
const EVALUATOR_SKILL = join(REPO_ROOT, 'harness-evaluator/SKILL.md');

describe('[BEHAVIOR] 三段式剧本格式升级', () => {
  // ===== proposer SKILL.md 验证 =====

  it('proposer 三段式关键词存在（动作/预期观察/验证命令）', () => {
    const content = readFileSync(PROPOSER_SKILL, 'utf8');
    expect(content).toContain('动作');
    expect(content).toContain('预期观察');
    expect(content).toContain('验证命令');
  });

  it('proposer until-loop 等待预算范式存在', () => {
    const content = readFileSync(PROPOSER_SKILL, 'utf8');
    expect(content).toMatch(/until/);
  });

  it('proposer legacy 标记存在', () => {
    const content = readFileSync(PROPOSER_SKILL, 'utf8');
    expect(content).toMatch(/legacy/);
  });

  it('proposer 样例等待预算关键词存在（within 或 60s）', () => {
    const content = readFileSync(PROPOSER_SKILL, 'utf8');
    expect(content).toMatch(/within|60s/);
  });

  it('proposer version 升级到 9.14.x+', () => {
    const content = readFileSync(PROPOSER_SKILL, 'utf8');
    // version 必须是 9.14.x 或更高（9.14 ~ 9.99）
    expect(content).toMatch(/version: 9\.(1[4-9]|[2-9]\d)\./);
  });

  // ===== evaluator SKILL.md 验证 =====

  it('evaluator action/expected 字段新增（behavior_tests 新字段）', () => {
    const content = readFileSync(EVALUATOR_SKILL, 'utf8');
    expect(content).toContain('action');
    expect(content).toContain('expected');
  });

  it('evaluator 存量字段保留（command/exit_code/log_tail 不得被删除）', () => {
    const content = readFileSync(EVALUATOR_SKILL, 'utf8');
    expect(content).toContain('log_tail');
    expect(content).toContain('command');
    expect(content).toContain('exit_code');
  });

  it('evaluator version 升级到 1.26.x+', () => {
    const content = readFileSync(EVALUATOR_SKILL, 'utf8');
    // version 必须是 1.26.x 或更高（1.26 ~ 1.29）
    expect(content).toMatch(/version: 1\.2[6-9]\./);
  });
});
