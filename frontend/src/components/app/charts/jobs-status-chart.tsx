import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from "recharts"
import { Briefcase } from "lucide-react"

interface JobsStatusChartProps {
  data?: {
    labels: string[]
    values: number[]
  }
  isLoading?: boolean
}

const STATUS_COLORS: Record<string, string> = {
  "New": "#3b82f6",
  "Scheduled": "#f59e0b",
  "In Progress": "#8b5cf6",
  "Waiting Parts": "#ef4444",
  "Quality Check": "#06b6d4",
  "Completed": "#22c55e",
  "Invoiced": "#10b981",
  "Paid": "#059669",
  // Fallback colors for unknown statuses
}

const DEFAULT_COLORS = [
  "#3b82f6", "#22c55e", "#f59e0b", "#ef4444",
  "#8b5cf6", "#06b6d4", "#ec4899", "#84cc16"
]

export function JobsStatusChart({ data, isLoading }: JobsStatusChartProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Briefcase className="h-5 w-5" />
            Jobs by Status
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
            <Briefcase className="h-5 w-5" />
            Jobs by Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[300px] flex items-center justify-center text-muted-foreground">
            No job status data available
          </div>
        </CardContent>
      </Card>
    )
  }

  // Transform data for Recharts
  const chartData = data.labels.map((label, index) => ({
    name: label,
    value: data.values[index] || 0,
    color: STATUS_COLORS[label] || DEFAULT_COLORS[index % DEFAULT_COLORS.length],
  }))

  // Filter out zero values for cleaner chart
  const filteredData = chartData.filter((item) => item.value > 0)

  if (filteredData.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Briefcase className="h-5 w-5" />
            Jobs by Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[300px] flex items-center justify-center text-muted-foreground">
            No jobs to display
          </div>
        </CardContent>
      </Card>
    )
  }

  const total = filteredData.reduce((sum, item) => sum + item.value, 0)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Briefcase className="h-5 w-5" />
          Jobs by Status
          <span className="ml-auto text-sm font-normal text-muted-foreground">
            {total} total
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={filteredData}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={100}
              paddingAngle={2}
              dataKey="value"
              label={({ name, percent }) =>
                `${name} (${(percent * 100).toFixed(0)}%)`
              }
              labelLine={{ stroke: "hsl(var(--muted-foreground))" }}
            >
              {filteredData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: number, name: string) => [value, name]}
              contentStyle={{
                backgroundColor: "hsl(var(--background))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "6px",
              }}
            />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
