import { useState } from 'react';
import { Search, Play } from 'lucide-react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

// Define Scene type based on prompt description
export interface Scene {
    id: string; // or number
    number: number;
    timestamp_start: string; // MM:SS
    timestamp_end: string;
    start_sec: number; // useful for jumping
    location: string;
    characters: string[];
    dialogue: string;
    visual_description: string;
    keywords: string[];
    description: string; // aggregated description
}

interface SceneSearchProps {
    sessionId: string;
    scenes: Scene[];
    onJumpTo: (seconds: number) => void;
}

export function SceneSearch({ sessionId, scenes, onJumpTo }: SceneSearchProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Scene[]>([]);

  const handleSearch = () => {
    if (!query.trim()) {
        setResults([]);
        return;
    }
    const lowerQuery = query.toLowerCase();
    const filtered = scenes.filter(scene => 
      (scene.keywords && scene.keywords.some(k => k.toLowerCase().includes(lowerQuery))) ||
      (scene.description && scene.description.toLowerCase().includes(lowerQuery)) ||
      (scene.dialogue && scene.dialogue.toLowerCase().includes(lowerQuery)) ||
      (scene.characters && scene.characters.some(c => c.toLowerCase().includes(lowerQuery)))
    );
    setResults(filtered);
  };

  return (
    <div className="space-y-4 glass rounded-xl p-4">
      <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
          <Search className="w-5 h-5" /> Scene Search
      </h3>
      
      <div className="flex gap-2">
        <Input
          type="text"
          placeholder='חפש סצנות... (לדוגמה: "משקפי שמש")'
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          className="bg-card"
        />
        <Button onClick={handleSearch}>🔍 חפש</Button>
      </div>

      <div className="space-y-3 mt-4 max-h-[400px] overflow-y-auto">
        {results.length > 0 ? (
            results.map((scene, idx) => (
            <div key={scene.id || idx} className="bg-secondary/50 p-3 rounded-lg border border-border/50 hover:border-primary/50 transition-colors">
                <div className="flex justify-between items-start mb-2">
                    <span className="font-bold text-sm">Scene {scene.number}</span>
                    <span className="text-xs font-mono bg-primary/20 text-primary px-1.5 py-0.5 rounded">
                        {scene.timestamp_start}
                        {scene.timestamp_end ? ` - ${scene.timestamp_end}` : ''}
                    </span>
                </div>
                <p className="text-sm text-foreground mb-2">{scene.description || scene.visual_description}</p>
                {scene.keywords && (
                    <div className="flex flex-wrap gap-1 mb-2">
                        {scene.keywords.map((k, i) => (
                            <span key={i} className="text-[10px] bg-secondary px-1.5 py-0.5 rounded text-muted-foreground">{k}</span>
                        ))}
                    </div>
                )}
                <Button variant="ghost" size="sm" className="w-full h-7 text-xs" onClick={() => onJumpTo(scene.start_sec)}>
                    <Play className="w-3 h-3 mr-1" /> Jump to Scene
                </Button>
            </div>
            ))
        ) : query && (
            <p className="text-sm text-muted-foreground text-center py-4">No scenes found matching "{query}"</p>
        )}
      </div>
    </div>
  );
}
