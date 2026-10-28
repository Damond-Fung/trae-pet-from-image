# 渲染、测试、部署与更新恢复

## 当前版本审计

`inspect`将当前入口、预加载、3D renderer、out/main.js和产品/包版本文件复制到本次任务快照并记录SHA256。main可能很大，使用rg查 `iCubeFloatingChat`、`completionVersion`、`cursor-position`、`input-caret` 等局部证据，不输出整个主进程文件或用户数据。

内置图鉴/清单来自2026-10-27审计，不能拿历史行号或压缩类名跨版本盲替换。已有自定义入口时：从受管bundle中的原生快照继续适配，或先读历史备份；找不到可信原版则说明缺项，不把自定义代码当成原生契约。

## 建议适配结构

```text
payload/
  floatingButton.html         # 从本次原生页面精确修改，保留事件与设置
  custom-pet/
    renderer.js              # 本次角色2D或实际3D表现
    pet.json                 # 素材映射、锚点与时间
    ...角色素材
```

优先复用原页面，把原生idle脚本加载切向自有渲染器，活动图片映射到自有动画；waiting/completed使用对应姿态＋原CSS。若改成全Canvas，需要逐条重接原生状态，不能提前return绕开任务初始化。不要直接复用历史四行动画v2作为“完整原生换肤”；该版缺superBusy、caret优先和部分原生动作。

### idle接口与命中

历史接口示例（以当前源码签名为准）：

```javascript
TraebaoRenderer.create({onFrame, onError, onBlink})
// -> {canvas, ready: Promise, setPointer(x,y), setHover(bool), setDrag(bool),
//     setActive(bool), setScale(scale), setTransformation(value), dispose()}
// native onFrame(canvas, imageData) uses the real alpha silhouette;
// invoking onFrame() without these arguments can break hit testing.
```

原生代码还会构造`TraebaoRenderer.EasterEgg`。不做新彩蛋也应提供当前调用者实际使用的无操作兼容接口，或精确禁用相关调用；不要遗漏该构造函数让idle加载失败。资源失败需回退原宠物/原图片/球，不留下空白且可点击的透明方框。

setPointer接收相对偏移与null；保留主进程距离门控、输入光标优先、hover/drag抑制及回正。2D仅做自然小幅运动，不把原3D的65°旋转硬套到平面。眨眼是叠加调度，避免有效指针/拖动时仍定时闪整张图。

setActive/visibility/reduced-motion必须停止调度；setScale保持画面和命中坐标一致；dispose清理定时器、监听、Canvas、待完成的加载回调。按每帧实际alpha刷新命中，透明留白应穿透。不能更改全局用户缩放或强制改设置来掩盖图太小。

### 状态不变量

- 语音优先于superBusy，superBusy优先于busy。
- 原生主进程running事件驱动繁忙；保留180秒/10秒循环，任务结束清计时器。
- waiting源于task-state，不是某张图出现就算接入。completed仅新completionVersion触发，等待、失败、新任务、语音能取消；相同版本不能重播。
- 头部方向和眨眼独立于任务状态，不把所有状态做成单一互斥枚举。
- 原版没有专属失败动画；新增失败表情注明新增。八张look资源存在不代表当前页面正在用它们。

## 自动检查矩阵

使用实际修改后的页面，在隔离预览中提供与预加载签名匹配的IPC mock。保存`verification.json`：逐项pass/fail和证据，不能只检查源码里有函数名。

1. 图像加载、alpha角落透明、身体有效区域可命中；动画过程中命中随轮廓更新。
2. idle安静、眨眼时序；鼠标左右上下、近中心死区、null回正、caret覆盖鼠标、hover/drag回正与恢复。
3. 真正独立头部：选取固定躯干标记在方向变化前后位置保持；不能用整身换视角蒙混通过。
4. hover进入/离开、drag按下超过原阈值、释放回正、点击打开聊天、右键、原生系统鼠标路径、大小设置。
5. busy、superBusy定时、voice优先、running结束；模拟时钟检查180秒和10秒，实机任务另验。
6. waiting/class以及completed三次动画；版本去重、首次快照不误触发、失败取消、重复消息、状态抢占、结束回真实状态。
7. 隐藏暂停、减少动态效果、切换ball与traebao、渲染器资源失败降级、dispose重建。

## 部署和恢复

petctl的bundle命令冻结本次原生契约、payload和哈希。只写入口HTML与custom-pet目录，HTML最后发布；写前检查所有输入及当前契约，备份当前文件，依赖复制失败不发布入口；入口发布/回读失败则回滚本次已写文件。恢复只恢复仍等于本次payload的文件，不覆盖更新后的未知文件。

同一个安装目录已有本技能bundle时，换新角色先运行旧bundle的restore；成功后重新inspect为新原生基线。旧bundle源代码和备份保留。先重用更新任务，变更其bundle参数，避免多个任务互相覆盖。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "<skill>/scripts/register-update-task.ps1" -Bundle "<job>/bundle" -PythonExe "<实际python.exe>"
```

任务使用本地用户权限、隐藏无窗口，每2分钟运行一次`petctl.py repair`（仅检查/重应用已经通过测试的bundle），配置永久保留的skill脚本绝对路径。脚本记录bundle目录中的`update-status.json`和`events.jsonl`。任务名随目标安装目录稳定，重新执行更新参数，不重复注册。重应用不会杀进程或自动触碰活动任务。

若用户明确不要后台任务则跳过并标记未启用。配置失败保留磁盘部署结果，如实报告，不称自动恢复已启用。停止更新检查：使用注册脚本的`-Remove`。先停任务再restore，防止恢复后被任务重新安装。

只有契约全部hash匹配原版/本bundle已安装hash时才重应用；新版main/renderer/preload等改变则`needs-adaptation`，不强刷。未知版本无法靠离线脚本自动写出新适配代码；用户下一次调用技能时由Agent重新审计/修改/测试，重新冻结bundle。安装改动不是官方皮肤API，不承诺未来版本无需适配。

### 实机激活

安装后先核对磁盘文件，再尝试当前已验证的桌宠关闭/开启；保持用户的外观选择和缩放。如果当前未选traebao，检查并使用对应设置入口，告诉用户改动。不要强杀Trae CN.exe，不结束主IDE，不把不存在的IPC发送当作重载。没有可用UI工具时只请用户手动关闭再开启桌宠这一项，标记“已部署，待重载”。

最终报告分别给出：素材合格、模拟通过、磁盘已部署、窗口已加载、真实任务/鼠标事件已验证、更新恢复任务已配置。缺项就写缺项。
