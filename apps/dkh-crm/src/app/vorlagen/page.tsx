"use client";

import { FileText, X } from "lucide-react";
import { useState } from "react";
import { PageHero } from "@/components/chrome/page-hero";
import { InvoiceForm } from "@/components/invoice/invoice-form";
import { PurchaseContractForm } from "@/components/purchase-contract/purchase-contract-form";
import { Button } from "@/components/ui/button";
import { Panel } from "@/components/ui/panel";

export default function TemplatesPage() {
  const [isPurchaseContractOpen, setIsPurchaseContractOpen] = useState(false);
  const [isInvoiceOpen, setIsInvoiceOpen] = useState(false);

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
            <h2 className="section-title">Vorlagen</h2>
            <p className="mt-1 text-sm text-[var(--muted)]">
              Blanko-Vorlagen ohne Kunden- oder Vorgangsverknüpfung.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              className="grid aspect-square w-36 place-items-center rounded-lg border border-[var(--border)] bg-[var(--surface-soft)] p-4 text-center shadow-sm transition hover:border-[var(--accent)] hover:bg-[var(--surface)]"
              onClick={() => setIsPurchaseContractOpen(true)}
            >
              <span className="grid place-items-center gap-3">
                <FileText size={30} aria-hidden />
                <span className="text-sm font-bold leading-tight">Blanco Kaufvertrag</span>
              </span>
            </button>

            <button
              type="button"
              className="grid aspect-square w-36 place-items-center rounded-lg border border-[var(--border)] bg-[var(--surface-soft)] p-4 text-center shadow-sm transition hover:border-[var(--accent)] hover:bg-[var(--surface)]"
              onClick={() => setIsInvoiceOpen(true)}
            >
              <span className="grid place-items-center gap-3">
                <FileText size={30} aria-hidden />
                <span className="text-sm font-bold leading-tight">Blanco Rechnung</span>
              </span>
            </button>
          </div>
        </div>
      </Panel>

      {isPurchaseContractOpen ? (
        <div
          className="fixed inset-0 z-50 grid place-items-center bg-black/45 p-4"
          role="dialog"
          aria-modal="true"
          aria-label="Blanco Kaufvertrag"
        >
          <section className="flex max-h-[92vh] min-h-0 w-full max-w-[1500px] flex-col overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--background)] shadow-2xl">
            <header className="shrink-0 flex items-center justify-between gap-4 border-b border-[var(--border)] bg-[var(--surface)] px-5 py-4">
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
            <div className="min-h-0 flex-1 overflow-y-auto p-5">
              <PurchaseContractForm
                customerNumberReadOnly={false}
                customerVatReadOnly={false}
                storageKey="dkh.purchase-contract.template.blanco.draft.v1"
              />
            </div>
          </section>
        </div>
      ) : null}

      {isInvoiceOpen ? (
        <div
          className="fixed inset-0 z-50 grid place-items-center bg-black/45 p-4"
          role="dialog"
          aria-modal="true"
          aria-label="Blanco Rechnung"
        >
          <section className="flex max-h-[92vh] min-h-0 w-full max-w-[1500px] flex-col overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--background)] shadow-2xl">
            <header className="flex shrink-0 items-center justify-between gap-4 border-b border-[var(--border)] bg-[var(--surface)] px-5 py-4">
              <div>
                <p className="badge">Vorlage</p>
                <h2 className="mt-2 text-xl font-bold">Blanco Rechnung</h2>
              </div>
              <Button
                type="button"
                variant="secondary"
                onClick={() => setIsInvoiceOpen(false)}
              >
                <X size={16} aria-hidden />
                Schließen
              </Button>
            </header>
            <div className="min-h-0 flex-1 overflow-y-auto p-5">
              <InvoiceForm
                customerNumberReadOnly={false}
                customerVatReadOnly={false}
                storageKey="dkh.invoice.template.blanco.draft.v1"
              />
            </div>
          </section>
        </div>
      ) : null}
    </div>
  );
}
