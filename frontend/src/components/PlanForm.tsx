import { useState } from "react";

const EXAMPLE = "Plan a 4-day Goa trip under ₹25,000 from Bangalore";

interface Props {
  onSubmit: (query: string) => void;
  loading: boolean;
}

export default function PlanForm({ onSubmit, loading }: Props) {
  const [query, setQuery] = useState(EXAMPLE);

  return (
    <form
      className="plan-form"
      onSubmit={(e) => {
        e.preventDefault();
        if (query.trim()) onSubmit(query.trim());
      }}
    >
      <textarea
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder={EXAMPLE}
        rows={2}
        disabled={loading}
      />
      <button type="submit" disabled={loading || !query.trim()}>
        {loading ? "Planning…" : "Plan my trip"}
      </button>
    </form>
  );
}
