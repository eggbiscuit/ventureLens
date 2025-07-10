"""
VentureLens - AI辅助的投资尽职调查MVP系统
主入口文件
"""

import asyncio
import logging
import json
import argparse
import os
from typing import Optional

from graph import VentureLensWorkflow


def setup_logging(level: str = "INFO") -> None:
    """设置日志"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('venturelens.log', encoding='utf-8')
        ]
    )


def load_config(config_path: str = "config.json") -> dict:
    """加载配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 从环境变量中读取API密钥
        config["llm"]["openrouter_api_key"] = os.getenv(
            "OPENROUTER_API_KEY", 
            config["llm"].get("openrouter_api_key", "")
        )
        
        config["search"]["tavily_api_key"] = os.getenv(
            "TAVILY_API_KEY",
            config["search"].get("tavily_api_key", "")
        )
        
        config["search"]["serper_api_key"] = os.getenv(
            "SERPER_API_KEY",
            config["search"].get("serper_api_key", "")
        )
        
        return config
        
    except FileNotFoundError:
        logging.error(f"Configuration file {config_path} not found")
        raise
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing configuration file: {e}")
        raise


async def main(company_name: str, bp_file_path: Optional[str] = None, 
               config_path: str = "config.json", run_id: Optional[str] = None,
               log_level: str = "INFO") -> None:
    """主函数"""
    
    # 设置日志
    setup_logging(log_level)
    logger = logging.getLogger(__name__)
    
    try:
        # 加载配置
        config = load_config(config_path)
        
        # 检查必要的配置
        if not config["llm"]["openrouter_api_key"]:
            logger.warning("OpenRouter API key not configured")
        
        # 创建工作流
        workflow = VentureLensWorkflow(config)
        
        # 运行尽调流程
        logger.info(f"Starting due diligence for: {company_name}")
        
        if bp_file_path and not os.path.exists(bp_file_path):
            logger.warning(f"BP file not found: {bp_file_path}")
            bp_file_path = None
        
        state = await workflow.run(company_name, bp_file_path, run_id)
        
        # 输出结果
        if state.get("final_report"):
            print("\n" + "="*50)
            print("VENTURELENS 尽职调查报告")
            print("="*50)
            print(state["final_report"])
            print("="*50)
            
            # 输出保存位置
            output_dir = config.get("output", {}).get("report_directory", "./report")
            report_file = f"{company_name}_{state['run_id']}_report.md"
            print(f"\n报告已保存至: {os.path.join(output_dir, report_file)}")
        else:
            print("❌ 未能生成报告")
        
        # 显示Agent状态
        status = workflow.get_agent_status(state)
        print(f"\nAgent执行状态:")
        for agent, agent_status in status.items():
            status_emoji = {"completed": "✅", "running": "🔄", "pending": "⏳"}
            print(f"  {status_emoji.get(agent_status, '❓')} {agent}: {agent_status}")
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        raise


def cli():
    """命令行接口"""
    parser = argparse.ArgumentParser(description="VentureLens - AI辅助的投资尽职调查系统")
    
    parser.add_argument("company_name", help="目标公司名称")
    parser.add_argument("--bp-file", help="商业计划书文件路径（可选）")
    parser.add_argument("--config", default="config.json", help="配置文件路径")
    parser.add_argument("--run-id", help="运行ID（用于恢复中断的流程）")
    parser.add_argument("--log-level", default="INFO", 
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="日志级别")
    
    args = parser.parse_args()
    
    # 运行主函数
    asyncio.run(main(
        company_name=args.company_name,
        bp_file_path=args.bp_file,
        config_path=args.config,
        run_id=args.run_id,
        log_level=args.log_level
    ))


if __name__ == "__main__":
    cli()
