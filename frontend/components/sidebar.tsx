"use client"

import type React from "react"

import { useState, useRef, useEffect } from "react"
import { Send, Sparkles, User, Bot, TrendingUp, Heart } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { CopilotChat } from "@copilotkit/react-ui"
import { useCopilotChat } from "@copilotkit/react-core"
import { ToolLog } from "./tool-logs"
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
  setQuery: (query: string) => void
  clearState: (state: any) => void
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
  setQuery,
  clearState,
  onSearch,
  suggestions,
  currentQuery,
  isSearching,
  currentView,
  wishlistCount,
}: SidebarProps) {
  // const [messages, setMessages] = useState<Message[]>(initialMessages)
  // const [inputValue, setInputValue] = useState("")
  // const [isTyping, setIsTyping] = useState(false)
  // const scrollAreaRef = useRef<HTMLDivElement>(null)
  // const inputRef = useRef<HTMLInputElement>(null)




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
${products.length === 2
        ? `Based on the comparison, the ${products[0].rating > products[1].rating ? products[0].name : products[1].name} offers better overall value with its ${products[0].rating > products[1].rating ? "higher rating and" : ""} strong performance. However, consider your budget and specific needs.`
        : `Among these ${products.length} options, I'd recommend focusing on your primary use case - whether that's performance, battery life, or value for money.`
      }

Would you like me to dive deeper into any specific aspect of this comparison?`
  }


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

  const { reset } = useCopilotChat()


  return (
    <div className="flex flex-col min-h-screen w-80 bg-[#FAFCFA] border-r border-[#D8D8E5]">
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
        <div className="flex items-center gap-2">
          <p className="text-sm text-[#575758]">{getViewTitle()}</p>
          <Button onClick={() => {
            reset()
            setQuery("")
            clearState({
              products: [],
              favorites: [] as string[],
              buffer_products: [],
              logs: [] as ToolLog[]
            })
          }} size="sm" className="text-[#575758] bg-blue-200 rounded-full hover:bg-[#f0f0f0] ml-auto">
            <span className="mr-1">🔄</span> Reset
          </Button>
        </div>
      </div>
      <div className="flex-1 overflow-auto">
        <CopilotChat className="h-full" labels={{
          initial: "Hi! I'm your AI shopping assistant. I can help you find and compare products across multiple websites. What are you looking for today? Laptops, Phones, Headphones, etc.",
        }} />
      </div>
    </div>
  )
}
