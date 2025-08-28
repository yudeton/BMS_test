import React from 'react'
import { Routes, Route } from 'react-router-dom'
import Dashboard from './views/Dashboard'
import CellDetails from './views/CellDetails'
import History from './views/History'
import Settings from './views/Settings'
import Layout from './components/Layout'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/cells" element={<CellDetails />} />
        <Route path="/history" element={<History />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </Layout>
  )
}

export default App