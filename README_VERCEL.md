# Vercel 部署说明

本项目已配置为可在 Vercel 平台部署。

## 文件结构

```
.
├── api/
│   └── index.py          # Vercel Serverless Function 入口
├── radiomics_custom_example.py  # Flask 主应用
├── requirements.txt      # Python 依赖
├── vercel.json          # Vercel 配置文件
└── dicom_data/          # DICOM 文件目录
```

## 部署步骤

### 方法1：通过 Vercel CLI

1. 安装 Vercel CLI：
```bash
npm i -g vercel
```

2. 登录 Vercel：
```bash
vercel login
```

3. 部署：
```bash
vercel
```

4. 生产环境部署：
```bash
vercel --prod
```

### 方法2：通过 GitHub 集成

1. 登录 [Vercel Dashboard](https://vercel.com/dashboard)
2. 点击 "New Project"
3. 导入 GitHub 仓库
4. Vercel 会自动检测配置并部署

## 配置说明

### vercel.json

- `builds`: 指定构建配置，使用 `@vercel/python` 运行时
- `routes`: 路由配置，将所有请求转发到 `/api/index.py`
- `functions`: 设置函数超时时间为 300 秒（5分钟）

### API 端点

部署后，你的 API 端点将是：

- `https://your-project.vercel.app/health` - 健康检查
- `https://your-project.vercel.app/api/radiomics` - 计算 Radiomics 特征

## 注意事项

1. **文件大小限制**：
   - Vercel 免费版 Serverless Function 最大超时时间为 10 秒（Pro 版为 60 秒）
   - 已配置为 300 秒，需要 Pro 计划支持
   - 如果使用免费版，建议将超时时间调整为 10 秒

2. **DICOM 文件**：
   - DICOM 文件需要上传到项目仓库
   - 确保文件大小在 Vercel 的限制内（免费版 100MB，Pro 版更大）

3. **依赖包大小**：
   - PyRadiomics 和 SimpleITK 等依赖包较大
   - 首次部署可能需要较长时间
   - 如果遇到超时，考虑使用 GitHub Actions 或 CI/CD 进行构建

4. **环境变量**：
   - 如需配置环境变量，在 Vercel Dashboard 中添加
   - 当前配置不需要额外的环境变量

## 故障排除

### 问题：缺少 app

如果遇到 "缺少 app" 错误，确保：

1. `api/index.py` 文件存在并正确导入了 `app` 对象
2. `vercel.json` 中的 `builds` 配置指向正确的文件
3. 主应用文件 `radiomics_custom_example.py` 中定义了 `app = Flask(__name__)`

### 问题：超时

如果计算超时：

1. 检查 Vercel 计划（免费版只有 10 秒）
2. 考虑使用异步处理或队列
3. 优化特征计算逻辑

### 问题：依赖安装失败

如果依赖安装失败：

1. 检查 `requirements.txt` 中的版本是否兼容
2. 某些包可能需要系统依赖（如 SimpleITK）
3. 考虑使用 Docker 容器部署（需要 Vercel Pro）

## 本地测试

在部署前，可以本地测试 Vercel 配置：

```bash
# 安装 Vercel CLI
npm i -g vercel

# 本地运行
vercel dev
```

这将启动本地开发服务器，模拟 Vercel 环境。
