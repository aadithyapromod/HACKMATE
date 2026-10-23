from typing import Union
from ai.models import FileListOutput, GeneratedFileModel, PlanOutput


def generate_files(idea: str, plan: Union[PlanOutput, dict]) -> FileListOutput:
    """Generates the file tree and contents for the React + Vite application.

    Args:
        idea: Original hackathon idea prompt.
        plan: Validated PlanOutput or dictionary containing architecture tasks.

    Returns:
        FileListOutput containing list of GeneratedFileModel instances.
    """
    clean_idea = idea.strip()

    package_json = """{
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

    vite_config = """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true
  }
})"""

    index_html = """<!doctype html>
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

    main_jsx = """import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)"""

    index_css = """* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  background-color: #090d16;
  color: #f1f5f9;
  min-height: 100vh;
}"""

    app_jsx = f"""import React, {{ useState }} from 'react';
import {{ Sparkles, CheckCircle2, Terminal }} from 'lucide-react';

export default function App() {{
  const [count, setCount] = useState(0);

  return (
    <main style={{{{ padding: '3rem 1.5rem', maxWidth: '800px', margin: '0 auto', textAlign: 'center' }}}}>
      <header style={{{{ marginBottom: '2.5rem' }}}}>
        <div style={{{{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', background: 'rgba(139, 92, 246, 0.1)', border: '1px solid #8b5cf6', padding: '0.4rem 1rem', borderRadius: '9999px', color: '#a78bfa', fontSize: '0.875rem', fontWeight: 600 }}}}>
          <Sparkles size={{16}} />
          HackMate Generated MVP
        </div>
        <h1 style={{{{ fontSize: '2.5rem', fontWeight: 800, marginTop: '1rem', background: 'linear-gradient(to right, #ffffff, #a78bfa)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}}}>
          Autonomous Hackathon Prototype
        </h1>
      </header>

      <section style={{{{ background: '#111827', border: '1px solid #1f2937', borderRadius: '1rem', padding: '2rem', marginBottom: '2rem', textAlign: 'left' }}}}>
        <h2 style={{{{ fontSize: '1rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#9ca3af', marginBottom: '0.75rem' }}}}>
          Original Prompt Idea
        </h2>
        <p style={{{{ fontSize: '1.125rem', color: '#e5e7eb', lineHeight: 1.6 }}}}>
          "{clean_idea}"
        </p>
      </section>

      <div style={{{{ display: 'flex', gap: '1rem', justifyContent: 'center', alignItems: 'center' }}}}>
        <button
          onClick={{() => setCount((prev) => prev + 1)}}
          style={{{{ backgroundColor: '#8b5cf6', color: '#ffffff', border: 'none', padding: '0.75rem 1.75rem', borderRadius: '0.5rem', fontSize: '1rem', fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem' }}}}
        >
          <CheckCircle2 size={{18}} /> Interactive Counter: {{count}}
        </button>
      </div>
    </main>
  );
}}"""

    return FileListOutput(
        files=[
            GeneratedFileModel(path="package.json", content=package_json),
            GeneratedFileModel(path="vite.config.js", content=vite_config),
            GeneratedFileModel(path="index.html", content=index_html),
            GeneratedFileModel(path="src/main.jsx", content=main_jsx),
            GeneratedFileModel(path="src/index.css", content=index_css),
            GeneratedFileModel(path="src/App.jsx", content=app_jsx),
        ]
    )
