import localFont from "next/font/local";

export const geist = localFont({
  src: [
    { path: "../../public/fonts/geist-400-normal.woff2", weight: "400", style: "normal" },
    { path: "../../public/fonts/geist-500-normal.woff2", weight: "500", style: "normal" },
    { path: "../../public/fonts/geist-600-normal.woff2", weight: "600", style: "normal" },
    { path: "../../public/fonts/geist-700-normal.woff2", weight: "700", style: "normal" },
  ],
  variable: "--font-geist",
  display: "swap",
});

export const geistMono = localFont({
  src: [
    { path: "../../public/fonts/geist-mono-400-normal.woff2", weight: "400", style: "normal" },
    { path: "../../public/fonts/geist-mono-500-normal.woff2", weight: "500", style: "normal" },
    { path: "../../public/fonts/geist-mono-600-normal.woff2", weight: "600", style: "normal" },
  ],
  variable: "--font-geist-mono",
  display: "swap",
});

export const newsreader = localFont({
  src: [
    { path: "../../public/fonts/newsreader-400-normal.woff2", weight: "400", style: "normal" },
    { path: "../../public/fonts/newsreader-400-italic.woff2", weight: "400", style: "italic" },
    { path: "../../public/fonts/newsreader-500-normal.woff2", weight: "500", style: "normal" },
    { path: "../../public/fonts/newsreader-500-italic.woff2", weight: "500", style: "italic" },
  ],
  variable: "--font-newsreader",
  display: "swap",
});
