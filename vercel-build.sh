#!/bin/bash
# Vercel 构建脚本
# 确保使用正确的 Python 版本和工具

echo "Installing build dependencies..."
pip install --upgrade pip setuptools wheel build

echo "Installing project dependencies..."
pip install -r requirements.txt

