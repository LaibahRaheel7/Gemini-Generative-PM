import React from "react";
import ReactDOM from "react-dom/client";
import FullCalendarComponent from "./FullCalendarComponent";
import "./index.css";

const root = ReactDOM.createRoot(
  document.getElementById("root") as HTMLElement
);

root.render(
  <React.StrictMode>
    <FullCalendarComponent
      args={{
        events: [],
        view: "week",
        height: 600,
        headerToolbar: {
          left: "prev,next today",
          center: "title",
          right: "week,month",
        },
      }}
    />
  </React.StrictMode>
);
