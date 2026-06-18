import type { Itinerary } from "../types";

// In dev, requests go through Vite's proxy (empty base). In prod, set VITE_API_URL
// to the deployed backend. With VITE_DEMO=1 (e.g. the GitHub Pages build) the app
// serves a bundled, pre-generated itinerary so the demo works with no backend.
const API_BASE = import.meta.env.VITE_API_URL ?? "";
export const DEMO_MODE = import.meta.env.VITE_DEMO === "1";

async function loadSample(): Promise<Itinerary> {
  const resp = await fetch(`${import.meta.env.BASE_URL}sample-itinerary.json`);
  if (!resp.ok) throw new Error("Demo data unavailable");
  return resp.json();
}

export async function createPlan(
  query: string,
  userId?: string,
): Promise<Itinerary> {
  if (!DEMO_MODE) {
    try {
      const resp = await fetch(`${API_BASE}/api/plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, user_id: userId || null }),
      });
      if (resp.ok) return resp.json();
      if (resp.status !== 404) {
        const detail = await resp.json().catch(() => ({}));
        throw new Error(detail.detail || `Request failed (${resp.status})`);
      }
    } catch (err) {
      if (err instanceof Error && err.message.startsWith("Request failed")) throw err;
      // network error / no backend -> fall back to bundled demo
    }
  }
  return loadSample();
}
