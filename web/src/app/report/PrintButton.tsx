"use client";

export function PrintButton() {
  return (
    <button type="button" onClick={() => window.print()} className="text-sm px-3 py-1.5 border border-hairline rounded text-ink2 hover:text-ink" data-testid="print">
      Print the briefing
    </button>
  );
}
