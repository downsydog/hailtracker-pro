import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts"
import { Users } from "lucide-react"

interface LeadSourcesChartProps {
  data?: {
    labels: string[]
    values: number[]
  }
  isLoading?: boolean
}

const SOURCE_COLORS: Record<string, string> = {
  "Website": "#3b82f6",
  "Referral": "#22c55e",
  "Storm Chase": "#f59e0b",
  "Door Knock": "#8b5cf6",
  "Social Media": "#ec4899",
  "Google Ads": "#06b6d4",
  "Facebook": "#1877f2",
  "Insurance": "#10b981",
  "Walk-in": "#84cc16",
  "Phone": "#6366f1",
}

const DEFAULT_COLORS = [
  "#3b82f6", "#22c55e", "#f59e0b", "#ef4444",
  "#8b5cf6", "#06b6d4", "#ec4899", "#84cc16"
]

export function LeadSourcesChart({ data, isLoading }: LeadSourcesChartProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            Lead Sources
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[300px] w-full" />
        </CardContent>
      </Card>
    )
  }

  if (!data?.labels?.length || !data?.values?.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            Lead Sources
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[300px] flex items-center justify-center text-muted-foreground">
            No lead source data available
          </div>
        </CardContent>
      </Card>
    )
  }

  // Transform data for Recharts
  const chartData = data.labels.map((label, index) => ({
    name: label,
    value: data.values[index] || 0,
    color: SOURCE_COLORS[label] || DEFAULT_COLORS[index % DEFAULT_COLORS.length],
  }))

  // Sort by value descending
  chartData.sort((a, b) => b.value - a.value)

  const total = chartData.reduce((sum, item) => sum + item.value, 0)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Users className="h-5 w-5" />
          Lead Sources
          <span className="ml-auto text-sm font-normal text-muted-foreground">
            {total} leads
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ left: 20, right: 20 }}
          >
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" horizontal={false} />
            <XAxis
              type="number"
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              width={100}
            />
            <Tooltip
              formatter={(value: number) => [value, "Leads"]}
              contentStyle={{
                backgroundColor: "hsl(var(--background))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "6px",
              }}
            />
            <Bar dataKey="value" radius={[0, 4, 4, 0]}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
