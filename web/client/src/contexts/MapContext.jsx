import { createContext, useContext, useRef } from 'react'

const MapContext = createContext(null)

export function MapProvider({ children }) {
  const panToRef    = useRef(null)   // (lat, lon) => void
  const highlightRef = useRef(null)  // (businessId) => void

  function registerPanTo(fn)    { panToRef.current    = fn }
  function registerHighlight(fn) { highlightRef.current = fn }

  function panTo(lat, lon)       { panToRef.current?.(lat, lon) }
  function highlight(businessId) { highlightRef.current?.(businessId) }

  return (
    <MapContext.Provider value={{ registerPanTo, registerHighlight, panTo, highlight }}>
      {children}
    </MapContext.Provider>
  )
}

export const useMapCtx = () => useContext(MapContext)
