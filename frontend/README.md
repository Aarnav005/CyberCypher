# Cyber Cypher Frontend (Sentinel‑Pay)

This is a small Next.js + TypeScript scaffold implementing a dashboard UI that mirrors the reference image in the repository root (see conversation screenshot). It uses a simple API route (`/api/status`) that attempts to read the simulation log (`continuous_stream.log`) and returns lightweight status data used by the dashboard components.

Quick start:

1. cd frontend
2. npm install
3. npm run dev

Notes:
- The UI is intentionally lightweight and uses inline styles and small SVG sparklines to avoid large dependencies.
- Put a preview/reference image at `frontend/public/reference-dashboard.png` if you want a local copy of the design snapshot used as inspiration.
- The API reads `../continuous_stream.log`. Ensure the Next process can access the file.
- For live updates the demo now includes a WebSocket broadcaster — run `python demo_continuous_stream.py` and the UI will connect to `ws://localhost:8765` to receive live telemetry updates.

Files added:
- `pages/index.tsx` — dashboard page
- `src/components/*` — modular components (Telemetry, AgentBrain, Interventions, Guardrails)
- `pages/api/status.ts` — simple log-based status endpoint

If you want, I can now:
- Add real-time websocket updates that stream telemetry from the Python loop
- Replace SVG sparklines with Chart.js and add package changes (one PR)
- Convert to Next 13 app-router and add server components

Which would you like next? ✅