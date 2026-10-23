import * as React from "react"
import { cn } from "@/lib/utils"

interface EmptyStateProps extends React.ComponentProps<"div"> {
  icon?: React.ReactNode
  title: string
  description?: string
  action?: React.ReactNode
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
  ...props
}: EmptyStateProps) {
  return (
    <div
      data-slot="empty-state"
      className={cn(
        "flex min-h-[200px] flex-col items-center justify-center rounded-xl border border-dashed border-border/70 bg-muted/20 p-8 text-center transition-colors",
        className
      )}
      {...props}
    >
      {icon && (
        <div className="mb-3.5 flex size-12 items-center justify-center rounded-xl bg-muted/60 text-muted-foreground ring-1 ring-border/50 [&>svg]:size-6">
          {icon}
        </div>
      )}
      <h3 className="font-heading text-base font-semibold text-foreground tracking-tight">
        {title}
      </h3>
      {description && (
        <p className="mt-1.5 max-w-sm text-sm text-muted-foreground leading-relaxed">
          {description}
        </p>
      )}
      {action && <div className="mt-4 flex items-center gap-2">{action}</div>}
    </div>
  )
}
