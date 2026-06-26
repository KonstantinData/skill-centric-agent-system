"use client";

import { useEffect, useMemo, useState } from "react";
import { Plus, Printer, RotateCcw, Save, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Field, Label, Textarea } from "@/components/ui/form";
import { Panel } from "@/components/ui/panel";

type InvoiceItem = {
  id: string;
  supplier: string;
  quantity: string;
  description: string;
  totalPrice: string;
};

type InvoiceDraft = {
  customerName: string;
  customerAddress: string;
  customerNumber: string;
  invoiceNumber: string;
  invoiceDate: string;
  customerVatRate: string;
  downPayments: string;
  notes: string;
  items: InvoiceItem[];
};

const STORAGE_KEY = "dkh.invoice.draft.v1";

type InvoiceFormProps = {
  initialDraft?: Partial<Omit<InvoiceDraft, "items">> & {
    items?: Array<Partial<Omit<InvoiceItem, "id">>>;
  };
  customerNumberReadOnly?: boolean;
  customerVatReadOnly?: boolean;
  storageKey?: string;
};

function newItem(initialItem?: Partial<Omit<InvoiceItem, "id">>): InvoiceItem {
  return {
    id: crypto.randomUUID(),
    supplier: initialItem?.supplier ?? "",
    quantity: initialItem?.quantity ?? "",
    description: initialItem?.description ?? "",
    totalPrice: initialItem?.totalPrice ?? "",
  };
}

function todayValue() {
  return new Date().toISOString().slice(0, 10);
}

function createInitialDraft(initialDraft?: InvoiceFormProps["initialDraft"]): InvoiceDraft {
  return {
    customerName: "",
    customerAddress: "",
    customerNumber: "",
    invoiceNumber: "",
    invoiceDate: todayValue(),
    customerVatRate: "19",
    downPayments: "",
    notes: "",
    ...initialDraft,
    items: initialDraft?.items?.length
      ? initialDraft.items.map((item) => newItem(item))
      : [newItem(), newItem(), newItem()],
  };
}

function parseMoney(value: string) {
  const normalized = value.replace(/[^\d,.-]/g, "").replace(/\./g, "").replace(",", ".");
  const parsed = Number.parseFloat(normalized);
  return Number.isFinite(parsed) ? parsed : 0;
}

function parsePercent(value: string) {
  const normalized = value.replace(/[^\d,.-]/g, "").replace(",", ".");
  const parsed = Number.parseFloat(normalized);
  return Number.isFinite(parsed) ? parsed : 0;
}

function roundMoney(value: number) {
  return Math.round((value + Number.EPSILON) * 100) / 100;
}

function formatMoney(value: number) {
  return new Intl.NumberFormat("de-DE", {
    style: "currency",
    currency: "EUR",
  })
    .format(value)
    .replace(/\u00a0/g, " ");
}

function formatMoneyInput(value: string) {
  const parsed = parseMoney(value);
  return parsed ? formatMoney(parsed) : "";
}

function formatPercentInput(value: string) {
  const parsed = parsePercent(value);
  return Number.isFinite(parsed) ? String(parsed).replace(".", ",") : "0";
}

function formatDateForPrint(value: string) {
  if (!value) return "";

  const parsed = new Date(`${value}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) return value;

  return [
    String(parsed.getDate()).padStart(2, "0"),
    String(parsed.getMonth() + 1).padStart(2, "0"),
    parsed.getFullYear(),
  ].join(".");
}

function nonEmptyLines(...values: string[]) {
  return values
    .flatMap((value) => value.split(/\r?\n/))
    .map((value) => value.trim())
    .filter(Boolean);
}

export function InvoiceForm({
  customerNumberReadOnly = true,
  customerVatReadOnly = true,
  initialDraft,
  storageKey = STORAGE_KEY,
}: InvoiceFormProps) {
  const [draft, setDraft] = useState<InvoiceDraft>(() => createInitialDraft(initialDraft));
  const [draftStatus, setDraftStatus] = useState("Noch nicht gespeichert");

  useEffect(() => {
    const saved = window.localStorage.getItem(storageKey);
    if (!saved) return;

    try {
      const parsed = JSON.parse(saved) as InvoiceDraft;
      const mergedDraft = {
        ...createInitialDraft(initialDraft),
        ...parsed,
        customerNumber: initialDraft?.customerNumber ?? parsed.customerNumber ?? "",
        customerVatRate: initialDraft?.customerVatRate ?? parsed.customerVatRate ?? "19",
        items: parsed.items?.length ? parsed.items : [newItem()],
      };
      setDraft(mergedDraft);
      setDraftStatus("Gespeicherter Entwurf geladen");
    } catch {
      setDraftStatus("Gespeicherter Entwurf konnte nicht geladen werden");
    }
  }, [initialDraft, storageKey]);

  const itemTotal = useMemo(
    () => draft.items.reduce((sum, item) => sum + parseMoney(item.totalPrice), 0),
    [draft.items],
  );
  const customerVatRate = parsePercent(draft.customerVatRate);
  const includedVat =
    customerVatRate > 0
      ? roundMoney(itemTotal - itemTotal / (1 + customerVatRate / 100))
      : 0;
  const downPayments = parseMoney(draft.downPayments);
  const remainingAmount = roundMoney(itemTotal - downPayments);
  const discountAmount = roundMoney(itemTotal * 0.02);
  const discountNote = itemTotal ? formatMoney(discountAmount) : "";

  function updateDraft<K extends keyof InvoiceDraft>(key: K, value: InvoiceDraft[K]) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  function updateItem(id: string, patch: Partial<InvoiceItem>) {
    setDraft((current) => ({
      ...current,
      items: current.items.map((item) =>
        item.id === id ? { ...item, ...patch } : item,
      ),
    }));
  }

  function addItem() {
    setDraft((current) => ({ ...current, items: [...current.items, newItem()] }));
  }

  function removeItem(id: string) {
    setDraft((current) => ({
      ...current,
      items:
        current.items.length > 1
          ? current.items.filter((item) => item.id !== id)
          : current.items,
    }));
  }

  function formatItemMoneyField(id: string) {
    setDraft((current) => ({
      ...current,
      items: current.items.map((item) =>
        item.id === id
          ? { ...item, totalPrice: formatMoneyInput(item.totalPrice) }
          : item,
      ),
    }));
  }

  function saveDraft() {
    window.localStorage.setItem(storageKey, JSON.stringify(draft));
    setDraftStatus(`Entwurf gespeichert: ${new Date().toLocaleTimeString("de-DE")}`);
  }

  function resetDraft() {
    window.localStorage.removeItem(storageKey);
    setDraft(createInitialDraft(initialDraft));
    setDraftStatus("Entwurf zurückgesetzt");
  }

  return (
    <>
      <form
        className="invoice-screen grid gap-4"
        onSubmit={(event) => event.preventDefault()}
      >
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_280px]">
          <div className="grid gap-4">
            <Panel>
              <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="section-title">Kunde und Rechnung</h2>
                  <p className="mt-1 text-sm text-[var(--muted)]">
                    Entspricht Adressfeld, Rechnungsnummer, Kunden-Nr. und Datum im Formular.
                  </p>
                </div>
                <span className="badge">{draftStatus}</span>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <Label label="Herr/Frau/Firma">
                  <Textarea
                    name="customer_name"
                    value={draft.customerName}
                    onChange={(event) => updateDraft("customerName", event.target.value)}
                    placeholder="Name oder Firma"
                  />
                </Label>
                <Label label="Rechnungsanschrift">
                  <Textarea
                    name="customer_address"
                    value={draft.customerAddress}
                    onChange={(event) => updateDraft("customerAddress", event.target.value)}
                    placeholder="Straße, PLZ, Ort"
                  />
                </Label>
                <Label label="Rechnungs-Nr.">
                  <Field
                    name="invoice_number"
                    value={draft.invoiceNumber}
                    onChange={(event) => updateDraft("invoiceNumber", event.target.value)}
                  />
                </Label>
                <Label label="Kunden-Nr.">
                  <Field
                    name="customer_number"
                    value={draft.customerNumber}
                    onChange={(event) => updateDraft("customerNumber", event.target.value)}
                    readOnly={customerNumberReadOnly}
                  />
                </Label>
                <Label label="Rechnungsdatum">
                  <Field
                    name="invoice_date"
                    type="date"
                    value={draft.invoiceDate}
                    onChange={(event) => updateDraft("invoiceDate", event.target.value)}
                  />
                </Label>
                <Label label="MwSt. laut Kundenstammdaten">
                  <Field
                    name="customer_vat_rate"
                    inputMode="decimal"
                    value={draft.customerVatRate}
                    onChange={(event) => updateDraft("customerVatRate", event.target.value)}
                    onBlur={() =>
                      updateDraft("customerVatRate", formatPercentInput(draft.customerVatRate))
                    }
                    readOnly={customerVatReadOnly}
                  />
                </Label>
              </div>
            </Panel>

            <Panel>
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="section-title">Positionen</h2>
                  <p className="mt-1 text-sm text-[var(--muted)]">
                    Spalten aus dem Formular: Werk, Stk., Bezeichnung und Gesamtpreis.
                  </p>
                </div>
                <Button type="button" variant="secondary" onClick={addItem}>
                  <Plus size={16} aria-hidden />
                  Position
                </Button>
              </div>
              <div className="grid gap-3">
                {draft.items.map((item, index) => (
                  <article
                    key={item.id}
                    className="invoice-position-row grid gap-3 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-3"
                  >
                    <Label label={`Werk ${index + 1}`}>
                      <Field
                        name={`items.${index}.supplier`}
                        value={item.supplier}
                        onChange={(event) =>
                          updateItem(item.id, { supplier: event.target.value })
                        }
                      />
                    </Label>
                    <Label label="Stk.">
                      <Field
                        name={`items.${index}.quantity`}
                        className="invoice-quantity-field"
                        inputMode="decimal"
                        value={item.quantity}
                        onChange={(event) =>
                          updateItem(item.id, { quantity: event.target.value })
                        }
                      />
                    </Label>
                    <Label label="Bezeichnung">
                      <Textarea
                        name={`items.${index}.description`}
                        className="invoice-description-field min-h-10"
                        value={item.description}
                        onChange={(event) =>
                          updateItem(item.id, { description: event.target.value })
                        }
                      />
                    </Label>
                    <Label label="Gesamtpreis">
                      <Field
                        name={`items.${index}.total_price`}
                        inputMode="decimal"
                        value={item.totalPrice}
                        onChange={(event) =>
                          updateItem(item.id, { totalPrice: event.target.value })
                        }
                        onBlur={() => formatItemMoneyField(item.id)}
                        placeholder="15.555,55 EUR"
                      />
                    </Label>
                    <button
                      type="button"
                      className="btn btn-secondary invoice-position-delete aspect-square p-0"
                      onClick={() => removeItem(item.id)}
                      aria-label={`Position ${index + 1} entfernen`}
                      title="Position entfernen"
                    >
                      <Trash2 size={16} aria-hidden />
                    </button>
                  </article>
                ))}
              </div>
            </Panel>
          </div>

          <div className="grid content-start gap-4">
            <Panel>
              <h2 className="section-title">Beträge</h2>
              <div className="mt-4 grid gap-3">
                <Label label="Rechnungsendbetrag inklusive MwSt.">
                  <Field name="invoice_gross" value={formatMoney(itemTotal)} readOnly />
                </Label>
                <Label label="Enthaltene MwSt.">
                  <Field name="included_vat" value={formatMoney(includedVat)} readOnly />
                </Label>
                <Label label="Anzahlungen">
                  <Field
                    name="down_payments"
                    inputMode="decimal"
                    value={draft.downPayments}
                    onChange={(event) => updateDraft("downPayments", event.target.value)}
                    onBlur={() =>
                      updateDraft("downPayments", formatMoneyInput(draft.downPayments))
                    }
                    placeholder="0,00 EUR"
                  />
                </Label>
                <Label label="Restbetrag">
                  <Field
                    name="remaining_amount"
                    value={formatMoney(remainingAmount)}
                    readOnly
                  />
                </Label>
                <Label label="Skonto-Hinweis">
                  <Field
                    name="discount_note"
                    value={discountNote}
                    readOnly
                    aria-label="2 Prozent Skonto aus Rechnungsendbetrag"
                  />
                </Label>
                <Label label="Interne Notiz">
                  <Textarea
                    name="notes"
                    value={draft.notes}
                    onChange={(event) => updateDraft("notes", event.target.value)}
                  />
                </Label>
              </div>
            </Panel>

            <Panel>
              <div className="grid gap-3">
                <Button type="button" onClick={saveDraft}>
                  <Save size={16} aria-hidden />
                  Entwurf speichern
                </Button>
                <Button type="button" variant="secondary" onClick={() => window.print()}>
                  <Printer size={16} aria-hidden />
                  Drucken
                </Button>
                <Button type="button" variant="danger" onClick={resetDraft}>
                  <RotateCcw size={16} aria-hidden />
                  Zurücksetzen
                </Button>
              </div>
            </Panel>
          </div>
        </div>
      </form>

      <InvoicePrintOverlay
        draft={draft}
        discountNote={discountNote}
        includedVat={includedVat}
        invoiceGross={itemTotal}
        remainingAmount={remainingAmount}
      />
    </>
  );
}

function InvoicePrintOverlay({
  draft,
  discountNote,
  includedVat,
  invoiceGross,
  remainingAmount,
}: {
  draft: InvoiceDraft;
  discountNote: string;
  includedVat: number;
  invoiceGross: number;
  remainingAmount: number;
}) {
  const customerLines = nonEmptyLines(draft.customerName, draft.customerAddress);
  const firstPrintItems = draft.items.slice(0, 23);
  const downPayments = parseMoney(draft.downPayments);

  return (
    <div className="invoice-print" aria-hidden="true">
      <section className="invoice-print-page">
        <div className="invoice-print-address-block invoice-print-customer-address">
          {customerLines.map((line, index) => (
            <div key={`${line}-${index}`}>{line}</div>
          ))}
        </div>

        <div className="invoice-print-field invoice-print-number">{draft.invoiceNumber}</div>
        <div className="invoice-print-field invoice-print-customer-number">
          {draft.customerNumber}
        </div>
        <div className="invoice-print-field invoice-print-date">
          {formatDateForPrint(draft.invoiceDate)}
        </div>

        <div className="invoice-print-items">
          {firstPrintItems.map((item, index) => (
            <div
              className={`invoice-print-item-row invoice-print-item-row-${index + 1}`}
              key={item.id}
            >
              <div className="invoice-print-item-supplier">{item.supplier}</div>
              <div className="invoice-print-item-quantity">{item.quantity}</div>
              <div className="invoice-print-item-description">{item.description}</div>
              <div className="invoice-print-item-price">
                {item.totalPrice ? formatMoneyInput(item.totalPrice) : ""}
              </div>
            </div>
          ))}
        </div>

        <div className="invoice-print-money invoice-print-gross">{formatMoney(invoiceGross)}</div>
        <div className="invoice-print-money invoice-print-vat">{formatMoney(includedVat)}</div>
        <div className="invoice-print-money invoice-print-down-payments">
          {downPayments ? formatMoney(downPayments) : ""}
        </div>
        <div className="invoice-print-money invoice-print-remaining">
          {formatMoney(remainingAmount)}
        </div>
        <div className="invoice-print-money invoice-print-discount">
          {discountNote}
        </div>
      </section>
    </div>
  );
}
