import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createHashRouter, RouterProvider, Navigate } from "react-router-dom";
import "./index.css";

import App from "./App.tsx";
import LastDetectedContentPage from "./LastDetectedContentPage";
import StreamerUpdatesPage from "./components/StreamerUpdatesPage";


const router = createHashRouter([
  {
    path: "/",
    element: <Navigate to="/guest" replace />,
  },
  {
    path: "/Guest",
    element: <App />,
  },
  {
    path: "/guest",
    element: <App />,
  },
  {
    path: "/Guest/lastdetectedcontent",
    element: <LastDetectedContentPage />,
  },
  {
    path: "/guest/lastdetectedcontent",
    element: <LastDetectedContentPage />,
  },
  {
    path: "/updates",
    element: <StreamerUpdatesPage />,
  },
  {
    path: "/guest/updates",
    element: <StreamerUpdatesPage />,
  },
  {
    path: "*",
    element: <Navigate to="/guest" replace />,
  },
]);

console.log("FAVCREATORS App Initializing...");

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>
);
