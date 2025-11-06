import { useEffect, useState } from "react";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/AppSidebar";
import { Button } from "@/components/ui/button";
import Index from "./pages/Index";
import Chat from "./pages/Chat";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const FONT_SCALE_MIN = 0.85;
const FONT_SCALE_MAX = 1.5;
const FONT_SCALE_STEP = 0.1;

const AppShell = () => {
  const location = useLocation();
  const isChatRoute = location.pathname.startsWith("/chat");
  const [fontScale, setFontScale] = useState(1);
  const [sidebarOpen, setSidebarOpen] = useState(isChatRoute);

  useEffect(() => {
    if (typeof document === "undefined") {
      return;
    }
    const normalized = Math.min(FONT_SCALE_MAX, Math.max(FONT_SCALE_MIN, fontScale));
    if (normalized !== fontScale) {
      setFontScale(normalized);
      return;
    }
    document.documentElement.style.setProperty("--font-scale", normalized.toString());
  }, [fontScale]);

  useEffect(() => {
    setSidebarOpen(isChatRoute);
  }, [isChatRoute]);

  const adjustFontScale = (delta: number) => {
    setFontScale((prev) => {
      const next = Math.round((prev + delta) * 100) / 100;
      return Math.min(FONT_SCALE_MAX, Math.max(FONT_SCALE_MIN, next));
    });
  };

  const fontScalePercent = Math.round(fontScale * 100);

  const handleFontScaleInput = (event: React.ChangeEvent<HTMLInputElement>) => {
    const rawPercent = Number.parseFloat(event.target.value);
    if (Number.isNaN(rawPercent)) {
      return;
    }
    const next = Math.round(rawPercent) / 100;
    const normalized = Math.min(FONT_SCALE_MAX, Math.max(FONT_SCALE_MIN, next));
    setFontScale(normalized);
  };

  return (
    <SidebarProvider open={sidebarOpen} onOpenChange={setSidebarOpen}>
      <div className="flex min-h-screen w-full">
        <AppSidebar />
        <SidebarInset className="flex flex-col">
          <header className="sticky top-0 z-10 flex h-14 items-center gap-2 border-b bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/60">
            <SidebarTrigger />
            <div className="ml-auto flex items-center gap-2 rounded-full border bg-muted/60 px-2 py-1 text-xs text-muted-foreground">
              <span className="hidden font-medium text-foreground sm:inline">글자 크기</span>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-sm"
                onClick={() => adjustFontScale(-FONT_SCALE_STEP)}
                disabled={fontScale <= FONT_SCALE_MIN}
              >
                <span aria-hidden>가-</span>
                <span className="sr-only">글씨 작게</span>
              </Button>
              <input
                type="number"
                inputMode="decimal"
                step={Math.round(FONT_SCALE_STEP * 100)}
                min={Math.round(FONT_SCALE_MIN * 100)}
                max={Math.round(FONT_SCALE_MAX * 100)}
                value={fontScalePercent}
                aria-label="글씨 크기 퍼센트"
                onChange={(event) => handleFontScaleInput(event)}
                className="h-8 w-16 rounded-md border border-input bg-background text-center text-sm font-semibold text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
              <span className="text-foreground">%</span>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-sm"
                onClick={() => adjustFontScale(FONT_SCALE_STEP)}
                disabled={fontScale >= FONT_SCALE_MAX}
              >
                <span aria-hidden>가+</span>
                <span className="sr-only">글씨 크게</span>
              </Button>
            </div>
          </header>
          <Routes>
            <Route path="/" element={<Index />} />
            <Route path="/chat/:category" element={<Chat />} />
            {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
};

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <AppShell />
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
