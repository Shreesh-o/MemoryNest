import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"

export default function DashboardPage() {
  return (
    <div className="p-6 max-w-4xl mx-auto">
      <Card>
        <CardHeader>
          <CardTitle>Dashboard</CardTitle>
          <CardDescription>Welcome to your MemoryNest dashboard</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">Dashboard coming soon</p>
        </CardContent>
      </Card>
    </div>
  )
}
