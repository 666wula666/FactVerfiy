import json
import os
import argparse
from typing import Any, List, Dict


INPUT_PATH = "/Users/zhangwenyang/Desktop/OpenFactVerification-main/merged_training_data.json"
OUTPUT_PATH = "/Users/zhangwenyang/Desktop/OpenFactVerification-main/test_first_3.json"


def load_items(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Normalize to a list of dicts
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # Try common container keys
        for key in ("data", "items", "results"):
            if key in data and isinstance(data[key], list):
                return data[key]
    raise ValueError("Unsupported JSON root structure; expected list or dict with items")


def extract_response(item: Dict[str, Any]) -> str:
    # Primary mapping: response <- output
    value = item.get("output")
    # Fallbacks if needed
    if value is None:
        for alt in ("response", "text", "content"):
            if alt in item:
                value = item.get(alt)
                break
    # Ensure string
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:
            return str(value)
    return str(value)


def convert(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for idx, item in enumerate(items, start=1):
        out.append({
            "id": idx,
            "response": extract_response(item),
        })
    return out


def main():
    parser = argparse.ArgumentParser(description="Convert merged_training_data.json to test format")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of items to output")
    parser.add_argument("--input", type=str, default=None, help="Input JSON path (default to preset)")
    parser.add_argument("--output", type=str, default=None, help="Output JSON path (default to preset)")
    args = parser.parse_args()

    in_path = args.input or INPUT_PATH
    out_path = args.output or OUTPUT_PATH

    print(f"Loading: {in_path}")
    items = load_items(in_path)
    print(f"Loaded {len(items)} items")

    if args.limit is not None:
        if args.limit <= 0:
            print("--limit must be > 0; ignoring")
        else:
            items = items[:args.limit]
            print(f"Limiting to {len(items)} items")

    converted = convert(items)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(converted, f, ensure_ascii=False, indent=2)
    print(f"Wrote: {out_path} ({len(converted)} items)")


if __name__ == "__main__":
    main()