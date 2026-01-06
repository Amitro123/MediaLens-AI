import { motion } from "framer-motion";
import { ScanEye, Menu, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useState } from "react";
import { cn } from "@/lib/utils";

export const Header = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navLinks = [
    { label: "Dashboard", href: "#dashboard" },
    { label: "Features", href: "#features" },
    { label: "Docs", href: "#docs" },
  ];

  return (
    <motion.header
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="fixed top-0 left-0 right-0 z-50 glass border-b border-border/50"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <a href="/" className="flex items-center gap-2.5 group">
            <div className="w-9 h-9 rounded-lg gradient-primary flex items-center justify-center shadow-glow group-hover:shadow-[0_0_30px_-5px_hsl(174_72%_56%/0.5)] transition-all">
              <ScanEye className="w-5 h-5 text-primary-foreground" />
            </div>
            <span className="font-display font-bold text-xl text-foreground">
              DevLens<span className="text-primary">AI</span>
            </span>
          </a>

          {/* Desktop Nav */}
          <nav className="hidden md:flex items-center gap-1">
            {navLinks.map((link) => (
              <a
                key={link.label}
                href={link.href}
                className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors rounded-lg hover:bg-secondary/50"
              >
                {link.label}
              </a>
            ))}
          </nav>

          {/* Desktop Actions */}
          <div className="hidden md:flex items-center gap-3">
            <Button variant="ghost" size="sm">
              Sign In
            </Button>
            <Button variant="default" size="sm">
              Get Started
            </Button>
          </div>

          {/* Mobile Menu Toggle */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2 text-muted-foreground hover:text-foreground transition-colors"
          >
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      <motion.div
        initial={false}
        animate={mobileMenuOpen ? { height: "auto", opacity: 1 } : { height: 0, opacity: 0 }}
        className={cn(
          "md:hidden overflow-hidden border-t border-border/50",
          !mobileMenuOpen && "pointer-events-none"
        )}
      >
        <div className="px-4 py-4 space-y-2">
          {navLinks.map((link) => (
            <a
              key={link.label}
              href={link.href}
              className="block px-4 py-3 text-muted-foreground hover:text-foreground hover:bg-secondary/50 rounded-lg transition-colors"
              onClick={() => setMobileMenuOpen(false)}
            >
              {link.label}
            </a>
          ))}
          <div className="pt-4 space-y-2">
            <Button variant="ghost" className="w-full justify-center">
              Sign In
            </Button>
            <Button variant="default" className="w-full justify-center">
              Get Started
            </Button>
          </div>
        </div>
      </motion.div>
    </motion.header>
  );
};
