import { useEffect, useState, type ReactNode } from "react";

type Headline = {
  point: string;
  budget: string;
  you_could_keep?: string;
  is_estimate: boolean;
};

export function App() {
  const [demo, setDemo] = useState(true);
  const [headline, setHeadline] = useState<Headline | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/v1/meta")
      .then((r) => r.json())
      .then((m) => setDemo(!!m.demo))
      .catch(() => {});
  }, []);

  async function plan() {
    setError(null);
    const res = await fetch("/v1/plans", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        destination: "chicago",
        start_date: "2026-12-05",
        days: 1,
        budget: "150",
        firmness: "wiggle",
        party: { adults: 2 },
        interests: ["food", "architecture"],
      }),
    });
    if (!res.ok) {
      setError(await res.text());
      return;
    }
    const data = await res.json();
    setHeadline(data.headline);
  }

  return (
    <main className="app">
      <header>
        <h1>VOYA</h1>
        <p>Trips that fit your budget</p>
      </header>
      {demo && <div className="banner">Demo prices</div>}
      <section>
        <h2>Where, when, and how much?</h2>
        <p className="hint">Chicago · Dec 5 · $150 for 2 · wiggle room</p>
        <button type="button" onClick={() => void plan()}>
          Plan
        </button>
        {error && <p className="error">{error}</p>}
        {headline && (
          <motionlessReveal>
            <p className="total">
              est. ${headline.point} · budget ${headline.budget}
            </p>
            {headline.you_could_keep && (
              <p>You could keep about ${headline.you_could_keep}</p>
            )}
          </motionlessReveal>
        )}
      </section>
    </main>
  );
}

function motionlessReveal({ children }: { children: ReactNode }) {
  return <div className="reveal">{children}</div>;
}
