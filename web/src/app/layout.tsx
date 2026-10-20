import "./globals.css";
import { Providers } from "./providers";

export const metadata = {
  title: "MemoryNest",
  description: "Personal knowledge vault — local RAG over your documents.",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased">
        <link rel="icon" href="/favicon.ico" />
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
