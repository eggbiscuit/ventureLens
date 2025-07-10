#!/bin/bash

# VentureLens 系统运行脚本

echo "=== 启动 VentureLens 投资尽职调查系统 ==="

# 检查依赖
echo "检查 Python 依赖..."
python3 -c "import aiohttp, asyncio, json, logging" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "错误：缺少必要的Python依赖，请运行：pip install -r requirements.txt"
    exit 1
fi

# 检查配置文件
if [ ! -f "config.json" ]; then
    echo "错误：未找到配置文件 config.json"
    echo "请参考 README.md 创建配置文件"
    exit 1
fi

# 默认参数
COMPANY_NAME="默认公司"
LOG_LEVEL="INFO"
SAVE_STATE=""

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--company)
            COMPANY_NAME="$2"
            shift 2
            ;;
        -l|--log-level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        -s|--save-state)
            SAVE_STATE="$2"
            shift 2
            ;;
        -h|--help)
            echo "使用方法: $0 [选项]"
            echo "选项:"
            echo "  -c, --company NAME      指定要分析的公司名称"
            echo "  -l, --log-level LEVEL   设置日志级别 (DEBUG, INFO, WARNING, ERROR)"
            echo "  -s, --save-state FILE   指定状态保存文件"
            echo "  -h, --help              显示此帮助信息"
            echo ""
            echo "示例:"
            echo "  $0 -c \"小米科技\" -l DEBUG"
            echo "  $0 --company \"蔚来汽车\" --save-state state.json"
            exit 0
            ;;
        *)
            echo "未知选项: $1"
            echo "使用 $0 --help 查看帮助"
            exit 1
            ;;
    esac
done

# 创建日志目录
mkdir -p logs

# 运行系统
echo "正在分析公司: $COMPANY_NAME"
echo "日志级别: $LOG_LEVEL"

python3 main.py \
    "$COMPANY_NAME" \
    --log-level "$LOG_LEVEL" \
    ${SAVE_STATE:+--run-id "$SAVE_STATE"}

# 检查运行结果
if [ $? -eq 0 ]; then
    echo "=== VentureLens 分析完成 ==="
    echo "检查 report/ 目录查看生成的报告"
    echo "检查 logs/ 目录查看详细日志"
else
    echo "=== VentureLens 分析失败 ==="
    echo "请检查日志文件了解详细错误信息"
    exit 1
fi
