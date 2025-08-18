"use client"

import { Star, ExternalLink, ThumbsUp, ThumbsDown, Heart, X, Lightbulb } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Progress } from "@/components/ui/progress"

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

interface ProductCardProps {
  product: Product
  isWishlisted: boolean
  onToggleWishlist: (productId: string) => void
  onDeleteProduct: (productId: string) => void
}

// Mock sentiment analysis data - in real app this would come from API
const getSentimentAnalysis = (productId: string) => {
  const analyses = {
    "1": {
      overallSentiment: "Very Positive",
      sentimentScore: 87,
      positivePercentage: 78,
      neutralPercentage: 15,
      negativePercentage: 7,
      keyInsights: [
        "Users consistently praise the exceptional build quality and premium materials",
        "Battery life receives overwhelmingly positive feedback with many reporting 15+ hours",
        "Display quality is frequently mentioned as 'stunning' and 'best-in-class'",
        "Performance with M3 chip exceeds expectations for creative workflows",
      ],
      commonPraises: [
        "Outstanding battery life",
        "Excellent display quality",
        "Premium build materials",
        "Fast M3 performance",
        "Great for creative work",
      ],
      commonCriticisms: [
        "High price point",
        "Limited port selection",
        "Learning curve for macOS switchers",
        "Expensive repairs",
      ],
      recommendationRate: 89,
      wouldBuyAgain: 92,
    },
    "2": {
      overallSentiment: "Positive",
      sentimentScore: 74,
      positivePercentage: 65,
      neutralPercentage: 23,
      negativePercentage: 12,
      keyInsights: [
        "Users appreciate the sleek design and compact form factor",
        "Performance is solid for the price point, though not exceptional",
        "Display quality receives mixed reviews - some love 4K, others prefer matte",
        "Keyboard layout changes are polarizing among users",
      ],
      commonPraises: [
        "Sleek modern design",
        "Good value for money",
        "Compact and portable",
        "4K display option",
        "Decent performance",
      ],
      commonCriticisms: [
        "Unusual keyboard layout",
        "Average battery life",
        "Limited upgradeability",
        "Can get warm under load",
        "Touch bar replacement issues",
      ],
      recommendationRate: 71,
      wouldBuyAgain: 68,
    },
    "3": {
      overallSentiment: "Positive",
      sentimentScore: 81,
      positivePercentage: 72,
      neutralPercentage: 18,
      negativePercentage: 10,
      keyInsights: [
        "Business users consistently rate the keyboard as the best in class",
        "Durability and build quality receive exceptional praise",
        "Security features are highly valued by enterprise customers",
        "Battery life meets expectations for business use cases",
      ],
      commonPraises: [
        "Exceptional keyboard quality",
        "Military-grade durability",
        "Excellent for business",
        "Great security features",
        "Reliable performance",
      ],
      commonCriticisms: [
        "Display could be brighter",
        "Conservative design",
        "Price premium over competitors",
        "Trackpad could be larger",
        "Fan noise under heavy load",
      ],
      recommendationRate: 84,
      wouldBuyAgain: 79,
    },
  }

  return analyses[productId as keyof typeof analyses] || analyses["1"]
}

export function ProductCard({ product, isWishlisted, onToggleWishlist, onDeleteProduct }: ProductCardProps) {
  const sentimentData = getSentimentAnalysis(product.id)

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case "Very Positive":
        return "text-[#1B606F]"
      case "Positive":
        return "text-[#86ECE4]"
      case "Neutral":
        return "text-[#858589]"
      case "Negative":
        return "text-[#FFA254]"
      default:
        return "text-[#858589]"
    }
  }

  return (
    <div className={`bg-white rounded-xl border p-6 hover:shadow-lg transition-all relative border-[#D8D8E5]`}>
      {/* Action Buttons */}
      <div className="absolute top-4 right-4 flex gap-2">
        <button
          onClick={() => onDeleteProduct(product.id)}
          className="p-2 rounded-full transition-colors bg-[#F7F7F9] text-[#858589] hover:bg-[#FFA254] hover:text-white"
        >
          <X className="w-4 h-4" />
        </button>

        <button
          onClick={() => onToggleWishlist(product.id)}
          className={`p-2 rounded-full transition-colors ${
            isWishlisted
              ? "bg-[#FFA254] text-white hover:bg-[#FF8C42]"
              : "bg-[#F7F7F9] text-[#858589] hover:bg-[#E8E8EF] hover:text-[#575758]"
          }`}
        >
          <Heart className={`w-4 h-4 ${isWishlisted ? "fill-current" : ""}`} />
        </button>
      </div>

      {/* Product Image */}
      <div className="aspect-square bg-[#F7F7F9] rounded-lg mb-4 overflow-hidden">
        <img src={product.image || "/placeholder.svg"} alt={product.name} className="w-full h-full object-cover" />
      </div>

      {/* Product Info */}
      <div className="space-y-4">
        <div>
          <h3 className="font-semibold text-[#030507] text-lg mb-1 font-['Roobert']">{product.name}</h3>
          <div className="flex items-center justify-between">
            <span className="text-2xl font-bold text-[#030507] font-['Roobert']">{product.price}</span>
            <Badge variant="outline" className="text-xs">
              {product.source}
            </Badge>
          </div>
        </div>

        {/* Rating with Insights */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex items-center">
              {[...Array(5)].map((_, i) => (
                <Star
                  key={i}
                  className={`w-4 h-4 ${
                    i < Math.floor(product.rating) ? "text-[#FFF388] fill-current" : "text-[#D8D8E5]"
                  }`}
                />
              ))}
            </div>
            <span className="text-sm text-[#575758]">
              {product.rating} ({product.reviews} reviews)
            </span>
          </div>

          {/* AI Insights Button */}
          <Dialog>
            <DialogTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="p-2 h-8 w-8 text-[#1B606F] hover:text-[#030507] hover:bg-[#86ECE4]/20"
              >
                <Lightbulb className="w-4 h-4" />
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl bg-white border-[#D8D8E5]">
              <DialogHeader>
                <DialogTitle className="text-xl font-semibold text-[#030507] font-['Roobert'] flex items-center gap-2">
                  <Lightbulb className="w-5 h-5 text-[#1B606F]" />
                  AI Review Insights: {product.name}
                </DialogTitle>
              </DialogHeader>

              <div className="space-y-6 mt-4">
                {/* Overall Sentiment */}
                <div className="bg-[#F7F7F9] rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-semibold text-[#030507]">Overall Sentiment</h3>
                    <span className={`font-semibold ${getSentimentColor(sentimentData.overallSentiment)}`}>
                      {sentimentData.overallSentiment}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-sm text-[#575758]">Sentiment Score</span>
                    <Progress value={sentimentData.sentimentScore} className="flex-1 h-2" />
                    <span className="text-sm font-medium text-[#030507]">{sentimentData.sentimentScore}/100</span>
                  </div>
                </div>

                {/* Sentiment Breakdown */}
                <div>
                  <h3 className="font-semibold text-[#030507] mb-3">Review Sentiment Breakdown</h3>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-[#1B606F] mb-1">{sentimentData.positivePercentage}%</div>
                      <div className="text-sm text-[#575758]">Positive</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-[#858589] mb-1">{sentimentData.neutralPercentage}%</div>
                      <div className="text-sm text-[#575758]">Neutral</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-[#FFA254] mb-1">{sentimentData.negativePercentage}%</div>
                      <div className="text-sm text-[#575758]">Negative</div>
                    </div>
                  </div>
                </div>

                {/* Key Insights */}
                <div>
                  <h3 className="font-semibold text-[#030507] mb-3">Key Insights from {product.reviews} Reviews</h3>
                  <ul className="space-y-2">
                    {sentimentData.keyInsights.map((insight, index) => (
                      <li key={index} className="flex items-start gap-2 text-sm text-[#575758]">
                        <span className="text-[#1B606F] mt-1">•</span>
                        {insight}
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Common Feedback */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <h4 className="font-semibold text-[#1B606F] mb-3 flex items-center gap-2">
                      <ThumbsUp className="w-4 h-4" />
                      Most Praised Features
                    </h4>
                    <ul className="space-y-1">
                      {sentimentData.commonPraises.map((praise, index) => (
                        <li key={index} className="text-sm text-[#575758] flex items-start gap-2">
                          <span className="text-[#1B606F] mt-1">•</span>
                          {praise}
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div>
                    <h4 className="font-semibold text-[#FFA254] mb-3 flex items-center gap-2">
                      <ThumbsDown className="w-4 h-4" />
                      Common Criticisms
                    </h4>
                    <ul className="space-y-1">
                      {sentimentData.commonCriticisms.map((criticism, index) => (
                        <li key={index} className="text-sm text-[#575758] flex items-start gap-2">
                          <span className="text-[#FFA254] mt-1">•</span>
                          {criticism}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                {/* Recommendation Stats */}
                <div className="bg-gradient-to-r from-[#86ECCE] to-[#FFF388] p-4 rounded-lg">
                  <div className="grid grid-cols-2 gap-4 text-center">
                    <div>
                      <div className="text-2xl font-bold text-[#030507] mb-1">{sentimentData.recommendationRate}%</div>
                      <div className="text-sm text-[#030507]">Would Recommend</div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-[#030507] mb-1">{sentimentData.wouldBuyAgain}%</div>
                      <div className="text-sm text-[#030507]">Would Buy Again</div>
                    </div>
                  </div>
                </div>

                <div className="text-xs text-[#858589] text-center">
                  Analysis based on {product.reviews} verified reviews from {product.source}
                </div>
              </div>
            </DialogContent>
          </Dialog>
        </div>

        {/* Pros and Cons */}
        <div className="space-y-3">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <ThumbsUp className="w-4 h-4 text-[#1B606F]" />
              <span className="text-sm font-medium text-[#030507]">Pros</span>
            </div>
            <ul className="space-y-1">
              {product.pros.slice(0, 2).map((pro, index) => (
                <li key={index} className="text-sm text-[#575758] flex items-start gap-2">
                  <span className="text-[#1B606F] mt-1">•</span>
                  {pro}
                </li>
              ))}
            </ul>
          </div>

          <div>
            <div className="flex items-center gap-2 mb-2">
              <ThumbsDown className="w-4 h-4 text-[#FFA254]" />
              <span className="text-sm font-medium text-[#030507]">Cons</span>
            </div>
            <ul className="space-y-1">
              {product.cons.slice(0, 2).map((con, index) => (
                <li key={index} className="text-sm text-[#575758] flex items-start gap-2">
                  <span className="text-[#FFA254] mt-1">•</span>
                  {con}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2 pt-2">
          <Button className="flex-1 bg-[#030507] hover:bg-[#575758] text-white">
            View Product
            <ExternalLink className="w-4 h-4 ml-2" />
          </Button>
        </div>
      </div>
    </div>
  )
}
