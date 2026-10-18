import "./globals.css";
import { ThemeProvider } from "next-themes";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/sonner";
import { formatDate } from "@/lib/api";

export const metadata = {
  title: "MemoryNest",
  description: "Personal knowledge vault — local RAG over your documents.",
};

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000,
      refetchOnWindowFocus: false,
    },
  },
});

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { theme } = useTheme();

  return (
    <html lang="en">
      <body className=" antialiased">
        <ThemeProvider attribute="class" hasSystemTheme>
          <QueryClientProvider client={queryClient}>
            <Toaster />
            {children}
          </QueryClientProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}

// Hook to get the current theme
function useTheme() {
  const [theme, setTheme] = React.useState<
    "light" | "dark" | "system"
  >("system");

  const setThemeValue = (value: "light" | "dark" | "system") => {
    setTheme(value);
  };

  return { theme, setThemeValue };
}

// Export formatDate for use in components
export { formatDate };
