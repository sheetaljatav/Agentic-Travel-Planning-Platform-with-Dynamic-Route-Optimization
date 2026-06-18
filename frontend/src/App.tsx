import { useState } from "react";
import PlanForm from "./components/PlanForm";
import ItineraryTimeline from "./components/ItineraryTimeline";
import BudgetSummary from "./components/BudgetSummary";
import AgentRuns from "./components/AgentRuns";
import { createPlan, DEMO_MODE } from "./api/client";
import { money } from "./format";
import type { Itinerary } from "./types";

export default function App() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [itinerary, setItinerary] = useState<Itinerary | null>(null);

  async function handleSubmit(query: string) {
    setLoading(true);
    setError(null);
    try {
      setItinerary(await createPlan(query, "demo-user"));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="hero">
        <h1>Agentic Travel Planner</h1>
        <p>
          Five LangGraph agents — Planner, Places, Routing, Budget, Booking —
          decompose your request, optimize the route, and price the trip.
        </p>
      </header>

      <PlanForm onSubmit={handleSubmit} loading={loading} />

      {DEMO_MODE && (
        <div className="demo-note">
          Demo mode — showing a pre-generated itinerary for the example query.
          Deploy the backend and set <code>VITE_API_URL</code> for live planning of
          any query.
        </div>
      )}

      {error && <div className="error">{error}</div>}

      {loading && !itinerary && (
        <div className="loading">Agents are planning your trip…</div>
      )}

      {itinerary && (
        <main className="result">
          <p className="summary">{itinerary.summary}</p>

          <div className="grid">
            <div className="col-main">
              <ItineraryTimeline days={itinerary.days} />
            </div>
            <aside className="col-side">
              <BudgetSummary
                budget={itinerary.budget}
                cap={itinerary.request.budget_cap}
                withinBudget={itinerary.within_budget}
              />

              <section className="bookings">
                <h3>Booking suggestions</h3>
                <ul>
                  {itinerary.bookings.map((b, i) => (
                    <li key={i}>
                      <a href={b.url ?? "#"} target="_blank" rel="noreferrer">
                        {b.title}
                      </a>
                      <span className="provider">{b.provider}</span>
                      {b.price != null && (
                        <span className="price">
                          {money(b.price, b.currency ?? "INR")}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              </section>
            </aside>
          </div>

          <AgentRuns runs={itinerary.agent_runs} />
        </main>
      )}

      <footer className="foot">
        Live, free data — OpenStreetMap · OpenRouteService · OpenTripMap ·
        Open-Meteo · Wikipedia. Google Maps used automatically when a key is set.
      </footer>
    </div>
  );
}
