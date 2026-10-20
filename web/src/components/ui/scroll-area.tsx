"use client"

import * as React from "react"
import { ScrollArea as ScrollAreaPrimitive } from "@base-ui/react/scroll-area"
import { cn } from "cn"

function ScrollArea({ className, children, ...props }: React.ComponentProps<"div">) {
  return (
    <ScrollAreaPrimitive.Root
      data-slot="scroll-area"
      className={cn("relative overflow-hidden", className)}
      {...props}
    >
      <ScrollAreaPrimitive.Viewport className="h-full w-full rounded-[inherit]">
        {children}
      </ScrollAreaPrimitive.Viewport>
      <ScrollAreaPrimitive.Scrollbar orientation="vertical" className="h-full w-2 border-l border-transparent">
        <ScrollAreaPrimitive.Thumb className="relative flex-1 rounded-full bg-border/50 transition-colors hover:bg-border/75" />
      </ScrollAreaPrimitive.Scrollbar>
      <ScrollAreaPrimitive.Scrollbar orientation="horizontal" className="h-2 w-full border-t border-transparent">
        <ScrollAreaPrimitive.Thumb className="relative h-full rounded-full bg-border/50 transition-colors hover:bg-border/75" />
      </ScrollAreaPrimitive.Scrollbar>
      <ScrollAreaPrimitive.Corner />
    </ScrollAreaPrimitive.Root>
  )
}

export { ScrollArea }