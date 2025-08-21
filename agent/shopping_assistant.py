from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage
from copilotkit.langgraph import copilotkit_emit_state, copilotkit_customize_config, CopilotKitState
from typing import List
import os, json, re, asyncio
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, urljoin
import uuid
from tavily import TavilyClient
from openai import OpenAI
from bs4 import BeautifulSoup
from jsonschema import Draft202012Validator, ValidationError
from dotenv import load_dotenv

load_dotenv()

class AgentState(CopilotKitState):
    """
    This is the state of the agent.
    It is a subclass of the MessagesState class from langgraph.
    """
    products: List
    favorites: List
    buffer_products: List
    logs: List


async def chat_node(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    This is the chat node of the agent.
    It is a function that takes in the state of the agent and the config and returns the state of the agent.
    """
    if config is None:
        config = RunnableConfig(recursion_limit=25)
    else:
        # Use CopilotKit's custom config functions to properly set up streaming
        config = copilotkit_customize_config(config, emit_messages=False, emit_tool_calls=True)
    
    if not os.getenv("TAVILY_API_KEY"):
        raise RuntimeError("Missing TAVILY_API_KEY")
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Missing OPENAI_API_KEY")
    model = ChatOpenAI(streaming=False)
    state["logs"].append({
        "message" : "Analyzing user query",
        "status" : "processing"
    })
    await copilotkit_emit_state(config, state)
    await asyncio.sleep(1)
    state["logs"][-1]["status"] = "completed"
    await copilotkit_emit_state(config, state)
    query = state["messages"][-1].content
    products_for_prompt = []
    wishlist_for_prompt = []
    for product in state["products"]:
        products_for_prompt.append({
            "name" : product["title"],
            "id" : product["id"],
        })
    for product in state["favorites"]:
        wishlist_for_prompt.append({
            "id" : product,
        })
    if(state["messages"][-1].type == 'tool'):
        if(state["messages"][-1].content == "Show more products"):
            state["messages"].append(AIMessage(id=str(uuid.uuid4()), type="ai",  content='Some more products also has been added to be shown in the canvas'))
            state["logs"] = []
            await copilotkit_emit_state(config, state)
            return Command(
                goto=END,
                update={
                    "buffer_products" : state["buffer_products"],
                    "messages" : state["messages"]
                }
            )
        if(state["messages"][-1].content == "Rejected"):
            state["messages"].append(AIMessage(id=str(uuid.uuid4()), type="ai",  content='You have rejected the products. Please try any other product search.'))
            state["logs"] = []
            await copilotkit_emit_state(config, state)
            return Command(
                goto=END,
                update={
                    "buffer_products" : state["buffer_products"],
                    "messages" : state["messages"]
                }
            )            
        response = await model.ainvoke(input=state['messages'])
        state["messages"].append(AIMessage(content=response.content, type="ai", id= str(uuid.uuid4())))
        state["logs"] = []
        await copilotkit_emit_state(config, state)
            
        return Command(
            goto=END,
            update={"messages" : state["messages"]}
        )
    
    messages = state["messages"]
    
    system_message = f"You are a shoppning assistant. You will be provided with the current products in canvas and wishlist. You will be able to edit the products in canvas and wishlist. If the products are not in the canvas or wishlist, you can just reply with 'No products found'. Also, if user asks for any other product, you can just reply with 'No products found'. Do not try to search for the products in the web. The current products in canvas are {json.dumps(products_for_prompt)} and the current products in wishlist are {json.dumps(wishlist_for_prompt)}"
    # system_message = ''
    state["copilotkit"]["actions"] = list(filter(lambda x: x['name'] == "edit_product_canvas", state["copilotkit"]["actions"]))
    response0 = await model.bind_tools([
        *state["copilotkit"]["actions"]
    ]).ainvoke([
        system_message,
        *messages
    ],config=config)
    if hasattr(response0, "tool_calls") and response0.tool_calls and response0.content == '':        
        state["logs"] = []
        await copilotkit_emit_state(config, state)
            
        return Command(
            goto=END,
            update={
                "buffer_products" : state["buffer_products"],
                "messages" : response0
            }
        )
    
    
    
    
    
    # query = state["messages"][-1].content
    max_search_results = 8
    target_follow = 6

    tv = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    results_all: List[Dict[str, Any]] = []

    state["logs"].append({
        "message" : "Identifying the sites to search",
        "status" : "processing"
    })
    await copilotkit_emit_state(config, state)
    await asyncio.sleep(1)
    state["logs"][-1]["status"] = "completed"
    await copilotkit_emit_state(config, state)
    # 1) Broad search across retailers
    search = tv.search(
        query=query,
        include_domains=RETAILERS,
        include_answer=False,
        include_images=False,
        include_raw_content=True,
        search_depth="advanced",
        max_results=max_search_results,
    )
    urls = [r["url"] for r in search.get("results", []) if r.get("url")]
    if not urls:
        return []

    state["logs"].append({
        "message" : "Extracting the sites",
        "status" : "processing"
    })
    await copilotkit_emit_state(config, state)
    await asyncio.sleep(1)
    # 2) First extract pass
    ext1 = tv.extract(urls, extract_depth="advanced", include_images=True)
    state["logs"][-1]["status"] = "completed"
    await copilotkit_emit_state(config, state)
    
    target_listing_pdps: List[str] = []
    done = False
    state["logs"].append({
        "message" : "Processing the data",
        "status" : "processing"
    })
    await copilotkit_emit_state(config, state)
    # await asyncio.sleep(1)
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
            if len(results_all) > 10:
                break
            data = call_llm(prompt)
            done = True
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

        results_all += data["products"]

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
    
    
    for item in results_all:
        item["id"] = str(uuid.uuid4())
    state["logs"][-1]["status"] = "completed"
    await copilotkit_emit_state(config, state)
    
    state["buffer_products"] = results_all
    
    await copilotkit_emit_state(config, state)
    state["messages"].append(AIMessage(id=str(uuid.uuid4()), tool_calls=[{"name": "list_products", "args": {"products": state["buffer_products"][:10], "buffer_products" : state["buffer_products"][:15]}, "id": str(uuid.uuid4())}], type="ai",  content=''))
    state["logs"] = []
    await copilotkit_emit_state(config, state)
            
    return Command(
        goto=END,
        update={
            "messages": state["messages"],
            "buffer_products" : state["buffer_products"]
        }
    )
    
    
    



workflow = StateGraph(AgentState)
workflow.add_node("chat", chat_node)
workflow.set_entry_point("chat")
workflow.add_edge(START, "chat")
workflow.add_edge("chat", END)

memory = MemorySaver()
graph = workflow.compile(checkpointer=memory)




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
        "id": {"type": "string"},
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
                    "price_value": {"type": ["number", "None"]},
                    "price_currency": {"type": ["string", "None"]},
                    "availability": {"type": ["string", "None"]},
                    "rating_value": {"type": ["number", "None"]},
                    "rating_count": {"type": ["integer", "None"]},
                    "model": {"type": ["string", "None"]},
                    "sku": {"type": ["string", "None"]},
                    "specifications": {
                        "type": ["object", "None"],
                        "additionalProperties": {"type": "string"},
                    },
                    "key_insights_from_reviews": {"type": "array", "items" : {"type" : "string"}},
                    "review_sentiment": {
                        "type": ["object", "None"],
                        "properties": {
                            "positive_score": {"type": "number"},
                            "negative_score": {"type": "number"},
                            "neutral_score": {"type": "number"}
                        },
                        "required": ["positive_score", "negative_score", "neutral_score"],
                        "additionalProperties": False
                    },
                    "recommendation_score_out_of_100": {"type": "number"},
                    "would_buy_again_score_out_of_100": {"type": "number"}
                    
                },
                "additionalProperties": False,
            },
        },
    },
    "required": ["products"],
    "additionalProperties": False,
}

SYSTEM_MSG = """You are a precise web data extractor
Return STRICT JSON matching the provided JSON Schema.

Rules:
- If input is a PDP, emit exactly one rich product object.
- If input is a listing, emit up to ~20 DISTINCT products, each with a PDP product_url (not homepage or category).
- Include title, product_url, price_text; add image_urls, availability, rating_value, rating_count, model, sku.
- Provide detailed "specifications" as key→value pairs.
- Provide one short "review_text" (from page if available) and "review_sentiment" (label: positive|neutral|negative, score in [-1,1]).
- Parse price_value and price_currency when possible, else set None.
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
