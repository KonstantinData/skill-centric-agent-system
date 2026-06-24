import Image from "next/image";

export function PageHero({
  eyebrow = "das küchenhaus",
  title,
  subtitle,
}: {
  eyebrow?: string | null;
  title: string;
  subtitle: string;
}) {
  return (
    <section className="relative isolate overflow-hidden rounded-lg border border-[var(--border)] bg-[#102007] px-5 py-8 text-white shadow-[var(--shadow)]">
      <Image
        src="/crm-hero.jpg"
        alt=""
        fill
        priority
        sizes="(max-width: 980px) 100vw, calc(100vw - 320px)"
        className="absolute inset-0 -z-10 object-cover opacity-38"
      />
      <div className="max-w-3xl">
        {eyebrow ? (
          <p className="mb-2 text-sm font-bold uppercase tracking-normal text-[#d8f0c8]">
            {eyebrow}
          </p>
        ) : null}
        <h1 className="text-3xl font-bold leading-tight md:text-4xl">{title}</h1>
        <p className="mt-2 max-w-2xl text-base text-[#eef7e8]">{subtitle}</p>
      </div>
    </section>
  );
}
