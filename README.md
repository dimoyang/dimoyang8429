# Meditour

面向国际游客的中国旅行助手。产品以目的地发现、行程规划和旅行工具为核心，健康与医疗协助仅作为用户主动进入的增值服务。

当前版本是 Flutter UI 原型，支持中文、英文、德文和法文，正在向可供真实用户测试的旅游 MVP 演进。

## 当前功能

- 中国热门目的地与详情。
- 四语言界面与语言偏好持久化。
- 旅行基础信息和工具入口。
- 健康服务的非核心入口与咨询表单原型。
- Web、Windows、Android 和 iOS 工程基础。

## 本地运行

```powershell
flutter pub get
flutter gen-l10n
flutter analyze
flutter test
flutter run -d edge
```

当前 Windows 环境如未识别 Chrome，可使用 `edge` 或 `windows`：

```powershell
flutter devices
flutter run -d windows
```

## 项目结构

```text
lib/
  app/           应用入口与路由
  business/      当前状态管理，后续按 feature 迁移
  core/          配置、常量、存储和通用能力
  data/          当前模型与示例数据仓库
  l10n/          生成的本地化代码
  presentation/  页面、主题和共享组件
```

目标结构将按 `features/discover`、`features/itinerary`、`features/travel_tools` 等业务功能逐步迁移，不进行一次性重写。

## 路线图

产品定位、功能阶段、目标工程结构、商业验证和融资准备详见：

- [产品与工程路线图](docs/PROJECT_ROADMAP.md)

## 当前阶段

当前仓库用于产品验证，尚未接入正式后端、支付或医疗数据处理。任何真实旅游交易和健康服务都应由具备相应资质的合作方承接。
