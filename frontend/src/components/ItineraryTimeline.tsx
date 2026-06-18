import type { ItineraryDay } from "../types";
import { minutes } from "../format";

export default function ItineraryTimeline({ days }: { days: ItineraryDay[] }) {
  return (
    <section className="timeline">
      {days.map((day) => (
        <div className="day-card" key={day.day}>
          <div className="day-head">
            <span className="day-badge">Day {day.day}</span>
            {day.weather && (
              <span className="weather">
                {day.weather.summary}
                {day.weather.temp_max_c != null && (
                  <em>
                    {Math.round(day.weather.temp_min_c ?? 0)}°–
                    {Math.round(day.weather.temp_max_c)}°C
                  </em>
                )}
              </span>
            )}
            <span className="travel">🚗 {minutes(day.travel_time_min)} travel</span>
          </div>
          <ol className="stops">
            {day.stops.length === 0 && <li className="muted">Free day / buffer</li>}
            {day.stops.map((s, i) => (
              <li key={i}>
                <span className="stop-name">{s.name}</span>
                <span className="stop-cat">{s.category}</span>
              </li>
            ))}
          </ol>
        </div>
      ))}
    </section>
  );
}
