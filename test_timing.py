#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试脚本：测量API响应时间和各阶段处理时间
"""

import json
import time
import argparse
from datetime import datetime
from factcheck.core.Retriever.serper_retriever import SerperEvidenceRetriever
from factcheck.utils.logger import CustomLogger

logger = CustomLogger(__name__).getlog()

class TimingTest:
    def __init__(self, test_file, api_key):
        """初始化测试类"""
        self.test_file = test_file
        self.api_key = api_key
        self.api_config = {
            "SERPER_API_KEY": self.api_key,
            "CLOUDSWAY_API_URL": "https://searchapi.cloudsway.net/search/NbYyRVhrORhcVYNm/full"
        }
        self.retriever = SerperEvidenceRetriever(None, self.api_config)
        self.test_data = self._load_test_data()
        
    def _load_test_data(self):
        """加载测试数据"""
        try:
            with open(self.test_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载测试数据失败: {e}")
            return []
            
    def run_tests(self):
        """运行所有测试"""
        results = []
        
        for idx, item in enumerate(self.test_data):
            logger.info(f"测试数据 {idx+1}/{len(self.test_data)}: {item.get('id', 'unknown')}")
            
            # 准备测试数据
            test_id = item.get('id')
            test_query = item.get('response', '')
            
            # 创建测试结果对象
            result = {
                "id": test_id,
                "query": test_query[:50] + "..." if len(test_query) > 50 else test_query,
                "timing": {}
            }
            
            # 运行测试并记录时间
            self._run_single_test(test_query, result)
            
            # 添加到结果列表
            results.append(result)
            
        return results
    
    def _run_single_test(self, query, result):
        """运行单个测试并记录各阶段时间"""
        # 记录总开始时间
        total_start_time = time.time()
        
        try:
            # 阶段1: 准备查询
            prep_start = time.time()
            claim_queries_dict = {"test_claim": [query]}
            prep_end = time.time()
            
            # 阶段2: API请求
            api_start = time.time()
            query_list = [y for x in claim_queries_dict.items() for y in x[1]]
            evidence_list = []
            
            for i in range(0, len(query_list), 100):
                batch_query_list = query_list[i: i + 100]
                batch_response = self.retriever._request_serper_api(batch_query_list)
                if batch_response is not None:
                    evidence_list.extend(batch_response)
            api_end = time.time()
            
            # 阶段3: 处理结果
            process_start = time.time()
            # 简单处理一下结果，实际项目中可能有更复杂的处理
            processed_results = []
            for resp in evidence_list:
                if isinstance(resp, dict) and "error" not in resp:
                    web_pages = resp.get("webPages", {}).get("value", [])
                    for page in web_pages[:3]:  # 只取前3个结果
                        processed_results.append({
                            "title": page.get("name", ""),
                            "url": page.get("url", ""),
                            "snippet": page.get("snippet", "")[:100] + "..."
                        })
            process_end = time.time()
            
            # 记录总结束时间
            total_end_time = time.time()
            
            # 计算各阶段时间
            result["timing"] = {
                "preparation_time": round(prep_end - prep_start, 3),
                "api_request_time": round(api_end - api_start, 3),
                "processing_time": round(process_end - process_start, 3),
                "total_time": round(total_end_time - total_start_time, 3)
            }
            
            # 记录结果数量
            result["result_count"] = len(processed_results)
            result["success"] = True
            
        except Exception as e:
            # 记录总结束时间
            total_end_time = time.time()
            
            # 记录错误信息
            result["timing"] = {
                "total_time": round(total_end_time - total_start_time, 3)
            }
            result["error"] = str(e)
            result["success"] = False
            
        return result

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="测试API响应时间和各阶段处理时间")
    parser.add_argument("--test_file", type=str, default="test_first_3.json", help="测试数据文件路径")
    parser.add_argument("--api_key", type=str, default="YAJGspbmOFvKPc4qSCsA", help="API密钥")
    parser.add_argument("--output", type=str, default="timing_results.json", help="输出结果文件路径")
    
    args = parser.parse_args()
    
    # 创建测试实例
    tester = TimingTest(args.test_file, args.api_key)
    
    # 运行测试
    logger.info(f"开始测试，使用测试文件: {args.test_file}")
    start_time = time.time()
    results = tester.run_tests()
    end_time = time.time()
    
    # 输出总结
    logger.info(f"测试完成，总耗时: {round(end_time - start_time, 3)}秒")
    logger.info(f"测试数据数量: {len(tester.test_data)}")
    success_count = sum(1 for r in results if r.get("success", False))
    logger.info(f"成功测试数量: {success_count}/{len(results)}")
    
    # 输出详细结果
    for result in results:
        logger.info(f"ID: {result.get('id')}, 成功: {result.get('success')}")
        if result.get("success"):
            timing = result.get("timing", {})
            logger.info(f"  总时间: {timing.get('total_time')}秒")
            logger.info(f"  准备时间: {timing.get('preparation_time')}秒")
            logger.info(f"  API请求时间: {timing.get('api_request_time')}秒")
            logger.info(f"  处理时间: {timing.get('processing_time')}秒")
            logger.info(f"  结果数量: {result.get('result_count', 0)}")
        else:
            logger.error(f"  错误: {result.get('error')}")
    
    # 保存结果到文件
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "test_file": args.test_file,
        "total_tests": len(results),
        "successful_tests": success_count,
        "total_time": round(end_time - start_time, 3),
        "results": results
    }
    
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"结果已保存到: {args.output}")

if __name__ == "__main__":
    main()