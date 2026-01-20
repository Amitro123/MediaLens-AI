/**
 * Sanitize JSON that might be wrapped in markdown code fences.
 * 
 * DevLens pattern: Defensive parsing for Gemini JSON responses.
 */
export function sanitizeJson(text: string): string {
    let s = text.trim();

    // Remove ```json ... ``` or ``` ... ```
    if (s.startsWith("```")) {
        s = s.replace(/^```[a-zA-Z0-9_-]*\s*/, "");
        s = s.replace(/```$/, "");
    }

    return s.trim();
}

/**
 * Safe JSON parsing with automatic fence handling.
 */
export function parseDocumentation<T = any>(doc: string): T | null {
    try {
        const cleaned = sanitizeJson(doc);
        console.log('🔍 Parsing documentation...');
        console.log('   Original length:', doc.length);
        console.log('   Cleaned length:', cleaned.length);
        console.log('   First 100 chars:', cleaned.substring(0, 100));

        const parsed = JSON.parse(cleaned);
        console.log('✅ JSON parse successful');
        return parsed;
    } catch (error) {
        console.error('❌ JSON parse failed:', error);
        console.error('📄 Content preview:', doc.substring(0, 200));
        return null;
    }
}
