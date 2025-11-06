import json
import re

from factcheck.utils.logger import CustomLogger
import nltk

logger = CustomLogger(__name__).getlog()


class Decompose:
    def __init__(self, llm_client, prompt):
        """Initialize the Decompose class

        Args:
            llm_client (BaseClient): The LLM client used for decomposing documents into claims.
            prompt (BasePrompt): The prompt used for fact checking.
        """
        self.llm_client = llm_client
        self.prompt = prompt
        self.doc2sent = self._nltk_doc2sent

    def _nltk_doc2sent(self, text: str):
        """Split the document into sentences using nltk

        Args:
            text (str): the document to be split into sentences

        Returns:
            list: a list of sentences
        """

        sentences = nltk.sent_tokenize(text)
        sentence_list = [s.strip() for s in sentences if len(s.strip()) >= 3]
        return sentence_list

    def getclaims(self, doc: str, num_retries: int = 3, prompt: str = None) -> list[str]:
        """Use GPT to decompose a document into claims

        Args:
            doc (str): the document to be decomposed into claims
            num_retries (int, optional): maximum attempts for GPT to decompose the document into claims. Defaults to 3.

        Returns:
            list: a list of claims
        """
        if prompt is None:
            user_input = self.prompt.decompose_prompt.format(doc=doc).strip()
        else:
            user_input = prompt.format(doc=doc).strip()

        claims = None
        messages = self.llm_client.construct_message_list([user_input])
        for i in range(num_retries):
            response = self.llm_client.call(
                messages=messages,
                num_retries=1,
                seed=42 + i,
            )
            try:
                claims = eval(response)["claims"]
                if isinstance(claims, list) and len(claims) > 0:
                    break
            except Exception as e:
                logger.error(f"Parse LLM response error {e}, response is: {response}")
                logger.error(f"Parse LLM response error, prompt is: {messages}")
        if isinstance(claims, list):
            return claims
        else:
            logger.info("It does not output a list of sentences correctly, return self.doc2sent_tool split results.")
            claims = self.doc2sent(doc)
        return claims

    def restore_claims(self, doc: str, claims: list, num_retries: int = 3, prompt: str = None) -> dict[str, dict]:
        """Use GPT to map claims back to the document

        Args:
            doc (str): the document to be decomposed into claims
            claims (list[str]): a list of claims to be mapped back to the document
            num_retries (int, optional): maximum attempts for GPT to decompose the document into claims. Defaults to 3.

        Returns:
            dict: a dictionary of claims and their corresponding text spans and start/end indices.
        """

        def restore(claim2doc):
            claim2doc_detail = {}
            flag = True

            # 第一步：找到每个句子在文档中的位置
            for claim, sent in claim2doc.items():
                st = doc.find(sent)
                if st != -1:
                    claim2doc_detail[claim] = {"text": sent, "start": st, "end": st + len(sent)}
                else:
                    # 尝试去除首尾空格再次查找
                    stripped_sent = sent.strip()
                    st = doc.find(stripped_sent)
                    if st != -1:
                        claim2doc_detail[claim] = {"text": stripped_sent, "start": st, "end": st + len(stripped_sent)}
                    else:
                        flag = False
                        claim2doc_detail[claim] = {"text": sent, "start": -1, "end": -1}

            # 按照 start 位置排序处理
            sorted_items = sorted(claim2doc_detail.items(), key=lambda x: x[1]['start'])

            cur_pos = -1
            texts = []

            for k, v in sorted_items:
                # 如果原始查找失败，跳过调整
                if v["start"] == -1:
                    continue

                # 检查是否发生重叠
                if v["start"] < cur_pos + 1:  # 发生重叠或间隙
                    if v["end"] > cur_pos:  # 有部分内容是新的
                        # 调整起始位置
                        original_start = v["start"]
                        v["start"] = cur_pos + 1
                        v["text"] = doc[v["start"]:v["end"]]
                        # 只有当调整较大时才标记为错误
                        if abs(original_start - v["start"]) > 1:
                            flag = False
                    else:  # 完全在已处理区域中
                        v["start"] = cur_pos + 1
                        v["end"] = cur_pos + 1
                        v["text"] = ""
                        flag = False

                # 提取文本片段
                if v["start"] < v["end"]:
                    v["text"] = doc[v["start"]:v["end"]]
                    texts.append(v["text"])
                else:
                    v["text"] = ""

                # 更新位置
                cur_pos = v["end"]

                # 更新原字典
                claim2doc_detail[k] = v

            return claim2doc_detail, flag


        if prompt is None:
            user_input = self.prompt.restore_prompt.format(doc=doc, claims=claims).strip()
        else:
            user_input = prompt.format(doc=doc, claims=claims).strip()

        messages = self.llm_client.construct_message_list([user_input])

        tmp_restore = {}
        for i in range(num_retries):
            response = self.llm_client.call(
                messages=messages,
                num_retries=1,
                seed=42 + i,
            )
            try:
                # 去除多余的 Markdown 代码块标记
                response = response.strip("```json\n").strip("```")
                # 确保 response 不为空字符串
                if not response.strip():
                    print("Received an empty response. Skipping this iteration.")
                    continue

                # 去除多余的空格和换行符
                response = response.strip()
                # claim2doc = eval(response)
                claim2doc = json.loads(response)
                assert len(claim2doc) == len(claims)
                claim2doc_detail, flag = restore(claim2doc)
                if flag:
                    return claim2doc_detail
                else:
                    tmp_restore = claim2doc_detail
                    #raise Exception("Restore claims not satisfied.")
            except Exception as e:
                logger.error(f"Parse LLM response error {e}, response is: {response}")
                logger.error(f"Parse LLM response error, prompt is: {messages}")

        return tmp_restore