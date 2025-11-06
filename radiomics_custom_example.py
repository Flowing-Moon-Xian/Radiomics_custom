# radiomics_api.py
# Flask API服务，用于计算Radiomics特征
import os
import json
import numpy as np
import pandas as pd
import SimpleITK as sitk
from radiomics import featureextractor
from scipy import stats
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# ------------------------------
# 配置路径 - DICOM文件硬编码在同目录下
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DICOM_BASE_DIR = os.path.join(BASE_DIR, "dicom_data")  # DICOM文件存储基目录
# ------------------------------

def load_dicom_series(dicom_folder):
    """加载DICOM序列"""
    reader = sitk.ImageSeriesReader()
    dicom_names = reader.GetGDCMSeriesFileNames(dicom_folder)

    if len(dicom_names) == 0:
        raise ValueError(f"未找到DICOM文件在: {dicom_folder}")

    print(f"找到 {len(dicom_names)} 个DICOM文件")
    reader.SetFileNames(dicom_names)
    img = reader.Execute()
    print(f"读取 DICOM 序列完成，维度: {img.GetSize()}")
    return img

def load_mask_from_json(mask_data, img):
    """从JSON数据加载mask（支持稀疏格式）"""
    print("正在加载mask数据...")

    shape = mask_data['shape']  # [depth, height, width] 或 [z, y, x]
    dtype = mask_data['dtype']

    # 检查格式
    if mask_data.get('format') == 'sparse_coo':
        # 稀疏格式：从坐标和值重建完整mask
        print("检测到稀疏格式，正在重建完整mask...")
        indices = np.array(mask_data['indices'])  # [[z, y, x], ...]
        values = np.array(mask_data['values'], dtype=np.uint8)  # [1, 1, ...]

        # 创建全零mask
        mask_arr = np.zeros(shape, dtype=np.uint8)

        # 填充非零像素
        for i, (z, y, x) in enumerate(indices):
            mask_arr[z, y, x] = values[i]

        print(f"重建完成: 非零像素数 = {len(values)}")
    else:
        # 旧格式（完整数组）
        data = mask_data['data']
        print(f"Mask shape: {shape}, dtype: {dtype}, 数据长度: {len(data)}")

        # 将列表转换为numpy数组
        mask_arr = np.array(data, dtype=np.uint8)
        mask_arr = mask_arr.reshape(shape)

    print(f"Mask数组形状: {mask_arr.shape}")
    print(f"Mask中非零像素数: {np.count_nonzero(mask_arr)}")

    # 转换为SimpleITK图像
    mask = sitk.GetImageFromArray(mask_arr)
    mask.CopyInformation(img)

    # 验证mask和图像尺寸是否匹配
    img_size = img.GetSize()
    mask_size = mask.GetSize()
    print(f"图像尺寸: {img_size}, Mask尺寸: {mask_size}")

    if img_size != mask_size:
        print(f"⚠️ 警告: 图像尺寸 {img_size} 与mask尺寸 {mask_size} 不匹配!")
        # 尝试调整mask尺寸
        if len(img_size) == 3 and len(mask_size) == 3:
            # 如果只是顺序不同，尝试转置
            if img_size == tuple(reversed(mask_size)):
                print("尝试转置mask...")
                mask_arr = np.transpose(mask_arr, (2, 1, 0))
                mask = sitk.GetImageFromArray(mask_arr)
                mask.CopyInformation(img)
                mask_size = mask.GetSize()
                print(f"转置后Mask尺寸: {mask_size}")

    return mask

def setup_extractor():
    """设置PyRadiomics特征提取器"""
    settings = {
        'binWidth': 25,
        'resampledPixelSpacing': None,
        'interpolator': sitk.sitkBSpline,
        'enableCExtensions': True,
        'featureClass': {
            'firstorder': [],  # 不用内置 firstorder，改为自定义
            'glcm': ['JointAverage', 'JointEnergy', 'JointEntropy',
                     'MaximumProbability', 'Contrast', 'Correlation'],
            'glrlm': ['GrayLevelNonUniformity', 'RunLengthNonUniformity',
                      'ShortRunEmphasis', 'LongRunEmphasis',
                      'RunPercentage', 'RunEntropy'],
            'glszm': ['GrayLevelNonUniformity', 'SizeZoneNonUniformity',
                      'ZonePercentage'],
            'shape': ['Elongation', 'Flatness', 'MajorAxisLength', 'MinorAxisLength']
        }
    }
    return featureextractor.RadiomicsFeatureExtractor(**settings)

def compute_custom_metrics(voxels):
    """计算自定义指标"""
    out = {}
    if voxels.size == 0:
        raise ValueError("mask contains no voxels")

    out['mean'] = float(np.mean(voxels))                                   # 1
    out['variance'] = float(np.var(voxels))                                # 2
    out['joint_mean'] = float(np.mean(voxels))                             # 3 (近似)
    out['joint_intensity'] = float(np.sum(voxels))                         # 4 累积强度
    out['randomness'] = float(stats.entropy(np.histogram(voxels, bins=256)[0]+1e-12))  # 5
    out['10_percentile'] = float(np.percentile(voxels, 10))                # 7
    out['90_percentile'] = float(np.percentile(voxels, 90))                # 8
    out['sum_of_squares'] = float(np.sum(np.square(voxels)))               # 9
    out['density_entropy'] = out['randomness']                             # 10 (同随机性)
    out['max'] = float(np.max(voxels))                                     # 11
    out['density_mean'] = out['mean']                                      # 12
    out['mean_abs_deviation'] = float(np.mean(np.abs(voxels - out['mean']))) # 13
    out['median'] = float(np.median(voxels))                               # 14
    low, high = np.percentile(voxels, [5,95])                              # 15
    trimmed = voxels[(voxels >= low) & (voxels <= high)]
    out['robust_pulse_sqdiff'] = float(np.mean(np.square(trimmed - np.mean(trimmed))))
    skew = float(stats.skew(voxels, bias=False))                           # 16–17
    kurt = float(stats.kurtosis(voxels, fisher=True, bias=False))
    out['texture_prominence'] = max(0.0, skew)   # 16 突出度
    out['texture_depression'] = max(0.0, -skew)  # 17 凹陷度
    out['texture_flatness'] = 1.0 / (1.0 + abs(kurt))                      # 18
    diffs = np.abs(np.diff(voxels))                                        # 20
    out['intensity_change_rate'] = float(np.mean(diffs))
    return out

def compute_features(study_uid, series_uid, mask_data):
    """计算Radiomics特征的主函数"""
    try:
        # 1. 构建DICOM文件路径
        # 假设DICOM文件按 study_uid/series_uid 组织
        dicom_folder = os.path.join(DICOM_BASE_DIR, study_uid, series_uid)

        if not os.path.exists(dicom_folder):
            raise ValueError(f"DICOM文件夹不存在: {dicom_folder}")

        # 2. 加载 DICOM 图像
        print("=" * 60)
        print("步骤1: 加载DICOM图像")
        print("=" * 60)
        img = load_dicom_series(dicom_folder)

        # 3. 加载 mask
        print("\n" + "=" * 60)
        print("步骤2: 加载Mask")
        print("=" * 60)
        mask = load_mask_from_json(mask_data, img)

        # 4. 验证mask和图像尺寸
        img_size = img.GetSize()
        mask_size = mask.GetSize()
        if img_size != mask_size:
            raise ValueError(f"图像尺寸 {img_size} 与mask尺寸 {mask_size} 不匹配!")

        # 5. 提取特征
        print("\n" + "=" * 60)
        print("步骤3: 提取PyRadiomics特征")
        print("=" * 60)
        print("⚠️ 注意: 纹理特征计算可能需要较长时间，请耐心等待...")
        extractor = setup_extractor()

        try:
            features = extractor.execute(img, mask, label=1)
            print(f"✅ PyRadiomics特征提取完成，共 {len(features)} 个特征")
        except Exception as e:
            print(f"⚠️ PyRadiomics特征提取出错: {e}")
            print("   尝试使用简化设置...")
            # 如果失败，尝试只计算部分特征
            simple_settings = {
                'binWidth': 25,
                'resampledPixelSpacing': None,
                'interpolator': sitk.sitkBSpline,
                'enableCExtensions': False,  # 禁用C扩展
                'featureClass': {
                    'firstorder': [],
                    'glcm': ['MaximumProbability'],  # 只计算一个
                    'glrlm': ['RunLengthNonUniformity'],  # 只计算一个
                    'glszm': ['ZonePercentage'],  # 只计算一个
                    'shape': ['MajorAxisLength', 'MinorAxisLength']  # 只计算形状特征
                }
            }
            extractor_simple = featureextractor.RadiomicsFeatureExtractor(**simple_settings)
            features = extractor_simple.execute(img, mask, label=1)
            print(f"✅ 简化版PyRadiomics特征提取完成，共 {len(features)} 个特征")

        # 6. 计算自定义指标
        print("\n" + "=" * 60)
        print("步骤4: 计算自定义指标")
        print("=" * 60)
        voxels = sitk.GetArrayFromImage(img)[sitk.GetArrayFromImage(mask) > 0]
        print(f"ROI中的体素数: {len(voxels)}")
        custom = compute_custom_metrics(voxels)
        print(f"✅ 自定义指标计算完成，共 {len(custom)} 个指标")

        # 7. 按需求整理输出特征
        print("\n" + "=" * 60)
        print("步骤5: 整理输出特征")
        print("=" * 60)
        selected = {}

        # 自定义指标
        selected.update({
            "灰度均值": custom['mean'],
            "灰度方差": custom['variance'],
            "联合分布均值": custom['joint_mean'],
            "联合分布强度": custom['joint_intensity'],
            "灰度随机性": custom['randomness'],
            "第10百分位CT值": custom['10_percentile'],
            "第90百分位CT值": custom['90_percentile'],
            "密度平方和": custom['sum_of_squares'],
            "密度随机性": custom['density_entropy'],
            "密度最大值": custom['max'],
            "密度平均值": custom['density_mean'],
            "平均绝对误差": custom['mean_abs_deviation'],
            "中位数": custom['median'],
            "鲁棒脉冲平方差": custom['robust_pulse_sqdiff'],
            "纹理突出度": custom['texture_prominence'],
            "纹理凹陷度": custom['texture_depression'],
            "纹理平坦度": custom['texture_flatness'],
            "变化速度": custom['intensity_change_rate'],
        })

        # PyRadiomics 指标（使用get方法避免KeyError）
        pyradiomics_features = {
            "GLCM最大频率值": features.get('original_glcm_MaximumProbability'),
            "纹理对比度": features.get('original_glcm_Contrast'),
            "纹理相关性": features.get('original_glcm_Correlation'),
            "行程灰度相似度": features.get('original_glrlm_GrayLevelNonUniformity'),
            "灰度行程重要性": features.get('original_glrlm_RunLengthNonUniformity'),
            "行程长度不确定性": features.get('original_glrlm_RunEntropy'),
            "行程长度分布相似性": features.get('original_glrlm_ShortRunEmphasis'),
            "行程长度比率": features.get('original_glrlm_RunPercentage'),
            "行程长度差异性": features.get('original_glrlm_LongRunEmphasis'),
            "灰度区域重要性": features.get('original_glszm_GrayLevelNonUniformity'),
            "灰度区域比率": features.get('original_glszm_ZonePercentage'),
            "灰度区域差异性": features.get('original_glszm_SizeZoneNonUniformity'),
            "延展性": features.get('original_shape_Elongation'),
            "平滑度": features.get('original_shape_Flatness'),
            "椭圆最长直径": features.get('original_shape_MajorAxisLength'),
            "椭圆最短直径": features.get('original_shape_MinorAxisLength'),
        }

        # 只添加成功计算的特征
        for key, value in pyradiomics_features.items():
            if value is not None:
                selected[key] = value
            else:
                print(f"⚠️ 警告: 特征 '{key}' 计算失败，使用默认值")
                selected[key] = 'N/A'

        print("\n" + "=" * 60)
        print("✅ 所有步骤完成!")
        print("=" * 60)

        return selected

    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ 错误发生:")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        raise


# Flask API路由
@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        "status": "healthy",
        "message": "Radiomics API服务运行正常"
    }), 200


@app.route('/api/radiomics', methods=['POST'])
def calculate_radiomics():
    """计算Radiomics特征的API接口"""
    try:
        # 获取请求数据
        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "error": "请求体不能为空"
            }), 400

        # 验证必需参数
        study_uid = data.get('study_uid')
        series_uid = data.get('series_uid')
        mask = data.get('mask')

        if not study_uid:
            return jsonify({
                "success": False,
                "error": "缺少必需参数: study_uid"
            }), 400

        if not series_uid:
            return jsonify({
                "success": False,
                "error": "缺少必需参数: series_uid"
            }), 400

        if not mask:
            return jsonify({
                "success": False,
                "error": "缺少必需参数: mask"
            }), 400

        # 计算特征
        features = compute_features(study_uid, series_uid, mask)

        # 返回结果
        return jsonify({
            "success": True,
            "study_uid": study_uid,
            "series_uid": series_uid,
            "features": features,
            "feature_count": len(features)
        }), 200

    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ API错误: {error_trace}")
        return jsonify({
            "success": False,
            "error": f"计算特征时发生错误: {str(e)}"
        }), 500


if __name__ == "__main__":
    # 开发环境
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
