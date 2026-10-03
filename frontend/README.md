# Stratify Frontend

The Stratify frontend is a modern, high-performance web dashboard built with React 19, TypeScript, and Vite. It connects to the FastAPI backend, utilizing a responsive glassmorphism dark-mode UI with SVG telemetry charts, number tickers, and real-time multi-agent decision history.

---

## 1. Quick Start

Ensure you have [Node.js](https://nodejs.org/) installed (v18+ recommended).

1. Change directory to the frontend:
   ```bash
   cd frontend
   ```
2. Install the package dependencies:
   ```bash
   npm install
   ```
3. Start the Vite development client:
   ```bash
   npm run dev
   ```

By default, the Vite dev server runs on `http://localhost:5173`.

---

## 2. Available Commands

| Command | Description |
|---------|-------------|
| `npm run dev` | Starts the local dev server (port `5173`) with HMR and API proxy. |
| `npm run build` | Compiles and builds production-ready static assets in the `dist` directory. |
| `npm run lint` | Runs oxlint over typescript files. |
| `npm run preview` | Previews the compiled production build locally. |

---

## 3. Architecture & Key Files

The frontend architecture is lightweight and clean, avoiding complex state managers in favor of native React state hooks and API clients:

- **`src/main.tsx`**: Entry point bootstrapping React into the DOM.
- **`src/App.tsx`**: The core component containing the application shell, navigation panel, page views (Bento grid dashboard, charts, tables, simulators, AI chat window), and state syncing.
- **`src/api.ts`**: Axios client configuration. Incorporates route functions calling the backend.
- **`src/index.css`**: Global design system declarations (OKLCH color themes, variables, card layout properties) conforming to the specs in [design.md](design.md).
- **`src/App.css`**: Layout helper styles.

---

## 4. API Proxy Integration

Vite is configured via [vite.config.ts](frontend/vite.config.ts) to proxy all requests starting with `/api` to the backend server at `http://localhost:8000`. This avoids CORS issues during development.

---

## 5. View States & Pages

Navigation is controlled dynamically using React states mapping to the following pages:
- `dashboard`: Telemetry bento grid displaying cash balance, health index, alerts, and transaction feed.
- `forecast`: Revenue, runway cash flow, and product demand SVG graphs.
- `risk`: Interactive lists rating customer payment delinquency and supplier shipping delay risks.
- `pricing`: Margin-optimised pricing advice per product.
- `agents`: Considers the reports of 6 domain expert agents and synthesizes action proposals.
- `simulate`: Digital twin simulation sandbox with interactive sliders.
- `chat`: Dynamic chat portal query-matching recent business contexts using the local LLM.
- `brief`: Summary briefs containing checklists of actions and opportunities.
- `history`: Decisions logs showcasing past recommendation cards and approval audits.
- `upload`: File dropzone for uploading invoices, bank statements, and spreadsheets.

