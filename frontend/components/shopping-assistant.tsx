"use client"

import { useState } from "react"
import { Sidebar } from "@/components/sidebar"
import { Canvas } from "@/components/canvas"
import { WishlistView } from "@/components/wishlist-view"
import { ReportView } from "@/components/report-view"

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
  const [products, setProducts] = useState(mockProducts)
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
    setWishlist((prev) => (prev.includes(productId) ? prev.filter((id) => id !== productId) : [...prev, productId]))
  }

  const deleteProduct = (productId: string) => {
    const productToDelete = products.find((p) => p.id === productId)
    if (!productToDelete) return

    // Simulate AI finding replacement
    const replacementProducts = [
      {
        id: "replacement-1",
        name: "ASUS ZenBook 14",
        price: "$899",
        image: "/placeholder.svg?height=200&width=200&text=ASUS+ZenBook",
        pros: ["Lightweight design", "Good battery life", "Affordable price", "Solid performance"],
        cons: ["Average display", "Limited ports", "Plastic build"],
        source: "ASUS Store",
        rating: 4.3,
        reviews: 456,
        specs: {
          processor: "Intel Core i5-1235U",
          ram: "8GB LPDDR4X",
          storage: "512GB SSD",
          display: '14" Full HD IPS',
          battery: "Up to 12 hours",
          weight: "3.17 lbs",
          ports: "2x USB-A, 1x USB-C, HDMI",
          os: "Windows 11",
        },
      },
      {
        id: "replacement-2",
        name: "HP Spectre x360",
        price: "$1,399",
        image: "/placeholder.svg?height=200&width=200&text=HP+Spectre",
        pros: ["2-in-1 convertible", "Premium build", "Great display", "Long battery life"],
        cons: ["Gets warm", "Expensive", "Heavy for tablet mode"],
        source: "HP.com",
        rating: 4.4,
        reviews: 789,
        specs: {
          processor: "Intel Core i7-1255U",
          ram: "16GB LPDDR4X",
          storage: "1TB SSD",
          display: '13.5" 3K2K OLED Touch',
          battery: "Up to 14 hours",
          weight: "3.01 lbs",
          ports: "2x Thunderbolt 4, 1x USB-A",
          os: "Windows 11",
        },
      },
    ]

    const replacement = replacementProducts[Math.floor(Math.random() * replacementProducts.length)]

    // Update products
    setProducts((prev) => prev.map((p) => (p.id === productId ? replacement : p)))

    // Update agent decisions
    setAgentDecisions((prev) => ({
      ...prev,
      replacementHistory: [
        ...prev.replacementHistory,
        {
          removedProduct: productToDelete.name,
          replacedWith: replacement.name,
          reason: `Found better alternative with similar specs but improved value proposition and user ratings`,
          timestamp: new Date(),
        },
      ],
    }))
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

  const wishlistProducts = products.filter((product) => wishlist.includes(product.id))

  return (
    <div className="flex h-screen bg-[#FAFCFA] overflow-hidden">
      <Sidebar
        onSearch={handleSearch}
        suggestions={mockSuggestions}
        currentQuery={query}
        isSearching={isSearching}
        currentView={currentView}
        wishlistCount={wishlist.length}
      />

      <div className="flex-1 flex flex-col min-w-0">
        {currentView === "report" ? (
          <ReportView products={products} onExit={exitToProducts} searchQuery={query} agentDecisions={agentDecisions} />
        ) : currentView === "wishlist" ? (
          <WishlistView
            products={wishlistProducts}
            onExit={exitToProducts}
            onToggleWishlist={toggleWishlist}
            onDeleteProduct={deleteProduct}
          />
        ) : (
          <Canvas
            products={products}
            isLoading={isSearching}
            query={query}
            wishlist={wishlist}
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
