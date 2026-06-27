import Image from "next/image";
import type { ComponentType } from "react";
import type { LucideProps } from "lucide-react";

type PageHeroProps = {
  title: string;
  functionText: string;
  icon?: ComponentType<LucideProps>;
};

export function PageHero({ title, functionText, icon: Icon }: PageHeroProps) {
  return (
    <section className="page-hero" aria-labelledby="page-title">
      <Image
        src="/kinderhaus-heuschrecken.jpg"
        alt=""
        fill
        sizes="(max-width: 980px) 100vw, calc(100vw - 256px)"
        className="page-hero-image"
        priority
      />
      <div className="page-hero-shade" />
      <div className="page-hero-content">
        {Icon ? (
          <div className="page-hero-icon">
            <Icon size={20} aria-hidden />
          </div>
        ) : null}
        <div className="min-w-0">
          <h1 id="page-title" className="page-hero-title">
            {title}
          </h1>
          <p className="page-hero-function">{functionText}</p>
        </div>
      </div>
    </section>
  );
}
