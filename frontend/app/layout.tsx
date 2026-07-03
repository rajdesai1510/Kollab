import type { Metadata } from "next";
import { Inter, Outfit, Geist } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";
import { QueryProvider } from "@/components/providers/QueryProvider";
import { ThemeProvider } from "@/components/theme-provider";
import { cn } from "@/lib/utils";

const geist = Geist({subsets:['latin'],variable:'--font-sans'});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const outfit = Outfit({
  subsets: ["latin"],
  variable: "--font-outfit",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Nexus — Connect Creators & Brands",
  description:
    "India's platform for micro-influencers and local D2C brands to find, connect, and collaborate — without the agency middleman.",
  keywords: ["influencer marketing", "micro-influencer", "brand collaboration", "India", "D2C"],
  openGraph: {
    title: "Nexus",
    description: "Where Indian micro-influencers meet the brands that matter.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={cn(inter.variable, outfit.variable, "font-sans", geist.variable)} suppressHydrationWarning>
      <body>
        <ThemeProvider
          attribute="class"
          defaultTheme="light"
          enableSystem={false}
          disableTransitionOnChange
        >
          <QueryProvider>
            <AuthProvider>{children}</AuthProvider>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
