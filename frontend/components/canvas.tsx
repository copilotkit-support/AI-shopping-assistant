"use client"

import { ProductCard } from "@/components/product-card"
import { Loader2, Package, Heart, FileText } from "lucide-react"
import { Button } from "@/components/ui/button"

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

interface CanvasProps {
  products: Product[]
  isLoading: boolean
  query: string
  wishlist: string[]
  onToggleWishlist: (productId: string) => void
  onDeleteProduct: (productId: string) => void
  onGoToWishlist: () => void
  onGoToReport: () => void
}

export function Canvas({
  products,
  isLoading,
  query,
  wishlist,
  onToggleWishlist,
  onDeleteProduct,
  onGoToWishlist,
  onGoToReport,
}: CanvasProps) {
  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-[#F7F7F9]">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-[#86ECE4] animate-spin mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-[#030507] mb-2">Searching across multiple stores...</h3>
          <p className="text-[#575758]">Finding the best products and comparing prices</p>
        </div>
      </div>
    )
  }

  if (!query) {
    return (
      <div className="flex-1 flex items-center justify-center bg-[#F7F7F9]">
        <div className="text-center max-w-md">
          <Package className="w-16 h-16 text-[#858589] mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-[#030507] mb-2 font-['Roobert']">Ready to help you shop smarter</h3>
          <p className="text-[#575758] mb-6">
            Enter a search query to discover and compare products from across the web. I'll help you find the best deals
            and make informed decisions.
          </p>
          <div className="bg-gradient-to-r from-[#86ECCE] to-[#FFF388] p-6 rounded-xl">
            <h4 className="font-semibold text-[#030507] mb-2">Get Started</h4>
            <p className="text-sm text-[#030507]">Try searching for "wireless headphones" or "gaming laptop"</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 p-6 bg-[#F7F7F9] overflow-y-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-semibold text-[#030507] mb-2 font-['Roobert']">Product Recommendations</h2>
          <p className="text-[#575758]">
            Found {products.length} AI-curated products for "{query}"
          </p>
        </div>

        <div className="flex gap-3">
          <Button
            onClick={onGoToReport}
            disabled={!query || products.length === 0}
            className="bg-[#1B606F] hover:bg-[#86ECE4] hover:text-[#030507] text-white flex items-center gap-2"
          >
            <FileText className="w-4 h-4" />
            View Report
          </Button>

          <Button
            onClick={onGoToWishlist}
            variant="outline"
            className="border-[#D8D8E5] hover:bg-[#E8E8EF] bg-white flex items-center gap-2"
          >
            <Heart className="w-4 h-4" />
            Wishlist ({wishlist.length})
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        {products.map((product) => (
          <ProductCard
            key={product.id}
            product={product}
            isWishlisted={wishlist.includes(product.id)}
            onToggleWishlist={onToggleWishlist}
            onDeleteProduct={onDeleteProduct}
          />
        ))}
      </div>
    </div>
  )
}
