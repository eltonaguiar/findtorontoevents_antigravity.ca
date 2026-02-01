import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createHashRouter, RouterProvider } from "react-router-dom";
import "./index.css";

import App from "./App.tsx";
import LastDetectedContentPage from "./LastDetectedContentPage";


const router = createHashRouter([
  {
    path: "/guest",
    element: <App />,
  },
  {
    path: "/guest/lastdetectedcontent",
    element: <LastDetectedContentPage />,
  },
  {
    path: "*",
    element: (
      <div style={{ padding: "2rem", color: "#f8fafc" }}>
        <h2>Access required</h2>
        <p>Go to #/guest after logging in.</p>
      </div>
    ),
  },
]);

console.log("FAVCREATORS App Initializing...");

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>
);
