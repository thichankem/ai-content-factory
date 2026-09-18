"use client";

import React, { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TooltipProvider } from "../components/ui/tooltip";
import "./globals.css";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 5000,
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <html lang="vi" className="dark">
      <head>
        <title>AI Content Factory • Pro NLE Studio</title>
        <meta
          name="description"
          content="AI-assisted professional short-form & long-form video production studio with NLE timeline, dynamic speed curves, parametric EQ, and visual node compositing."
        />
      </head>
      <body className="bg-nle-base min-h-screen text-gray-100 flex flex-col font-sans antialiased">
        <QueryClientProvider client={queryClient}>
          <TooltipProvider>{children}</TooltipProvider>
        </QueryClientProvider>
      </body>
    </html>
  );
}
