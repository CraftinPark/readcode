import { useEffect, useState } from 'react'
import ExercisePage from './pages/ExercisePage'
import ExercisesPage from './pages/ExercisesPage'
import LandingPage from './pages/LandingPage'
import TaskPage from './pages/TaskPage'

// Hash routes: #/  #/exercises  #/exercise/<id>  #/exercise/<id>/task/<T#>
function useRoute() {
  const read = () => window.location.hash.replace(/^#/, '') || '/'
  const [route, setRoute] = useState(read)
  useEffect(() => {
    const onChange = () => {
      setRoute(read())
      window.scrollTo(0, 0)
    }
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  return route
}

export default function App() {
  const route = useRoute()
  const task = /^\/exercise\/([\w-]+)\/task\/(T\d+)$/.exec(route)
  if (task) return <TaskPage id={task[1]} taskId={task[2]} />
  const exercise = /^\/exercise\/([\w-]+)$/.exec(route)
  if (exercise) return <ExercisePage id={exercise[1]} />
  if (route === '/exercises') return <ExercisesPage />
  return <LandingPage />
}
