---
name: avatar
description: |
  AI 数字人口播视频制作 runbook + 全部踩坑结论。做"丢一张脸/一段视频 + 文案 → 出会说话的口播视频"产品时触发。
  覆盖："AI 数字人 / 数字人 / ai avatar / ai shuziren / 数字人口播 / 数字人视频 / 口播视频 / 对口型 /
  换脸 / 让照片说话 / talking head / LongCat / 龙猫 / 混元 Avatar / LatentSync / FaceFusion / DFL /
  DeepFaceLab / OmniHuman / 即梦数字人 / CosyVoice 声音克隆 / 怎么做数字人 / 数字人怎么换脸 / 数字人成本"。
  本 skill 给：① 路线对比与最终结论（哪条死、哪条活）② 三段式组合拳流水线 ③ 每个工具的可复现命令
  ④ AutoDL/A800 部署运维坑（含计费教训）⑤ 成本实测。机器映射见 [[machines]]，凭据见 1Password CS。
---

# AI 数字人口播 Runbook（2026-06 多日实测）

目标产品：客户丢「一张脸/一段口播视频 + 文案」→ 自动出「这个人说这段话」的口播视频，**全开源自部署、能卖工作流**（不转卖闭源 API）。

## ⭐ 一句话最终结论

**开源里"真脸 + 自然嘴 + 动作"没有单一工具能做到，要三段式组合拳：**
```
LongCat（出身体动作/手势） → LatentSync（重绘自然嘴） → DFL/FaceFusion（换上你的真脸）
```
- 单段都验证跑通过。代价：3 段重流水线、要好几张 GPU、不是一键。
- 想"脸真的是你"→ 必须 DFL 训练（FaceFusion 单图换脸有天花板，只"有点像"）。

## 路线对比（全部实测，别再走死路）

| 路线 | 工具 | 嘴 | 动作 | 一致性(像不像) | 开源能卖 | 结论 |
|---|---|---|---|---|---|---|
| 真人对口型 | LatentSync | ✅自然(真视频补嘴) | ❌身体不动 | ✅100%是你(真视频) | ✅ | 自然嘴的唯一来源 |
| 端到端 | LongCat(美团开源SOTA) | ❌夸张张大嘴(天生,参数调不掉) | ✅有 | ❌逐帧生成会飘 | ✅MIT | 出动作可以，脸/嘴都不行 |
| 端到端 | 混元Avatar | ❌夸张/假 | ✅有 | ❌ | ✅ | 同 LongCat，更糊 |
| 端到端 | OmniHuman/即梦 | ✅ | ✅ | ✅ | ❌闭源 | 效果最好但卖不了，否决 |
| 单图换脸 | FaceFusion | — | — | ⚠️部分迁移,有天花板 | ✅ | 快但不会100%像你 |
| 训练换脸 | DFL | — | — | ✅真变成你(质变路) | ✅ | 要几百张脸训练，重 |
| 卡通 | LongCat+卡通图 | 夸张但卡通可接受 | ✅ | ✅(固定IP角色,不飘) | ✅ | 用户"问题不大"，备选方向 |

硬结论（反复验证）：
- 端到端模型(LongCat/混元)的"嘴过度张大"是天生的：试遍 audio_guidance(4.0→1.0)、关蒸馏跑完整50步、INT8→FP16、真人/卡通输入——嘴都收不住。参数救不了。
- LongCat 擅长卡通不擅长真人：卡通脸飘了还是"那个角色"，真人脸飘一点就恐怖谷/不像。
- 输入图决定成片：带字幕/说话中途张嘴/眼神飘的烂帧 → 出来必怪。要正脸、闭嘴、无字幕、清晰的干净图。
- FaceFusion 单图换脸只用1张图，多给照片没用；多图质变要换 DFL。

## 三段式流水线（每段命令）

### 1. LongCat 出动作（A800 / AutoDL）
图+音频→说话视频，8步蒸馏快推理。详见下方部署。--stage_1=ai2v(图+音频)，--num_segments N 控制时长(每段~3.7s，45s≈12段)。注意需要两个模型：avatar + 基座 LongCat-Video(tokenizer/text_encoder/vae)，checkpoint_dir/../LongCat-Video 硬编码路径，avatar 必须真目录不能软链(软链让 .. 解析穿透)。FP16 满精度比 INT8 细节好(治"不像")，A800 80G 装得下满精度(30G模型+22G text_encoder)。

### 2. LatentSync 重绘嘴（xian-rog，复用见 latentsync_setup）
把 LongCat 的夸张嘴整个覆盖成自然嘴（不是微调，是重绘嘴区）。已验证有效。
ssh xian-rog → conda activate latentsync → cd C:\Users\asus\LatentSync
set HF_ENDPOINT=https://hf-mirror.com
python -u -m scripts.inference --unet_config_path configs/unet/stage2_512.yaml --inference_ckpt_path checkpoints/latentsync_unet.pt --inference_steps 20 --guidance_scale 1.5 --enable_deepcache --video_path <脸视频> --audio_path <mono16k.wav> --video_out_path out.mp4
- 音频必须 mono 16k wav（stereo/44.1k 会 ffmpeg "Permission denied" 挂）。
- 必须 stage2_512.yaml(512)。deepcache+短片几分钟出。

### 3a. FaceFusion 单图换脸（快但有天花板，xian-rog conda env facefusion）
cd /d C:\Users\asus\facefusion && set HF_ENDPOINT=https://hf-mirror.com
python facefusion.py headless-run --processors face_swapper face_enhancer --face-swapper-model simswap_unofficial_512 --face-detector-model retinaface --face-detector-score 0.3 --face-mask-types box occlusion --face-mask-blur 0.5 --face-enhancer-model gfpgan_1.4 --execution-thread-count 1 --source-paths <绝对路径脸.png> --target-path <绝对路径视频.mp4> --output-path <绝对路径out.mp4>
- 路径必须绝对路径（相对路径报 "specify output within a directory!"）。
- xian-rog 4070 上慢到 20-26秒/帧(onnxruntime CUDA 没发挥)→ 1秒视频要8分钟，量产必须挪 A800。
- inswapper_128 没缓存会卡下载(github/hf 挂)；simswap_512 已缓存能跑。gfpgan 增强更慢更清晰，不加则软。
- Windows ssh 会话断会杀进程→长任务超时给够或用计划任务。

### 3b. DFL 训练换脸（质变路，待做，需用户脸素材）
- 用户给口播视频(现成51s real-person.mp4在COS就能用，但偏薄；多给1-2个口播视频更稳)→抽几百帧建脸集→A800训几小时→得"你的脸模型"→以后每条 LongCat+LatentSync 成片套用换脸。
- 训练一次永久反复用。是真项目不是快测。最佳素材=口播视频(正脸,目标也正脸正好对口)，别开美颜。

### 声音克隆（CosyVoice，阿里 DashScope）
from dashscope.audio.tts_v2 import VoiceEnrollmentService, SpeechSynthesizer
vid=VoiceEnrollmentService().create_voice(target_model='cosyvoice-v2', prefix='me', url='<公网样本mp3>')
audio=SpeechSynthesizer(model='cosyvoice-v2', voice=vid).call(text)
~¥2/万字，克隆一次反复用。样本越长越像。或直接用原视频原声（最干净）。

## AutoDL / A800 部署运维（计费坑！）

- A800-80GB ¥4.98/h，账号存 1Password "AutoDL A800 (LongCat数字人)"；SSH ssh -p 25523 root@connect.nma1.seetacloud.com。
- AutoDL 无可用 API：开发者 token 会过期("登录超时")；/api/v1/dev/ 只管弹性部署不管租用实例。我只能从实例内部关机，开机必须用户在控制台点。
- 关机用 shutdown -h now（看门狗有效）；poweroff -f 有时"Operation not permitted"→改 shutdown -h now + echo o>/proc/sysrq-trigger。关机=计费停(关15天后释放，盘+env+模型保留)。
- 看门狗只留一个！多个残留短 sleep 会误关(被自己45分钟看门狗凌晨3点关过，别赖余额)。base64 法部署避转义坑：echo <b64> | base64 -d | nohup bash &。
- 86GB 数据盘装不下 int8+fp16 双 base_model(各15/30G)+22G text_encoder+其他→用谁删谁，--use_int8 就删 fp16 base_model。扩容要重启(端口不变但要等1-2分钟SSH就绪)。付费数据盘每日0点扣费(关机也扣)，养模型约¥60-120/月。
- 下载：ModelScope 大分片会卡死(多进程抢文件/反复重试零进度)→改 huggingface_hub snapshot_download + HF_ENDPOINT=hf-mirror + 卸 hf_xet。GitHub 代码 clone 国内卡→hk-vps(100.86.118.99)clone→tar→COS→AutoDL curl 拉。预编译 wheel(flash-attn)同走 hk-vps→COS，保留精确 wheel 文件名(改名 pip 拒)。
- 社区镜像 env 不全：LongCat 镜像只给 conda env，缺 transformers==4.41.0/diffusers==0.35.1/flash-attn/audio-separator/accelerate/huggingface_hub；requirements 里 libsndfile1==0.0.1 不是pip包会中断整批；ffmpeg 要 conda install -n env ffmpeg 且跑时 export PATH=env/bin:$PATH。

## 成本实测

| 视频 | A800 GPU时间 | 钱 |
|---|---|---|
| 卡通/真人 ~26-39s | ~18-27分钟(含模型加载) | ~¥1.5-2.3 |
| 45s | ~30分钟 | ~¥2.5 |
| 90s | ~55分钟 | ~¥4.6 |
- ≈ ¥0.06/秒。LatentSync/FaceFusion 另算（xian-rog慢，量产挪A800）。
- 量小用完即关(on-demand)：开机~2min+加载~3min+生成 → 单条含冷启动 ~¥1-3，不养常驻卡(否则¥3600/月闲置烧钱)，只固定养盘 ~¥100/月。
- 闭源 API 现价参考：腾讯智影 ¥0.055/s(配额内)、Wan2.6 ¥0.5/s、Seedance ¥0.7/s。

## 资源/机器

- A800：AutoDL 租用，跑 LongCat / 将来 DFL 训练。¥4.98/h。
- xian-rog(RTX4070L 8G, Windows, conda)：LatentSync(env latentsync) + FaceFusion(env facefusion) 现成。换脸慢。
- 声音：阿里 DashScope CosyVoice-v2，~/.credentials 有 key。
- 文件中转：用户传文件→COS 预签名/或我用 COS 密钥 download_file(预签名GET易过期，用密钥直拉 temp/<key>)。COS bucket zenithjoy-static-1333590468 ap-guangzhou，给用户看片上传 publish/ 直链。
- 凭据：1Password CS（腾讯云 key 在 "Tencent Cloud (腾讯云)" notesPlain）。

## 相关 memory
digital_human_exploration_0623（真人/卡通/混元全路线）、longcat_endtoend_mouth_deadend（LongCat嘴死结+A800部署全坑）、latentsync_setup、line07_faceswap_findings（DFL是唯一质变路+FaceFusion坑）、tencent_hai_cheap_gpu、machines。

## 商业/闭源 API 选项（对标参考——我们不转卖，但要知道行情）

我们做开源自部署，但调研过的闭源数字人/对口型 API（被掐脖子、无护城河，故否决转卖，仅作效果/定价对标）：
- HappyHorse(happy horse)：~¥0.8-0.9/秒，对口型/数字人
- 腾讯智影：会员 ¥0.055/秒(配额内)，最便宜
- 即梦 / OmniHuman-1.5(字节)：效果最强（动作+情绪语义+多人+走位），闭源只 App / BytePlus API
- 可灵 Kling Avatar 2.0：数字人
- Seedance：~¥0.7/秒（Seedance mini 更便宜）
- Wan 2.6：¥0.5/秒
- 美团 LongCat-Video-Avatar-1.5：开源 SOTA（评测胜率胜 OmniHuman-1.5 61%、胜可灵 66%、胜 HeyGen 54%），**我们自部署用的就是它**
为什么不用闭源：转卖别人 API 没护城河、被掐脖子、客户量大成本不可控。开源自部署 = 工作流自己掌控、能卖。

## 对口型工具对比（"口型"这条线）

| 工具 | 原理 | 评价 |
|---|---|---|
| LatentSync(字节) | 扩散重绘嘴区 | ✅ 自然，我们主用（真视频补嘴 + 覆盖 LongCat 夸张嘴） |
| Wav2Lip | 老 GAN 对口型 | 糊，过时不用 |
| MuseTalk | 长视频嘴部填充 | 提到没用上 |
| 端到端生成嘴(LongCat/混元) | 听声生成整脸 | 嘴夸张（前述死结） |
结论：要自然嘴 = LatentSync 在真实/已生成画面上"补嘴"；别指望端到端生成的嘴。

## 换背景（顺带，非口播但常一起问）

LongCat 是"生成"不是"编辑"，**换背景它做不了**。换背景用视频抠像：RVM(RobustVideoMatting，line07 用过) / BiRefNet 抠人 → 合成新背景。换脸=FaceFusion/DFL，换背景=RVM，对口型=LatentSync，三件不同事别混。

## 机器分工与历史（什么在哪台跑过——血泪经验）

| 机器 | 配置 | 跑过/适合 | 坑 |
|---|---|---|---|
| **xian-rog** | RTX 4070L 8GB, Windows, conda | **本地主力 GPU**：LatentSync 对口型(env `latentsync`, 2026-06-19装) + FaceFusion 换脸(env `facefusion`) | 8GB 小：LatentSync 512 跑得动但慢(VAE tiling补丁)；FaceFusion onnxruntime 慢到20+s/帧 |
| **xian-5060** | RTX 5060 (Blackwell) | 抠像换背景(RVM)只能走 **CPU** | **Blackwell 太新**：onnxruntime-gpu CUDA 首次推理直接挂死 → 换脸/对口型的 GPU 在5060上有坑，**主力放4070,别指望5060的onnxruntime-gpu**。RVM mobilenetv3 CPU 11fps够用 |
| **A10 / A800** | 腾讯HAI / AutoDL 云租 | 4070跑不动的重模型：**混元Avatar、LongCat**，将来 **DFL 训练** | 见上方 AutoDL 部署坑 |

历史脉络：最初想在 **xian-rog 4070** 上跑混元 Avatar → **8GB 不够(需≥10GB)** → 催生租云 GPU(HAI A10 → AutoDL A800)。LatentSync(对口型) + FaceFusion(换脸) 一直在 4070 本地跑通。5060 因 Blackwell CUDA 坑只做 CPU 抠像。

**当前能力清单（都已跑通验证）：**
- ✅ 对口型(换嘴唇)：LatentSync @ xian-rog
- ✅ 换脸：FaceFusion(单图,快但有天花板) @ xian-rog；DFL(训练,质变) 待做 @ A800
- ✅ 出动作(端到端生成)：LongCat @ A800
- ✅ 换背景：RVM 抠像 @ xian-5060(CPU)
- ✅ 声音克隆：CosyVoice @ 阿里云
