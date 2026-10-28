# 从一张图自动制作素材

工作帧与头部素材的硬性质量要求见[素材与视线质量检查](visual-quality.md)。busy/superbusy提示词必须明确可见电脑屏幕和键盘、前爪接触键盘及跨帧道具固定；头部素材要求同身份、同头颈裁切范围，生成后按实际屏幕朝向校准而非信任命名。

v2新增必需素材：`idleSit`蹲坐发呆，按[闲置规则](idle-policy.md)在无交互2秒后显示。先判断真实任务路由，切换已有角色不进入本生成流程；调整仅改必要状态。图像后端需实际支持参考图编辑并先验角色一致性，不允许在缺专业工具时用SVG/Canvas代码画近似角色冒充模型输出。DeepSeek等调度模型名称不等于图像模型名称，记录实际图像工具/后端及参考输入。

目标是一次任务完成桌宠，而不是让用户管理生图项目。图片数量由角色与动画方式决定，不固定成四行24帧，也不先画无必要的八方向图。

## 参考输入与母版

- 先读取真实附件，抽取角色特征；GIF的放大帧不会增加原图细节。原图与工具原始输出均保留。
- 不同图像工具的参考图参数可能不同，需按当前工具文档和实际调用结果确认。当前工具支持时实际传参考图，输出调用记录和文件；不支持则停在明确的工具能力缺项，不编造调用成功。
- 默认尊重当前形象、配色、头身比与配饰；用户要求可爱/胖/毛茸茸时加这些要求。半身补全身体自然即可，不强制固定站姿，不自动增加背包/耳机。
- 标准图可由一次生成得到；自动检查身份后立即继续，不追加人工确认环节。已经有合格标准图则复用，只有换角色时重做。
- 参考输入至少含原图和母版；其他视角作为辅助，不让互相矛盾的全部参考同时支配生成。

## 提示词构造模板

以下模板由Agent补齐实际角色特征、动作与输出形式后调用工具；模板不等于已生成。

```text
Use the attached user character as the identity reference and the approved generated master as the proportion reference. Preserve [observable identity, colors, markings, proportions, materials and accessories]. Render the SAME character and style for a desktop companion visible at 105px.
State: [state]. Actual motion: [pose A -> B -> C -> return]. Expression: [expression].
Fixed camera, light, body scale and ground baseline. Whole character visible, with clearance for this action. No labels, grid lines, duplicate limbs, background props or frame-to-frame costume changes.
Output [single layered component / N sequential keyframes]. [Transparency request if supported, otherwise a background suited to the available matting tool].
For gaze: torso remains front-facing; ONLY the head and eyes look [target]. Do not turn the entire body. Preserve neck overlap and remove the underlying original head from the body layer.
```

每种状态单独明确动作，避免“统一可爱”导致所有状态都只是同一个站姿。繁忙可以工作，超级繁忙节奏与表情更明显，语音听说，等待注视，完成一次性庆祝。新增道具保持风格，别改角色身份。

## 产物设计

1. idle：正常姿态、半闭眼、闭眼；可独立头/身体/眼层更好。闲置默认安静，避免永远挥手。
2. gaze：身体固定的头部正面、左右、上下及所需斜向或可变形分层结构。绕竖轴八个全身视图不解决上下看，也不解决独立转头。
3. hover/drag：悬停轻弹，拖动悬空与摆腿及释放落地；可关键帧配合程序动画，必须实际变化。
4. busy/superBusy/voice：分别生成连贯关键帧，用已确认可用的编码库制成带alpha动画WebP，或在自研渲染器内播放。不要只复制帧制造“25帧动画”。关键帧少于原生帧数可以，只要动作节奏和触发符合原生；不要声称原生同等流畅。
5. waiting/completed：专属姿态/表情配合原CSS即可；保留其实际触发条件和取消规则，避免代码和CSS重复跳跃。

无需给所有状态画所有方向：idle默认只需头部转向，busy/voice无需跟随时不额外生成八套。

## 后处理和自动质量检查

使用目标环境确实可用的抠图/图像编辑能力；遵守该环境工具规则。PNG扩展名不证明透明；JPEG原图和后处理alpha须区分。近白阈值容易抹掉胡须、白毛和眼高光，不能不检查就当合格。

- 看深色、白色与棋盘格边缘；以105px视觉为主，放大图查残留/接缝。
- 统一逻辑画布（如1024方形）、身体尺度和脚底锚点。一个动作按整组运动包围盒计算缩放，不逐帧按外接框自动撑满；跳跃时脚底高度可以变化。
- 检查透明留白不会把角色缩成过小，尾巴/头部极限动作不会出界。
- 分层身体不能残留原头，后背层/身体层要补齐被遮挡部分；在全部朝向和眨眼下验接缝。
- 眼睛闭合局部改动，避免闭眼帧整张重新生图导致变脸。
- 遇到单个缺陷只修局部/对应动作，不为背包小差异无限重生成全套。必要项两轮修正仍失败则保留未通过并报告一次。

保存 `assets.json`：角色参考hash、每个状态文件、关键帧/时间、图层锚点、画布大小、生图工具与实际prompt、后处理方法、已知限制。
