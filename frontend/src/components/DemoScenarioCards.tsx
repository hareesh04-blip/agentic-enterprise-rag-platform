interface DemoScenario {
  id: string;
  title: string;
  description: string;
  question: string;
}

const DEMO_SCENARIOS: DemoScenario[] = [
  {
    id: "qr-auth",
    title: "QR Authentication Demo",
    description: "Credentials and auth expectations for QR generation.",
    question: "What authentication is required for the QR generation API?",
  },
  {
    id: "qr-request",
    title: "QR Request Structure Demo",
    description: "Request parameters and structure for QR generation.",
    question: "What are the request parameters for the QR generation API?",
  },
  {
    id: "qr-errors",
    title: "QR Error Code Demo",
    description: "Documented failures and error codes.",
    question: "What are the error codes for the QR generation API?",
  },
  {
    id: "qr-response",
    title: "QR Response Fields Demo",
    description: "Success payload fields returned by the API.",
    question: "What are the success response fields for the QR generation API?",
  },
];

interface DemoScenarioCardsProps {
  disabled?: boolean;
  onSelect: (question: string) => void | Promise<void>;
}

export function DemoScenarioCards({ disabled, onSelect }: DemoScenarioCardsProps) {
  return (
    <div className="rounded-lg border border-dashed border-indigo-200 bg-indigo-50/40 p-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-indigo-900">Demo scenarios</p>
      <p className="mt-1 text-[11px] text-indigo-900/80">
        Click a card to fill the question and run the query against the selected KB.
      </p>
      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        {DEMO_SCENARIOS.map((s) => (
          <button
            key={s.id}
            type="button"
            disabled={disabled}
            onClick={() => void onSelect(s.question)}
            className="rounded-md border border-indigo-200 bg-white p-3 text-left text-xs shadow-sm transition hover:border-indigo-400 hover:bg-indigo-50/60 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <p className="font-semibold text-indigo-950">{s.title}</p>
            <p className="mt-1 text-[11px] text-slate-600">{s.description}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
