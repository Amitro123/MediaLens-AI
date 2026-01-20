import uvicorn
import os
import sys

# Add the current directory to sys.path to ensure app module can be found
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    # reload=True: Auto-reload on code changes (disable with reload=False for production/testing)
    # reload_dirs: Only watch app/ directory to avoid reloads from test file changes
    uvicorn.run(
        "app.main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        reload_dirs=["app"]  # Only reload on changes in app/ directory
    )
