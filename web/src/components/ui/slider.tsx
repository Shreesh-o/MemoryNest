"use client"

import * as React from "react"
import { Slider } from "@base-ui/react/slider"
import { cn } from "@/lib/utils"

interface SliderProps extends React.ComponentPropsWithoutRef<typeof Slider.Root> {
  className?: string
}

const SliderComponent = React.forwardRef<
  React.ElementRef<typeof Slider.Root>,
  SliderProps
>(({ className, ...props }, ref) => (
  <Slider.Root
    ref={ref}
    className={cn(
      "relative flex w-full touch-none select-none items-center",
      className
    )}
    {...props}
  >
    <Slider.Track className="relative h-2 w-full grow overflow-hidden rounded-full bg-muted border border-border/50">
      <Slider.Indicator className="h-full bg-primary" />
    </Slider.Track>
    <Slider.Thumb className="block size-4.5 rounded-full border-2 border-primary bg-background shadow-xs transition-all hover:scale-110 active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 cursor-grab active:cursor-grabbing" />
  </Slider.Root>
))
SliderComponent.displayName = "Slider"

export { SliderComponent as Slider }