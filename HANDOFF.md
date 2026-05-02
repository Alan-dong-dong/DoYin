# HANDOFF

## Project
DoYin - Web 短视频平台 MVP

## Project goal
构建一个本地可运行的网页版短视频平台，核心体验参考抖音一类沉浸式刷流产品。  
当前阶段以 MVP 为主，优先保证主链路可用、界面体验自然、功能边界清晰。

## Tech stack
### Frontend
- Vue 3
- Vite
- TypeScript
- Pinia
- Vue Router

### Backend
- FastAPI
- PostgreSQL

### Media pipeline
- 原始视频上传
- FFmpeg 转码
- HLS 播放

### Local deployment
- Docker Compose
- 本地文件存储

---

## Completed OpenSpec changes
已完成并归档的 changes：

- project-foundation
- auth-and-user
- video-upload-and-transcode
- feed-and-player
- player-controls
- admin-and-moderation
- auth-register-page
- landscape-video-immersive-layout
- overlay-layout-and-safe-area-fix

---

## Current user-visible capabilities
当前项目已经具备以下能力：

### Authentication
- 用户注册
- 用户登录
- JWT 登录态
- 登录后受保护路由访问
- 登录页 / 注册页切换

### Feed and player
- 首页沉浸式刷流
- 一屏一视频
- 视频自动播放
- 手动暂停 / 继续播放
- 上一个视频 / 下一个视频
- 播放器基础状态处理

### Upload and transcode
- 视频上传
- 上传任务状态
- 后台转码
- HLS 输出
- 封面生成
- 前台播放转码后视频

### Admin
- 后台管理入口
- 管理员访问控制
- 视频列表查看
- 视频隐藏 / 下架
- 查看视频转码状态和失败状态

### UI / immersion
- 沉浸式视频舞台
- 横屏视频展示优化
- overlay 安全区优化
- 顶部信息条和底部信息区布局修正

---

## Important implementation decisions
以下是当前项目的重要实现决策，后续修改时应优先保持一致：

### 1. 首页 `/` 当前为受保护路由
这是一个最小实现假设，用于让登录保护和登录后回跳真正落地。  
后续可以调整，但不要在未明确设计前随意改掉。

### 2. 视频容器固定为视口高度
沉浸式刷流容器固定为视口高度，保持一屏一视频的产品感。  
注意：固定的是外层舞台，不是把视频素材强行拉伸铺满。

### 3. 视频素材不得强行拉伸
视频必须保持原始宽高比。  
禁止通过拉伸方式让视频硬铺满容器。

### 4. 横屏视频不能只做简单 contain + 大黑边
当前已经做过一轮修正。  
目标是通过：
- 主视频层保持比例
- 同源背景层 / 模糊背景层
- 更合理的 overlay 位置
来增强横屏视频的沉浸感。

### 5. overlay 应轻量化
底部信息区不应再使用大面积黑色信息卡片。  
当前方向是：
- 左下角 caption overlay / gradient overlay
- 右侧独立控制区
- 顶部信息条轻量、贴边、安全区布局

### 6. 不随意扩大 OpenSpec change 范围
每次只解决一类问题。  
不要在一个 change 里混入无关能力，避免规格漂移和回归困难。

---

## Current known issues / polish items
以下是目前仍值得继续优化的点：

### Playback / UX
- 某些横屏视频在桌面端的视觉占比还可以继续优化
- 某些 overlay 在不同分辨率下仍可能需要更细的安全区适配
- 加载态、失败态、转码中状态还可以继续做得更轻量、更产品化

### Admin
- 后台界面功能已有基础，但 UI 还可以继续 polish
- 表格密度、状态标签、筛选交互还可以优化

### Product completeness
当前还没有以下能力：
- interactions（点赞、评论、关注）
- notifications
- creator analytics / creator studio
- search / discovery
- recommendation ranking
- moderation for comments / reporting

---

## Recommended next changes
建议后续优先顺序如下：

### Option A: 先稳住现有体验
1. integration-and-stabilization
2. ux-polish-and-immersion 的后续细化
3. admin-ui-polish

### Option B: 继续补产品闭环
1. interactions
2. creator-studio-and-analytics
3. comment-moderation-and-reporting

当前更推荐先走 **Option A**，先把现有主链路打磨得更顺、更像真实产品。

---

## Main end-to-end flows to verify
后续联调和回归时，优先验证这些主链路：

### Flow 1: Authentication
- 访问首页
- 未登录跳转登录页
- 登录成功回到首页
- 刷新后登录态仍有效

### Flow 2: Register
- 打开注册页
- 表单校验
- 注册成功
- 跳转登录或自动登录
- 注册页 / 登录页切换正常

### Flow 3: Upload to playback
- 登录后上传视频
- 创建 upload job
- 后台转码
- 转码完成后视频进入可播放状态
- 首页能刷到并播放该视频

### Flow 4: Feed playback
- 首页一屏一视频
- 自动播放当前视频
- 点击暂停 / 继续
- 上一个 / 下一个切换正常
- 边界状态正常
- 横屏 / 竖屏 / 特殊比例视频显示合理

### Flow 5: Admin
- 普通用户不能访问后台
- 管理员能访问后台
- 能看到视频列表
- 能隐藏 / 下架视频
- 能看到转码状态与失败状态

---

