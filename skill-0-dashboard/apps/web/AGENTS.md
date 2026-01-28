# DASHBOARD WEB — React Frontend

## OVERVIEW

Governance dashboard UI. React 19 + Vite + TailwindCSS + shadcn/ui components.

## STRUCTURE

```
web/
├── src/
│   ├── pages/           # Route pages
│   ├── components/
│   │   ├── ui/          # shadcn/ui primitives
│   │   ├── layout/      # Layout components
│   │   ├── cards/       # Card components
│   │   ├── charts/      # Recharts wrappers
│   │   └── tables/      # Data tables
│   ├── api/             # API client functions
│   ├── lib/             # Utilities
│   └── styles/          # Global CSS
├── @/components/ui/     # shadcn/ui alias path
└── public/              # Static assets
```

## STACK

- **React** 19.2 + react-router-dom 7
- **Build**: Vite 7
- **Styling**: TailwindCSS 3.4 + tailwind-merge + class-variance-authority
- **Data**: TanStack Query 5 + Axios
- **Charts**: Recharts 3
- **Icons**: Lucide React
- **UI Kit**: Radix UI primitives

## WHERE TO LOOK

| Task | Location |
|------|----------|
| Add page | `src/pages/` + update router |
| Add component | `src/components/{category}/` |
| Add API call | `src/api/` |
| Modify theme | `tailwind.config.js` |

## CONVENTIONS

- Use `cn()` from `lib/utils` for class merging
- API base URL configured in `src/api/client.ts`
- Pages are lazy-loaded

## COMMANDS

```bash
npm run dev       # Dev server (port 5173)
npm run build     # Production build
npm run preview   # Preview production build
npm run lint      # ESLint check
```
