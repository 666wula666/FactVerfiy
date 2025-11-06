from concurrent.futures import ThreadPoolExecutor
import json
from urllib.parse import quote

import requests
import os
import re
import bs4
import asyncio
import aiohttp
from factcheck.utils.logger import CustomLogger
from factcheck.utils.web_util import crawl_web

logger = CustomLogger(__name__).getlog()


class SerperEvidenceRetriever:
    def __init__(self, llm_client, api_config: dict = None):
        """Initialize the SerperEvidenceRetrieve class"""
        # self.lang = "en"
        self.serper_key = api_config["SERPER_API_KEY"]
        self.serper_url = api_config["CLOUDSWAY_API_URL"]
        self.api_config = api_config
        self.llm_client = llm_client

    def retrieve_evidence(self, claim_queries_dict, top_k: int = 3, snippet_extend_flag: bool = True):
        """Retrieve evidences for the given claims

        Args:
            claim_queries_dict (dict): a dictionary of claims and their corresponding queries.
            top_k (int, optional): the number of top relevant results to retrieve. Defaults to 3.
            snippet_extend_flag (bool, optional): whether to extend the snippet. Defaults to True.

        Returns:
            dict: a dictionary of claims and their corresponding evidences.
        """
        logger.info("Collecting evidences ...")
        query_list = [y for x in claim_queries_dict.items() for y in x[1]]
        evidence_list = self._retrieve_evidence_4_all_claim(
            query_list=query_list, top_k=top_k, snippet_extend_flag=snippet_extend_flag
        )

        i = 0
        claim_evidence_dict = {}
        for claim, queries in claim_queries_dict.items():
            evidences_per_query_L = evidence_list[i : i + len(queries)]
            claim_evidence_dict[claim] = [e for evidences in evidences_per_query_L for e in evidences]
            i += len(queries)
        assert i == len(evidence_list)
        logger.info("Collect evidences done!")
        return claim_evidence_dict

    def _retrieve_evidence_4_all_claim(
            self, query_list: list[str], top_k: int = 3, snippet_extend_flag: bool = True
    ) -> list[list[str]]:
        """Retrieve evidences for the given queries

        Args:
            query_list (list[str]): a list of queries to retrieve evidences for.
            top_k (int, optional): the number of top relevant results to retrieve. Defaults to 3.
            snippet_extend_flag (bool, optional): whether to extend the snippet. Defaults to True.

        Returns:
            list[list[]]: a list of [a list of evidences for each given query].
        """

        # init the evidence list with None
        evidences = [[] for _ in query_list]

        # # get the response from tavily
        # serper_responses = []
        # for i in range(0, len(query_list), 100):
        #     batch_query_list = query_list[i: i + 100]
        #     batch_response = self._request_serper_api(batch_query_list)
        #     if batch_response is None:
        #         logger.error("Serper API request error!")
        #         return evidences
        #     else:
        #         serper_responses.extend(batch_response)
       
       
        serper_responses = []
        # Prefer async concurrent requests for better throughput
        try:
            serper_responses = asyncio.run(self._request_serper_api_async(query_list))
        except Exception as e:
            logger.warning(f"Async serper request failed ({e}), falling back to threaded requests.")
            response = self._request_serper_api(query_list)
            if response is None:
                logger.error("Serper API request error!")
                return evidences
            else:
                serper_responses.extend(response)


         # get the responses for queries
        query_url_dict = {}
        url_to_date = {}  # TODO: decide whether to use date
        _snippet_to_check = []
     
        for i, (query, response) in enumerate(zip(query_list, serper_responses)):
            # Tavily没有searchParameters字段，直接使用原始查询
            response_query = response.get("query", query)
            if query != response_query:
                logger.warning("Tavily changed query from {} TO {}".format(query, response_query))

            # Tavily的answer字段处理
            if response.get("answer"):  # 如果有answer字段
                evidences[i] = [
                    {
                        "text": f"{query}\nAnswer: {response['answer']}",
                        "url": "Tavily Answer Box",
                    }
                ]
            else:

                # topk_results = response["webPages"][:top_k]  # Choose top k response
                # 提取 webPages 中的 value 列表
                web_pages = response.get("webPages", {}).get("value", [])
                topk_results = web_pages[:top_k]  # Choose top 5 response
                if (len(_snippet_to_check) == 0) or (not snippet_extend_flag):
                    evidences[i] += [
                        {"text": re.sub(r"\n+", "\n", _result["snippet"]), "url": _result["url"]}
                        for _result in topk_results if "snippet" in _result and "url" in _result
                    ]

                # Save date for each url (Tavily可能没有date字段)
                for _result in topk_results:
                    if "url" in _result:
                        url_to_date.update({_result["url"]: _result.get("date", "")})
                        # Save query-url pair, 1 query may have multiple urls
                        current_urls = query_url_dict.get(query, [])
                        current_urls.append(_result["url"])
                        query_url_dict[query] = current_urls
                        # 收集需要检查的片段
                        _snippet_to_check.append(_result.get("snippet", ""))

        # return if there is no snippet to check or snippet_extend_flag is False
        if (len(_snippet_to_check) == 0) or (not snippet_extend_flag):
            return evidences

        # crawl web for queries without answer box
        responses = crawl_web(query_url_dict)
        # Get extended snippets based on the snippet from serper
        flag_to_check = [_item[0] for _item in responses]
        response_to_check = [_item[1] for _item in responses]
        url_to_check = [_item[2] for _item in responses]
        query_to_check = [_item[3] for _item in responses]

        def bs4_parse_text(response, snippet, flag):
            """Parse the text from the response and extend the snippet

            Args:
                response (web response): the response from the web
                snippet (str): the snippet to extend from the search result
                flag (bool): flag to extend the snippet

            Returns:
                _type_: _description_
            """
            if flag and response and ".pdf" not in str(response.url):
                try:
                    soup = bs4.BeautifulSoup(response.text, "html.parser")
                    text = soup.get_text()
                    # Search for the snippet in text
                    snippet_start = text.find(snippet[:-10]) if len(snippet) > 10 else text.find(snippet)
                    if snippet_start == -1:
                        return snippet
                    else:
                        pre_context_range = 0  # Number of characters around the snippet to display
                        post_context_range = 500  # Number of characters around the snippet to display
                        start = max(0, snippet_start - pre_context_range)
                        end = snippet_start + len(snippet) + post_context_range
                        return text[start:end] + " ..."
                except Exception as e:
                    logger.warning(f"Error parsing web content: {e}")
                    return snippet
            else:
                return snippet

        # Question: if os.cpu_count() cause problems when running in parallel?
        with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            _extended_snippet = list(
                executor.map(
                    lambda _r, _s, _f: bs4_parse_text(_r, _s, _f),
                    response_to_check,
                    _snippet_to_check,
                    flag_to_check,
                )
            )

        # merge the snippets by query
        query_snippet_url_dict = {}
        for _query, _url, _snippet in zip(query_to_check, url_to_check, _extended_snippet):
            _snippet_url_list = query_snippet_url_dict.get(_query, [])
            _snippet_url_list.append((_snippet, _url))
            query_snippet_url_dict[_query] = _snippet_url_list

        # extend the evidence list for each query
        for _query in query_snippet_url_dict.keys():
            if _query in query_list:  # 确保查询存在
                _query_index = query_list.index(_query)
                _snippet_url_list = query_snippet_url_dict[_query]
                evidences[_query_index] += [
                    {"text": re.sub(r"\n+", "\n", snippet), "url": _url} for snippet, _url in _snippet_url_list
                ]

        return evidences



    # def _request_serper_api(self, questions):
    #     """Request the tavily api
    #
    #     Args:
    #         questions (list): a list of questions to request the tavily api.
    #
    #     Returns:
    #         web response: the response from the tavily api
    #     """
    #     url = "https://api.tavily.com/search"
    #
    #     headers = {
    #         "Content-Type": "application/json",
    #     }
    #
    #     responses = []
    #     for question in questions:
    #         payload = {
    #             "api_key": self.serper_key,  # Tavily API key在请求体中
    #             "query": question,
    #             "search_depth": "basic",  # 或 "advanced" 获取更多结果
    #             "include_answer": False,
    #             "include_images": False,
    #             "include_raw_content": False,
    #             "max_results": 5  # 根据需要调整结果数量
    #         }
    #
    #         response = requests.post(url, headers=headers, json=payload)
    #
    #         if response.status_code == 200:
    #             responses.append(response.json())
    #         elif response.status_code == 401:
    #             raise Exception("Failed to authenticate. Check your Tavily API key.")
    #         elif response.status_code == 429:
    #             raise Exception("Rate limit exceeded. Please wait before making more requests.")
    #         else:
    #             raise Exception(f"Error occurred with question '{question}': {response.text}")
    #
    #     return responses
    def _request_serper_api(self, questions):
        """Request the tavily api (replaces serper)

        Args:
            questions (list): a list of questions to request the tavily api.

        Returns:
            list: list of responses from the tavily api
        """
        import concurrent.futures
        
        url = "https://searchapi.cloudsway.net/search/NbYyRVhrORhcVYNm/full"
        
        def fetch_single_question(question):
            # URL编码查询参数
            encoded_question = quote(question)

            # 构建查询参数
            params = {
                "q": encoded_question,
                "autocorrect": "false",
                "mainText": "true",  # 设置为true表示只查询核心内容，不查询全文
                "num": "3"  # 限制每个查询只返回3个证据
            }

            # 尝试不同的认证方法
            auth_methods = [
                # 方法1: Bearer 认证
                {"headers": {"Authorization": f"Bearer {self.serper_key}"}},
                # 方法2: API Key 认证
                {"headers": {"X-API-KEY": self.serper_key}},
                # 方法3: 自定义 API-Key 头
                {"headers": {"API-Key": self.serper_key}},
                # 方法4: 自定义 apikey 头
                {"headers": {"apikey": self.serper_key}},
                # 方法5: URL 参数认证
                {"params": {"api_key": self.serper_key}},
            ]

            success = False
            last_error = None
            
            for auth_method in auth_methods:
                try:
                    # 合并认证参数
                    request_params = params.copy()
                    if "params" in auth_method:
                        request_params.update(auth_method["params"])
                    
                    # 合并头信息
                    headers = {"Content-Type": "application/json"}
                    if "headers" in auth_method:
                        headers.update(auth_method["headers"])
                    
                    # 发送请求
                    logger.info(f"尝试使用认证方法: {auth_method} 查询问题: {question}")
                    response = requests.get(
                        url, 
                        params=request_params,
                        headers=headers,
                        timeout=10
                    )
                    
                    # 处理响应
                    if response.status_code == 200:
                        logger.info(f"搜索成功，状态码: {response.status_code}，问题: {question}")
                        return response.json()
                    else:
                        logger.warning(f"搜索失败，状态码: {response.status_code}，问题: {question}")
                        last_error = f"HTTP错误: {response.status_code}"
                except Exception as e:
                    logger.error(f"请求异常: {str(e)}，问题: {question}")
                    last_error = str(e)
            
            logger.error(f"所有认证方法都失败，问题: '{question}'，最后错误: {last_error}")
            return {"error": f"所有认证方法都失败，问题: '{question}'，最后错误: {last_error}"}
        
        # 使用线程池并发请求所有问题（退路实现）
        max_workers = min(len(questions), int(self.api_config.get("SERPER_MAX_CONCURRENCY", 56))) if self.api_config else min(len(questions), 56)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            responses = list(executor.map(fetch_single_question, questions))
        
        return responses

    async def _request_serper_api_async(self, questions):
        """Request the serper/cloudsway API concurrently using aiohttp.

        Args:
            questions (list[str]): list of queries to request.

        Returns:
            list[dict]: list of JSON responses corresponding to questions.
        """
        url = self.serper_url or "https://searchapi.cloudsway.net/search/NbYyRVhrORhcVYNm/full"
        max_concurrency = int(self.api_config.get("SERPER_MAX_CONCURRENCY", 56)) if self.api_config else 56

        connector = aiohttp.TCPConnector(limit=max_concurrency)
        timeout = aiohttp.ClientTimeout(total=15)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            async def fetch_single_question(question: str):
                # URL encode the query param
                encoded_question = quote(question)
                request_params = {
                    "q": encoded_question,
                    "gl": "us",
                    "hl": "en",
                    "autocorrect": "true",
                }

                # Try a set of auth methods to be tolerant of API gateway configuration
                auth_methods = [
                    {},
                    {"headers": {"Authorization": f"Bearer {self.serper_key}"}},
                    {"headers": {"X-API-KEY": self.serper_key}},
                    {"headers": {"API-Key": self.serper_key}},
                    {"headers": {"apikey": self.serper_key}},
                    {"params": {"api_key": self.serper_key}},
                ]

                last_error = None
                for auth_method in auth_methods:
                    try:
                        # Merge auth params
                        params = request_params.copy()
                        if "params" in auth_method:
                            params.update(auth_method["params"])

                        headers = {"Content-Type": "application/json"}
                        if "headers" in auth_method:
                            headers.update(auth_method["headers"])

                        async with session.get(url, params=params, headers=headers) as resp:
                            if resp.status == 200 :
                                return await resp.json()
                            else:
                                last_error = f"HTTP {resp.status}"
                                # logger.warning(f"搜索失败，状态码: {resp.status}，问题: {question}")
                    except Exception as e:
                        last_error = str(e)
                        logger.error(f"请求异常: {e}，问题: {question}")

                logger.error(f"所有认证方法都失败，问题: '{question}'，最后错误: {last_error}")
                return {"error": f"所有认证方法都失败，问题: '{question}'，最后错误: {last_error}"}

            tasks = [fetch_single_question(q) for q in questions]
            return await asyncio.gather(*tasks)
      


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--serper_api_key", type=str, help="API key for serper")
    # args = parser.parse_args()

    api_config = {"SERPER_API_KEY": args.serper_api_key}
    retriever = SerperEvidenceRetriever(api_config)

    result = retriever._request_serper_api(["Apple", "IBM"])
    print(result.json())
