"use client"

import type React from "react"

import { useState, useRef, useEffect } from "react"
import { Send, Sparkles, User, Bot, TrendingUp, Heart } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"

interface Message {
  id: string
  type: "user" | "assistant"
  content: string
  timestamp: Date
}

interface Product {
  id: string
  name: string
  price: string
  image: string
  pros: string[]
  cons: string[]
  source: string
  rating: number
  reviews: number
  specs: {
    processor: string
    ram: string
    storage: string
    display: string
    battery: string
    weight: string
    ports: string
    os: string
  }
}

interface SidebarProps {
  onSearch: (query: string) => void
  suggestions: string[]
  currentQuery: string
  isSearching: boolean
  currentView: "products" | "wishlist" | "report"
  wishlistCount: number
}

const initialMessages: Message[] = [
  {
    id: "1",
    type: "assistant",
    content:
      "Hi! I'm your AI shopping assistant. I can help you find and compare products across multiple websites. What are you looking for today?",
    timestamp: new Date(),
  },
]

const quickSuggestions = ["Compare these laptops", "Which has better battery life?", "Show me cheaper alternatives"]

export function Sidebar({
  onSearch,
  suggestions,
  currentQuery,
  isSearching,
  currentView,
  wishlistCount,
}: SidebarProps) {
  const [messages, setMessages] = useState<Message[]>(initialMessages)
  const [inputValue, setInputValue] = useState("")
  const [isTyping, setIsTyping] = useState(false)
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const scrollToBottom = () => {
    if (scrollAreaRef.current) {
      const scrollContainer = scrollAreaRef.current.querySelector("[data-radix-scroll-area-viewport]")
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight
      }
    }
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Auto-generate comparison analysis when entering comparison mode
  useEffect(() => {}, [])

  // Auto-generate wishlist message when entering wishlist view
  useEffect(() => {
    if (currentView === "wishlist" && wishlistCount > 0) {
      const wishlistMessage: Message = {
        id: `wishlist-${Date.now()}`,
        type: "assistant",
        content: `You have ${wishlistCount} products in your wishlist! These are great choices you've saved. 

I can help you:
• Compare any of these products side-by-side
• Find similar alternatives at different price points  
• Analyze which one offers the best value for your needs
• Check for current deals and discounts

What would you like to know about your saved products?`,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, wishlistMessage])
    } else if (currentView === "wishlist" && wishlistCount === 0) {
      const emptyWishlistMessage: Message = {
        id: `empty-wishlist-${Date.now()}`,
        type: "assistant",
        content: `Your wishlist is currently empty, but that's okay! 

Here's how to make the most of your wishlist:
• Click the ❤️ heart icon on any product to save it
• Use it to keep track of products you're considering
• Compare wishlisted items to make better decisions
• I'll help you analyze your saved products anytime

Ready to start shopping? Let me know what you're looking for!`,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, emptyWishlistMessage])
    }
  }, [currentView, wishlistCount])

  const generateComparisonAnalysis = (products: Product[]) => {
    const productNames = products.map((p) => p.name).join(", ")

    return `## Comparison Analysis: ${productNames}

**💰 Price Comparison:**
${products.map((p) => `• ${p.name}: ${p.price}`).join("\n")}

**⭐ Rating Analysis:**
${products.map((p) => `• ${p.name}: ${p.rating}/5 (${p.reviews} reviews)`).join("\n")}

**🔋 Battery Life:**
${products.map((p) => `• ${p.name}: ${p.specs.battery}`).join("\n")}

**💻 Performance:**
${products.map((p) => `• ${p.name}: ${p.specs.processor}`).join("\n")}

**📊 My Recommendation:**
${
  products.length === 2
    ? `Based on the comparison, the ${products[0].rating > products[1].rating ? products[0].name : products[1].name} offers better overall value with its ${products[0].rating > products[1].rating ? "higher rating and" : ""} strong performance. However, consider your budget and specific needs.`
    : `Among these ${products.length} options, I'd recommend focusing on your primary use case - whether that's performance, battery life, or value for money.`
}

Would you like me to dive deeper into any specific aspect of this comparison?`
  }

  const simulateAssistantResponse = (userMessage: string) => {
    setIsTyping(true)

    setTimeout(() => {
      let response = ""

      if (currentView === "wishlist") {
        // Wishlist-specific responses
        if (userMessage.toLowerCase().includes("compare") || userMessage.toLowerCase().includes("which")) {
          response = `To compare your wishlisted products, simply click the compare button (⚖️) on the products you want to analyze, then click the "Compare" button that appears. I'll provide detailed side-by-side analysis!

You can compare things like:
• Performance and specifications
• Price and value for money  
• Battery life and portability
• User ratings and reviews

Which products from your wishlist are you most interested in comparing?`
        } else if (userMessage.toLowerCase().includes("deal") || userMessage.toLowerCase().includes("price")) {
          response = `I can help you track prices on your wishlisted items! While I don't have real-time pricing data in this demo, here's what I'd normally do:

• Monitor price changes across retailers
• Alert you when items go on sale
• Find coupon codes and discounts
• Suggest the best time to buy

Would you like me to analyze the current prices of your wishlisted products?`
        } else {
          response = `I'm here to help with your wishlist! I can help you:

• Compare products side-by-side
• Find better deals or alternatives
• Analyze which product best fits your needs
• Organize your wishlist by priority

What specific aspect of your saved products would you like to explore?`
        }
      } else {
        // Regular responses for products view
        if (userMessage.toLowerCase().includes("laptop") || userMessage.toLowerCase().includes("computer")) {
          response =
            "I'll search for laptops across multiple retailers. Let me find the best options for you with detailed comparisons including specs, prices, and reviews."
          onSearch(userMessage)
        } else if (userMessage.toLowerCase().includes("compare")) {
          response =
            "To compare products, click the compare button (⚖️) on the product cards you're interested in, then click the 'Compare' button that appears. I'll provide detailed analysis once you start the comparison!"
        } else {
          response =
            "I understand you're looking for more information. I can help you with product comparisons, finding alternatives, checking specifications, or searching for new products. What specific aspect would you like to explore?"
        }
      }

      const assistantMessage: Message = {
        id: Date.now().toString(),
        type: "assistant",
        content: response,
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, assistantMessage])
      setIsTyping(false)
    }, 1500)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (inputValue.trim()) {
      const userMessage: Message = {
        id: Date.now().toString(),
        type: "user",
        content: inputValue.trim(),
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, userMessage])
      simulateAssistantResponse(inputValue.trim())
      setInputValue("")
    }
  }

  const handleQuickSuggestion = (suggestion: string) => {
    const userMessage: Message = {
      id: Date.now().toString(),
      type: "user",
      content: suggestion,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    simulateAssistantResponse(suggestion)
  }

  const comparisonSuggestions = ["Which one should I buy?", "Compare battery life", "What about performance?"]
  const wishlistSuggestions = ["Compare my saved products", "Which is the best value?", "Find deals on these items"]

  const getViewTitle = () => {
    switch (currentView) {
      case "report":
        return "Analysis Report"
      case "wishlist":
        return "Wishlist Mode"
      default:
        return "AI Shopping Assistant"
    }
  }

  const getCurrentSuggestions = () => {
    if (currentView === "wishlist") return wishlistSuggestions
    return quickSuggestions
  }

  const getSuggestionTitle = () => {
    if (currentView === "wishlist") return "Ask About Wishlist"
    return "Ask About Products"
  }

  return (
    <div className="w-80 bg-[#FAFCFA] border-r border-[#D8D8E5] flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-[#D8D8E5] bg-white">
        <div className="flex items-center gap-3 mb-2">
          <div className="text-2xl">🪁</div>
          <div>
            <h1 className="text-lg font-semibold text-[#030507] font-['Roobert']">Assistant Shopper Chat</h1>
            <Badge variant="secondary" className="text-xs bg-[#BEC9FF] text-[#030507] font-semibold">
              PRO
            </Badge>
          </div>
        </div>
        <p className="text-sm text-[#575758]">{getViewTitle()}</p>
      </div>

      {/* Chat Messages */}
      <ScrollArea ref={scrollAreaRef} className="flex-1 p-4">
        <div className="space-y-4">
          {messages.map((message) => (
            <div key={message.id} className={`flex gap-3 ${message.type === "user" ? "justify-end" : "justify-start"}`}>
              {message.type === "assistant" && (
                <div className="w-8 h-8 rounded-full bg-[#86ECE4] flex items-center justify-center flex-shrink-0 mt-1">
                  <Bot className="w-4 h-4 text-[#030507]" />
                </div>
              )}

              <div
                className={`max-w-[240px] rounded-lg p-3 ${
                  message.type === "user"
                    ? "bg-[#030507] text-white ml-8"
                    : "bg-white border border-[#D8D8E5] text-[#030507]"
                }`}
              >
                <div className="text-sm whitespace-pre-line">{message.content}</div>
                <div className={`text-xs mt-1 ${message.type === "user" ? "text-gray-300" : "text-[#858589]"}`}>
                  {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </div>
              </div>

              {message.type === "user" && (
                <div className="w-8 h-8 rounded-full bg-[#BEC9FF] flex items-center justify-center flex-shrink-0 mt-1">
                  <User className="w-4 h-4 text-[#030507]" />
                </div>
              )}
            </div>
          ))}

          {isTyping && (
            <div className="flex gap-3 justify-start">
              <div className="w-8 h-8 rounded-full bg-[#86ECE4] flex items-center justify-center flex-shrink-0 mt-1">
                <Bot className="w-4 h-4 text-[#030507]" />
              </div>
              <div className="bg-white border border-[#D8D8E5] rounded-lg p-3">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-[#858589] rounded-full animate-bounce"></div>
                  <div
                    className="w-2 h-2 bg-[#858589] rounded-full animate-bounce"
                    style={{ animationDelay: "0.1s" }}
                  ></div>
                  <div
                    className="w-2 h-2 bg-[#858589] rounded-full animate-bounce"
                    style={{ animationDelay: "0.2s" }}
                  ></div>
                </div>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Quick Suggestions */}
      {currentView === "products" && messages.length <= 2 && (
        <div className="p-4 border-t border-[#D8D8E5] bg-[#F7F7F9]">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp className="w-4 h-4 text-[#575758]" />
            <span className="text-xs font-semibold text-[#575758] uppercase tracking-wide">Quick Start</span>
          </div>
          <div className="space-y-2">
            {suggestions.slice(0, 3).map((suggestion, index) => (
              <button
                key={index}
                onClick={() => handleQuickSuggestion(suggestion)}
                className="w-full text-left p-2 rounded-lg bg-white border border-[#D8D8E5] hover:bg-[#E8E8EF] transition-colors text-xs text-[#030507]"
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Context-Specific Suggestions */}
      {((currentQuery && messages.length > 2 && currentView === "products") || currentView === "wishlist") && (
        <div className="p-4 border-t border-[#D8D8E5] bg-[#F7F7F9]">
          <div className="flex items-center gap-2 mb-3">
            {currentView === "wishlist" ? (
              <Heart className="w-4 h-4 text-[#FFA254]" />
            ) : (
              <Sparkles className="w-4 h-4 text-[#1B606F]" />
            )}
            <span className="text-xs font-semibold text-[#575758] uppercase tracking-wide">{getSuggestionTitle()}</span>
          </div>
          <div className="grid grid-cols-1 gap-2">
            {getCurrentSuggestions().map((suggestion, index) => (
              <button
                key={index}
                onClick={() => handleQuickSuggestion(suggestion)}
                className="text-left p-2 rounded-lg bg-white border border-[#D8D8E5] hover:bg-[#E8E8EF] transition-colors text-xs text-[#030507]"
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Chat Input */}
      <div className="p-4 border-t border-[#D8D8E5] bg-white">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <Input
            ref={inputRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder={
              currentView === "wishlist" ? "Ask about your wishlist..." : "Ask me anything about these products..."
            }
            className="flex-1 bg-[#F7F7F9] border-[#D8D8E5] text-[#030507] placeholder:text-[#858589] text-sm"
            disabled={isTyping}
          />
          <Button
            type="submit"
            size="sm"
            className="bg-[#030507] hover:bg-[#575758] text-white px-3"
            disabled={isTyping || !inputValue.trim()}
          >
            <Send className="w-4 h-4" />
          </Button>
        </form>
      </div>
    </div>
  )
}
