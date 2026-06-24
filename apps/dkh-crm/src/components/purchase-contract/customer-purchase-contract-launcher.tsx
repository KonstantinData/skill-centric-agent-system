"use client";

import type { ComponentProps } from "react";
import { useState } from "react";
import { FileText, X } from "lucide-react";
import { PurchaseContractForm } from "@/components/purchase-contract/purchase-contract-form";
import { Button } from "@/components/ui/button";
import { Panel } from "@/components/ui/panel";

type CustomerPurchaseContractLauncherProps = {
  initialDraft: ComponentProps<typeof PurchaseContractForm>["initialDraft"];
  storageKey: string;
};

export function CustomerPurchaseContractLauncher({
  initialDraft,
  storageKey,
}: CustomerPurchaseContractLauncherProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <Panel>
        <div className="grid gap-4">
          <div>
            <h2 className="section-title">Kaufvertrag</h2>
            <p className="mt-1 text-sm text-[var(--muted)]">
              Kundenverknüpfter Kaufvertrag für diesen Vorgang.
            </p>
          </div>

          <button
            type="button"
            className="grid aspect-square w-36 place-items-center rounded-lg border border-[var(--border)] bg-[var(--surface-soft)] p-4 text-center shadow-sm transition hover:border-[var(--accent)] hover:bg-[var(--surface)]"
            onClick={() => setIsOpen(true)}
          >
            <span className="grid place-items-center gap-3">
              <FileText size={30} aria-hidden />
              <span className="text-sm font-bold leading-tight">Kaufvertrag</span>
            </span>
          </button>
        </div>
      </Panel>

      {isOpen ? (
        <div
          className="fixed inset-0 z-50 grid place-items-center bg-black/45 p-4"
          role="dialog"
          aria-modal="true"
          aria-label="Kaufvertrag"
        >
          <section className="flex max-h-[92vh] min-h-0 w-full max-w-[1500px] flex-col overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--background)] shadow-2xl">
            <header className="flex shrink-0 items-center justify-between gap-4 border-b border-[var(--border)] bg-[var(--surface)] px-5 py-4">
              <div>
                <p className="badge">Angebot / Auftrag</p>
                <h2 className="mt-2 text-xl font-bold">Kaufvertrag</h2>
              </div>
              <Button type="button" variant="secondary" onClick={() => setIsOpen(false)}>
                <X size={16} aria-hidden />
                Schließen
              </Button>
            </header>
            <div className="min-h-0 flex-1 overflow-y-auto p-5">
              <PurchaseContractForm initialDraft={initialDraft} storageKey={storageKey} />
            </div>
          </section>
        </div>
      ) : null}
    </>
  );
}
