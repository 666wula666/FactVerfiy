#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import argparse
import json
import time
import datetime

from factcheck.utils.utils import load_yaml
from factcheck import FactCheck
from factcheck.utils.web_util import scrape_url

#中国历史上实际控制领土面积最大的朝代是清朝。尽管元朝名义上疆域广阔（约1372万平方公里），但其统治范围主要集中于中原本土，而四大汗国（钦察、察合台、窝阔台、伊尔汗国）属于独立封地，并未真正纳入中央管辖体系。\\n\\n清朝通过设立驻藏大臣（1727年）、在新疆建省（1884年）、设台湾府（1684年）等举措，将西藏、新疆、蒙古、东北及台湾等约1316万平方公里土地纳入实际治理体系，奠定了现代中国版图的基础。即使晚清失去部分领土，其鼎盛时期的有效控制范围仍超过历代中原王朝。
        
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="google/gemini-2.5-flash")
    parser.add_argument("--client", type=str, default=None)
    parser.add_argument("--prompt", type=str, default="chatgpt_prompt")
    parser.add_argument("--retriever", type=str, default="serper")
    parser.add_argument("--input_text", type=str, default="清朝通过设立驻藏大臣（1727年）,在新疆建省（1884年）,设台湾府（1684年）等举措，奠定了现代中国版图的基础", help="直接传入要检测的文本")
    parser.add_argument("--input_file", type=str, default=None, help="从文件读取文本进行检测")
    parser.add_argument("--input_json", type=str, default=None, help="传入 JSON 测试文件（数组，每项含 response 字段）")
    parser.add_argument("--api_config", type=str, default="factcheck/config/api_config.yaml")
    parser.add_argument("--input_url", type=str, default=None, help="从URL获取文本进行检测")
    args = parser.parse_args()

    # Load API config from yaml file
    try:
        api_config = load_yaml(args.api_config)
    except Exception as e:
        print(f"Error loading api config: {e}")
        api_config = {}

    # Initialize FactCheck instance
    factcheck_instance = FactCheck(
        default_model=args.model,
        api_config=api_config,
        prompt=args.prompt,
        retriever=args.retriever,
    )

    # JSON 批量测试
    if args.input_json:
        if not os.path.exists(args.input_json):
            print(json.dumps({"error": "input_json not found", "path": args.input_json}, ensure_ascii=False))
            sys.exit(1)
        with open(args.input_json, "r", encoding="utf-8") as jf:
            tests = json.load(jf)

        # 兼容 merged_conversations.json 等对话数据结构
        def _extract_response_from_item(item: dict) -> str:
            # 1) 优先使用标准字段
            resp = item.get("response")
            if isinstance(resp, str) and resp.strip():
                return resp.strip()
            # 2) 尝试从 responses 列表中选择最后一个人类文本
            resps = item.get("responses")
            if isinstance(resps, list) and resps:
                candidates = [
                    r for r in resps
                    if isinstance(r, dict) and r.get("type") == "human" and isinstance(r.get("content"), str)
                ]
                if candidates:
                    return candidates[-1].get("content", "").strip()
                last = resps[-1]
                if isinstance(last, dict) and isinstance(last.get("content"), str):
                    return last.get("content", "").strip()
            # 3) 回退到 question 字段
            q = item.get("question")
            if isinstance(q, str) and q.strip():
                return q.strip()
            return ""
        outputs = []
        total_start_time = time.time()
        md_rows = []
        
        for item in tests:
        
            txt = _extract_response_from_item(item)
            expected = item.get("attributes", {}).get("factuality")
            try:
                # 记录单项开始时间
                item_start_time = time.time()
                
                # 执行检查
                res = factcheck_instance.check_text(txt)
                
                # 计算单项响应时间
                item_end_time = time.time()
                item_response_time = item_end_time - item_start_time
                
                # 添加响应时间信息
                # 保存流水线分步耗时
                pipeline_timing = getattr(factcheck_instance, "_last_timing", {})
                outputs.append({
                    "id": item.get("id"),
                    "input": txt,
                    "expected": expected,
                    "result": res,
                    "timing": {
                        "response_time_seconds": item_response_time
                    },
                    "pipeline_timing": pipeline_timing,
                })

                # 构建 Markdown 表格行
                try:
                    summary = res.get("summary", {})
                    claim_detail = res.get("claim_detail", [])
                    usage = res.get("usage", {})

                    # 关系计数与证据数量
                    supports = 0
                    refutes = 0
                    irrelevant = 0
                    num_evidences = 0
                    for c in claim_detail:
                        evs = c.get("evidences", [])
                        num_evidences += len(evs)
                        for e in evs:
                            rel = (e.get("relationship") or "").upper()
                            if rel == "SUPPORTS":
                                supports += 1
                            elif rel == "REFUTES":
                                refutes += 1
                            elif rel == "IRRELEVANT":
                                irrelevant += 1

                    # tokens
                    def _tp(name):
                        v = usage.get(name) or {}
                        return int(v.get("prompt_tokens") or 0)
                    def _tc(name):
                        v = usage.get(name) or {}
                        return int(v.get("completion_tokens") or 0)

                    de_tp, de_tc = _tp("decomposer"), _tc("decomposer")
                    cw_tp, cw_tc = _tp("checkworthy"), _tc("checkworthy")
                    qg_tp, qg_tc = _tp("query_generator"), _tc("query_generator")
                    ec_tp, ec_tc = _tp("evidence_crawler"), _tc("evidence_crawler")
                    cv_tp, cv_tc = _tp("claimverify"), _tc("claimverify")
                    total_tokens = de_tp + de_tc + cw_tp + cw_tc + qg_tp + qg_tc + ec_tp + ec_tc + cv_tp + cv_tc

                    # 分步耗时
                    create_t = pipeline_timing.get("create_claims_time_seconds", 0)
                    retrieve_t = pipeline_timing.get("retrieve_time_seconds", 0)
                    verify_t = pipeline_timing.get("verify_time_seconds", 0)
                    total_t = pipeline_timing.get("total_time_seconds", 0)

                    md_rows.append([
                        str(item.get("id")),
                        str(txt).replace("\n", " "),
                        str(expected),
                        str(summary.get("factuality", "")),
                        str(summary.get("num_claims", 0)),
                        str(num_evidences),
                        str(supports),
                        str(refutes),
                        str(irrelevant),
                        f"{create_t:.4f}",
                        f"{retrieve_t:.4f}",
                        f"{verify_t:.4f}",
                        f"{total_t:.4f}",
                        str(de_tp),
                        str(de_tc),
                        str(cw_tp),
                        str(cw_tc),
                        str(qg_tp),
                        str(qg_tc),
                        str(ec_tp),
                        str(ec_tc),
                        str(cv_tp),
                        str(cv_tc),
                        str(total_tokens),
                    ])
                except Exception as _:
                    pass
            except Exception as e:
                res = {"error": str(e)}
                outputs.append({"id": item.get("id"), "input": txt, "expected": expected, "result": res})
        
        # 计算总响应时间
        total_end_time = time.time()
        total_response_time = total_end_time - total_start_time
        
        # 创建最终结果
        final_result = {
            "results": outputs,
            "timing": {
                "total_response_time_seconds": total_response_time,
                "average_response_time_seconds": total_response_time / len(tests) if tests else 0,
                "timestamp": datetime.datetime.now().isoformat()
            },
            "summary": {
                "total_tests": len(tests),
                "successful_tests": sum(1 for item in outputs if "error" not in item.get("result", {}))
            }
        }
        
        # 打印结果
        print(json.dumps(final_result, ensure_ascii=False, indent=2))

        # 保存结果到z_result.json
        with open("z_result.json", "w", encoding="utf-8") as f:
            json.dump(final_result, f, ensure_ascii=False, indent=2)

        # 生成并保存 Markdown 表格
        md_header = [
            "id",
            "response",
            "attributes：factuality",
            "test:factuality",
            "num_claims",
            "num_evidences",
            "Supports_ relationship",
            "Refutes_ relationship",
            "Irrelevant_ relationship",
            "Create claims time",
            "Retrieve time",
            "Verify time",
            "Total time",
            "Decomposer's prompt_tokens",
            "Decomposer's completion_tokens",
            "checkworthy's prompt_tokens",
            "checkworthy's completion_tokens",
            "query_generator's prompt_tokens",
            "query_generator's completion_tokens",
            "evidence_crawler's prompt_tokens",
            "evidence_crawler's completion_tokens",
            "claimverify's prompt_tokens",
            "claimverify's completion_tokens",
            "total_tokens",
        ]
        md_lines = ["| " + " | ".join(md_header) + " |", "| " + " | ".join(["---"] * len(md_header)) + " |"]
        for row in md_rows:
            md_lines.append("| " + " | ".join(row) + " |")
        md_content = "\n".join(md_lines)
        with open("z_result.md", "w", encoding="utf-8") as f:
            f.write(md_content)
            
        sys.exit(0)

    # 处理单条文本输入
    text_to_check = None
    if args.input_text:
        text_to_check = args.input_text
    elif args.input_url:
        # 从URL获取内容
        print(f"正在从URL获取内容: {args.input_url}")
        web_text, url = scrape_url(args.input_url)
        print(f"从URL获取到的内容长度: {len(web_text) if web_text else 0}")
        if web_text:
            text_to_check = web_text
            print(f"成功获取URL内容，长度: {len(web_text)} 字符")
            print(f"前200个字符: {web_text[:200]}...")
        else:
            print(f"无法从URL获取内容: {args.input_url}")
            print("这可能是因为网站使用了JavaScript动态加载内容，或者有反爬虫保护。")
            print("建议手动复制内容并使用 --input_text 参数，或者将内容保存到文件并使用 --input_file 参数。")
            sys.exit(1)
    elif args.input_file:
        if os.path.exists(args.input_file):
            with open(args.input_file, "r", encoding="utf-8") as f:
                text_to_check = f.read().strip()
        else:
            print(f"Input file not found: {args.input_file}")
            sys.exit(1)

    if text_to_check:
        try:
            # 记录开始时间
            start_time = time.time()
            
            # 执行检查
            result = factcheck_instance.check_text(text_to_check)
            
            # 计算响应时间
            end_time = time.time()
            response_time = end_time - start_time
            
            # 添加响应时间到结果
            # 保存流水线分步耗时
            pipeline_timing = getattr(factcheck_instance, "_last_timing", {})
            result_with_timing = {
                "result": result,
                "timing": {
                    "response_time_seconds": response_time,
                    "timestamp": datetime.datetime.now().isoformat()
                },
                "pipeline_timing": pipeline_timing,
            }
            
            # 打印结果
            print(json.dumps(result_with_timing, ensure_ascii=False, indent=2))
            
            # 保存结果到z_result.json
            with open("z_result.json", "w", encoding="utf-8") as f:
                json.dump(result_with_timing, f, ensure_ascii=False, indent=2)

            # 生成并保存单条 Markdown 表格
            try:
                res = result
                summary = res.get("summary", {})
                claim_detail = res.get("claim_detail", [])
                usage = res.get("usage", {})
                txt = text_to_check
                supports = refutes = irrelevant = 0
                num_evidences = 0
                for c in claim_detail:
                    evs = c.get("evidences", [])
                    num_evidences += len(evs)
                    for e in evs:
                        rel = (e.get("relationship") or "").upper()
                        if rel == "SUPPORTS":
                            supports += 1
                        elif rel == "REFUTES":
                            refutes += 1
                        elif rel == "IRRELEVANT":
                            irrelevant += 1

                def _tp(name):
                    v = usage.get(name) or {}
                    return int(v.get("prompt_tokens") or 0)
                def _tc(name):
                    v = usage.get(name) or {}
                    return int(v.get("completion_tokens") or 0)

                de_tp, de_tc = _tp("decomposer"), _tc("decomposer")
                cw_tp, cw_tc = _tp("checkworthy"), _tc("checkworthy")
                qg_tp, qg_tc = _tp("query_generator"), _tc("query_generator")
                ec_tp, ec_tc = _tp("evidence_crawler"), _tc("evidence_crawler")
                cv_tp, cv_tc = _tp("claimverify"), _tc("claimverify")
                total_tokens = de_tp + de_tc + cw_tp + cw_tc + qg_tp + qg_tc + ec_tp + ec_tc + cv_tp + cv_tc

                create_t = pipeline_timing.get("create_claims_time_seconds", 0)
                retrieve_t = pipeline_timing.get("retrieve_time_seconds", 0)
                verify_t = pipeline_timing.get("verify_time_seconds", 0)
                total_t = pipeline_timing.get("total_time_seconds", 0)

                md_header = [
                    "id",
                    "response",
                    "attributes：factuality",
                    "test:factuality",
                    "num_claims",
                    "num_evidences",
                    "Supports_ relationship",
                    "Refutes_ relationship",
                    "Irrelevant_ relationship",
                    "Create claims time",
                    "Retrieve time",
                    "Verify time",
                    "Total time",
                    "Decomposer's prompt_tokens",
                    "Decomposer's completion_tokens",
                    "checkworthy's prompt_tokens",
                    "checkworthy's completion_tokens",
                    "query_generator's prompt_tokens",
                    "query_generator's completion_tokens",
                    "evidence_crawler's prompt_tokens",
                    "evidence_crawler's completion_tokens",
                    "claimverify's prompt_tokens",
                    "claimverify's completion_tokens",
                    "total_tokens",
                ]
                md_lines = ["| " + " | ".join(md_header) + " |", "| " + " | ".join(["---"] * len(md_header)) + " |"]
                md_row = [
                    "-",
                    str(txt).replace("\n", " "),
                    "-",
                    str(summary.get("factuality", "")),
                    str(summary.get("num_claims", 0)),
                    str(num_evidences),
                    str(supports),
                    str(refutes),
                    str(irrelevant),
                    f"{create_t:.4f}",
                    f"{retrieve_t:.4f}",
                    f"{verify_t:.4f}",
                    f"{total_t:.4f}",
                    str(de_tp),
                    str(de_tc),
                    str(cw_tp),
                    str(cw_tc),
                    str(qg_tp),
                    str(qg_tc),
                    str(ec_tp),
                    str(ec_tc),
                    str(cv_tp),
                    str(cv_tc),
                    str(total_tokens),
                ]
                md_lines.append("| " + " | ".join(md_row) + " |")
                with open("z_result.md", "w", encoding="utf-8") as f:
                    f.write("\n".join(md_lines))
            except Exception:
                pass
                
        except Exception as e:
            print(f"Error checking text: {e}")
            sys.exit(1)
    else:
        print("Please provide text to check using --input_text, --input_url or --input_file")
        sys.exit(1)


if __name__ == "__main__":
    main()