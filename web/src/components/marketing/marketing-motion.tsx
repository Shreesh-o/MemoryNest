"use client"

import * as React from "react"
import { gsap } from "gsap"
import { ScrollTrigger } from "gsap/ScrollTrigger"
import Lenis from "lenis"

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger)
}

export function MarketingMotion({ children }: { children: React.ReactNode }) {
  React.useEffect(() => {
    // Check if user prefers reduced motion
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches
    if (prefersReducedMotion) {
      return
    }

    // Initialize Lenis for smooth momentum scrolling on marketing page
    const lenis = new Lenis({
      duration: 1.1,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      orientation: "vertical",
      gestureOrientation: "vertical",
      smoothWheel: true,
      wheelMultiplier: 0.9,
    })

    // Synchronize Lenis with GSAP's central ticker
    const onTick = (time: number) => {
      lenis.raf(time * 1000)
    }

    lenis.on("scroll", ScrollTrigger.update)
    gsap.ticker.add(onTick)
    gsap.ticker.lagSmoothing(0)

    // GSAP context for clean lifecycle scoping and automatic cleanup
    const ctx = gsap.context(() => {
      // 1. Reveal hero section elements
      gsap.from("#hero-heading", {
        opacity: 0,
        y: 20,
        duration: 0.8,
        ease: "power3.out",
        delay: 0.1,
      })

      // 2. Animate Capabilities Dossier sections on scroll
      const featureCards = gsap.utils.toArray<HTMLElement>("#features .paper-folio")
      if (featureCards.length > 0) {
        gsap.from(featureCards, {
          scrollTrigger: {
            trigger: "#features",
            start: "top 80%",
            toggleActions: "play none none none",
          },
          opacity: 0,
          y: 28,
          duration: 0.7,
          stagger: 0.08,
          ease: "power3.out",
        })
      }

      // 3. Animate How It Works sequential pipeline stages
      const stages = gsap.utils.toArray<HTMLElement>("#how-it-works .paper-folio")
      if (stages.length > 0) {
        gsap.from(stages, {
          scrollTrigger: {
            trigger: "#how-it-works",
            start: "top 80%",
            toggleActions: "play none none none",
          },
          opacity: 0,
          y: 24,
          duration: 0.65,
          stagger: 0.1,
          ease: "power3.out",
        })
      }

      // 4. Animate Privacy & Sovereignty sections
      const privacyCards = gsap.utils.toArray<HTMLElement>("#privacy .paper-folio")
      if (privacyCards.length > 0) {
        gsap.from(privacyCards, {
          scrollTrigger: {
            trigger: "#privacy",
            start: "top 80%",
            toggleActions: "play none none none",
          },
          opacity: 0,
          y: 24,
          duration: 0.65,
          stagger: 0.08,
          ease: "power3.out",
        })
      }
    })

    return () => {
      ctx.revert()
      gsap.ticker.remove(onTick)
      lenis.destroy()
      ScrollTrigger.getAll().forEach((trigger) => trigger.kill())
    }
  }, [])

  return <>{children}</>
}
