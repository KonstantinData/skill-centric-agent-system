"use client";

import { FileText, X } from "lucide-react";
import { useState } from "react";
import { PageHero } from "@/components/chrome/page-hero";
import { PurchaseContractForm } from "@/components/purchase-contract/purchase-contract-form";
import { Button } from "@/components/ui/button";
import { Panel } from "@/components/ui/panel";

export default function TemplatesPage() {
  const [isPurchaseContractOpen, setIsPurchaseContractOpen] = useState(false);

  return (
    <div className="content-stack">
      <PageHero
        eyebrow={null}
        title="Vorlagen"
        subtitle="Blanko-Formulare und wiederverwendbare Dokumentvorlagen."
      />

      <Panel>
        <div className="grid gap-4">
          <div>
            <h2 className="section-title">Kaufverträge</h2>
            <p className="mt-1 text-sm text-[var(--muted)]">
              Blanko-Vorlagen ohne Kunden- oder Vorgangsverknüpfung.
            </p>
          </div>

          <button
            type="button"
            className="grid aspect-square w-36 place-items-center rounded-lg border border-[var(--border)] bg-[var(--surface-soft)] p-4 text-center shadow-sm transition hover:border-[var(--accent)] hover:bg-[var(--surface)]"
            onClick={() => setIsPurchaseContractOpen(true)}
          >
            <span className="grid gap-3 place-items-center">
              <FileText size={30} aria-hidden />
              <span className="text-sm font-bold leading-tight">Blanco Kaufvertrag</span>
            </span>
          </button>
        </div>
      </Panel>

      {isPurchaseContractOpen ? (
        <div
          className="fixed inset-0 z-50 grid place-items-center bg-black/45 p-4"
          role="dialog"
          aria-modal="true"
          aria-label="Blanco Kaufvertrag"
        >
          <section className="grid max-h-[92vh] w-full max-w-[1500px] overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--background)] shadow-2xl">
            <header className="flex items-center justify-between gap-4 border-b border-[var(--border)] bg-[var(--surface)] px-5 py-4">
              <div>
                <p className="badge">Vorlage</p>
                <h2 className="mt-2 text-xl font-bold">Blanco Kaufvertrag</h2>
              </div>
              <Button
                type="button"
                variant="secondary"
                onClick={() => setIsPurchaseContractOpen(false)}
              >
                <X size={16} aria-hidden />
                Schließen
              </Button>
            </header>
            <div className="overflow-auto p-5">
              <PurchaseContractForm
                customerNumberReadOnly={false}
                customerVatReadOnly={false}
                storageKey="dkh.purchase-contract.template.blanco.draft.v1"
              />
            </div>
          </section>
        </div>
      ) : null}
    </div>
  );
}
