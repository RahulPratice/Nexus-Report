import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Dashboard from './pages/Dashboard';
import RunExplorer from './pages/RunExplorer';
import Trends from './pages/Trends';
import { LayoutDashboard, TrendingUp, FolderKanban, Settings } from 'lucide-react';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 10_000, retry: 2 },
  },
});

const NAV = [
  { to: '/',        icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/trends',  icon: TrendingUp,      label: 'Trends'    },
  { to: '/projects',icon: FolderKanban,    label: 'Projects'  },
  { to: '/settings',icon: Settings,        label: 'Settings'  },
];

function Sidebar() {
  return (
    <aside className="w-56 h-screen bg-gray-950 flex flex-col py-6 px-4 fixed left-0 top-0">
      <div className="mb-8 px-2">
        <span className="text-white font-bold text-lg tracking-tight">Nexus</span>
        <span className="text-indigo-400 font-bold text-lg">Report</span>
      </div>
      <nav className="space-y-1">
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive
                  ? 'bg-indigo-600 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800'
              }`
            }
          >
            <Icon className="w-4 h-4" />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="flex bg-gray-50 min-h-screen">
          <Sidebar />
          <main className="ml-56 flex-1">
            <Routes>
              <Route path="/"              element={<Dashboard />} />
              <Route path="/runs/:runId"   element={<RunExplorer />} />
              <Route path="/trends"        element={<Trends />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
