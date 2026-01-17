# AMIT CODING PREFERENCES v1.0
Session: 2026-01-17 - MediaLens Adaptation
Learned:
✅ Approved: [Smart Extraction Logic] → Pattern: Always initialize optional accumulation lists (e.g., `timestamps = []`) before conditional blocks to ensure ensuring stability if the condition (e.g., `relevant_segments`) is false but the variable is used later.
✅ Approved: [AI Mode Config] → Pattern: Use centralized YAML prompt configurations (`PromptLoader`) to decouple prompt engineering from code logic, allowing rapid iteration on AI personas.
