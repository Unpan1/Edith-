import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './layout/AppShell'
import { AdminPage } from './pages/AdminPage'
import { AnalyticsPage } from './pages/AnalyticsPage'
import { AutomationPage } from './pages/AutomationPage'
import { CalendarPage } from './pages/CalendarPage'
import { ClipWorkspacePage } from './pages/ClipWorkspacePage'
import { CreditsPage } from './pages/CreditsPage'
import { DashboardPage } from './pages/DashboardPage'
import { GrowthPage } from './pages/GrowthPage'
import { HomePage } from './pages/HomePage'
import { LearningPage } from './pages/LearningPage'
import { LibraryPage } from './pages/LibraryPage'
import { PublishingPage } from './pages/PublishingPage'
import { TrendsPage } from './pages/TrendsPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 5_000,
      refetchOnWindowFocus: true,
    },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={<DashboardPage />} />
            <Route path="dashboard" element={<Navigate to="/" replace />} />
            <Route path="studio" element={<HomePage />} />
            <Route path="library" element={<LibraryPage />} />
            <Route path="library/clips/:id" element={<ClipWorkspacePage />} />
            <Route path="trends" element={<TrendsPage />} />
            <Route path="calendar" element={<CalendarPage />} />
            <Route path="publishing" element={<PublishingPage />} />
            <Route path="analytics" element={<AnalyticsPage />} />
            <Route path="learning" element={<LearningPage />} />
            <Route path="automation" element={<AutomationPage />} />
            <Route path="growth" element={<GrowthPage />} />
            <Route path="credits" element={<CreditsPage />} />
            <Route path="admin" element={<AdminPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
