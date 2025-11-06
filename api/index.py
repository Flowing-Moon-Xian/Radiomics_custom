# Vercel Serverless Function入口
# Vercel Python运行时需要的格式
import sys
import os

# 添加父目录到路径，以便导入主应用
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# 从主应用文件导入app对象
from radiomics_custom_example import app

# Vercel Python运行时需要导出app对象
# 这是Vercel识别的标准格式
