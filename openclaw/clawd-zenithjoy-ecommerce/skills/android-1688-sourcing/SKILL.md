---
name: android-1688-sourcing
description: 1688 安卓真机选品 + 商品素材采集（✅ 2026-09-11 金诺机全链路实测：登录含风控 → 搜索 → 商品页 → 图集截图 → 裁剪）。
  设备通道/截图回传/中文输入等底座见 android-publish。
  触发场景：1688 选品 / 找货源 / 采集商品图 / 跨境电商选品 / 1688 登录 / 阿里巴巴 App 自动化。
---

# 1688 安卓真机选品采集

包名 `com.alibaba.wireless`。设备通道、截图回传、ADBKeyboard 中文输入见 **android-publish 底座**，本文不重复。

## 为什么走真机 App 而不是网页版

网页版图片能直接拿 `<img src>`，但**限流风险高**；真机 App 是已验证过的稳定通道（跟抖音/快手那套同一套基础设施），
代价是图片拿不到直链、只能截图。

**实践结论：截图完全够用**——下游要过 AI 去水印重绘（见 `codex-image-cleanup`），原图直链的画质优势没有意义。

## 登录（一次性，之后保持登录态）

⚠️ **无 SIM 卡设备不能走"一键登录"**（依赖运营商本机号码校验，`gsm.sim.state=ABSENT` 时必然弹回登录页）。只能走验证码：

| # | 动作 | 锚点 / 参考坐标（1200×2664） | 说明 |
|---|---|---|---|
| 1 | 同意隐私弹窗 | `wave_resend_sure` | 首次启动 |
| 2 | 允许通知 | `permission_allow_button` | 系统弹窗 |
| 3 | 切到验证码登录 | `phone_login_option` [52,2277][600,2487] | 别点一键登录 |
| 4 | 再次同意协议弹窗 | 文本"同意" | 会重复弹 |
| 5 | 输手机号 | `aliuser_login_mobile_et` | |
| 6 | 勾协议 | `check_image` [64,1873][116,1925] | 不勾发不出验证码 |
| 7 | 获取验证码 | `aliuser_login_send_smscode_btn` | 成功后显示"56S后重新获取" |
| 8 | 输验证码 | `aliuser_register_sms_code_et` | 需真人实时提供 |
| 9 | 登录 | `aliuser_login_login_btn` | |
| 10 | **风控：身份证验证** | WebViewActivity「身份验证」 | 老号新设备登录会触发，要输实名身份证号 |

第 10 步不是每次都有——手机号若曾实名绑定过阿里账号就会触发。**需真人提供身份证号**，AI 不能编。

## 选品与采集

`<搜索框>` 每次用 `uiautomator dump` 现场定位坐标，不像登录流程固定——搜索入口位置随进入路径变化，不可写死坐标。`<serial>` 用 `adb devices` 列出的真实设备序列号，与 `android-publish` 底座的设备选择约定一致。

```bash
# 搜索
adb shell input tap <搜索框>             # SearchInputActivity，坐标现场用 uiautomator dump 定位
adb shell ime set com.android.adbkeyboard/.AdbIME
adb shell am broadcast -a ADB_INPUT_B64 --es msg $(printf '关键词' | base64)
adb shell input keyevent 66

# 进商品详情（DetailActivity），滑图集逐张截图：循环滑动+截图，直到某张截图与上一张视觉重复
# （判定图集已采完）；单商品按 p<商品ID>_<序号>.png 命名；采集数量优先核对商品页读到的
# 「图集张数」字段是否达标，达标或判定重复即终止循环
adb shell input swipe 1000 500 200 500 300
adb shell screencap -p /sdcard/s.png
```

截图回传（m4 宿主走 base64 管道，`<serial>` 用 `adb devices` 输出的真实序列号）：
```bash
ssh xian-m4 "adb -s <serial> shell screencap -p /sdcard/s.png; \
  adb -s <serial> pull /sdcard/s.png /tmp/s.png 1>&2; base64 -i /tmp/s.png" 2>/dev/null | base64 -d > local.png
```

### 🔴 裁剪边界必须核对

商品图在屏幕的垂直区间**随页面结构变化**，写死比例会翻车：

```python
from PIL import Image
img = Image.open(src); w,h = img.size
img.crop((0, int(h*0.12), w, int(h*0.335))).save(dst)   # 主图页参考值
```

早期版本用过 `0.084`，实测在某些页面会把**底部缩略图条一角**带进来，成品图顶部出现黑块，且下游 AI 不会帮你修（见 `codex-image-cleanup` 坑2）——已改用 `0.12` 避开此问题。
**每张裁完仍须看一眼**，个别页面结构特殊仍可能需要微调起点。

## 商品页能读到的信息

标题、价格区间（如 ¥2~¥12.8）、起批量、已售数、回头客数、发货地、48h发货承诺、图集张数。
这些是选品打分的输入。截图后由 AI 读图提取，无 API。

## 尚未实现（别假装有）

- **无选品打分逻辑**：目前纯人工看销量/价格拍板。规则化打分（销量门槛/价格带/重量运费/侵权风险）只是设计，未落地。
- **无批量采集**：一次一个商品手动走完。
- **分享链接路线未验证**：商品页「···」→ 复制链接可拿到公开 URL，理论上能用网页端抠图直链，未实测。
