import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Video, FileText, Zap, ArrowRight } from "lucide-react";

export const Hero = () => {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden px-4 py-20">
      {/* Background Effects */}
      <div className="absolute inset-0 gradient-glow opacity-50" />
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/5 rounded-full blur-3xl animate-pulse-glow" />
      <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-accent/5 rounded-full blur-3xl animate-pulse-glow" style={{ animationDelay: "1.5s" }} />
      
      {/* Grid Pattern */}
      <div className="absolute inset-0 bg-[linear-gradient(hsl(220_16%_12%/0.3)_1px,transparent_1px),linear-gradient(90deg,hsl(220_16%_12%/0.3)_1px,transparent_1px)] bg-[size:60px_60px] [mask-image:radial-gradient(ellipse_at_center,black_20%,transparent_70%)]" />

      <div className="relative z-10 max-w-5xl mx-auto text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <Badge variant="glow" className="mb-6">
            <Zap className="w-3 h-3 mr-1" />
            Enterprise-Grade AI Documentation
          </Badge>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="text-5xl md:text-7xl lg:text-8xl font-bold tracking-tight mb-6"
        >
          <span className="text-foreground">Turn </span>
          <span className="text-gradient">Videos</span>
          <br />
          <span className="text-foreground">into </span>
          <span className="text-gradient-accent">Documentation</span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-10"
        >
          DevLens AI automatically converts video recordings from Zoom, Loom, and screen captures 
          into structured, professional technical documentation using multimodal AI.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="flex flex-col sm:flex-row gap-4 justify-center"
        >
          <Button variant="hero" size="xl">
            Get Started
            <ArrowRight className="w-5 h-5" />
          </Button>
          <Button variant="glass" size="xl">
            <Video className="w-5 h-5" />
            Watch Demo
          </Button>
        </motion.div>

        {/* Feature Pills */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="flex flex-wrap justify-center gap-3 mt-16"
        >
          {[
            { icon: FileText, label: "Bug Reports" },
            { icon: FileText, label: "Feature Specs" },
            { icon: FileText, label: "Technical Docs" },
            { icon: FileText, label: "HR Interviews" },
            { icon: FileText, label: "Finance Reviews" },
          ].map((item, index) => (
            <motion.div
              key={item.label}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.4, delay: 0.5 + index * 0.1 }}
              className="glass px-4 py-2 rounded-full flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground hover:border-primary/30 transition-all cursor-default"
            >
              <item.icon className="w-4 h-4 text-primary" />
              {item.label}
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
};
