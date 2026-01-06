import { ScanEye } from "lucide-react";

export const Footer = () => {
  return (
    <footer className="border-t border-border py-12 px-4">
      <div className="max-w-6xl mx-auto">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          {/* Logo */}
          <a href="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg gradient-primary flex items-center justify-center">
              <ScanEye className="w-4 h-4 text-primary-foreground" />
            </div>
            <span className="font-display font-bold text-lg text-foreground">
              DevLens<span className="text-primary">AI</span>
            </span>
          </a>

          {/* Links */}
          <nav className="flex items-center gap-6 text-sm">
            <a href="#" className="text-muted-foreground hover:text-foreground transition-colors">
              Documentation
            </a>
            <a href="#" className="text-muted-foreground hover:text-foreground transition-colors">
              GitHub
            </a>
            <a href="#" className="text-muted-foreground hover:text-foreground transition-colors">
              Privacy
            </a>
            <a href="#" className="text-muted-foreground hover:text-foreground transition-colors">
              Terms
            </a>
          </nav>

          {/* Copyright */}
          <p className="text-sm text-muted-foreground">
            © 2024 DevLens AI. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
};
