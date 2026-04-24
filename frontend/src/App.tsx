import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import { AuthProvider } from './auth/AuthContext'
import { RequireAuth } from './auth/RequireAuth'
import { Login } from './routes/Login'
import { Placeholder } from './routes/Placeholder'
import { Root } from './routes/Root'
import { Search } from './routes/Search'
import { Signup } from './routes/Signup'
import { Upload } from './routes/Upload'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, refetchOnWindowFocus: false },
  },
})

const router = createBrowserRouter([
  { path: '/login', element: <Login /> },
  { path: '/signup', element: <Signup /> },
  {
    path: '/',
    element: (
      <RequireAuth>
        <Root />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <Search /> },
      { path: 'dashboard', element: <Placeholder title="Dashboard" /> },
      { path: 'upload', element: <Upload /> },
    ],
  },
])

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </QueryClientProvider>
  )
}
