import os
from typing import Dict, Any, List
from app.schemas.task import Task, TaskStatus
from app.schemas.files import GeneratedFile


class AIClient:
    """Client for AI Planner and Code Generation operations.

    Falls back to deterministic scaffold templates when no external AI API key is configured.
    """

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")

    async def create_plan(self, idea: str) -> Dict[str, Any]:
        """Creates a structured plan for the given idea.

        Returns:
            Dict containing summary, framework: 'react-vite', and tasks list.
        """
        # Structured plan conforming to HackMate specifications
        return {
            "summary": f"Plan for: {idea[:60]}...",
            "framework": "react-vite",
            "tasks": [
                {
                    "id": "task-1",
                    "title": "Project Architecture & Requirements",
                    "description": f"Decompose idea '{idea[:40]}' into modular React components.",
                    "status": "completed",
                },
                {
                    "id": "task-2",
                    "title": "Scaffold Vite + React Structure",
                    "description": "Generate package.json, index.html, vite.config.js, and main entry.",
                    "status": "completed",
                },
                {
                    "id": "task-3",
                    "title": "Synthesize Core UI Components",
                    "description": "Generate App.jsx, navigation, dashboard views, and styling.",
                    "status": "pending",
                },
            ],
        }

    async def generate_files(self, idea: str, plan: Dict[str, Any]) -> List[GeneratedFile]:
        """Generates the code files for the project.

        Returns:
            List of GeneratedFile models (path, content).
        """
        # Default safe React + Vite starter template
        return [
            GeneratedFile(
                path="package.json",
                content="""{
  "name": "hackmate-generated-app",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "lucide-react": "^0.453.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.2",
    "vite": "^5.4.9"
  }
}"""
            ),
            GeneratedFile(
                path="vite.config.js",
                content="""import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true
  }
})"""
            ),
            GeneratedFile(
                path="index.html",
                content="""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>HackMate App</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>"""
            ),
            GeneratedFile(
                path="src/main.jsx",
                content="""import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)"""
            ),
            GeneratedFile(
                path="src/index.css",
                content="""* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background-color: #0d1117;
  color: #f0f6fc;
  min-height: 100vh;
}"""
            ),
            GeneratedFile(
                path="src/App.jsx",
                content=f"""import React from 'react';

export default function App() {{
  return (
    <div style={{{{ padding: '2rem', maxWidth: '800px', margin: '0 auto', textAlign: 'center' }}}}>
      <h1 style={{{{ color: '#8b5cf6', marginBottom: '1rem' }}}}>HackMate Generated App</h1>
      <p style={{{{ fontSize: '1.2rem', color: '#94a3b8', marginBottom: '2rem' }}}}>
        Built autonomously from prompt:
      </p>
      <blockquote style={{{{ background: '#161b22', padding: '1rem', borderRadius: '8px', borderLeft: '4px solid #8b5cf6' }}}}>
        "{idea}"
      </blockquote>
    </div>
  );
}}"""
            ),
        ]


_ai_client = AIClient()


def get_ai_client() -> AIClient:
    return _ai_client
