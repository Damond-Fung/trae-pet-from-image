# 入口路由与多角色库

## 一次选择

先扫描，后展示菜单；此时不生图、不安装、不注册后台任务。记录用户选择，恢复任务时不要重复菜单。

示例（名称来自真实记录，没有则显示空库）：

> 当前启用：奶牛；已有：TRAE娘、奶牛。
> 本次想做什么？
> 1 新增：从参考图制作新角色，保留旧角色
> 2 切换：启用库里的角色，不重生成
> 3 调整：改动作/表情/外观，保留旧版本
> 4 修复：检查不显示、更新覆盖或动作失效
> 推荐1。回复数字即可。

TRAE支持选择控件时使用该控件，否则文字数字即可，不假装有不存在的原生按钮。用户明确“新增”“切换到X”“修复更新覆盖”“修改奶牛闲置动作”等，直接进入对应路由；“上传图片＋调用Skill”或“换一个”才询问入口。只允许只读判断推荐，不能在用户选择前默认执行。

- 新增：参考图来自本轮附件；同hash已有角色时告知可以复用，若用户明确重制就新增版本。默认新角色名从外观提取，使用唯一id，名字可重复。
- 切换：列表带缩略图、版本、兼容状态。只有一个明确匹配则直接切换，否则一次问角色选择。缺素材/未知客户端先自动转兼容诊断，不重新生图。
- 调整：默认当前角色，明确内容则直接做；内容缺失只问想改什么。新版本继承未改素材，不全套重画。
- 修复：默认当前角色或用户指定角色，先诊断原生契约/文件/事件。用户只说“修复”，无需再问是什么故障才开始只读检查。需要重生素材才调用图像工具。

进入分支后由AI自动执行，只有真实工具阻断或多种角色无法识别才再询问必要项。自动流程并不保证所有工具存在，不能为完成而用代码画一只近似角色冒充专业生图结果。

## 保存位置与数据

角色库是本技能自建目录，不是TRAE官方皮肤API：Windows默认 `%LOCALAPPDATA%/TraePetLibrary/`。项目`.trae-pet/jobs/<jobId>`保留本次工作记录，最终素材与bundle进入角色库稳定路径，项目移动不影响已注册任务。

```text
TraePetLibrary/
  library.json
  installations/<installationId>.json
  pets/<petId>/versions/<versionId>/
    skin.json
    preview.png
    source/                    # 原始图和实际prompt/来源
    payload/                   # 独立渲染器、配置和素材
    bundles/<contractId>/      # petctl的不可变bundle，含备份
```

library.json：schema=2，pets数组，每项包含id、displayName、sourceSha256、versions、selectedVersion。版本含id、path、status（ready/needs-adaptation/missing-assets）、contractId。installations记录media绝对路径、desiredPetId/version、deployedPetId/version、bundle路径、activation（pending-reload/verified）、updateTaskName。磁盘部署和窗口激活分别记录。

写JSON使用临时文件＋同目录原子替换。每次写前重读当前版本号revision，旧revision不能覆盖新选择；失败保留上一份。切换操作加锁，同一安装只运行一个部署事务。引用文件先校验存在和hash，目录参数只能落在角色库内，不把角色名直接拼成删除路径。

不要求所有角色同一头身比/帧数；每版本携带renderer、锚点、状态映射。公共接口保持一致，TRAE事件语义来自本机审计。旧TRAE娘四行动画若缺功能应标needs-adaptation，不冒充完整原生覆盖。迁入历史资产不删除源文件，不将工程里的任意图片当成可用角色。

## 切换事务

1. 锁定目标安装，读取active和任务记录；目标素材及原生契约预检查。
2. 暂停该安装已有更新检查任务，保存原状态。一个安装只允许一个更新恢复任务。
3. 通过旧bundle安全restore恢复原生入口，再用目标已适配bundle apply。未知文件停止，不强覆。
4. 目标失败则重新apply旧bundle，恢复原更新任务；active保持旧值。回滚失败须如实记录，不能标成功。
5. 成功后原子更新deployed指针，以新的bundle重新配置同一个更新任务；不要让旧任务把旧角色重新装回。
6. 重载桌宠并检查。没UI能力仅请用户关闭/开启一次，不重启IDE。activation保持pending直至真实观察。

第一次目标bundle应从可信原生快照构建；不得把另一个角色的补丁当成原生基线。更新兼容性按安装分别管理。未知版本停止自动覆盖，Agent下次修复时重新适配，不让离线脚本生成代码。
