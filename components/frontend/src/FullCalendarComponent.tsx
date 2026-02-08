import React, { useEffect, useMemo } from "react";
import { Calendar, dateFnsLocalizer, View } from "react-big-calendar";
import { format, parse, startOfWeek, getDay } from "date-fns";
import { enUS } from "date-fns/locale";
import { Streamlit, withStreamlitConnection } from "streamlit-component-lib";
import "react-big-calendar/lib/css/react-big-calendar.css";

interface Event {
  id: string;
  title: string;
  start: string;
  end: string;
  resourceId?: string;
  backgroundColor?: string;
  borderColor?: string;
  extendedProps?: Record<string, unknown>;
}

export interface FullCalendarComponentProps {
  args?: {
    events: Event[];
    resources?: { id: string; title: string }[];
    view: string;
    initialDate?: string;
    height: number;
    headerToolbar: { left: string; center: string; right: string };
  };
}

const VIEW_MAP: Record<string, View> = {
  resourceTimelineWeek: "week",
  resourceTimelineMonth: "month",
  resourceTimelineDay: "day",
  resourceTimelineYear: "month",
  dayGridMonth: "month",
  timeGridWeek: "week",
  timeGridDay: "day",
  month: "month",
  week: "week",
  day: "day",
  agenda: "agenda",
};

const localizer = dateFnsLocalizer({
  format,
  parse,
  startOfWeek,
  getDay,
  locales: { "en-US": enUS },
});

const DEFAULT_ARGS: NonNullable<FullCalendarComponentProps["args"]> = {
  events: [],
  view: "week",
  height: 600,
  headerToolbar: {
    left: "prev,next today",
    center: "title",
    right: "week,month",
  },
};

const FullCalendarComponent: React.FC<FullCalendarComponentProps> = ({
  args: argsProp,
}) => {
  const args = argsProp ?? DEFAULT_ARGS;
  const view = VIEW_MAP[args.view] ?? "week";
  const date = args.initialDate ? new Date(args.initialDate) : undefined;

  const events = useMemo(
    () =>
      args.events.map((e) => ({
        ...e,
        start: new Date(e.start),
        end: new Date(e.end),
        resourceId: e.resourceId,
      })),
    [args.events]
  );

  useEffect(() => {
    Streamlit.setFrameHeight(args.height);
  }, [args.height]);

  const handleSelectEvent = (event: {
    id?: string;
    title?: string;
    start?: Date;
    end?: Date;
    resourceId?: string;
    extendedProps?: Record<string, unknown>;
  }) => {
    Streamlit.setComponentValue({
      type: "eventClick",
      event: {
        id: event.id ?? "",
        title: event.title ?? "",
        start: event.start?.toISOString(),
        end: event.end?.toISOString(),
        resourceId: event.resourceId,
        extendedProps: event.extendedProps,
      },
    });
  };

  const eventPropGetter = (event: {
    backgroundColor?: string;
    borderColor?: string;
  }) => ({
    style: {
      backgroundColor: event.backgroundColor ?? "#3498db",
      borderColor: event.borderColor ?? event.backgroundColor ?? "#3498db",
      borderRadius: "4px",
    },
  });

  return (
    <div style={{ height: args.height, width: "100%" }}>
      <Calendar
        localizer={localizer}
        events={events}
        view={view}
        date={date}
        onSelectEvent={handleSelectEvent}
        eventPropGetter={eventPropGetter}
        startAccessor="start"
        endAccessor="end"
        titleAccessor="title"
        style={{ height: args.height - 8 }}
        views={["month", "week", "day", "agenda"]}
      />
    </div>
  );
};

const ConnectedCalendar = withStreamlitConnection(FullCalendarComponent);
export default ConnectedCalendar as React.FC<FullCalendarComponentProps>;
