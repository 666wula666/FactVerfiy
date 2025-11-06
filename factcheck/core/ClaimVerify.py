from __future__ import annotations

import json
import concurrent.futures
from factcheck.utils.logger import CustomLogger
from factcheck.utils.data_class import Evidence

logger = CustomLogger(__name__).getlog()


class ClaimVerify:
    def __init__(self, llm_client, prompt):
        """Initialize the ClaimVerify class

        Args:
            llm_client (BaseClient): The LLM client used for verifying the factuality of claims.
            prompt (BasePrompt): The prompt used for verifying the factuality of claims.
        """
        self.llm_client = llm_client
        self.prompt = prompt

    def verify_claims(self, claim_evidences_dict, prompt: str = None) -> dict[str, list[Evidence]]:
        """Verify the factuality of the claims with respect to the given evidences

        Args:
            claim_evidences_dict (dict): a dictionary of claims and their corresponding evidences.

        Returns:
            dict: a dictionary of claims and their relationship to each evidence, including evidence, reasoning, relationship.
        """

        claim_verifications_dict = self._verify_all_claims(claim_evidences_dict, prompt=prompt)

        return claim_verifications_dict

    def _process_single_response(self, response, attempts):
        """处理单个LLM响应并解析结果

        Args:
            response (str): LLM的响应
            attempts (int): 当前尝试次数

        Returns:
            dict: 解析后的响应JSON，如果解析失败则返回None
        """
        try:
            _response = response.strip("```json\n").strip("```")
            _response_json = json.loads(_response)
            assert all(k in _response_json for k in ["reasoning", "relationship"])
            return _response_json
        except:  # noqa: E722
            logger.info(f"Warning: LLM response parse fail, retry {attempts}.")
            return None

    def _verify_all_claims(
        self,
        claim_evidences_dict: dict[str, list[str]],
        num_retries=3,
        prompt: str = None,
        max_workers=10,
    ) -> dict[str, list[Evidence]]:
        """Verify the factuality of the claims with respect to the given evidences

        Args:
            claim_evidences_dict (dict): a dictionary of claims and their corresponding evidences.
            num_retries (int, optional): maximum attempts for GPT to verify the factuality of the claims. Defaults to 3.
            prompt (str, optional): Custom prompt to use. Defaults to None.
            max_workers (int, optional): Maximum number of concurrent workers. Defaults to 10.

        Returns:
            list[dict[str, any]]: a list of relationship results, including evidence, reasoning, relationship.
        """
        attempts = 0
        # construct user inputs with respect to each claim and its evidences
        claim_evidence_list = []
        messages_list = []
        for claim, _evidences in claim_evidences_dict.items():
            for e in _evidences:
                if prompt is None:
                    user_input = self.prompt.verify_prompt.format(claim=claim, evidence=e)
                else:
                    user_input = prompt.format(claim=claim, evidence=e)
                claim_evidence_list.append((claim, e))
                messages_list.append(user_input)
        factual_results = [None] * len(messages_list)

        while (attempts < num_retries) and (None in factual_results):
            _messages = [_message for _i, _message in enumerate(messages_list) if factual_results[_i] is None]
            _indices = [_i for _i, _message in enumerate(messages_list) if factual_results[_i] is None]

            _message_list = self.llm_client.construct_message_list(_messages)
            _response_list = self.llm_client.multi_call(_message_list)
            
            # 使用线程池并发处理响应
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(max_workers, len(_response_list))) as executor:
                # 创建处理任务
                future_to_index = {
                    executor.submit(self._process_single_response, _response, attempts): i
                    for i, (_response, _index) in enumerate(zip(_response_list, _indices))
                }
                
                # 收集处理结果
                for future in concurrent.futures.as_completed(future_to_index):
                    i = future_to_index[future]
                    result = future.result()
                    if result is not None:
                        factual_results[_indices[i]] = result
            
            attempts += 1

        _template_results = {
            "reasoning": "[System Warning] Can not identify the factuality of the claim.",
            "relationship": "IRRELEVANT",
        }

        # 使用线程池并发构建证据列表
        evidences = []
        
        def create_evidence(item):
            (claim, evidence), verification = item
            if verification is None:
                verification = _template_results
            return Evidence(claim=claim, **evidence, **verification)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(max_workers, len(claim_evidence_list))) as executor:
            evidences = list(executor.map(create_evidence, zip(claim_evidence_list, factual_results)))

        # aggregate the results from list to dict
        claim_verifications_dict = {k: [] for k in claim_evidences_dict.keys()}
        for e in evidences:
            claim_verifications_dict[e.claim].append(e)

        return claim_verifications_dict
