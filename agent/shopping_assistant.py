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
import re
from urllib.parse import unquote
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import random
load_dotenv()

class AgentState(CopilotKitState):
    """
    This is the state of the agent.
    It is a subclass of the MessagesState class from langgraph.
    """
    products: List
    favorites: List
    buffer_products: List
    wishlist: List
    logs: List
    report: str
    show_results: bool
    canvas_logs : dict = { "title" : "", "subtitle" : "" }


async def agent_node(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    This is the chat node of the agent.
    It is a function that takes in the state of the agent and the config and returns the state of the agent.
    """
    try:
        if config is None:
            config = RunnableConfig(recursion_limit=25)
        else:
            # Use CopilotKit's custom config functions to properly set up streaming
            config = copilotkit_customize_config(config, emit_messages=False, emit_tool_calls=True)
        state["canvas_logs"] = {
            "title" : f"Analyzing user query",
            "subtitle" : "Deciding to run product search or not"
        }
        await copilotkit_emit_state(config, state)
        await asyncio.sleep(0)
        if not os.getenv("TAVILY_API_KEY"):
            raise RuntimeError("Missing TAVILY_API_KEY")
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("Missing OPENAI_API_KEY")
        if state['messages'][-1].type == 'ai':
            result =await generate_report(state["products"])
            print(result, "result")
            return Command(
                goto=END,
                update={
                    **state,
                    "report" : json.loads(result)
                }
            )
        model = ChatOpenAI(model="gpt-4o-mini")
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
                "name" : product['title'],
                "id" : product['id'],
            })
        if(state["messages"][-1].type == 'tool'):
            if(state["messages"][-1].content == "Show more products"):
                state["messages"].append(AIMessage(id=state["messages"][-2].tool_calls[0]['id'], type="ai",  content='Some more products also has been added to be shown in the canvas'))
                state["logs"] = []
                state["show_results"] = True
                await copilotkit_emit_state(config, state)
                return Command(
                    goto=END,
                    update={
                        "buffer_products" : state["buffer_products"],
                        "messages" : state["messages"]
                    }
                )
            if(state["messages"][-1].content == "Rejected"):
                state["messages"].append(AIMessage(id=state["messages"][-2].tool_calls[0]['id'], type="ai",  content='You have rejected the products. Please try any other product search.'))
                state["logs"] = []
                await copilotkit_emit_state(config, state)
                return Command(
                    goto=END,
                    update={
                        "buffer_products" : state["buffer_products"],
                        "messages" : state["messages"]
                    }
                )            
            if(state["messages"][-1].content == "Accepted"):
                state["messages"].append(AIMessage(id=state["messages"][-2].tool_calls[0]['id'], type="ai",  content='The top 5 products have been added to the canvas.'))
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
            state["messages"].append(AIMessage(content=response.content, type="ai", id= state["messages"][-2].tool_calls[0]['id']))
            state["logs"] = []
            if len(state["products"]) > 0:
                state["show_results"] = True
            await copilotkit_emit_state(config, state)
                
            return Command(
                goto=END,
                update={
                    "messages" : state["messages"],
                    "buffer_products" : state["buffer_products"]
                }
            )
        
        messages = state["messages"]
        system_message = f"""You are a shoppning assistant. You will be provided with the current products in canvas and wishlist. You will be able to edit the products in canvas and wishlist. If the products are not in the canvas or wishlist, you can just reply with 'No products found'. The current products in canvas are {json.dumps(products_for_prompt)} and the current products in wishlist are {json.dumps(wishlist_for_prompt)}.
        #IMPORTANT NOTE:
        -If the user asks any general question, you can just reply with some general replies. 
        -If user ask to search for any other product without explicitly saying to look in the canvas or wishlist, you need to just reply with 'SEARCH'. DO NOT TRIGGER the edit_product_canvas tool when user asks to search for any other product. Instead reply with 'SEARCH'.
        
        EXAMPLES:
        - Get me some amazing Dishwashers.
        - Get me some amazing Laptops.
            The above 2 shoule return 'SEARCH'
        - Move LG G5 to wishlist.
        - Remove LG G5 to wishlist.
            THe above 2 should trigger the edit_product_canvas tool.
        """
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
            state["messages"].append(AIMessage(id=str(uuid.uuid4()), type="ai",  tool_calls=response0.tool_calls, content=''))
            return Command(
                goto=END,
                update={
                    "buffer_products" : state["buffer_products"],
                    "messages" : state["messages"]
                }
            )
        if (not response0.content.startswith('SEARCH')):
            state["messages"].append(AIMessage(id=str(uuid.uuid4()), type="ai",  content=response0.content))
            state["logs"] = []
            await copilotkit_emit_state(config, state)
            return Command(
                goto=END,
                update={
                    "buffer_products" : state["buffer_products"],
                    "messages" : state["messages"]
                }
            )
        
        
        
        
        
        query = state["messages"][-1].content
        max_search_results = 6
        target_follow = 6
        state["show_results"] = False
        await copilotkit_emit_state(config, state)
        tv = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        results_all: List[Dict[str, Any]] = []
        total_mappings_list = []
        state["logs"].append({
            "message" : "Identifying the sites to search",
            "status" : "processing"
        })
        await copilotkit_emit_state(config, state)
        await asyncio.sleep(1)
        state["logs"][-1]["status"] = "completed"
        await copilotkit_emit_state(config, state)
        # 1) Broad search across retailers
        urls = {}
        for retailer in RETAILERS:
            search = tv.search(
                query=query,
                include_domains=[retailer],
                include_answer=False,
                include_images=False,
                include_raw_content=False,
                search_depth="advanced",
                max_results=max_search_results,
            )
                
            urls[retailer] = [r["url"] for r in search.get("results", []) if r.get("url")]
            if not urls[retailer]:
                continue

        state["logs"].append({
            "message" : "Extracting the sites",
            "status" : "processing"
        })
        state["canvas_logs"] = {
            "title" : "Extracting the sites markdown content from the identified sites",
            "subtitle" : "Tavily extraction in progress...."
        }
        await copilotkit_emit_state(config, state)
        await asyncio.sleep(1)
        # 2) First extract pass
        
        
        def extract_urls(urls: List[str], retailer: str) -> Dict[str, Any]:
            try:
                print(f"Extracting urls for {retailer}. Started at {datetime.now()}")
                ext1 = tv.extract(urls, extract_depth="advanced", include_images=True, timeout=120)
                return [ext1, retailer]
            except Exception as e:
                print(f"Error extracting urls: {e}")
                return None
        ext_results = {}
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(extract_urls, urls[retailer], retailer) : retailer for retailer in RETAILERS}
            
            for future in as_completed(futures):
                result = future.result()
                ext_results[result[1]] = result[0].get("results", [])
                if result == None:
                    print("Condition met! Cancelling remaining tasks...")
                    # Cancel all futures not yet started
                    for f in futures:
                        f.cancel()
                    break

        
        
        
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
        products_from_each_site= {
            "target.com" : [],
            "amazon.com" : [],
            "ebay.com" : []
        }
        
        async def process_data(ext_results1: Dict[str, Any], retailer: str) -> str:
            print(f"Processing data for {retailer}. Started at {datetime.now()}")
            for item in ext_results1:
                url = item["url"]
                raw = item.get("raw_content") or ""
                if not raw:
                    return None
                modiefied_text, mappings_list = replace_urls_with_product_and_image_links(raw)
                total_mappings_list.extend(mappings_list)
                dom = retailer_of(url)
                detail_hint = is_pdp(url)
                assist = parse_target_structured(modiefied_text) if "target.com" in dom else None
                prompt = build_llm_prompt(modiefied_text, url, assist=assist, detail_hint=detail_hint)
                try:
                    if len(products_from_each_site[retailer]) > 2:
                        break
                    print(f"Calling LLM for {url}")
                    # state["canvas_logs"] = {
                    #     "title" : "Structuring product content from site's markdown",
                    #     "subtitle" : "LLM processing in progress...."
                    # }
                    # await copilotkit_emit_state(config, state)
                    # await asyncio.sleep(2)
                    state["canvas_logs"] = {
                        "title" : f"Processing the Markdown content from {unquote(url)}",
                        "subtitle" : "LLM processing in progress...."
                    }
                    await copilotkit_emit_state(config, state)
                    await asyncio.sleep(0)
                    data = call_llm(prompt)
                    print(f"Completed extracting {url}")
                    done = True
                except Exception as e:
                    # If LLM fails, skip this page
                    print(f"LLM 1st-pass failed for {url}: {e}")
                    continue

                data.setdefault("source_url", url)
                data.setdefault("retailer", dom)
                products_from_each_site[retailer] += data["products"]
            return "Completed"

        
        
        # for retailer in ext_results:
        tasks = [process_data(ext_results[retailer], retailer) for retailer in ext_results]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Task failed with exception: {result}")
            elif result is None:
                print("Condition met in one of the tasks")
        
        
        results_all = combine_products_from_sites(products_from_each_site)
        print(len(results_all), "results_all here")
        
        for item in results_all:
            item["id"] = str(uuid.uuid4())
        state["logs"][-1]["status"] = "completed"
        await copilotkit_emit_state(config, state)
        
        updated_products = apply_url_mappings_to_products(results_all, total_mappings_list)
        print(len(updated_products), "updated_products here")
        state["buffer_products"] = updated_products
        # state["buffer_products"] = results_all
        print("HERE")
        chat_name = await generate_name_for_chat(query)
        print(chat_name, "chat_name here")
        # await copilotkit_emit_state(config, state)
        state["messages"].append(AIMessage(id=str(uuid.uuid4()), tool_calls=[{"name": "list_products", "args": {"products": state["buffer_products"][:5], "buffer_products" : state["buffer_products"], "chat_name" : chat_name}, "id": str(uuid.uuid4())}], type="ai",  content=''))
        state["logs"] = []
        # await copilotkit_emit_state(config, state)
        state["show_results"] = True
        await copilotkit_emit_state(config, state)
        return Command(
            goto=END,
            update={
                "messages": state["messages"],
                "buffer_products" : state["buffer_products"],
                "report" : None,
                "canvas_logs" : {
                    "title" : "Awaiting confirmation from the user",
                    "subtitle" : "Choose to accept, reject or show all products"
                }
            }
        )
    except Exception as e:
        print(e, "error")
        if hasattr(e, 'code') and e.code == "context_length_exceeded":
            error_message = AIMessage(content="Context length limit exceeded. Please try your query in a new chat.", id=str(uuid.uuid4()), type="ai")
            state["logs"] = []
            state["messages"].append(error_message)
        else:
            error_message = AIMessage(content="Something went wrong. Please try your query in a new chat.", id=str(uuid.uuid4()), type="ai")
            state["messages"].append(error_message)
            state["logs"] = []
        return Command(
            goto=END,
            update={
                "messages": state["messages"],
            }
        )
    
    
    
    
    


async def generate_report(products: List[Dict[str, Any]]) -> str:
    """
    Generate a report for the given products.
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format= {"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_MSG1},
            {"role": "user", "content": json.dumps(products)}
        ]
    )
    return response.choices[0].message.content



async def generate_name_for_chat(query: str) -> str:
    """
    Generate a report for the given products.
    """
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_MSG2},
                {"role": "user", "content": query}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(e, "error")
        raise e

workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)
workflow.set_entry_point("agent")
workflow.add_edge(START, "agent")
workflow.add_edge("agent", END)

memory = MemorySaver()
graph = workflow.compile(checkpointer=memory)




RETAILERS = ["target.com", "amazon.com", "ebay.com"]

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
                    "price_value": {"type": ["number", "null"]},
                    "price_currency": {"type": ["string", "null"]},
                    "availability": {"type": ["string", "null"]},
                    "rating_value": {"type": ["number", "null"]},
                    "rating_count": {"type": ["integer", "null"]},
                    "model": {"type": ["string", "null"]},
                    "sku": {"type": ["string", "null"]},
                    "pros": {"type": "array", "items" : {"type" : "string"}},
                    "cons": {"type": "array", "items" : {"type" : "string"}},
                    "key_insights_from_reviews": {"type": "array", "items" : {"type" : "string"}},
                    "review_sentiment": {
                        "type": ["object", "null"],
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
            },
        },
    },
    "required": ["products"],
    "additionalProperties": False,
}
REPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "top_pick": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "summary": {"type": "string"},
            }
        },
        "best_performance": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "summary": {"type": "string"},
            }
        },
        "best_value_for_money": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "summary": {"type": "string"},
            }
        },
        "products_specifications": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "specifications": {"type": "array", "items": {"type": "string"}},
            }
        }
    }
}
SYSTEM_MSG = """You are a precise web data extractor
Return STRICT JSON matching the provided JSON Schema.

Rules:
- If input is a PDP, emit exactly one rich product object.
- If input is a listing, emit up to ~20 DISTINCT products, each with a PDP product_url (not homepage or category).
- Include title, product_url, price_text; add image_urls, availability, rating_value, rating_count, model, sku.
- If image_urls is not present, then return empty array.
- Provide "pros" and "cons" as array of strings. Make sure to have 2 pros and 2 cons. If you cant find pros and cons from the text data, Generate it yourself.
- Provide at least 5 "key_insights_from_reviews" and "review_sentiment" (label: positive|neutral|negative, score in [0,1]).
- Parse price_value and price_currency when possible, else set null.
- Output ONLY minified JSON, no commentary.
"""
SYSTEM_MSG1 = f"""You are a Products report generator
Return STRICT JSON matching the provided JSON Schema

Rules:
- You are given a list of products.
- You need to generate a report based on the given products.
- You should also generate specifications for all the products that is given. Make sure to have at least 5 specifications for each product. Also the specs titles should be uniform for all the products. like processor, ram, storage, display, battery, weight, ports, os, etc. You need to use web search for the specifications.
- The report should have the product with a top pick with a bit of summary.
- The report should have the product with best performance with a bit of summary.
- The report should have the product with best value for the money with a bit of summary

JSON_SCHEMA:
{json.dumps(REPORT_SCHEMA)}

"""

SYSTEM_MSG2 = """
You are a name generator for a chat. You will be given a user query and you need to generate a name for the chat based on the query.
# RULES:
- The output should strictly contain only the name for the chat. DO NOT ADD ANYTHING ELSE.
- The name should be of appropriate length. Maximum 3 or 4 words.
- The name of the chat should be professional and should not be too casual.
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
        model="gpt-5-mini",
        response_format={"type": "json_object"},
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



import re
from urllib.parse import urlsplit

def replace_urls_with_product_and_image_links(
    text: str,
    product_base: str = "https://amzn.com/url{}",
    image_base: str = "https://amzn.com/img/url{}",
    exempt_prefixes: tuple = (),
):
    """
    Replace URLs in `text` with unique placeholders:
      - image URLs -> image_base.format(i) e.g., https://productImg1.ai
      - non-image URLs -> product_base.format(j) e.g., https://productUrl1.ai

    Rules:
      - Same original URL always maps to the same replacement.
      - URLs starting with any `exempt_prefixes` are left untouched.
      - Trailing punctuation like '),.;:!?]' is preserved.

    Returns
    -------
    new_text : str
        Text with all replacements applied.
    mappings_list : list[list[str, str]]
        Pairs of [original_url, replacement_url] for all *non-exempt* URLs
        (includes both image and non-image mappings).
    """
    # Robust-enough matcher for http/https inside natural text
    url_re = re.compile(r'\bhttps?://[^\s<>()"\']+', re.IGNORECASE)
    TRAILING_PUNCT = set('),.;:!?]')

    # Common image extensions (lowercased, matched on the URL path)
    IMAGE_EXTS = (
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp",
        ".svg", ".tif", ".tiff", ".avif", ".heic", ".heif", ".jfif"
    )

    def _is_image_url(u: str) -> bool:
        # Strip query/fragment; decide using only the path
        path = urlsplit(u).path.lower()
        return any(path.endswith(ext) for ext in IMAGE_EXTS)

    # One mapping table for all URLs (image + non-image)
    mapping: dict[str, str] = {}
    pairs: list[list[str, str]] = []

    # Independent counters to keep numbering separate & clear
    product_counter = 0
    image_counter = 0

    def _repl(m: re.Match) -> str:
        nonlocal product_counter, image_counter
        token = m.group(0)

        # Separate trailing punctuation often glued to URLs in prose
        url = token
        trailing = ""
        while url and url[-1] in TRAILING_PUNCT:
            trailing = url[-1] + trailing
            url = url[:-1]

        # Exemptions: leave untouched
        if url.startswith(exempt_prefixes):
            return url + trailing

        # Assign or reuse a replacement
        if url not in mapping:
            if _is_image_url(url):
                image_counter += 1
                repl_url = image_base.format(image_counter)
            else:
                product_counter += 1
                repl_url = product_base.format(product_counter)
            mapping[url] = repl_url
            pairs.append([repl_url, url])
        else:
            repl_url = mapping[url]

        return repl_url + trailing

    new_text = url_re.sub(_repl, text)
    return new_text, pairs



def apply_url_mappings_to_products(products: list[dict], mappings: list[list[str, str]]) -> list[dict]:
    """
    Replace 'product_url' and 'image_urls' values in each product dict 
    using the given URL mappings.

    Parameters
    ----------
    products : list of dict
        Each dict has keys like 'product_url' and 'image_urls'.
    mappings : list of [original_url, replacement_url]
        Output from replace_urls_with_product_links.

    Returns
    -------
    updated_products : list of dict
        New list with URLs replaced where possible.
    """
    mapping_dict = dict(mappings)  # quick lookup

    updated_products = []
    for product in products:
        new_product = product.copy()

        # Replace product_url if present in mapping
        if "product_url" in new_product and new_product["product_url"] in mapping_dict:
            new_product["product_url"] = next((mapping for mapping in mappings if product['product_url'] in mapping), None )
            new_product["product_url"] = new_product["product_url"][1]
        # Replace each image URL
        if "image_urls" in new_product:
            if(len(new_product["image_urls"]) > 0):
                new_product["image_urls"] = next((mapping for mapping in mappings if new_product['image_urls'][0] in mapping), None )
                new_product["image_urls"] = [new_product["image_urls"][1]]
            else:
                new_product["image_urls"] = []

        updated_products.append(new_product)

    return updated_products


def combine_products_from_sites(products_from_each_site: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Combine exactly 5 products from all retailers, ensuring at least one product from each retailer.
    Returns only 5 products total.

    Args:
        products_from_each_site: Dict with site names as keys and list of products as values

    Returns:
        List of exactly 5 combined products
    """
    retailers = list(products_from_each_site.keys())
    selected_products = []

    # Step 1: Take exactly one product from each retailer
    for retailer in retailers:
        products = products_from_each_site[retailer]
        print(len(products), f"products from {retailer} here")
        if products:  # Make sure there are products available
            # Take the first product from this retailer
            selected_products.append(products[0])

    # Step 2: Take 2 more products randomly from any retailer
    # Create a pool of remaining products from all retailers
    remaining_pool = []
    for retailer in retailers:
        products = products_from_each_site[retailer]
        if len(products) > 1:  # Skip the first product since we already took it
            remaining_pool.extend(products[1:])

    # Randomly select 2 more products from the remaining pool
    if len(remaining_pool) >= 2:
        additional_products = random.sample(remaining_pool, 2)
        selected_products.extend(additional_products)
        remaining_pool = [p for p in remaining_pool if p not in additional_products]
    elif len(remaining_pool) == 1:
        # If only 1 remaining product, take it
        selected_products.extend(remaining_pool)
    # If no remaining products, we'll have only the guaranteed one from each retailer

    # Step 3: If we don't have exactly 5 products, fill with more from any retailer
    while len(selected_products) < 5:
        # Try to get more products from retailers that have them
        for retailer in retailers:
            products = products_from_each_site[retailer]
            # Find products not already selected
            used_indices = set()
            for selected in selected_products:
                if selected in products:
                    used_indices.add(products.index(selected))

            available_products = [p for i, p in enumerate(products) if i not in used_indices]
            if available_products:
                selected_products.append(random.choice(available_products))
                break

    # Step 4: Randomly shuffle the final 5 products
    random.shuffle(selected_products)
    print(len(selected_products), "selected_products here")
    selected_products.extend(remaining_pool)
    print(len(selected_products), "final_products here")
    # Return only the first 5 products
    return selected_products
