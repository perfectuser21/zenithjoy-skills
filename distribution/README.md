# 技能维护源与业务仓引用

技能正文与纯参考资料只在此仓维护。`catalog.json` 按来源仓库记录原路径、中心路径、SHA-256 与来源版本；同名但不同内容的业务版本保留来源路径，不覆盖现有技能。

业务仓提交 `.skills-source.json`，固定本仓完整 commit 和 profile。业务原路径是被 Git 忽略的生成文件；加载器校验全部源文件后再还原，发现本地修改就拒绝覆盖。Windows 与部署使用普通文件，不依赖符号链接。

```bash
# 在业务仓运行；使用已有 Git 认证读取私有技能仓
python3 scripts/skills-source.py install
python3 scripts/skills-source.py verify
```

运行脚本、发布器、设备控制器及依赖业务目录的代码保留在业务仓，清单 `runtime_files` 逐项列出。技能的执行目录仍为 `execution_directory` 指定的业务仓原目录；直接从中心查看技能时，先还原并切换到该目录运行命令。

`retired-in-shared-catalog` 表示该名称已在共享技能目录退役。迁移只保存业务兼容版本，不重新注册、启用或自动安装为全局技能。现有 `_archive`、有效根技能与业务来源版本的合并应分别评审。

更新时先改本仓对应中心文件与清单校验和，验证后提交；再更新业务仓锁定的 commit。CI 用 `SKILLS_SOURCE_SSH_KEY` 只读 deploy key 拉取固定版本，不随 main 自动更新。禁止在业务生成文件上维护正文。

`retired_files` 精确记录已停止向业务仓物化的历史文件及其来源摘要；这些源文件保留并继续校验字节，不进入 `files` 安装清单。Cecelia 的 `/dev` 正文还原到 `.claude/skills/dev/SKILL.md`，使用当前中央 `dev/SKILL.md`，不再恢复旧 Engine/Quality 目录。

固定版本首次下载只使用明确的 `SKILLS_SOURCE_SSH_KEY` 文件身份，禁用交互和 ssh-agent，不回退到 HTTPS 或其他凭据。连接超时为 10 秒，单次 fetch 进程上限 35 秒；暂态连接故障或同身份已成功过的间歇公钥拒绝最多尝试 3 次，间隔 1、2 秒，总 fetch 预算不超过 108 秒。每次请求始终使用同一个完整 commit、私钥临时文件及严格 host-key 校验。已缓存的固定对象仍可不带网络凭据本地还原。

私钥格式、host-key、仓库不存在与固定对象不存在属于永久错误，立即失败；重试耗尽仍输出原失败原因并非零退出。源 loader 校验、install 或 verify 失败不进入网络重试。`test_bootstrap_fetch.py` 以真实 bootstrap 子进程和真实临时 Git 对象覆盖这些边界，网络传输仅由本地 fixture 接管，不接触真实凭据。

首次 fetch 前诊断临时身份，只输出派生公钥的类型和 SHA256 fingerprint；不输出公钥、私钥或任何密钥正文片段。`ssh-keygen -y -P ''` 关闭标准输入且限时 5 秒；诊断不可用时仅报告固定提示，实际 fetch 与后续字节校验仍按原规则成功或失败。SSH 使用 `-F /dev/null`，不继承 runner 的用户配置。
