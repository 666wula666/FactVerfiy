"""
CloudswaySearchClient 同步测试脚本
使用同步方法测试 CloudswaySearchClient 的基本功能
"""

import json
import requests
import sys
import logging
from urllib.parse import quote

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

class CloudswaySearchClientSync:
    """CloudswaySearchClient 的同步版本，用于测试"""

    # Cloudsway API endpoint
    FULLTEXT_URL = "https://searchapi.cloudsway.net/search/NbYyRVhrORhcVYNm/full"

    def __init__(self):
        """初始化搜索客户端"""
        self.api_key = "YAJGspbmOFvKPc4qSCsA"
        if not self.api_key:
            raise ValueError("CLOUDSWAY_API_KEY environment variable is required")

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def search(self, query, count=10, sites=None, include_raw_content=False):
        """执行同步搜索查询"""
        # URL encode query
        encoded_query = quote(query)

        # Build request parameters
        params = {"q": encoded_query, "count": count}

        # Add sites filter if provided
        if sites:
            sites_str = ",".join(sites) if isinstance(sites, list) else str(sites)
            params["sites"] = sites_str

        # Always use fulltext endpoint to get mainText (long summary)
        endpoint_url = self.FULLTEXT_URL
        params["mainText"] = "True"

        try:
            # 尝试不同的认证方法
            return self._search_with_retry(endpoint_url, params, query, include_raw_content)
        except Exception as e:
            logger.error(f"搜索出错: {str(e)}")
            return self._empty_result(query)

    def _search_with_retry(self, endpoint_url, params, query, include_raw_content):
        """使用重试逻辑的内部搜索方法"""
        # 尝试不同的认证方法
        auth_methods = [
            # 方法1: Bearer 认证
            {"headers": {"Authorization": f"Bearer {self.api_key}"}},
            # 方法2: API Key 认证
            {"headers": {"X-API-KEY": self.api_key}},
            # 方法3: 自定义 API-Key 头
            {"headers": {"API-Key": self.api_key}},
            # 方法4: 自定义 apikey 头
            {"headers": {"apikey": self.api_key}},
            # 方法5: URL 参数认证
            {"params": {"api_key": self.api_key}},
        ]

        last_error = None
        for auth_method in auth_methods:
            try:
                # 合并认证参数
                request_params = params.copy()
                if "params" in auth_method:
                    request_params.update(auth_method["params"])
                
                # 合并头信息
                headers = {}
                if "headers" in auth_method:
                    headers.update(auth_method["headers"])
                
                # 发送请求
                logger.info(f"尝试使用认证方法: {auth_method}")
                response = self.session.get(
                    endpoint_url, 
                    params=request_params,
                    headers=headers,
                    timeout=10
                )
                
                # 处理响应
                if response.status_code == 200:
                    logger.info(f"搜索成功，状态码: {response.status_code}")
                    data = response.json()
                    return self._transform_to_tavily_format(
                        data, query, response.headers.get("x-ws-request-id"), include_raw_content
                    )
                else:
                    logger.warning(f"请求失败，状态码: {response.status_code}")
                    response.raise_for_status()
            
            except requests.exceptions.RequestException as e:
                last_error = e
                logger.warning(f"请求异常: {str(e)}")
                continue
        
        # 所有认证方法都失败
        if last_error:
            raise last_error
        return self._empty_result(query)

    def _transform_to_tavily_format(self, response, query, request_id, include_raw_content):
        """转换 Cloudsway API 响应为 Tavily 兼容格式"""
        # 解析响应为字典
        data = self._parse_response(response)
        if not isinstance(data, dict):
            return self._empty_result(query)

        # 提取原始查询
        original_query = (
            (data.get("queryContext") or {}).get("originalQuery")
            or data.get("query")
            or query
        )

        # 初始化 Tavily 兼容的结果结构
        result = {
            "query": original_query,
            "follow_up_questions": None,
            "answer": None,
            "images": [],
            "results": [],
            "response_time": None,
            "request_id": request_id,
        }

        # 提取网页结果
        web_values = []
        if isinstance(data.get("webPages"), dict) and isinstance(
            data["webPages"].get("value"), list
        ):
            web_values = data["webPages"]["value"]
        elif isinstance(data.get("results"), list):
            web_values = data["results"]

        # 转换每个结果
        for web_page in web_values:
            if not isinstance(web_page, dict):
                continue

            url = web_page.get("url") or ""
            title = web_page.get("name") or ""
            snippet = web_page.get("snippet") or ""
            main_text = web_page.get("mainText") or ""
            full_content = web_page.get("content") or ""
            score = web_page.get("score", 0.0)

            # 内容映射逻辑
            if main_text:
                content_field = main_text
            elif include_raw_content:
                content_field = full_content or snippet
            else:
                content_field = snippet

            # 原始内容映射
            raw_content = None
            if include_raw_content:
                raw_content = full_content

            result["results"].append({
                "url": url,
                "title": title,
                "content": content_field,
                "score": score,
                "raw_content": raw_content,
                "favicon": None,
            })

        return result

    def _parse_response(self, response):
        """解析响应为字典"""
        if isinstance(response, dict):
            return response

        if isinstance(response, (bytes, bytearray)):
            try:
                return json.loads(response.decode("utf-8", "ignore"))
            except json.JSONDecodeError as e:
                logger.warning(f"解析字节响应失败: {e}")
                return {}

        if isinstance(response, str):
            if not response.strip():
                logger.warning("空字符串响应")
                return {}
            try:
                return json.loads(response)
            except json.JSONDecodeError as e:
                logger.warning(f"无效的 JSON 响应: {e}")
                return {}

        logger.warning(f"不支持的响应类型: {type(response)}")
        return {}

    def _empty_result(self, query):
        """返回空结果结构"""
        return {
            "query": query,
            "follow_up_questions": None,
            "answer": None,
            "images": [],
            "results": [],
            "response_time": None,
            "request_id": None,
        }


def main():
    """主函数"""
    # 创建客户端
    client = CloudswaySearchClientSync()
    
    # 测试查询
    queries =  ['How large was the territory of Yuan Dynasty', 'What territories did the Qing Dynasty incorporate into its governance?']
    
    for query in queries:
        print(f"\n执行查询: {query}")
        
        # 执行搜索
        results = client.search(
            query=query,
            count=1,  # 限制结果数量
            include_raw_content=False  # 不包含完整内容
        )
        
        # 打印查询结果
        print(f"查询: {results['query']}")
        print(f"结果数量: {len(results['results'])}")
        
        # 打印每个结果的标题和URL
        for i, result in enumerate(results['results'], 1):
            print(f"\n结果 {i}:")
            print(f"标题: {result['title']}")
            print(f"URL: {result['url']}")
            print(f"内容摘要: {result['content'][:150]}..." if result['content'] else "无内容")


if __name__ == "__main__":
    main()