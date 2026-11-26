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

### V5 首页与搜索结果页

2026-11-26 在 M4 小蓝实测：首页 `V5HomeActivity` 的搜索入口可由 `com.alibaba.wireless:id/search_navigator_center_search_character_exp` 定位。点击后可能先进入预填推荐词的 `QuickSearchResultActivity`。用结果页顶部的 `com.alibaba.wireless:id/ll_search_keyword_bg` 打开关键词输入页。起点已在结果页时直接核对这个顶部控件。

每次从当前树取唯一目标的 bounds。等输入框获得焦点，选中并替换已有文字，逐字读回本次关键词后再提交。结果页的顶部关键词栏和画面用于核对本次搜索。卡片在树中缺少标题时，可用本机 OCR 核对同一商品区域的标题和价格，再打开该商品并读回详情页、保存首屏。登录、验证页或目标控件不确定时停止。


```bash
# 搜索
adb shell input tap <搜索框>             # SearchInputActivity
adb shell ime set com.android.adbkeyboard/.AdbIME
adb shell am broadcast -a ADB_INPUT_B64 --es msg $(printf '关键词' | base64)
adb shell input keyevent 66

```

### 逐页采集图集

1. 按公共底座取得设备双锁，核对前台是 1688、页面是本商品的 `DetailActivity`。按当页控件树定位 `album_view` 内文字为「图集」的入口，回到第 1 页。截图确认商品标题、主图区域和 `1/N` 页码。
2. 在当前主图区域内逐次短距离横滑。M4 小蓝（1200×2664）在 USB 定制商品上实测用 `input swipe 803 750 413 750 170` 从 1/6 逐页到 5/6，从 5/6 到 6/6 用 `input swipe 876 750 401 750 180`。这些坐标仅供同屏参考，其他页面按当前主图边界定位。
3. 每次等画面稳定，读回截图中的 `页码/N`，仅在总页数一致且准确前进一页时保存下一张。页码模糊时放大页码区域核对。停在原页可调整一次手势并再次核对。遇跳页、循环或仍读不到页码时，回「图集」首项补采缺页，仍缺页则报实际已采页码。图库缩略图条还包含讲解、属性和 SKU，横滑或选中后位置会变。
4. 成功条件是同一商品的 `1/N` 至 `N/N` 均有可核对的原图，按实际页码命名。首项有播放按钮时保留封面截图，标记为视频封面，只把其余静态页送进图片素材。小蓝本次读回 6 个图集项（1 个视频封面、5 张静态图）。保留原始证据，并在裁剪后逐张复核；完成后回桌面并核对双锁释放。

截图回传（m4 宿主走 base64 管道）：
```bash
ssh xian-m4 "adb -s <serial> shell screencap -p /sdcard/s.png; \
  adb -s <serial> pull /sdcard/s.png /tmp/s.png 1>&2; base64 -i /tmp/s.png" 2>/dev/null | base64 -d > local.png
```

### 🔴 裁剪边界必须核对

商品图在屏幕的垂直区间**随页面结构变化**，写死比例会翻车：

```python
from PIL import Image
img = Image.open(src); w,h = img.size
img.crop((0, int(h*0.084), w, int(h*0.335))).save(dst)   # 主图页参考值
```

实测 `0.084` 在某些页面会把**底部缩略图条一角**带进来，成品图顶部出现黑块，且下游 AI 不会帮你修（见 `codex-image-cleanup` 坑2）。
**每张裁完必须看一眼**，不合适改起点（实测 `0.12` 可避开）。

## 商品页能读到的信息

标题、价格区间（如 ¥2~¥12.8）、起批量、已售数、回头客数、发货地、48h发货承诺、图集张数。
这些是选品打分的输入。截图后由 AI 读图提取，无 API。

## 尚未实现（别假装有）

- **无选品打分逻辑**：目前纯人工看销量/价格拍板。规则化打分（销量门槛/价格带/重量运费/侵权风险）只是设计，未落地。
- **无批量采集**：一次一个商品手动走完。
- **分享链接路线未验证**：商品页「···」→ 复制链接可拿到公开 URL，理论上能用网页端抠图直链，未实测。
