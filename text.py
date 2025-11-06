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
    parser.add_argument("--input_text", type=str, default="中国近代史（1840-1949）发展趋势分析\n\n#### 一、核心矛盾：半殖民地化与现代化的双重主线\n**关键发现**：\n1. **半殖民地化进程**（据中国社会科学院研究）：\n   - 鸦片战争后签订的不平等条约体系（如《南京条约》《马关条约》）形成\"条约口岸经济\"，外国资本通过铁路贷款（如《中俄密约》）、工业投资（如日本在东北的鞍山制铁所）等方式控制中国经济命脉。\n   - 1931年后日本在东北的重工业投资占全国比重：煤炭49.4%、生铁87.7%（据中国近代工业史资料）。\n\n2. **现代化探索**（据中华文史网研究）：\n   - 洋务运动创建江南制造总局等军事工业，但1894年甲午战争时全国近代工业资本仅占外国在华工业资本的1/7（据浙江大学数据）。\n   - 民族资本在1914-1920年迎来\"黄金时代\"，荣氏家族申新纺织系统纱锭数从1915年的12,960枚增至1922年的134,907枚。\n\n#### 二、政治体制演变\n**阶段特征**：\n1. **皇权危机**（1840-1911）：\n   - 1901年《辛丑条约》后，清政府财政收入47.2%用于赔款（据中南财经政法大学数据）。\n   - 1908年《钦定宪法大纲》确立\"皇权永固\"原则，与日本《明治宪法》相比缺失内阁责任制。\n\n2. **共和实践**（1912-1927）：\n   - 1913年首届国会选举中，国民党获392/596席，但宋教仁遇刺暴露宪政危机。\n   - 1925年广州国民政府建立党军制度，黄埔军校前五期培养7,399名军官（据中国人民大学研究）。\n\n3. **新民主主义革命**（1927-1949）：\n   - 延安时期建立\"三三制\"政权（共产党员、左派进步分子、中间分子各占1/3）。\n   - 1948年解放区面积达235万平方公里，人口1.68亿（据国家统计局资料）。\n\n#### 三、经济结构转型\n**数据对比**：\n| 指标                | 1933年        | 1949年        |\n|---------------------|--------------|--------------|\n| 工业占GDP比重       | 10.8%        | 17%          |\n| 铁路里程            | 21,761公里   | 21,800公里   |\n| 钢产量              | 3万吨         | 15.8万吨      |\n| 外资控制比重        | 电力67%      | 煤炭28%       |\n\n（数据来源：中国近代工业史资料、中南财经政法大学研究）\n\n#### 四、思想文化流变\n**关键转折**：\n1. **体用之争**（1860-1895）：\n   - 张之洞《劝学篇》提出\"旧学为体，新学为用\"，但1898年京师大学堂章程仍规定经学课时占43%。\n\n2. **启蒙运动**（1915-1923）：\n   - 《新青年》发行量从1915年的1,000份增至1921年的16,000份。\n   - 1920年北京大学开设马克思主义课程，李大钊组建北京共产主义小组。\n\n3. **本土化转向**（1927-1945）：\n   - 延安整风运动批判教条主义，毛泽东《改造我们的学习》强调\"实事求是\"。\n   - 1942年《在延安文艺座谈会上的讲话》确立文艺为工农兵服务方向。\n\n#### 五、历史转折点影响\n**关键节点分析**：\n1. **甲午战争**（1894-1895）：\n   - 赔款2.3亿两白银，相当于清政府3年财政收入，直接导致1896年\"昭信股票\"内债发行失败。\n\n2. **五四运动**（1919）：\n   - 全国200多个城市学生罢课，上海日资纱厂工人罢工使日商损失1,200万日元。\n\n3. **抗日战争**（1937-1945）：\n   - 工业内迁保存152家工厂、12,000余吨设备，但战时工业损失达4.4亿美元（1937年币值）。\n\n#### 结论：双重转型的历史逻辑\n中国近代史呈现\"被动全球化\"与\"主动现代化\"的复杂交织。外国资本控制（如1936年外资占中国工业资本57%）、传统社会解构（1949年城市化率仅10.6%）与本土现代性萌发（如1920-1936年民族工业年均增长7.7%）形成张力。这种历史特殊性决定了中国现代化必须通过彻底的社会革命实现主权独立与发展自主的统一。\n\n（注：部分URL因技术限制未能获取完整内容，本报告基于可验证的学术研究成果综合而成）", help="直接传入要检测的文本")
    parser.add_argument("--input_file", type=str, default=None, help="从文件读取文本进行检测")
    parser.add_argument("--input_json", type=str, default="/Users/zhangwenyang/Desktop/OpenFactVerification-main/test_first_3.json", help="传入 JSON 测试文件（数组，每项含 response 字段）")
    parser.add_argument("--api_config", type=str, default="factcheck/config/api_config.yaml")
    parser.add_argument("--input_url", type=str, default=None, help="从URL获取文本进行检测")
    parser.add_argument("--limit", type=int, default=None, help="仅处理前N条JSON测试数据，用于快速验证")
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
            # 4) 最后回退到 text 字段（如 test_data_50.json）
            t = item.get("text")
            if isinstance(t, str) and t.strip():
                return t.strip()
            return ""
        outputs = []
        total_start_time = time.time()
        md_rows = []
        
        # 如果设置了limit，则只取前N条
        if args.limit is not None and isinstance(args.limit, int) and args.limit > 0:
            tests = tests[:args.limit]

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

        # 生成 Excel 文件（优先使用 pandas，其次 openpyxl，最后降级为 CSV）
        try:
            # 整理为结构化行
            excel_rows = []
            for row in md_rows:
                excel_rows.append({
                    "id": row[0],
                    "response": row[1],
                    "attributes:factuality": row[2],
                    "test:factuality": row[3],
                    "num_claims": int(row[4]),
                    "num_evidences": int(row[5]),
                    "Supports": int(row[6]),
                    "Refutes": int(row[7]),
                    "Irrelevant": int(row[8]),
                    "Create claims time": float(row[9]),
                    "Retrieve time": float(row[10]),
                    "Verify time": float(row[11]),
                    "Total time": float(row[12]),
                    "decomposer_prompt_tokens": int(row[13]),
                    "decomposer_completion_tokens": int(row[14]),
                    "checkworthy_prompt_tokens": int(row[15]),
                    "checkworthy_completion_tokens": int(row[16]),
                    "query_generator_prompt_tokens": int(row[17]),
                    "query_generator_completion_tokens": int(row[18]),
                    "evidence_crawler_prompt_tokens": int(row[19]),
                    "evidence_crawler_completion_tokens": int(row[20]),
                    "claimverify_prompt_tokens": int(row[21]),
                    "claimverify_completion_tokens": int(row[22]),
                    "total_tokens": int(row[23]),
                })

            # pandas 导出
            try:
                import pandas as pd
                df = pd.DataFrame(excel_rows)
                df.to_excel("z_result.xlsx", index=False)
            except Exception:
                # openpyxl 导出
                try:
                    from openpyxl import Workbook
                    wb = Workbook()
                    ws = wb.active
                    ws.title = "Results"
                    headers = list(excel_rows[0].keys()) if excel_rows else md_header
                    ws.append(headers)
                    for r in excel_rows:
                        ws.append([r.get(h, "") for h in headers])
                    wb.save("z_result.xlsx")
                except Exception:
                    # 最后降级为 CSV
                    import csv
                    headers = list(excel_rows[0].keys()) if excel_rows else md_header
                    with open("z_result.csv", "w", newline="", encoding="utf-8") as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow(headers)
                        for r in excel_rows:
                            writer.writerow([r.get(h, "") for h in headers])
        except Exception:
            # 忽略Excel导出错误，继续流程
            pass
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
            with open("z_result_1.json", "w", encoding="utf-8") as f:
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