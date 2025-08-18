"use client"

import { ArrowLeft, FileText, TrendingUp } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

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

interface ReportViewProps {
  products: Product[]
  onExit: () => void
  searchQuery: string
  agentDecisions: any
}

export function ReportView({ products, onExit, searchQuery, agentDecisions }: ReportViewProps) {
  const generateComparisonReport = () => {
    const topRated = products.reduce((prev, current) => (prev.rating > current.rating ? prev : current))
    const bestValue = products.reduce((prev, current) => {
      const prevPrice = Number.parseFloat(prev.price.replace(/[$,]/g, ""))
      const currentPrice = Number.parseFloat(current.price.replace(/[$,]/g, ""))
      return current.rating / currentPrice > prev.rating / prevPrice ? current : prev
    })

    return {
      topRated,
      bestValue,
      priceRange: {
        min: Math.min(...products.map((p) => Number.parseFloat(p.price.replace(/[$,]/g, "")))),
        max: Math.max(...products.map((p) => Number.parseFloat(p.price.replace(/[$,]/g, "")))),
      },
      avgRating: (products.reduce((sum, p) => sum + p.rating, 0) / products.length).toFixed(1),
    }
  }

  const report = generateComparisonReport()

  return (
    <div className="flex-1 bg-[#F7F7F9] overflow-y-auto">
      {/* Header */}
      <div className="bg-white border-b border-[#D8D8E5] p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="outline" onClick={onExit} className="border-[#D8D8E5] hover:bg-[#E8E8EF] bg-white">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Products
            </Button>
            <div>
              <h1 className="text-2xl font-semibold text-[#030507] font-['Roobert']">AI Analysis Report</h1>
              <p className="text-[#575758]">Comprehensive analysis for "{searchQuery}"</p>
            </div>
          </div>
          <Badge variant="outline" className="bg-[#86ECE4] text-[#030507] border-[#86ECE4]">
            <FileText className="w-4 h-4 mr-1" />
            AI Generated
          </Badge>
        </div>
      </div>

      {/* Report Content */}
      <div className="p-6">
        {/* AI Recommendations */}
        <Card className="bg-white border-[#D8D8E5]">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-[#030507]">
              <TrendingUp className="w-5 h-5 text-[#1B606F]" />
              AI Recommendations
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="bg-gradient-to-r from-[#86ECCE] to-[#FFF388] p-4 rounded-lg">
              <h3 className="font-semibold text-[#030507] mb-2">🏆 Top Pick: {report.topRated.name}</h3>
              <p className="text-sm text-[#030507]">
                Based on comprehensive analysis, this product offers the best combination of performance, user
                satisfaction, and reliability. With a {report.topRated.rating}/5 rating from {report.topRated.reviews}{" "}
                reviews, it consistently delivers on user expectations.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="border border-[#1B606F] rounded-lg p-4">
                <h4 className="font-semibold text-[#1B606F] mb-2">✅ Best For Performance</h4>
                <p className="text-sm text-[#575758]">
                  {products.find((p) => p.specs.processor.includes("M3") || p.specs.processor.includes("i7"))?.name ||
                    products[0].name}
                  - Superior processing power for demanding tasks
                </p>
              </div>
              <div className="border border-[#FFA254] rounded-lg p-4">
                <h4 className="font-semibold text-[#FFA254] mb-2">💰 Best Value</h4>
                <p className="text-sm text-[#575758]">
                  {report.bestValue.name} - Optimal balance of features and price point
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Detailed Comparison */}
        <Card className="bg-white border-[#D8D8E5]">
          <CardHeader>
            <CardTitle className="text-[#030507]">Detailed Product Comparison</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[#D8D8E5]">
                    <th className="text-left p-3 text-[#030507] font-semibold">Product</th>
                    <th className="text-left p-3 text-[#030507] font-semibold">Price</th>
                    <th className="text-left p-3 text-[#030507] font-semibold">Rating</th>
                    <th className="text-left p-3 text-[#030507] font-semibold">Processor</th>
                    <th className="text-left p-3 text-[#030507] font-semibold">RAM</th>
                    <th className="text-left p-3 text-[#030507] font-semibold">Battery</th>
                  </tr>
                </thead>
                <tbody>
                  {products.map((product, index) => (
                    <tr key={product.id} className={index % 2 === 0 ? "bg-[#F7F7F9]" : "bg-white"}>
                      <td className="p-3">
                        <div className="flex items-center gap-3">
                          <img
                            src={product.image || "/placeholder.svg"}
                            alt={product.name}
                            className="w-12 h-12 rounded-lg object-cover"
                          />
                          <div>
                            <div className="font-semibold text-[#030507]">{product.name}</div>
                            <div className="text-sm text-[#575758]">{product.source}</div>
                          </div>
                        </div>
                      </td>
                      <td className="p-3 font-semibold text-[#030507]">{product.price}</td>
                      <td className="p-3">
                        <div className="flex items-center gap-1">
                          <span className="font-semibold text-[#030507]">{product.rating}</span>
                          <span className="text-[#575758]">({product.reviews})</span>
                        </div>
                      </td>
                      <td className="p-3 text-[#575758]">{product.specs.processor}</td>
                      <td className="p-3 text-[#575758]">{product.specs.ram}</td>
                      <td className="p-3 text-[#575758]">{product.specs.battery}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
