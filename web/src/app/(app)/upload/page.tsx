import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"

export default function UploadPage() {
  return (
    <div className="p-6 max-w-4xl mx-auto">
      <Card>
        <CardHeader>
          <CardTitle>Upload</CardTitle>
          <CardDescription>Upload new documents</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">Upload page coming soon</p>
        </CardContent>
      </Card>
    </div>
  )
}
