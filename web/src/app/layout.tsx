import "./globals.css";
import { Providers } from "./providers";
import { geist, geistMono, newsreader } from "./fonts";

export const metadata = {
  title: "MemoryNest — Local-First Personal Knowledge Manager",
  description: "A private personal knowledge vault with strictly cited document Q&A, Document Map relationships, and local LLM execution.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${geist.variable} ${geistMono.variable} ${newsreader.variable}`}
    >
      <body className="antialiased min-h-screen bg-background text-foreground font-sans selection:bg-primary/15 selection:text-foreground">
        <link rel="icon" href="/favicon.ico" />
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
