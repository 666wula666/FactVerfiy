import json
import logging
from typing import Optional, List, Dict, Any, Union
from typing_extensions import TypeAlias
from urllib.parse import quote

import aiohttp
from tenacity import (
    retry, 
    stop_after_attempt, 
    wait_exponential, 
    retry_if_exception_type, 
    RetryError
)

# 配置日志
logger = logging.getLogger(__name__)

# 自定义异常类
class RateLimitError(Exception):
    """API速率限制异常"""
    pass

class RetryableError(Exception):
    """可重试的临时错误"""
    pass

class CloudswaySearchClient:
    """
    High-performance async Cloudsway search client with connection pooling.

    Uses aiohttp.ClientSession with:
    - Connection pooling via TCPConnector
    - Connection reuse via keep-alive
    - Automatic session lifecycle management
    """

    # Cloudsway API endpoint
    FULLTEXT_URL = "https://searchapi.cloudsway.net/search/NbYyRVhrORhcVYNm/full"

    def __init__(self):
        """
        Initialize Cloudsway search client.

        Required ENV variables:
        - CLOUDSWAY_API_KEY: API authentication key
        """
        self.api_key = "YAJGspbmOFvKPc4qSCsA"
        if not self.api_key:
            raise ValueError("CLOUDSWAY_API_KEY environment variable is required")

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        # Async HTTP session (initialized lazily)
        self._session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """
        Ensure async HTTP session is initialized.

        Creates aiohttp.ClientSession with:
        - Connection pooling (max 100 connections)
        - Keep-alive for connection reuse
        - 30s timeout for requests
        """
        if self._session is None or self._session.closed:
            # Create connector with connection pooling
            connector = aiohttp.TCPConnector(
                limit=100,           # Max total connections
                limit_per_host=20,   # Max connections per host
                ttl_dns_cache=300,   # DNS cache TTL (5 minutes)
            )

            # Create timeout configuration
            timeout = aiohttp.ClientTimeout(total=30.0)

            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self.headers,
            )
            logger.debug("Initialized aiohttp.ClientSession with connection pooling")
        return self._session

    async def close(self):
        """Close the async HTTP session and release connections."""
        if self._session is not None and not self._session.closed:
            await self._session.close()
            logger.debug("Closed aiohttp.ClientSession")

    @retry(
        stop=stop_after_attempt(4),  # Initial + 3 retries
        wait=wait_exponential(multiplier=1, min=1, max=10),  # 1s, 2s, 4s, 8s (capped at 10s)
        retry=retry_if_exception_type((RateLimitError, RetryableError)),
        reraise=True,
    )
    async def _search_with_retry(
        self,
        session: aiohttp.ClientSession,
        endpoint_url: str,
        params: dict,
        query: str,
        include_raw_content: bool,
    ) -> dict:
        """
        Internal method with retry logic for transient errors.

        Uses tenacity for exponential backoff retry on:
        - RateLimitError (429)
        - RetryableError (500, 502, 503, 504, timeouts, connection errors)
        """
        try:
            async with session.get(endpoint_url, params=params) as response:
                # Handle rate limit (429) - always retry
                if response.status == 429:
                    logger.warning(f"Cloudsway rate limit (429) for query: {query}, retrying...")
                    raise RateLimitError(f"Rate limit exceeded for query: {query}")

                # Handle server errors (5xx) - retry
                if response.status >= 500:
                    logger.warning(
                        f"Cloudsway server error ({response.status}) for query: {query}, retrying..."
                    )
                    raise RetryableError(f"Server error {response.status} for query: {query}")

                # Handle other errors (4xx except 429) - don't retry
                response.raise_for_status()

                # Log request metadata
                request_id = response.headers.get("x-ws-request-id")
                logger.info(f"Cloudsway search query: {query}, request_id: {request_id}")

                # Parse JSON response
                data = await response.json()

                # Transform response to Tavily format
                result = self._transform_to_tavily_format(
                    data, query, request_id, include_raw_content
                )
                return result

        except aiohttp.ClientTimeout as e:
            # Timeout - retry
            logger.warning(f"Cloudsway timeout for query: {query}, retrying...")
            raise RetryableError(f"Timeout for query: {query}") from e

        except aiohttp.ClientConnectionError as e:
            # Connection error - retry
            logger.warning(f"Cloudsway connection error for query: {query}, retrying...")
            raise RetryableError(f"Connection error for query: {query}") from e

        except aiohttp.ServerDisconnectedError as e:
            # Server disconnected - retry
            logger.warning(f"Cloudsway server disconnected for query: {query}, retrying...")
            raise RetryableError(f"Server disconnected for query: {query}") from e

    async def search(
        self,
        query: str,
        count: int = 10,
        sites: Optional[list[str]] = None,
        include_raw_content: bool = False,
    ) -> dict:
        """
        Execute async search query with automatic retry for transient errors (non-blocking).

        Always uses the fulltext endpoint to access mainText (long summary).
        Automatically retries on transient errors with exponential backoff (max 3 retries):
        - 429 (rate limit)
        - 5xx (server errors)
        - Timeouts
        - Connection errors

        Args:
            query: Search query string
            count: Maximum number of results to return (default: 10)
            sites: Optional list of domains to restrict search to
            include_raw_content: If True, include full page content in raw_content field

        Returns:
            dict: Tavily-compatible search results with content mapping:
                - content field: mainText (long summary, ~300-400 chars) if available,
                                fallback to snippet (~100 chars) if mainText not available
                - raw_content field: full content (~3500 chars) if include_raw_content=True,
                                    None otherwise
        """
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

        # Ensure session is initialized
        session = await self._ensure_session()

        try:
            # Execute search with automatic retry on transient errors
            return await self._search_with_retry(
                session, endpoint_url, params, query, include_raw_content
            )

        except RetryError as e:
            # Max retries exceeded - determine error type from cause
            original_error = e.last_attempt.exception()
            if isinstance(original_error, RateLimitError):
                logger.error(f"Cloudsway rate limit (429) exceeded max retries for query: {query}")
            else:
                logger.error(f"Cloudsway transient error exceeded max retries for query: {query}")
            return self._empty_result(query)
        except aiohttp.ClientResponseError as e:
            # Non-retryable client errors (4xx except 429)
            logger.error(f"Cloudsway API error: {e.status} - {e.message} for query: {query}")
            return self._empty_result(query)
        except Exception as e:
            # Unexpected errors
            logger.exception(f"Unexpected error in Cloudsway search for query: {query}: {str(e)}")
            return self._empty_result(query)

    def _transform_to_tavily_format(
        self,
        response: dict | str | bytes,
        query: str,
        request_id: Optional[str],
        include_raw_content: bool,
    ) -> dict:
        """
        Transform Cloudsway API response to Tavily-compatible format.

        Handles multiple input types: dict, JSON string, or bytes.

        Content mapping strategy:
        - content field: Prioritizes mainText (long summary, ~300-400 chars)
                        Falls back to snippet if mainText unavailable
        - raw_content field: Full content (~3500 chars) when include_raw_content=True
        """
        # Parse response to dict
        data = self._parse_response(response)
        if not isinstance(data, dict):
            return self._empty_result(query)

        # Extract original query from response (fallback to input query)
        original_query = (
            (data.get("queryContext") or {}).get("originalQuery")
            or data.get("query")
            or query
        )

        # Initialize Tavily-compatible result structure
        result = {
            "query": original_query,
            "follow_up_questions": None,
            "answer": None,
            "images": [],
            "results": [],
            "response_time": None,
            "request_id": request_id,
        }

        # Extract web results from different possible response structures
        web_values = []
        if isinstance(data.get("webPages"), dict) and isinstance(
            data["webPages"].get("value"), list
        ):
            web_values = data["webPages"]["value"]
        elif isinstance(data.get("results"), list):
            web_values = data["results"]

        # Transform each result
        for web_page in web_values:
            if not isinstance(web_page, dict):
                continue

            url = web_page.get("url") or ""
            title = web_page.get("name") or ""
            snippet = web_page.get("snippet") or ""
            main_text = web_page.get("mainText") or ""
            full_content = web_page.get("content") or ""
            score = web_page.get("score", 0.0)

            # Content mapping logic:
            # - Always prefer mainText (long summary, ~300-400 chars) for content field
            # - If mainText not available:
            #   - include_raw_content=False: use snippet (short summary, ~100 chars)
            #   - include_raw_content=True: use content (full content, ~3500 chars)
            if main_text:
                content_field = main_text
            elif include_raw_content:
                content_field = full_content or snippet
            else:
                content_field = snippet

            # Raw content mapping:
            # - include_raw_content=False: None
            # - include_raw_content=True: full content field (~3500 chars)
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

    def _parse_response(self, response: dict | str | bytes) -> dict:
        """Parse response from various formats to dict."""
        if isinstance(response, dict):
            return response

        if isinstance(response, (bytes, bytearray)):
            try:
                return json.loads(response.decode("utf-8", "ignore"))
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to decode bytes response: {e}")
                return {}

        if isinstance(response, str):
            if not response.strip():
                logger.warning("Empty string response")
                return {}
            try:
                return json.loads(response)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON response: {e}")
                return {}

        logger.warning(f"Unsupported response type: {type(response)}")
        return {}

    def _empty_result(self, query: str) -> dict:
        """Return empty result structure for error cases."""
        return {
            "query": query,
            "follow_up_questions": None,
            "answer": None,
            "images": [],
            "results": [],
            "response_time": None,
            "request_id": None,
        }


async def main():
    """
    测试 CloudswaySearchClient 的主函数
    演示如何初始化客户端、执行搜索并处理结果
    """
    import asyncio
    import sys
    import os
    
    # 设置日志级别，便于观察请求过程
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )
    
    # 创建搜索客户端
    client = CloudswaySearchClient()
    
    try:
        # 测试查询
        queries = [
            "中国历史朝代",
            "人工智能最新发展"
        ]
        
        for query in queries:
            print(f"\n执行查询: {query}")
            
            # 执行搜索
            results = await client.search(
                query=query,
                count=5,  # 限制结果数量
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
                
    except Exception as e:
        print(f"发生错误: {str(e)}")
    finally:
        # 关闭客户端会话
        await client.close()
        print("\n客户端会话已关闭")


if __name__ == "__main__":
    import asyncio
    import sys
    
    # 在Windows上需要使用不同的事件循环策略
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # 运行主函数
    asyncio.run(main())