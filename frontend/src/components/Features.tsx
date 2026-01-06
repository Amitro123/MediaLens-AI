import { motion } from "framer-motion";
import {
  Zap,
  Code2,
  Mic2,
  Brain,
  Clock,
  Shield,
  Layers,
  BarChart3,
} from "lucide-react";

const features = [
  {
    icon: Zap,
    title: "Audio-First Smart Sampling",
    description: "Analyzes audio to extract frames only during technical discussions, saving cost and time.",
  },
  {
    icon: Code2,
    title: "Code Extraction (OCR)",
    description: "Transcribes visible code from IDEs and terminals verbatim with high accuracy.",
  },
  {
    icon: Mic2,
    title: "Fast STT Service",
    description: "Local faster-whisper transcription with Gemini fallback — 10x faster than cloud APIs.",
  },
  {
    icon: Brain,
    title: "Multi-Model Intelligence",
    description: "Gemini Flash for analysis, Gemini Pro for generation. Best of both worlds.",
  },
  {
    icon: Clock,
    title: "78% Cost Reduction",
    description: "Process only relevant frames — ~$0.11 per 10-minute video vs traditional $0.50.",
  },
  {
    icon: Layers,
    title: "Chunk-based Processing",
    description: "Videos processed in 30-second segments for granular progress and smaller AI contexts.",
  },
  {
    icon: BarChart3,
    title: "Full Observability",
    description: "Every decision logged as a Turn with JSONL for context, search, and analytics.",
  },
  {
    icon: Shield,
    title: "Visual Quality Control",
    description: "AI filters out blank screens, loading spinners, and blurred transitions automatically.",
  },
];

export const Features = () => {
  return (
    <section id="features" className="py-24 px-4">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4">
            Powered by <span className="text-gradient">Dual-Stream</span> Architecture
          </h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            Speed + Quality. Our intelligent pipeline processes videos efficiently
            while maintaining pristine documentation quality.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {features.map((feature, index) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.05 }}
              className="group p-6 rounded-2xl border border-border bg-card hover:border-primary/30 hover:shadow-card transition-all"
            >
              <div className="w-12 h-12 rounded-xl bg-secondary flex items-center justify-center mb-4 group-hover:bg-primary/10 transition-colors">
                <feature.icon className="w-6 h-6 text-muted-foreground group-hover:text-primary transition-colors" />
              </div>
              <h3 className="font-semibold text-foreground mb-2 group-hover:text-primary transition-colors">
                {feature.title}
              </h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {feature.description}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};
