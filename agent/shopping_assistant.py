from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage
from copilotkit.langgraph import copilotkit_emit_state, copilotkit_customize_config
from typing import List
import os, json, re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, urljoin
import uuid
from tavily import TavilyClient
from openai import OpenAI
from bs4 import BeautifulSoup
from jsonschema import Draft202012Validator, ValidationError
from dotenv import load_dotenv

load_dotenv()

class AgentState(MessagesState):
    """
    This is the state of the agent.
    It is a subclass of the MessagesState class from langgraph.
    """
    products: List
    favorites: List
    buffer_products: List


async def chat_node(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    This is the chat node of the agent.
    It is a function that takes in the state of the agent and the config and returns the state of the agent.
    """
    if config is None:
        config = RunnableConfig(recursion_limit=25)
    else:
        # Use CopilotKit's custom config functions to properly set up streaming
        config = copilotkit_customize_config(config)
    
    if not os.getenv("TAVILY_API_KEY"):
        raise RuntimeError("Missing TAVILY_API_KEY")
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Missing OPENAI_API_KEY")
    
    if(state["messages"][-1].type == 'tool'):
        if(state["messages"][-1].content == "Show more products"):
            state["messages"].append(AIMessage(id=str(uuid.uuid4()), type="ai",  content='Some more products also has been added to be shown in the canvas'))
            return Command(
                goto=END,
                update={"messages" : state["messages"]}
            )
        if(state["messages"][-1].content == "Rejected"):
            state["messages"].append(AIMessage(id=str(uuid.uuid4()), type="ai",  content='You have rejected the products. Please try any other product search.'))
            return Command(
                goto=END,
                update={"messages" : state["messages"]}
            )            
        model = ChatOpenAI()
        response = await model.ainvoke(input=state['messages'])
        state["messages"].append(AIMessage(content=response.content, type="ai", id= str(uuid.uuid4())))
        return Command(
            goto=END,
            update={"messages" : state["messages"]}
        )
    
    query = state["messages"][-1].content
    max_search_results = 8
    target_follow = 6

    tv = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    # results_all: List[Dict[str, Any]] = []
    results_all: List[Dict[str, Any]] = [{"title": "Apple iPhone 13, 128GB, Midnight - Unlocked (Renewed)", "product_url": "https://www.amazon.com/Apple-iPhone-13-128GB-Midnight/dp/B09LNW3CY2/ref=zg_bs_g_17871142011_d_sccl_1/145-3511079-4848163?psc=1", "image_urls": ["https://images-na.ssl-images-amazon.com/images/I/61VuVU94RnL._AC_UL600_SR600,400_.jpg"], "price_text": "$302.98", "price_value": 302.98, "price_currency": "USD", "availability": "In Stock", "rating_value": 4.0, "rating_count": 17233, "model": "iPhone 13", "sku": "B09LNW3CY2", "specifications": {"Storage": "128GB", "Color": "Midnight", "Unlocked": "Yes"}, "review_text": ["Great phone, works perfectly!"], "review_sentiment": {"label": "positive", "score": 0.9}}, {"title": "Apple iPhone 12, 64GB, Black - Fully Unlocked (Renewed)", "product_url": "https://www.amazon.com/Apple-iPhone-12-64GB-Black/dp/B08PP5MSVB/ref=zg_bs_g_17871142011_d_sccl_2/145-3511079-4848163?psc=1", "image_urls": ["https://images-na.ssl-images-amazon.com/images/I/51fYXSnSu9L._AC_UL600_SR600,400_.jpg"], "price_text": "$216.00", "price_value": 216.0, "price_currency": "USD", "availability": "In Stock", "rating_value": 4.1, "rating_count": 30949, "model": "iPhone 12", "sku": "B08PP5MSVB", "specifications": {"Storage": "64GB", "Color": "Black", "Unlocked": "Yes"}, "review_text": ["Excellent value for the price."], "review_sentiment": {"label": "positive", "score": 0.85}}, {"title": "Apple iPhone 14, 128GB, Midnight - Unlocked (Renewed)", "product_url": "https://www.amazon.com/Apple-iPhone-14-128GB-Midnight/dp/B0BN72FYFG/ref=zg_bs_g_17871142011_d_sccl_3/145-3511079-4848163?psc=1", "image_urls": ["https://images-na.ssl-images-amazon.com/images/I/61WUSYIQdKL._AC_UL600_SR600,400_.jpg"], "price_text": "$360.00", "price_value": 360.0, "price_currency": "USD", "availability": "In Stock", "rating_value": 4.0, "rating_count": 5324, "model": "iPhone 14", "sku": "B0BN72FYFG", "specifications": {"Storage": "128GB", "Color": "Midnight", "Unlocked": "Yes"}, "review_text": ["Great upgrade from my old phone."], "review_sentiment": {"label": "positive", "score": 0.9}}, {"title": "Apple iPhone 12 Mini, 64GB, Black - Unlocked (Renewed)", "product_url": "https://www.amazon.com/Apple-iPhone-12-Mini-Black/dp/B08PPDJWC8/ref=zg_bs_g_17871142011_d_sccl_4/145-3511079-4848163?psc=1", "image_urls": ["https://images-na.ssl-images-amazon.com/images/I/61bbqGftbUL._AC_UL600_SR600,400_.jpg"], "price_text": "$190.00", "price_value": 190.0, "price_currency": "USD", "availability": "In Stock", "rating_value": 4.0, "rating_count": 16347, "model": "iPhone 12 Mini", "sku": "B08PPDJWC8", "specifications": {"Storage": "64GB", "Color": "Black", "Unlocked": "Yes"}, "review_text": ["Compact and powerful."], "review_sentiment": {"label": "positive", "score": 0.8}}, {"title": "Apple iPhone 11, 64GB, Black - Unlocked (Renewed)", "product_url": "https://www.amazon.com/Apple-iPhone-11-64GB-Black/dp/B07ZPKN6YR/ref=zg_bs_g_17871142011_d_sccl_5/145-3511079-4848163?psc=1", "image_urls": ["https://images-na.ssl-images-amazon.com/images/I/61MG3m5FhIL._AC_UL600_SR600,400_.jpg"], "price_text": "$201.00", "price_value": 201.0, "price_currency": "USD", "availability": "In Stock", "rating_value": 4.2, "rating_count": 56332, "model": "iPhone 11", "sku": "B07ZPKN6YR", "specifications": {"Storage": "64GB", "Color": "Black", "Unlocked": "Yes"}, "review_text": ["Fantastic phone for the price."], "review_sentiment": {"label": "positive", "score": 0.9}}, {"title": "Apple iPhone 13 Pro, 128GB, Graphite - Unlocked (Renewed)", "product_url": "https://www.amazon.com/Apple-iPhone-13-Pro-Graphite/dp/B09LP77GDL/ref=zg_bs_g_17871142011_d_sccl_6/145-3511079-4848163?psc=1", "image_urls": ["https://images-na.ssl-images-amazon.com/images/I/51UtM-A3fdL._AC_UL600_SR600,400_.jpg"], "price_text": "$386.95", "price_value": 386.95, "price_currency": "USD", "availability": "In Stock", "rating_value": 4.0, "rating_count": 6807, "model": "iPhone 13 Pro", "sku": "B09LP77GDL", "specifications": {"Storage": "128GB", "Color": "Graphite", "Unlocked": "Yes"}, "review_text": ["Great performance and camera."], "review_sentiment": {"label": "positive", "score": 0.9}}, {"title": "Apple iPhone 13 Mini, 128GB, Midnight - Unlocked (Renewed)", "product_url": "https://www.amazon.com/Apple-iPhone-13-Mini-Midnight/dp/B09LKTXKXQ/ref=zg_bs_g_17871142011_d_sccl_7/145-3511079-4848163?psc=1", "image_urls": ["https://images-na.ssl-images-amazon.com/images/I/61H3jeeHnUL._AC_UL600_SR600,400_.jpg"], "price_text": "$272.00", "price_value": 272.0, "price_currency": "USD", "availability": "In Stock", "rating_value": 4.0, "rating_count": 5911, "model": "iPhone 13 Mini", "sku": "B09LKTXKXQ", "specifications": {"Storage": "128GB", "Color": "Midnight", "Unlocked": "Yes"}, "review_text": ["Perfect size and great features."], "review_sentiment": {"label": "positive", "score": 0.85}}, {"title": "Apple iPhone 15, 128GB, Black - Unlocked (Renewed)", "product_url": "https://www.amazon.com/Apple-iPhone-15-128GB-Black/dp/B0CMPMY9ZZ/ref=zg_bs_g_17871142011_d_sccl_8/145-3511079-4848163?psc=1", "image_urls": ["https://images-na.ssl-images-amazon.com/images/I/51PtFHUPjBL._AC_UL600_SR600,400_.jpg"], "price_text": "$498.85", "price_value": 498.85, "price_currency": "USD", "availability": "In Stock", "rating_value": 4.2, "rating_count": 1672, "model": "iPhone 15", "sku": "B0CMPMY9ZZ", "specifications": {"Storage": "128GB", "Color": "Black", "Unlocked": "Yes"}, "review_text": ["Amazing camera and performance."], "review_sentiment": {"label": "positive", "score": 0.9}}, {"title": "Apple iPhone XR, 64GB, Black - Unlocked (Renewed)", "product_url": "https://www.amazon.com/Apple-iPhone-XR-Fully-Unlocked/dp/B07P6Y7954/ref=zg_bs_g_17871142011_d_sccl_9/145-3511079-4848163?psc=1", "image_urls": ["https://images-na.ssl-images-amazon.com/images/I/51z1UO6N6LL._AC_UL600_SR600,400_.jpg"], "price_text": "$169.00", "price_value": 169.0, "price_currency": "USD", "availability": "In Stock", "rating_value": 4.4, "rating_count": 66430, "model": "iPhone XR", "sku": "B07P6Y7954", "specifications": {"Storage": "64GB", "Color": "Black", "Unlocked": "Yes"}, "review_text": ["Great battery life and performance."], "review_sentiment": {"label": "positive", "score": 0.9}}, {"title": "Apple iPhone SE 2nd Generation, US Version, 64GB, Black - Unlocked (Renewed)", "product_url": "https://www.amazon.com/Apple-iPhone-SE-64GB-Black/dp/B088NQXD8T/ref=zg_bs_g_17871142011_d_sccl_10/145-3511079-4848163?psc=1", "image_urls": ["https://images-na.ssl-images-amazon.com/images/I/71Ta1OO00fL._AC_UL600_SR600,400_.jpg"], "price_text": "$131.93", "price_value": 131.93, "price_currency": "USD", "availability": "In Stock", "rating_value": 4.2, "rating_count": 20871, "model": "iPhone SE 2nd Gen", "sku": "B088NQXD8T", "specifications": {"Storage": "64GB", "Color": "Black", "Unlocked": "Yes"}, "review_text": ["Perfect for those who want a compact phone."], "review_sentiment": {"label": "positive", "score": 0.85}}, {"title": "Apple iPhone 14 Plus, 128GB, Midnight - Unlocked (Renewed)", "product_url": "https://www.amazon.com/Apple-iPhone-14-Plus-Midnight/dp/B0BN9426PP/ref=zg_bs_g_17871142011_d_sccl_11/145-3511079-4848163?psc=1", "image_urls": ["https://images-na.ssl-images-amazon.com/images/I/513-nH35+UL._AC_UL600_SR600,400_.jpg"], "price_text": "$377.00", "price_value": 377.0, "price_currency": "USD", "availability": "In Stock", "rating_value": 4.1, "rating_count": 2470, "model": "iPhone 14 Plus", "sku": "B0BN9426PP", "specifications": {"Storage": "128GB", "Color": "Midnight", "Unlocked": "Yes"}, "review_text": ["Great battery life and performance."], "review_sentiment": {"label": "positive", "score": 0.9}}, {"title": "Apple iPhone 15 Pro Max, 256GB, Natural Titanium - Unlocked (Renewed)", "product_url": "https://www.amazon.com/Apple-iPhone-15-Pro-Max/dp/B0CMZD7VCV/ref=zg_bs_g_17871142011_d_sccl_12/145-3511079-4848163?psc=1", "image_urls": ["https://images-na.ssl-images-amazon.com/images/I/616mZZm8-7L._AC_UL600_SR600,400_.jpg"], "price_text": "$759.95", "price_value": 759.95, "price_currency": "USD", "availability": "In Stock", "rating_value": 3.9, "rating_count": 1391, "model": "iPhone 15 Pro Max", "sku": "B0CMZD7VCV", "specifications": {"Storage": "256GB", "Color": "Natural Titanium", "Unlocked": "Yes"}, "review_text": ["Top-notch performance and camera."], "review_sentiment": {"label": "positive", "score": 0.9}}, {"title": "Samsung Galaxy S21 5G, US Version, 128GB, Phantom Gray - Unlocked (Renewed)", "product_url": "https://www.amazon.com/Samsung-Galaxy-S21-5G-Version/dp/B08VLMQ3KS/ref=zg_bs_g_17871142011_d_sccl_13/145-3511079-4848163?psc=1", "image_urls": ["https://images-na.ssl-images-amazon.com/images/I/61XyNdmvr6L._AC_UL600_SR600,400_.jpg"], "price_text": "$178.46", "price_value": 178.46, "price_currency": "USD", "availability": "In Stock", "rating_value": 4.0, "rating_count": 17357, "model": "Galaxy S21", "sku": "B08VLMQ3KS", "specifications": {"Storage": "128GB", "Color": "Phantom Gray", "Unlocked": "Yes"}, "review_text": ["Good performance for the price."], "review_sentiment": {"label": "positive", "score": 0.8}}, {"title": "Apple iPhone 13 Pro Max, 128GB, Graphite - Unlocked (Renewed)", "product_url": "https://www.amazon.com/Apple-13-Pro-Max-Graphite/dp/B09LPK77YY/ref=zg_bs_g_17871142011_d_sccl_14/145-3511079-4848163?psc=1", "image_urls": ["https://images-na.ssl-images-amazon.com/images/I/51UtM-A3fdL._AC_UL600_SR600,400_.jpg"], "price_text": "$474.95", "price_value": 474.95, "price_currency": "USD", "availability": "In Stock", "rating_value": 4.1, "rating_count": 8647, "model": "iPhone 13 Pro Max", "sku": "B09LPK77YY", "specifications": {"Storage": "128GB", "Color": "Graphite", "Unlocked": "Yes"}, "review_text": ["Excellent camera and battery life."], "review_sentiment": {"label": "positive", "score": 0.9}}, {"title": "Apple iPhone 12 Pro, 128GB, Pacific Blue - Fully Unlocked (Renewed)", "product_url": "https://www.amazon.com/Apple-iPhone-128GB-Pacific-Blue/dp/B08PMYLKVF/ref=zg_bs_g_17871142011_d_sccl_15/145-3511079-4848163?psc=1", "image_urls": ["https://images-na.ssl-images-amazon.com/images/I/51n-83C8HYL._AC_UL600_SR600,400_.jpg"], "price_text": "$316.00", "price_value": 316.0, "price_currency": "USD", "availability": "In Stock", "rating_value": 4.1, "rating_count": 12202, "model": "iPhone 12 Pro", "sku": "B08PMYLKVF", "specifications": {"Storage": "128GB", "Color": "Pacific Blue", "Unlocked": "Yes"}, "review_text": ["Great phone with excellent features."], "review_sentiment": {"label": "positive", "score": 0.85}}, {"title": "Apple iPhone 14 Pro, 256GB, Space Black - Unlocked (Renewed)", "product_url": "https://www.amazon.com/Apple-iPhone-14-Pro-256GB/dp/B0BN96CCM6/ref=zg_bs_g_17871142011_d_sccl_16/145-3511079-4848163?psc=1", "image_urls": ["https://images-na.ssl-images-amazon.com/images/I/41al5-lNvML._AC_UL600_SR600,400_.jpg"], "price_text": "$520.00", "price_value": 520.0, "price_currency": "USD", "availability": "In Stock", "rating_value": 4.0, "rating_count": 3453, "model": "iPhone 14 Pro", "sku": "B0BN96CCM6", "specifications": {"Storage": "256GB", "Color": "Space Black", "Unlocked": "Yes"}, "review_text": ["Amazing performance and display."], "review_sentiment": {"label": "positive", "score": 0.9}}, {"title": "Apple iPhone SE 3rd Gen, 64GB, Midnight - Unlocked (Renewed)", "product_url": "https://www.amazon.com/Apple-iPhone-SE-3rd-Midnight/dp/B0BDY71GRG/ref=zg_bs_g_17871142011_d_sccl_17/145-3511079-4848163?psc=1", "image_urls": ["https://images-na.ssl-images-amazon.com/images/I/61-wAIWB8NL._AC_UL600_SR600,400_.jpg"], "price_text": "$156.79", "price_value": 156.79, "price_currency": "USD", "availability": "In Stock", "rating_value": 4.1, "rating_count": 2906, "model": "iPhone SE 3rd Gen", "sku": "B0BDY71GRG", "specifications": {"Storage": "64GB", "Color": "Midnight", "Unlocked": "Yes"}, "review_text": ["Great value for a budget phone."], "review_sentiment": {"label": "positive", "score": 0.85}}, {"title": "SAMSUNG Galaxy S22 Ultra 5G, US Version, 128GB, Black - Unlocked (Renewed)", "product_url": "https://www.amazon.com/Samsung-Galaxy-S22-5G-Unlocked/dp/B09VD33WHW/ref=zg_bs_g_17871142011_d_sccl_18/145-3511079-4848163?psc=1", "image_urls": ["https://images-na.ssl-images-amazon.com/images/I/613Fp7fknhL._AC_UL600_SR600,400_.jpg"], "price_text": "$359.00", "price_value": 359.0, "price_currency": "USD", "availability": "In Stock", "rating_value": 3.7, "rating_count": 5743, "model": "Galaxy S22 Ultra", "sku": "B09VD33WHW", "specifications": {"Storage": "128GB", "Color": "Black", "Unlocked": "Yes"}, "review_text": ["Good performance but a bit heavy."], "review_sentiment": {"label": "neutral", "score": 0.0}}, {"title": "Apple iPhone 14 Pro Max, 128GB, Deep Purple - Unlocked (Renewed)", "product_url": "https://www.amazon.com/Apple-iPhone-128GB-Deep-Purple/dp/B0BN9P1GXC/ref=zg_bs_g_17871142011_d_sccl_19/145-3511079-4848163?psc=1", "image_urls": ["https://images-na.ssl-images-amazon.com/images/I/51KLILQ67nL._AC_UL600_SR600,400_.jpg"], "price_text": "$551.35", "price_value": 551.35, "price_currency": "USD", "availability": "In Stock", "rating_value": 4.0, "rating_count": 3537, "model": "iPhone 14 Pro Max", "sku": "B0BN9P1GXC", "specifications": {"Storage": "128GB", "Color": "Deep Purple", "Unlocked": "Yes"}, "review_text": ["Excellent camera and performance."], "review_sentiment": {"label": "positive", "score": 0.9}}, {"title": "Apple iPhone 15 Pro, 256GB, Blue Titanium - Unlocked (Renewed)", "product_url": "https://www.amazon.com/Apple-iPhone-15-Pro-Titanium/dp/B0CMYXFK3R/ref=zg_bs_g_17871142011_d_sccl_20/145-3511079-4848163?psc=1", "image_urls": ["https://images-na.ssl-images-amazon.com/images/I/71Yp3z87X4L._AC_UL600_SR600,400_.jpg"], "price_text": "$690.40", "price_value": 690.4, "price_currency": "USD", "availability": "In Stock", "rating_value": 4.1, "rating_count": 1449, "model": "iPhone 15 Pro", "sku": "B0CMYXFK3R", "specifications": {"Storage": "256GB", "Color": "Blue Titanium", "Unlocked": "Yes"}, "review_text": ["Great phone with amazing features."], "review_sentiment": {"label": "positive", "score": 0.9}}, {"title": "Apple iPhone 13, 128GB, Midnight - Unlocked (Renewed Premium)", "product_url": "https://www.amazon.com/iPhone-13-128GB-Midnight-Unlocked/dp/B0BGQKY8S9/ref=zg_bs_g_17871142011_d_sccl_21/145-3511079-4848163?psc=1", "image_urls": ["https://images-na.ssl-images-amazon.com/images/I/61BUt5ZErdL._AC_UL600_SR600,400_.jpg"], "price_text": "$342.00", "price_value": 342.0, "price_currency": "USD", "availability": "In Stock", "rating_value": 4.3, "rating_count": 1947, "model": "iPhone 13", "sku": "B0BGQKY8S9", "specifications": {"Storage": "128GB", "Color": "Midnight", "Unlocked": "Yes"}, "review_text": ["Excellent condition and performance."], "review_sentiment": {"label": "positive", "score": 0.9}}, {"title": "Samsung Galaxy S20 FE 5G, 128GB, Cloud Navy - Unlocked (Renewed)", "product_url": "https://www.amazon.com/Samsung-Galaxy-S20-FE-128GB/dp/B08L34JQ9C/ref=zg_bs_g_17871142011_d_sccl_22/145-3511079-4848163?psc=1", "image_urls": ["https://images-na.ssl-images-amazon.com/images/I/51yxI5nkPWL._AC_UL600_SR600,400_.jpg"], "price_text": "$152.00", "price_value": 152.0, "price_currency": "USD", "availability": "In Stock", "rating_value": 3.9, "rating_count": 9820, "model": "Galaxy S20 FE", "sku": "B08L34JQ9C", "specifications": {"Storage": "128GB", "Color": "Cloud Navy", "Unlocked": "Yes"}, "review_text": ["Good phone for the price."], "review_sentiment": {"label": "positive", "score": 0.8}}, {"title": "Samsung Galaxy S22+ 5G S906U 128GB GSM/CDMA Unlocked Android Smartphone (USA Version) - Phantom Black (Renewed)", "product_url": "https://www.amazon.com/SAMSUNG-Galaxy-S22-Version-Phantom/dp/B09VH9BKHS/ref=zg_bs_g_17871142011_d_sccl_23/145-3511079-4848163?psc=1", "image_urls": ["https://images-na.ssl-images-amazon.com/images/I/61R5xNY4ZWL._AC_UL600_SR600,400_.jpg"], "price_text": "$228.99", "price_value": 228.99, "price_currency": "USD", "availability": "In Stock", "rating_value": 4.2, "rating_count": 2022, "model": "Galaxy S22+", "sku": "B09VH9BKHS", "specifications": {"Storage": "128GB", "Color": "Phantom Black", "Unlocked": "Yes"}, "review_text": ["Great phone with good features."], "review_sentiment": {"label": "positive", "score": 0.85}}, {"title": "Apple iPhone 12 Pro Max 5G, US Version, 128GB, Graphite - Unlocked (Renewed)", "product_url": "https://www.amazon.com/Apple-iPhone-Pro-128GB-Graphite/dp/B08PL89SJS/ref=zg_bs_g_17871142011_d_sccl_24/145-3511079-4848163?psc=1", "image_urls": ["https://images-na.ssl-images-amazon.com/images/I/5109dvnof9L._AC_UL600_SR600,400_.jpg"], "price_text": "$384.99", "price_value": 384.99, "price_currency": "USD", "availability": "In Stock", "rating_value": 4.1, "rating_count": 7535, "model": "iPhone 12 Pro Max", "sku": "B08PL89SJS", "specifications": {"Storage": "128GB", "Color": "Graphite", "Unlocked": "Yes"}, "review_text": ["Excellent phone with great features."], "review_sentiment": {"label": "positive", "score": 0.9}}, {"title": "Samsung Galaxy S22 Smartphone, Factory Unlocked Android Cell Phone, 128GB, 8K Camera & Video, Brightest Display, Long Battery Life, Fast 4nm Processor, US Version, Phantom Black (Renewed)", "product_url": "https://www.amazon.com/Samsung-Smartphone-Unlocked-Brightest-Processor/dp/B09V5LDZQ4/ref=zg_bs_g_17871142011_d_sccl_25/145-3511079-4848163?psc=1", "image_urls": ["https://images-na.ssl-images-amazon.com/images/I/61M4ndNetDL._AC_UL600_SR600,400_.jpg"], "price_text": "$213.59", "price_value": 213.59, "price_currency": "USD", "availability": "In Stock", "rating_value": 3.9, "rating_count": 3341, "model": "Galaxy S22", "sku": "B09V5LDZQ4", "specifications": {"Storage": "128GB", "Color": "Phantom Black", "Unlocked": "Yes"}, "review_text": ["Good performance and camera."], "review_sentiment": {"label": "positive", "score": 0.8}}, {"title": "Samsung Galaxy A14 5G A Series, Factory Unlocked, 64GB, US Version, Black (Renewed)", "product_url": "https://www.amazon.com/SAMSUNG-Factory-Unlocked-Android-Smartphone/dp/B0C1Q3MVBP/ref=zg_bs_g_17871142011_d_sccl_26/145-3511079-4848163?psc=1", "image_urls": ["https://images-na.ssl-images-amazon.com/images/I/71L1ezoIH9L._AC_UL600_SR600,400_.jpg"], "price_text": "$99.99", "price_value": 99.99, "price_currency": "USD", "availability": "In Stock", "rating_value": 3.8, "rating_count": 1502, "model": "Galaxy A14", "sku": "B0C1Q3MVBP", "specifications": {"Storage": "64GB", "Color": "Black", "Unlocked": "Yes"}, "review_text": ["Great budget phone."], "review_sentiment": {"label": "positive", "score": 0.85}}, {"title": "Apple iPhone 15, 128GB, Black - Unlocked (Renewed Premium)", "product_url": "https://www.amazon.com/Apple-iPhone-15-128GB-Black/dp/B0CRJ13WM7/ref=zg_bs_g_17871142011_d_sccl_27/145-3511079-4848163?psc=1", "image_urls": ["https://images-na.ssl-images-amazon.com/images/I/41xawTmtrjL._AC_UL300_SR300,200_.jpg"], "price_text": "$534.69", "price_value": 534.69, "price_currency": "USD", "availability": "In Stock", "rating_value": 4.3, "rating_count": 486, "model": "iPhone 15", "sku": "B0CRJ13WM7", "specifications": {"Storage": "128GB", "Color": "Black", "Unlocked": "Yes"}, "review_text": ["Excellent phone with great features."], "review_sentiment": {"label": "positive", "score": 0.9}}, {"title": "SAMSUNG Galaxy S24 Ultra 5G, US Version, 256GB, Titanium Black - Unlocked (Renewed)", "product_url": "https://www.amazon.com/SAMSUNG-Galaxy-S24-Ultra-Titanium/dp/B0D362HGNP/ref=zg_bs_g_17871142011_d_sccl_28/145-3511079-4848163?psc=1", "image_urls": ["https://images-na.ssl-images-amazon.com/images/I/51A-Q4eMBxL._AC_UL300_SR300,200_.jpg"], "price_text": "$689.00", "price_value": 689.0, "price_currency": "USD", "availability": "In Stock", "rating_value": 4.2, "rating_count": 410, "model": "Galaxy S24 Ultra", "sku": "B0D362HGNP", "specifications": {"Storage": "256GB", "Color": "Titanium Black", "Unlocked": "Yes"}, "review_text": ["Great performance and camera."], "review_sentiment": {"label": "positive", "score": 0.9}}, {"title": "SAMSUNG Galaxy S21 Ultra 5G, US Version, 128GB, Phantom Black - Unlocked (Renewed)", "product_url": "https://www.amazon.com/Galaxy-S21-Ultra-5G-Smartphone/dp/B096T6Y623/ref=zg_bs_g_17871142011_d_sccl_29/145-3511079-4848163?psc=1", "image_urls": ["https://images-na.ssl-images-amazon.com/images/I/71A87GtJnoL._AC_UL300_SR300,200_.jpg"], "price_text": "$239.99", "price_value": 239.99, "price_currency": "USD", "availability": "In Stock", "rating_value": 3.8, "rating_count": 3347, "model": "Galaxy S21 Ultra", "sku": "B096T6Y623", "specifications": {"Storage": "128GB", "Color": "Phantom Black", "Unlocked": "Yes"}, "review_text": ["Good performance but a bit heavy."], "review_sentiment": {"label": "neutral", "score": 0.0}}, {"title": "Apple iPhone 14, 128GB, Midnight - Unlocked (Renewed Premium)", "product_url": "https://www.amazon.com/Apple-iPhone-14-128GB-Midnight/dp/B0BYL93774/ref=zg_bs_g_17871142011_d_sccl_30/145-3511079-4848163?psc=1", "image_urls": ["https://images-na.ssl-images-amazon.com/images/I/61WUSYIQdKL._AC_UL600_SR600,400_.jpg"], "price_text": "$409.99", "price_value": 409.99, "price_currency": "USD", "availability": "In Stock", "rating_value": 4.2, "rating_count": 1151, "model": "iPhone 14", "sku": "B0BYL93774", "specifications": {"Storage": "128GB", "Color": "Midnight", "Unlocked": "Yes"}, "review_text": ["Great phone with excellent features."], "review_sentiment": {"label": "positive", "score": 0.9}}]

    # # 1) Broad search across retailers
    # search = tv.search(
    #     query=query,
    #     include_domains=RETAILERS,
    #     include_answer=False,
    #     include_images=False,
    #     include_raw_content=True,
    #     search_depth="advanced",
    #     max_results=max_search_results,
    # )
    # urls = [r["url"] for r in search.get("results", []) if r.get("url")]
    # if not urls:
    #     return []

    # # 2) First extract pass
    # ext1 = tv.extract(urls, extract_depth="advanced", include_images=True)
    # target_listing_pdps: List[str] = []
    # done = False
    # for item in ext1.get("results", []):
    #     url = item["url"]
    #     raw = item.get("raw_content") or ""
    #     if not raw:
    #         continue

    #     dom = retailer_of(url)
    #     detail_hint = is_pdp(url)
    #     assist = parse_target_structured(raw) if "target.com" in dom else None
    #     prompt = build_llm_prompt(raw, url, assist=assist, detail_hint=detail_hint)
    #     try:
    #         if len(results_all) > 10:
    #             break
    #         data = call_llm(prompt)
    #         done = True
    #     except Exception as e:
    #         # If LLM fails, skip this page
    #         print(f"LLM 1st-pass failed for {url}: {e}")
    #         continue

    #     data.setdefault("source_url", url)
    #     data.setdefault("retailer", dom)

    #     # Enforce PDP URLs only for Target to avoid promo tiles
    #     if "target.com" in dom:
    #         pdps = filter_only_pdps(data.get("products", []))
    #         data["products"] = pdps
    #         # If thin or empty, harvest PDPs from listing HTML
    #         if not pdps:
    #             harvested = find_target_pdps_in_html(raw, url)
    #             target_listing_pdps.extend(harvested[:target_follow])

    #     results_all += data["products"]

    # 3) If Target listing PDPs found, do a second extract pass focused on PDPs
    # target_listing_pdps = list(dict.fromkeys([u for u in target_listing_pdps if is_pdp(u)]))[:target_follow]
    # if target_listing_pdps:
    #     ext2 = tv.extract(target_listing_pdps, extract_depth="advanced", include_images=True)
    #     for item in ext2.get("results", []):
    #         url = item["url"]
    #         raw = item.get("raw_content") or ""
    #         if not raw:
    #             continue
    #         assist = parse_target_structured(raw)
    #         prompt = build_llm_prompt(raw, url, assist=assist, detail_hint=True)
    #         try:
    #             data = call_llm(prompt)
    #             data["source_url"] = url
    #             data["retailer"] = "target.com"
    #             # Keep exactly one product for PDP
    #             if data.get("products"):
    #                 data["products"] = data["products"][:1]
    #                 results_all.append(data)
    #         except Exception as e:
    #             print(f"Target PDP enrich failed for {url}: {e}")
    
    state["buffer_products"] = results_all
    await copilotkit_emit_state(config, state)
    state["messages"].append(AIMessage(id=str(uuid.uuid4()), tool_calls=[{"name": "list_products", "args": {"products": state["buffer_products"][:10]}, "id": str(uuid.uuid4())}], type="ai",  content=''))
    # state["messages"].append(AIMessage(id=str(uuid.uuid4()), tool_calls=[{"name": "list_products", "args": {"products": (results_all)}, "id": str(uuid.uuid4())}], type="ai",  content=''))
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
                    "review_text": {"type": "array", "items" : {"type" : "string"}},
                    "review_sentiment": {
                        "type": ["object", "None"],
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
