import type { SectionHeadingProps } from "./types";

export function SectionHeading({ lead, accent, sub }: Readonly<SectionHeadingProps>) {
  return (
    <div className="mx-auto max-w-3xl space-y-2.5 text-center">
      <h2 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl lg:text-4xl">
        {lead} {accent && <span className="text-brand-text">{accent}</span>}
      </h2>
      <p className="text-sm leading-relaxed text-ink/80 sm:text-base">{sub}</p>
    </div>
  );
}
