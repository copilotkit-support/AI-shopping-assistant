"""
Deeper Target support: Search → Extract → (Target PDP discovery) → Extract → JSON-Assist LLM
Retailers: Amazon + Target + eBay

pip install tavily-python openai beautifulsoup4 jsonschema python-dotenv
export TAVILY_API_KEY="tvly-XXXX"
export OPENAI_API_KEY="sk-XXXX"
"""

import os, json, re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, urljoin

from tavily import TavilyClient
from openai import OpenAI
from bs4 import BeautifulSoup
from jsonschema import Draft202012Validator, ValidationError
from dotenv import load_dotenv

load_dotenv()

# RETAILERS = ["amazon.com", "target.com", "ebay.com"]
RETAILERS = ["amazon.com"]

PDP_PATTERNS = {
    "amazon.com": re.compile(r"amazon\.com/.+?/dp/"),
    "target.com": re.compile(r"target\.com/p/"),
    "ebay.com":   re.compile(r"ebay\.com/(itm|p)/"),
}

TARGET_PDP_RX = PDP_PATTERNS["target.com"]
TARGET_ABS = re.compile(r"^https?://")

PRODUCTS_SCHEMA = {
    "type": "object",
    "properties": {
        "source_url": {"type": "string"},
        "retailer": {"type": "string"},
        "products": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["title", "price_text", "product_url"],
                "properties": {
                    "title": {"type": "string"},
                    "product_url": {"type": "string"},
                    "image_urls": {"type": "array", "items": {"type": "string"}},
                    "price_text": {"type": "string"},
                    "price_value": {"type": ["number", "null"]},
                    "price_currency": {"type": ["string", "null"]},
                    "availability": {"type": ["string", "null"]},
                    "rating_value": {"type": ["number", "null"]},
                    "rating_count": {"type": ["integer", "null"]},
                    "model": {"type": ["string", "null"]},
                    "sku": {"type": ["string", "null"]},
                    "specifications": {
                        "type": ["object", "null"],
                        "additionalProperties": {"type": "string"},
                    },
                    "review_text": {"type": ["string", "null"]},
                    "review_sentiment": {
                        "type": ["object", "null"],
                        "properties": {
                            "label": {"type": "string"},
                            "score": {"type": "number"}
                        },
                        "required": ["label", "score"],
                        "additionalProperties": False
                    }
                },
                "additionalProperties": False,
            },
        },
    },
    "required": ["products"],
    "additionalProperties": False,
}

SYSTEM_MSG = """You are a precise web data extractor.
Return STRICT JSON matching the provided JSON Schema.

Rules:
- If input is a PDP, emit exactly one rich product object.
- If input is a listing, emit up to ~20 DISTINCT products, each with a PDP product_url (not homepage or category).
- Include title, product_url, price_text; add image_urls, availability, rating_value, rating_count, model, sku.
- Provide detailed "specifications" as key→value pairs.
- Provide one short "review_text" (from page if available) and "review_sentiment" (label: positive|neutral|negative, score in [-1,1]).
- Parse price_value and price_currency when possible, else set null.
- Output ONLY minified JSON, no commentary.
"""

DETAIL_MODE_HINT = "IMPORTANT: This content is a PRODUCT DETAIL PAGE (PDP). Extract exactly 1 rich product."
LISTING_MODE_HINT = "IMPORTANT: This content is a LISTING. Extract distinct items and ensure each product_url is a PDP."

def is_pdp(url: str) -> bool:
    host = urlparse(url).netloc.replace("www.", "")
    for dom, pat in PDP_PATTERNS.items():
        if dom in host and pat.search(url):
            return True
    return False

def retailer_of(url: str) -> str:
    return urlparse(url).netloc.replace("www.", "")

def find_target_pdps_in_html(raw: str, base: str) -> List[str]:
    """Extract Target PDP links (/p/…) from a category page."""
    out = []

    # Parse DOM
    try:
        soup = BeautifulSoup(raw, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not TARGET_ABS.search(href):
                href = urljoin("https://www.target.com", href)
            if TARGET_PDP_RX.search(href):
                out.append(href.split("?")[0])
    except Exception:
        pass

    # Text regex fallback
    if not out:
        rx = re.compile(r"https?://www\.target\.com/p/[^\s\"')]+")
        out = rx.findall(raw)

    # De-dup & normalize
    uniq = []
    seen = set()
    for u in out:
        u = u.split("?")[0]
        if u not in seen and TARGET_PDP_RX.search(u):
            uniq.append(u)
            seen.add(u)
    return uniq

def parse_target_structured(raw: str) -> Dict[str, Any]:
    """
    Best-effort parse of Target’s on-page JSON (ld+json, Redux-like blobs).
    Returns a lightweight dict with fields we care about to assist the LLM.
    """
    info: Dict[str, Any] = {}
    soup = None
    try:
        soup = BeautifulSoup(raw, "html.parser")
    except Exception:
        return info

    # JSON-LD blocks
    for tag in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string or "{}")
        except Exception:
            continue

        # Some pages wrap in a list
        candidates = data if isinstance(data, list) else [data]
        for d in candidates:
            if not isinstance(d, dict):
                continue
            # Product schema
            if d.get("@type") == "Product":
                info.setdefault("title", d.get("name"))
                agg = d.get("aggregateRating") or {}
                info.setdefault("rating_value", agg.get("ratingValue"))
                info.setdefault("rating_count", agg.get("reviewCount") or agg.get("ratingCount"))
                offers = d.get("offers") or {}
                if isinstance(offers, list) and offers:
                    offers = offers[0]
                if isinstance(offers, dict):
                    info.setdefault("price_text", offers.get("price"))
                    info.setdefault("price_currency", offers.get("priceCurrency"))
                    info.setdefault("availability", offers.get("availability"))
                imgs = d.get("image")
                if isinstance(imgs, list):
                    info.setdefault("image_urls", imgs)
                elif isinstance(imgs, str):
                    info.setdefault("image_urls", [imgs])

    # Look for Redux/state blobs that include technical specs
    # Common key names observed: "product", "bullet_points", "attributes", "specifications", "tcin", "dpci"
    for tag in soup.find_all("script"):
        txt = (tag.string or "").strip()
        if not txt or ("{") not in txt:
            continue
        if any(k in txt for k in ["specifications", "bullet", "attributes", "tcin", "dpci", "price"]):
            # Try to extract the largest JSON object
            start = txt.find("{")
            end = txt.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    blob = json.loads(txt[start:end+1])
                    # naive walk for useful bits
                    def walk(o):
                        if isinstance(o, dict):
                            # price
                            for k in ["current_retail", "price", "formatted_current_price"]:
                                if k in o and "price_text" not in info:
                                    v = o[k]
                                    info["price_text"] = str(v)
                            # specs
                            for k in ["specifications", "attributes", "bullets", "bullet_points"]:
                                if k in o:
                                    specs = {}
                                    v = o[k]
                                    if isinstance(v, dict):
                                        for kk, vv in v.items():
                                            specs[str(kk)] = str(vv)
                                    elif isinstance(v, list):
                                        for item in v:
                                            if isinstance(item, dict) and "name" in item and "value" in item:
                                                specs[str(item["name"])] = str(item["value"])
                                            elif isinstance(item, str):
                                                # key: value lines
                                                if ":" in item:
                                                    kk, vv = item.split(":", 1)
                                                    specs[kk.strip()] = vv.strip()
                                    if specs:
                                        info.setdefault("specifications", specs)
                            # ids
                            for k in ["tcin", "dpci", "upc", "model"]:
                                if k in o and k not in info:
                                    info[k] = str(o[k])
                            # rating
                            for k in ["average_rating", "rating", "rating_value"]:
                                if k in o and "rating_value" not in info:
                                    try:
                                        info["rating_value"] = float(o[k])
                                    except Exception:
                                        pass
                            for k in ["total_reviews", "rating_count", "review_count"]:
                                if k in o and "rating_count" not in info:
                                    try:
                                        info["rating_count"] = int(o[k])
                                    except Exception:
                                        pass
                            for v in o.values():
                                walk(v)
                        elif isinstance(o, list):
                            for it in o:
                                walk(it)
                    walk(blob)
                except Exception:
                    pass

    # Normalize some fields
    if "tcin" in info and "sku" not in info:
        info["sku"] = info["tcin"]
    return info

def build_llm_prompt(raw: str, source_url: str, assist: Optional[Dict[str, Any]] = None, detail_hint: bool = False) -> str:
    hint = DETAIL_MODE_HINT if detail_hint else LISTING_MODE_HINT
    assist_str = json.dumps(assist or {}, ensure_ascii=False)
    return f"""SOURCE_URL: {source_url}

JSON_SCHEMA:
{json.dumps(PRODUCTS_SCHEMA)}

ASSIST_STRUCTURED_HINTS:
{assist_str}

HINTS:
{hint}

RAW_WEB_PAGE:
{raw[:200000]}"""

def call_llm(prompt: str, model: str = "gpt-4o-mini") -> Dict[str, Any]:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_MSG},
            {"role": "user", "content": prompt},
        ],
    )
    data = json.loads(resp.choices[0].message.content)
    Draft202012Validator(PRODUCTS_SCHEMA).validate(data)
    return data

def filter_only_pdps(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for p in products:
        u = p.get("product_url") or ""
        if is_pdp(u):
            out.append(p)
    return out

def search_and_extract_deep(query: str, max_search_results: int = 6, target_follow: int = 6) -> List[Dict[str, Any]]:
    # Setup
    if not os.getenv("TAVILY_API_KEY"):
        raise RuntimeError("Missing TAVILY_API_KEY")
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Missing OPENAI_API_KEY")

    tv = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    results_all: List[Dict[str, Any]] = []

    # 1) Broad search across retailers
    search = tv.search(
        query=query,
        include_domains=RETAILERS,
        include_answer=False,
        include_images=False,
        include_raw_content=False,
        search_depth="advanced",
        max_results=max_search_results,
    )
    urls = [r["url"] for r in search.get("results", []) if r.get("url")]
    if not urls:
        return []

    # 2) First extract pass
    ext1 = tv.extract(urls, extract_depth="advanced", include_images=True)
    target_listing_pdps: List[str] = []

    for item in ext1.get("results", []):
        url = item["url"]
        raw = item.get("raw_content") or ""
        if not raw:
            continue

        dom = retailer_of(url)
        detail_hint = is_pdp(url)
        assist = parse_target_structured(raw) if "target.com" in dom else None
        prompt = build_llm_prompt(raw, url, assist=assist, detail_hint=detail_hint)
        try:
            data = call_llm(prompt)
        except Exception as e:
            # If LLM fails, skip this page
            print(f"LLM 1st-pass failed for {url}: {e}")
            continue

        data.setdefault("source_url", url)
        data.setdefault("retailer", dom)

        # Enforce PDP URLs only for Target to avoid promo tiles
        if "target.com" in dom:
            pdps = filter_only_pdps(data.get("products", []))
            data["products"] = pdps
            # If thin or empty, harvest PDPs from listing HTML
            if not pdps:
                harvested = find_target_pdps_in_html(raw, url)
                target_listing_pdps.extend(harvested[:target_follow])

        results_all.append(data)

    # 3) If Target listing PDPs found, do a second extract pass focused on PDPs
    target_listing_pdps = list(dict.fromkeys([u for u in target_listing_pdps if is_pdp(u)]))[:target_follow]
    if target_listing_pdps:
        ext2 = tv.extract(target_listing_pdps, extract_depth="advanced", include_images=True)
        for item in ext2.get("results", []):
            url = item["url"]
            raw = item.get("raw_content") or ""
            if not raw:
                continue
            assist = parse_target_structured(raw)
            prompt = build_llm_prompt(raw, url, assist=assist, detail_hint=True)
            try:
                data = call_llm(prompt)
                data["source_url"] = url
                data["retailer"] = "target.com"
                # Keep exactly one product for PDP
                if data.get("products"):
                    data["products"] = data["products"][:1]
                    results_all.append(data)
            except Exception as e:
                print(f"Target PDP enrich failed for {url}: {e}")

    return results_all

def main():
    query = "Best Smartwatches under $400"
    results = search_and_extract_deep(query, max_search_results=8, target_follow=8)

    for site in results:
        print(f"\n=== {site.get('retailer')} ({site.get('source_url')}) ===")
        for p in site.get("products", []):
            print(json.dumps(p, ensure_ascii=False))

if __name__ == "__main__":
    main()
