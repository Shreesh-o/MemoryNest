import { Metadata } from "next"
import { cookies } from "next/headers"
import { redirect } from "next/navigation"
import { HeroSection } from "@/components/marketing/hero-section"
import { BentoGrid } from "@/components/marketing/bento-grid"
import { HowItWorks } from "@/components/marketing/how-it-works"
import { PrivacySection } from "@/components/marketing/privacy-section"
import { TechStack } from "@/components/marketing/tech-stack"
import { CTASection } from "@/components/marketing/cta-section"

export const metadata: Metadata = {
  title: "MemoryNest — Local-First Personal Knowledge Vault",
  description:
    "A local-first personal knowledge manager: upload PDFs, DOCX, TXT, and scanned images with OCR. Ask questions with verifiable citations, summarize documents, and stay on top of deadlines with zero cloud lock-in.",
  openGraph: {
    title: "MemoryNest — Local-First Personal Knowledge Vault",
    description:
      "Local-first personal knowledge manager: upload, ask, summarize, and never lose a deadline with local Ollama LLM and ChromaDB vector search.",
    type: "website",
  },
}

export default async function LandingPage() {
  // If the user already has an active session cookie, redirect to /dashboard
  const cookieStore = await cookies()
  if (cookieStore.has("mn_session")) {
    redirect("/dashboard")
  }

  return (
    <>
      <HeroSection />
      <BentoGrid />
      <HowItWorks />
      <PrivacySection />
      <TechStack />
      <CTASection />
    </>
  )
}
