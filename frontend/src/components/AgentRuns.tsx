import type { AgentRun } from "../types";

// Compact orchestration summary: which agent ran, its status and latency.
export default function AgentRuns({ runs }: { runs: AgentRun[] }) {
  return (
    <details className="agents">
      <summary>Agent orchestration ({runs.length} steps)</summary>
      <ul>
        {runs.map((r, i) => (
          <li key={i}>
            <span className={`dot ${r.status}`} />
            <span className="agent-name">{r.agent}</span>
            <span className="agent-detail">{r.detail}</span>
            <span className="agent-ms">{Math.round(r.latency_ms)} ms</span>
          </li>
        ))}
      </ul>
    </details>
  );
}
