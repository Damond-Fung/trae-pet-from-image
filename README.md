# 一张图换 TRAE 桌宠

上传喜欢的角色图，让 TRAE 根据原生动作清单与资源图鉴制作桌宠，检查后备份部署。

## 使用

将本仓库完整目录放入项目 `.trae/skills/trae-pet-from-image/`，保留 scripts、references 和 templates。在 TRAE 新对话上传图片并发送：

> 使用 trae-pet-from-image 技能。

AI先给一次新增、切换、调整、修复选择；已明确说“切换到奶牛”等操作时直接路由。新增保留旧角色，调整保留版本。默认无有效交互2秒后蹲坐发呆，任务等待独立处理。

## 包含什么

- 原生动作清单与可播放资源图鉴。
- 参考图生成、角色一致性与透明背景检查规范。
- 入口路由、多角色库和客户端兼容规范。
- 版本快照、备份部署、还原及无控制台更新检查脚本。
- 独立闲置计时策略模板和隔离测试。

## 环境与边界

适用于Windows上的TRAE CN，需Python 3.11或兼容版本；生图需自行配置实际支持参考图输入的工具，技能本身不提供图像服务或额度。脚本不负责凭空生成角色与适配代码，由执行技能的Agent完成。

这是本地客户端适配方案，会修改客户端文件。先备份并核对版本，未知新版本拒绝强制覆盖。2D表现不等于真实3D模型。角色库与完整自动流程仍需在目标环境实机验收，不能将模拟测试当作全部真实事件已通过。

## 修复旧版终端弹窗

在PowerShell中执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/repair-terminal-popup.ps1
```

脚本备份并停用本技能旧计划任务，保留当前桌宠和TRAE进程。自动更新恢复暂时暂停；检查当前bundle后，使用修复版register-update-task.ps1重新注册。新版任务直接启动pythonw.exe，运行依赖复制到稳定用户目录；缺pythonw不回退到控制台方式。

## 验证

```powershell
py -3.11 tests/test_deployment.py
node tests/test_idle_policy.js
```

部署测试仅使用临时模拟安装目录；闲置测试检查纯计时和抢占逻辑。运行本技能后仍需验证素材与真实交互。

原生资源图鉴仅用于说明TRAE的行为，相关形象与资源权利归其原权利人。本项目不包含用户生成的角色、客户端主程序、用户日志、账号配置或授权信息。
