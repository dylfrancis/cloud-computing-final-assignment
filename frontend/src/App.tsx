import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import { Root } from './routes/Root'
import { Search } from './routes/Search'
import { Placeholder } from './routes/Placeholder'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, refetchOnWindowFocus: false },
  },
})

const router = createBrowserRouter([
  {
    path: '/',
    element: <Root />,
    children: [
      { index: true, element: <Search /> },
      { path: 'dashboard', element: <Placeholder title="Dashboard" /> },
      { path: 'upload', element: <Placeholder title="Upload" /> },
    ],
  },
])

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  )
}
