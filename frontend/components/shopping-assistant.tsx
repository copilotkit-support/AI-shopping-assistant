"use client"

import { useEffect, useState } from "react"
import { Sidebar } from "@/components/sidebar"
import { Canvas } from "@/components/canvas"
import { WishlistView } from "@/components/wishlist-view"
import { ReportView } from "@/components/report-view"
import { useCoAgent, useCoAgentStateRender, useCopilotAction, useCopilotChat } from "@copilotkit/react-core"
import DialogBox from "./tool-response"
import { useCopilotChatSuggestions } from "@copilotkit/react-ui"
import { ToolLog, ToolLogs } from "./tool-logs"
const mockProducts = [
  {
    id: "1",
    name: 'Apple MacBook Pro 14"',
    price: "$1,999",
    image: "/placeholder.svg?height=200&width=200&text=MacBook+Pro",
    pros: [
      "M3 Pro chip performance",
      "Excellent Liquid Retina display",
      "18-hour battery life",
      "Premium build quality",
    ],
    cons: ["Expensive price point", "Limited port selection", "No touchscreen"],
    source: "Apple Store",
    rating: 4.8,
    reviews: 1247,
    specs: {
      processor: "Apple M3 Pro",
      ram: "18GB Unified Memory",
      storage: "512GB SSD",
      display: '14.2" Liquid Retina XDR',
      battery: "Up to 18 hours",
      weight: "3.5 lbs",
      ports: "3x Thunderbolt 4, HDMI, SD card",
      os: "macOS Sonoma",
    },
  },
  {
    id: "2",
    name: "Dell XPS 13 Plus",
    price: "$1,299",
    image: "/placeholder.svg?height=200&width=200&text=Dell+XPS+13",
    pros: ["Sleek modern design", "Good performance for price", "4K display option", "Compact form factor"],
    cons: ["Average 10-hour battery", "Unique keyboard layout", "Limited upgradeability"],
    source: "Dell.com",
    rating: 4.5,
    reviews: 892,
    specs: {
      processor: "Intel Core i7-1360P",
      ram: "16GB LPDDR5",
      storage: "512GB SSD",
      display: '13.4" 4K+ Touch',
      battery: "Up to 10 hours",
      weight: "2.73 lbs",
      ports: "2x Thunderbolt 4",
      os: "Windows 11",
    },
  },
  {
    id: "3",
    name: "Lenovo ThinkPad X1 Carbon",
    price: "$1,599",
    image: "/placeholder.svg?height=200&width=200&text=ThinkPad+X1",
    pros: ["Military-grade durability", "Excellent keyboard", "Business security features", "15-hour battery life"],
    cons: ["Higher price than competitors", "Average display quality", "Conservative design"],
    source: "Lenovo.com",
    rating: 4.6,
    reviews: 634,
    specs: {
      processor: "Intel Core i7-1365U",
      ram: "16GB LPDDR5",
      storage: "1TB SSD",
      display: '14" WUXGA IPS',
      battery: "Up to 15 hours",
      weight: "2.48 lbs",
      ports: "2x Thunderbolt 4, 2x USB-A, HDMI",
      os: "Windows 11 Pro",
    },
  },
]

const mockSuggestions = [
  "Find laptops under $1500",
  "Compare gaming headphones",
  "Show wireless earbuds with ANC",
  "Best smartphones for photography",
  "Budget 4K monitors under $400",
]

export function ShoppingAssistant() {
  const [query, setQuery] = useState("")
  const [isSearching, setIsSearching] = useState(false)
  const [products, setProducts] = useState<any>(mockProducts)
  const [wishlist, setWishlist] = useState<string[]>([])
  const [agentDecisions, setAgentDecisions] = useState({
    searchStrategy: "",
    databasesSearched: [] as string[],
    selectionCriteria: [] as string[],
    replacementHistory: [] as Array<{
      removedProduct: string
      replacedWith: string
      reason: string
      timestamp: Date
    }>,
  })
  const [currentView, setCurrentView] = useState<"products" | "wishlist" | "report">("products")

  const toggleWishlist = (productId: string) => {
    setState({
      ...state,
      favorites: state?.favorites?.includes(productId) ? state?.favorites?.filter((id: any) => id !== productId) : [...state?.favorites, productId]
    })
  }

  const deleteProduct = (productId: string) => {
    const productToDelete = state?.products?.find((p: any) => p.id === productId)
    if (!productToDelete) return

    if (state?.buffer_products?.length > 0) {
      let a = state?.buffer_products.pop()
      setState({
        ...state,
        products: [...state?.products?.filter((p: any) => p.id !== productId), ...(a ? [a] : [])]
      })
    }
    else {
      setState({
        ...state,
        products: state?.products?.filter((p: any) => p.id !== productId)
      })
    }
  }

  const goToReport = () => {
    setCurrentView("report")
  }

  const goToWishlist = () => {
    setCurrentView("wishlist")
  }

  const exitToProducts = () => {
    setCurrentView("products")
  }

  const handleSearch = async (searchQuery: string) => {
    setIsSearching(true)
    setQuery(searchQuery)

    // Set agent decisions based on search
    setAgentDecisions({
      searchStrategy: searchQuery.toLowerCase().includes("laptop")
        ? "laptop comparison and recommendation"
        : "product discovery and analysis",
      databasesSearched: [
        "Amazon Product API",
        "Best Buy Catalog",
        "Newegg Database",
        "Manufacturer Websites",
        "Review Aggregators",
      ],
      selectionCriteria: [
        "User rating above 4.0 stars",
        "Minimum 100 verified reviews",
        "Price range optimization",
        "Feature diversity for comparison",
        "Availability and shipping options",
      ],
      replacementHistory: [],
    })

    // Simulate API call
    setTimeout(() => {
      if (searchQuery.toLowerCase().includes("laptop") || searchQuery.toLowerCase().includes("computer")) {
        setProducts(mockProducts)
      }
      setIsSearching(false)
    }, 2000)
  }


  const { state, setState, start, run } = useCoAgent({
    name: "shopping_agent",
    initialState: {
      products: [],
      favorites: [] as string[],
      buffer_products: [],
      logs: [] as ToolLog[],
      report: null
    }
  })
  const wishlistProducts = state?.products?.filter((product: any) => state?.favorites?.includes(product.id))

  useCoAgentStateRender({
    name: "shopping_agent",
    render: (state1: any) => {
      // useEffect(() => {
      // console.log(state1, "state1")
      // }, [state1])

      return <ToolLogs logs={state1?.state?.logs || []} />
    }
  })


  useCopilotAction({
    name: "edit_product_canvas",
    description: "Ability to edit the products like moving it to wishlist or removing it from playlist or removing it from the product canvas",
    parameters: [
      {
        name: "remove_from_canvas",
        type: "object[]",
        description: "The id of the product to be edited",
        attributes: [
          {
            name: "product_id",
            type: "string",
            description: "The id of the product to be removed from the canvas"
          }
        ]
      },
      {
        name: "move_to_wishlist",
        type: "object[]",
        description: "The id of the product that needs to be moved to wishlist",
        attributes: [
          {
            name: "product_id",
            type: "string",
            description: "The id of the product to be moved to wishlist"
          }
        ]
      },
      {
        name: "remove_from_wishlist",
        type: "object[]",
        description: "The id of the product that needs to be removed from wishlist",
        attributes: [
          {
            name: "product_id",
            type: "string",
            description: "The id of the product to be removed from wishlist"
          }
        ]
      }
    ],
    handler: (args) => {
      console.log(args, "argsargsargsargs")
      debugger
      if (args?.move_to_wishlist?.length > 0) {
        setState({
          ...state,
          favorites: [...state?.favorites, ...args?.move_to_wishlist?.map((product: any) => product?.product_id)]
        })
      }
      if (args?.remove_from_wishlist?.length > 0) {
        let itemsToRemove = args?.remove_from_wishlist?.map((product: any) => product?.product_id)
        setState({
          ...state,
          favorites: state?.favorites?.filter((id: any) => !itemsToRemove?.includes(id))
        })
      }
      if (args?.remove_from_canvas?.length > 0) {
        debugger
        let itemsToRemove = args?.remove_from_canvas?.map((product: any) => product?.product_id)
        if (state?.buffer_products?.length > 0) {
          let a = state?.buffer_products.pop()
          setState({
            ...state,
            products: [...state?.products?.filter((p: any) => !itemsToRemove?.includes(p?.id)), ...(a ? [a] : [])]
          })
        }
        else {
          setState({
            ...state,
            products: state?.products?.filter((p: any) => !itemsToRemove?.includes(p?.id))
          })
        }

      }
      return "Product edited successfully"
    }
  })

  useEffect(() => {
    console.log(state, "statestatestatestate")
  }, [state])

  useCopilotAction({
    name: "list_products",
    description: "A list of products that are scraped from web",
    renderAndWaitForResponse: ({ status, respond, args }) => {
      console.log(args, "argsargsargsargs")

      return <DialogBox isDisabled={respond == undefined} contentList={args?.products?.map((product: any) => ({ title: product.title, url: product.product_url }))} onAccept={() => {
        if (respond) {
          respond(true)
          setState({
            ...state,
            products: args?.products,
            buffer_products: args?.buffer_products.slice(5, args?.buffer_products.length)
          })
          setProducts(args?.products)
        }
      }} onReject={() => { if (respond) respond("Rejected") }} onNeedInfo={() => {
        if (respond) {
          respond("Show more products")
          setState({
            ...state,
            products: args?.buffer_products?.slice(0, 10),
            buffer_products: args?.buffer_products.slice(10, args?.buffer_products.length)
          })
          setProducts(args?.buffer_products?.slice(0, 10))
        }
      }} />
    }

  })

  useCopilotChatSuggestions({
    available: "enabled",
    instructions: "You need to provide suggestions for the user to buy products like laptops, phones, headphones, etc. Example suggestions: Find laptops under $1500, Find good smartphones for photography, Get me some wireless earbuds with ANC, Best smartphones under $500, Budget 4K monitors under $400",
  })

  const { visibleMessages, isLoading } = useCopilotChat()

  useEffect(() => {
    console.log(visibleMessages.filter((message: any) => message?.role === "user"))
    // @ts-ignore
    setQuery(visibleMessages.filter((message: any) => message?.role === "user")[0]?.content)
    // visibleMessages.filter((message : any) => message.type)
  }, [isLoading])


  return (
    <div className="flex h-screen bg-[#FAFCFA] overflow-hidden">
      <Sidebar
        setQuery={setQuery}
        clearState={setState}
        onSearch={handleSearch}
        suggestions={mockSuggestions}
        currentQuery={query}
        isSearching={isSearching}
        currentView={currentView}
        wishlistCount={state?.favorites?.length}
      />

      <div className="flex-1 flex flex-col min-w-0">
        {currentView === "report" ? (
          <ReportView isLoading={isLoading} products={products} onExit={exitToProducts} searchQuery={query}  report={state?.report}/>
        ) : currentView === "wishlist" ? (
          <WishlistView
            clearAllWishlist={() => {
              setState({
                ...state,
                favorites: []
              })
            }}
            products={wishlistProducts}
            onExit={exitToProducts}
            onToggleWishlist={toggleWishlist}
            onDeleteProduct={deleteProduct}
          />
        ) : (
          <Canvas
            start={run}
            report={state?.report}
            products={state?.products}
            isLoading={isLoading && state?.products?.length == 0}
            query={query}
            wishlist={state?.favorites}
            onToggleWishlist={toggleWishlist}
            onDeleteProduct={deleteProduct}
            onGoToWishlist={goToWishlist}
            onGoToReport={goToReport}
          />
        )}
      </div>
    </div>
  )
}
