# Radiomics API 服务

这是一个基于Flask的Radiomics特征计算API服务，可以部署到Render平台。

## 功能说明

该API服务接收study_uid、series_uid和mask数据，返回计算出的Radiomics特征值。

## 目录结构

```
.
├── radiomics_custom_example.py  # 主应用文件
├── requirements.txt              # Python依赖
├── render.yaml                  # Render部署配置
├── dicom_data/                  # DICOM文件存储目录（硬编码）
│   └── {study_uid}/
│       └── {series_uid}/
│           └── *.dcm           # DICOM文件
└── README_RADIOMICS_API.md      # 本文档
```

## DICOM文件组织方式

DICOM文件需要按照以下结构组织在同目录下的`dicom_data`文件夹中：

```
dicom_data/
  └── {study_uid}/
      └── {series_uid}/
          ├── file1.dcm
          ├── file2.dcm
          └── ...
```

例如：
```
dicom_data/
  └── 1.2.840.113619.2.55.3.604829832.123.1234567890.123456/
      └── 1.2.840.113619.2.55.3.604829832.123.1234567890.123457/
          ├── IM-0001-0001.dcm
          ├── IM-0001-0002.dcm
          └── ...
```

## API接口说明

### 1. 健康检查

**请求**
```
GET /health
```

**响应**
```json
{
  "status": "healthy",
  "message": "Radiomics API服务运行正常"
}
```

### 2. 计算Radiomics特征

**请求**
```
POST /api/radiomics
Content-Type: application/json
```

**请求体**
```json
{
  "study_uid": "1.2.840.113619.2.55.3.604829832.123.1234567890.123456",
  "series_uid": "1.2.840.113619.2.55.3.604829832.123.1234567890.123457",
  "mask": {
    "format": "sparse_coo",
    "shape": [100, 512, 512],
    "dtype": "uint8",
    "indices": [[0, 10, 20], [1, 11, 21], ...],
    "values": [1, 1, ...]
  }
}
```

或者使用完整数组格式：
```json
{
  "study_uid": "...",
  "series_uid": "...",
  "mask": {
    "shape": [100, 512, 512],
    "dtype": "uint8",
    "data": [0, 0, 1, 0, ...]
  }
}
```

**响应（成功）**
```json
{
  "success": true,
  "study_uid": "1.2.840.113619.2.55.3.604829832.123.1234567890.123456",
  "series_uid": "1.2.840.113619.2.55.3.604829832.123.1234567890.123457",
  "features": {
    "灰度均值": 123.45,
    "灰度方差": 456.78,
    "联合分布均值": 123.45,
    "联合分布强度": 12345678.9,
    "灰度随机性": 5.67,
    "第10百分位CT值": 100.0,
    "第90百分位CT值": 200.0,
    "密度平方和": 12345678.9,
    "密度随机性": 5.67,
    "密度最大值": 255.0,
    "密度平均值": 123.45,
    "平均绝对误差": 10.23,
    "中位数": 120.0,
    "鲁棒脉冲平方差": 50.12,
    "纹理突出度": 0.5,
    "纹理凹陷度": 0.3,
    "纹理平坦度": 0.8,
    "变化速度": 5.43,
    "GLCM最大频率值": 0.123,
    "纹理对比度": 45.67,
    "纹理相关性": 0.89,
    "行程灰度相似度": 1234.56,
    "灰度行程重要性": 567.89,
    "行程长度不确定性": 3.45,
    "行程长度分布相似性": 0.56,
    "行程长度比率": 0.78,
    "行程长度差异性": 1.23,
    "灰度区域重要性": 1234.56,
    "灰度区域比率": 0.45,
    "灰度区域差异性": 789.01,
    "延展性": 1.23,
    "平滑度": 0.67,
    "椭圆最长直径": 45.67,
    "椭圆最短直径": 23.45
  },
  "feature_count": 34
}
```

**响应（错误）**
```json
{
  "success": false,
  "error": "错误信息描述"
}
```

## 部署到Render

### 1. 准备文件

确保以下文件存在于项目根目录：
- `radiomics_custom_example.py`
- `requirements.txt`
- `render.yaml`
- `dicom_data/` 目录（包含DICOM文件）

### 2. 上传到GitHub

```bash
git add .
git commit -m "Add Radiomics API service"
git push origin main
```

### 3. 在Render中部署

1. 登录 [Render Dashboard](https://dashboard.render.com)
2. 点击 "New +" -> "Web Service"
3. 连接你的GitHub仓库
4. Render会自动检测`render.yaml`配置
5. 点击 "Create Web Service"

### 4. 配置环境变量（如需要）

在Render Dashboard中，可以添加环境变量：
- `PORT`: 端口号（Render会自动设置，无需手动配置）

## 本地开发

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行服务

```bash
python radiomics_custom_example.py
```

或者使用gunicorn：

```bash
gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 300 radiomics_custom_example:app
```

### 测试API

使用curl测试：

```bash
# 健康检查
curl http://localhost:5000/health

# 计算特征
curl -X POST http://localhost:5000/api/radiomics \
  -H "Content-Type: application/json" \
  -d '{
    "study_uid": "your_study_uid",
    "series_uid": "your_series_uid",
    "mask": {
      "format": "sparse_coo",
      "shape": [100, 512, 512],
      "dtype": "uint8",
      "indices": [[0, 10, 20]],
      "values": [1]
    }
  }'
```

## 注意事项

1. **DICOM文件位置**: DICOM文件必须按照`dicom_data/{study_uid}/{series_uid}/`的结构组织
2. **内存使用**: Radiomics特征计算可能需要较多内存，建议使用至少2GB内存的实例
3. **超时设置**: Render的默认超时可能不够，已设置300秒超时
4. **并发处理**: 使用gunicorn的2个worker处理并发请求
5. **文件大小**: 确保上传的DICOM文件和mask数据大小在Render允许的范围内

## 特征列表

API返回34个Radiomics特征，包括：

### 自定义指标（18个）
- 灰度均值
- 灰度方差
- 联合分布均值
- 联合分布强度
- 灰度随机性
- 第10百分位CT值
- 第90百分位CT值
- 密度平方和
- 密度随机性
- 密度最大值
- 密度平均值
- 平均绝对误差
- 中位数
- 鲁棒脉冲平方差
- 纹理突出度
- 纹理凹陷度
- 纹理平坦度
- 变化速度

### PyRadiomics特征（16个）
- GLCM最大频率值
- 纹理对比度
- 纹理相关性
- 行程灰度相似度
- 灰度行程重要性
- 行程长度不确定性
- 行程长度分布相似性
- 行程长度比率
- 行程长度差异性
- 灰度区域重要性
- 灰度区域比率
- 灰度区域差异性
- 延展性
- 平滑度
- 椭圆最长直径
- 椭圆最短直径

## 故障排除

### 问题：DICOM文件夹不存在
**解决**: 确保DICOM文件按照正确的目录结构组织

### 问题：计算超时
**解决**: 检查数据大小，可能需要增加超时时间或优化数据处理

### 问题：内存不足
**解决**: 升级Render实例规格，增加可用内存

## 许可证

请根据项目实际情况添加许可证信息。
