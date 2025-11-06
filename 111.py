# from concurrent.futures import ThreadPoolExecutor
# import json
# from urllib.parse import quote
#
# import requests
# import os
# import re
# import bs4
# from factcheck.utils.logger import CustomLogger
# from factcheck.utils.web_util import crawl_web
#
# logger = CustomLogger(__name__).getlog()
#
#
# class SerperEvidenceRetriever:
#     def __init__(self, llm_client, api_config: dict = None):
#         """Initialize the SerperEvidenceRetrieve class"""
#         self.lang = "en"
#         self.serper_key = api_config["SERPER_API_KEY"]
#         self.serper_url = api_config["CLOUDSWAY_API_URL"]
#         self.llm_client = llm_client
#
#     def retrieve_evidence(self, claim_queries_dict, top_k: int = 3, snippet_extend_flag: bool = True):
#         """Retrieve evidences for the given claims
#
#         Args:
#             claim_queries_dict (dict): a dictionary of claims and their corresponding queries.
#             top_k (int, optional): the number of top relevant results to retrieve. Defaults to 3.
#             snippet_extend_flag (bool, optional): whether to extend the snippet. Defaults to True.
#
#         Returns:
#             dict: a dictionary of claims and their corresponding evidences.
#         """
#         logger.info("Collecting evidences ...")
#         query_list = [y for x in claim_queries_dict.items() for y in x[1]]
#         evidence_list = self._retrieve_evidence_4_all_claim(
#             query_list=query_list, top_k=top_k, snippet_extend_flag=snippet_extend_flag
#         )
#
#         i = 0
#         claim_evidence_dict = {}
#         for claim, queries in claim_queries_dict.items():
#             evidences_per_query_L = evidence_list[i : i + len(queries)]
#             claim_evidence_dict[claim] = [e for evidences in evidences_per_query_L for e in evidences]
#             i += len(queries)
#         assert i == len(evidence_list)
#         logger.info("Collect evidences done!")
#         return claim_evidence_dict
#
#     def _retrieve_evidence_4_all_claim(
#             self, query_list: list[str], top_k: int = 3, snippet_extend_flag: bool = True
#     ) -> list[list[str]]:
#         """Retrieve evidences for the given queries
#
#         Args:
#             query_list (list[str]): a list of queries to retrieve evidences for.
#             top_k (int, optional): the number of top relevant results to retrieve. Defaults to 3.
#             snippet_extend_flag (bool, optional): whether to extend the snippet. Defaults to True.
#
#         Returns:
#             list[list[]]: a list of [a list of evidences for each given query].
#         """
#
#         # init the evidence list with None
#         evidences = [[] for _ in query_list]
#
#         # get the response from tavily
#         serper_responses = []
#         for i in range(0, len(query_list), 100):
#             batch_query_list = query_list[i: i + 100]
#             batch_response = self._request_serper_api(batch_query_list)
#             if batch_response is None:
#                 logger.error("Tavily API request error!")
#                 return evidences
#             else:
#                 serper_responses.extend(batch_response)
#
#         # get the responses for queries
#         query_url_dict = {}
#         url_to_date = {}  # TODO: decide whether to use date
#         _snippet_to_check = []
#
#         for i, (query, response) in enumerate(zip(query_list, serper_responses)):
#             # Tavily没有searchParameters字段，直接使用原始查询
#             response_query = response.get("query", query)
#             if query != response_query:
#                 logger.warning("Tavily changed query from {} TO {}".format(query, response_query))
#
#             # Tavily的answer字段处理
#             if response.get("answer"):  # 如果有answer字段
#                 evidences[i] = [
#                     {
#                         "text": f"{query}\nAnswer: {response['answer']}",
#                         "url": "Tavily Answer Box",
#                     }
#                 ]
#             else:
#                 # Tavily使用results而不是organic
#                 topk_results = response.get("results", [])[:top_k]  # Choose top k response
#
#                 if (len(_snippet_to_check) == 0) or (not snippet_extend_flag):
#                     evidences[i] += [
#                         {"text": re.sub(r"\n+", "\n", _result["content"]), "url": _result["url"]}
#                         for _result in topk_results if "content" in _result and "url" in _result
#                     ]
#
#                 # Save date for each url (Tavily可能没有date字段)
#                 for _result in topk_results:
#                     if "url" in _result:
#                         url_to_date.update({_result["url"]: _result.get("date", "")})
#                         # Save query-url pair, 1 query may have multiple urls
#                         current_urls = query_url_dict.get(query, [])
#                         current_urls.append(_result["url"])
#                         query_url_dict[query] = current_urls
#                         # 收集需要检查的片段
#                         _snippet_to_check.append(_result.get("content", ""))
#
#         # return if there is no snippet to check or snippet_extend_flag is False
#         if (len(_snippet_to_check) == 0) or (not snippet_extend_flag):
#             return evidences
#
#         # crawl web for queries without answer box
#         responses = crawl_web(query_url_dict)
#         # Get extended snippets based on the snippet from serper
#         flag_to_check = [_item[0] for _item in responses]
#         response_to_check = [_item[1] for _item in responses]
#         url_to_check = [_item[2] for _item in responses]
#         query_to_check = [_item[3] for _item in responses]
#
#         def bs4_parse_text(response, snippet, flag):
#             """Parse the text from the response and extend the snippet
#
#             Args:
#                 response (web response): the response from the web
#                 snippet (str): the snippet to extend from the search result
#                 flag (bool): flag to extend the snippet
#
#             Returns:
#                 _type_: _description_
#             """
#             if flag and response and ".pdf" not in str(response.url):
#                 try:
#                     soup = bs4.BeautifulSoup(response.text, "html.parser")
#                     text = soup.get_text()
#                     # Search for the snippet in text
#                     snippet_start = text.find(snippet[:-10]) if len(snippet) > 10 else text.find(snippet)
#                     if snippet_start == -1:
#                         return snippet
#                     else:
#                         pre_context_range = 0  # Number of characters around the snippet to display
#                         post_context_range = 500  # Number of characters around the snippet to display
#                         start = max(0, snippet_start - pre_context_range)
#                         end = snippet_start + len(snippet) + post_context_range
#                         return text[start:end] + " ..."
#                 except Exception as e:
#                     logger.warning(f"Error parsing web content: {e}")
#                     return snippet
#             else:
#                 return snippet
#
#         # Question: if os.cpu_count() cause problems when running in parallel?
#         with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
#             _extended_snippet = list(
#                 executor.map(
#                     lambda _r, _s, _f: bs4_parse_text(_r, _s, _f),
#                     response_to_check,
#                     _snippet_to_check,
#                     flag_to_check,
#                 )
#             )
#
#         # merge the snippets by query
#         query_snippet_url_dict = {}
#         for _query, _url, _snippet in zip(query_to_check, url_to_check, _extended_snippet):
#             _snippet_url_list = query_snippet_url_dict.get(_query, [])
#             _snippet_url_list.append((_snippet, _url))
#             query_snippet_url_dict[_query] = _snippet_url_list
#
#         # extend the evidence list for each query
#         for _query in query_snippet_url_dict.keys():
#             if _query in query_list:  # 确保查询存在
#                 _query_index = query_list.index(_query)
#                 _snippet_url_list = query_snippet_url_dict[_query]
#                 evidences[_query_index] += [
#                     {"text": re.sub(r"\n+", "\n", snippet), "url": _url} for snippet, _url in _snippet_url_list
#                 ]
#
#         return evidences
#
#
#
#     # def _request_serper_api(self, questions):
#     #     """Request the tavily api
#     #
#     #     Args:
#     #         questions (list): a list of questions to request the tavily api.
#     #
#     #     Returns:
#     #         web response: the response from the tavily api
#     #     """
#     #     url = "https://api.tavily.com/search"
#     #
#     #     headers = {
#     #         "Content-Type": "application/json",
#     #     }
#     #
#     #     responses = []
#     #     for question in questions:
#     #         payload = {
#     #             "api_key": self.serper_key,  # Tavily API key在请求体中
#     #             "query": question,
#     #             "search_depth": "basic",  # 或 "advanced" 获取更多结果
#     #             "include_answer": False,
#     #             "include_images": False,
#     #             "include_raw_content": False,
#     #             "max_results": 5  # 根据需要调整结果数量
#     #         }
#     #
#     #         response = requests.post(url, headers=headers, json=payload)
#     #
#     #         if response.status_code == 200:
#     #             responses.append(response.json())
#     #         elif response.status_code == 401:
#     #             raise Exception("Failed to authenticate. Check your Tavily API key.")
#     #         elif response.status_code == 429:
#     #             raise Exception("Rate limit exceeded. Please wait before making more requests.")
#     #         else:
#     #             raise Exception(f"Error occurred with question '{question}': {response.text}")
#     #
#     #     return responses
#     def _request_serper_api(self, questions):
#         """Request the tavily api (replaces serper)
#
#         Args:
#             questions (list): a list of questions to request the tavily api.
#
#         Returns:
#             list: list of responses from the tavily api
#         """
#         url = self.serper_url
#
#
#         # headers = {
#         #     "Content-Type": "application/json",
#         # }
#         headers = {
#             "Authorization": f"Bearer {self.serper_key}",
#             "Content-Type": "application/json",
#         }
#         # 收集所有响应
#         responses = []
#
#         for question in questions:
#             # URL编码查询参数
#             encoded_question = quote(question)
#
#             # 构建查询参数
#             params = {
#                 "q": encoded_question,
#                 "autocorrect": "false",
#                 "mainText": "true"
#             }
#
#             # 发送GET请求
#             response = requests.get(url, headers=headers, params=params)
#             # responses.append(response)
#
#             if response.status_code == 200:
#                 responses.append(response.json())
#             elif response.status_code == 401:
#                 raise Exception("Failed to authenticate. Check your API key.")
#             elif response.status_code == 403:
#                 raise Exception("Failed to authenticate. Check your API key.")
#             elif response.status_code == 429:
#                 raise Exception("Rate limit exceeded. Please wait before making more requests.")
#             else:
#                 raise Exception(f"Error occurred with question '{question}': {response.text}")
#
#         return responses
#
#
# if __name__ == "__main__":
#     import argparse
#
#     parser = argparse.ArgumentParser()
#     parser.add_argument("--serper_api_key", type=str, help="API key for serper")
#     # args = parser.parse_args()
#
#     api_config = {"SERPER_API_KEY": args.serper_api_key}
#     retriever = SerperEvidenceRetriever(api_config)
#
#     result = retriever._request_serper_api(["Apple", "IBM"])
#     print(result.json())
