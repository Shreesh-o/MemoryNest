import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"

export default function DocumentsPage() {
  return (
    <div className="p-6 max-w-4xl mx-auto">
      <Card>
        <CardHeader>
          <CardTitle>Documents</CardTitle>
          <CardDescription>Manage your documents</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">Documents page coming soon</p>
        </CardContent>
      </Card>
    </div>
  )
}
