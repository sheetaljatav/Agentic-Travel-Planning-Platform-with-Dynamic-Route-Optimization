import type { BudgetBreakdown } from "../types";
import { money } from "../format";

const LABELS: Record<string, string> = {
  intercity_transport: "Intercity transport",
  lodging: "Lodging",
  local_transport: "Local transport",
  attractions: "Attractions",
  food: "Food",
  buffer: "Contingency (10%)",
};

interface Props {
  budget: BudgetBreakdown;
  cap: number;
  withinBudget: boolean;
}

export default function BudgetSummary({ budget, cap, withinBudget }: Props) {
  const lines = Object.keys(LABELS).map((key) => ({
    key,
    label: LABELS[key],
    value: (budget as unknown as Record<string, number>)[key],
    source: budget.sources[key],
  }));
  const max = Math.max(...lines.map((l) => l.value), 1);

  return (
    <section className="budget">
      <div className="budget-head">
        <h3>Budget</h3>
        <span className={`badge ${withinBudget ? "ok" : "over"}`}>
          {withinBudget ? "Within budget" : "Over budget"}
        </span>
      </div>
      <ul className="budget-lines">
        {lines.map((l) => (
          <li key={l.key}>
            <span className="bl-label">
              {l.label}
              {l.source && <em className={`tag ${l.source}`}>{l.source}</em>}
            </span>
            <span className="bl-bar">
              <span style={{ width: `${(l.value / max) * 100}%` }} />
            </span>
            <span className="bl-value">{money(l.value, budget.currency)}</span>
          </li>
        ))}
      </ul>
      <div className="budget-total">
        <span>Total</span>
        <strong>{money(budget.total, budget.currency)}</strong>
        <span className="cap">of {money(cap, budget.currency)} cap</span>
      </div>
    </section>
  );
}
