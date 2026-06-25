"use client";

import { useEffect, useMemo, useState } from "react";
import { Plus, Printer, RotateCcw, Save, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Field, Label, Select, Textarea } from "@/components/ui/form";
import { Panel } from "@/components/ui/panel";

type ContractItem = {
  id: string;
  supplier: string;
  quantity: string;
  description: string;
  totalPrice: string;
};

type ContractDraft = {
  customerName: string;
  customerPhone: string;
  customerAddress: string;
  deliveryAddress: string;
  deliveryPhone: string;
  deliveryMode: "pickup" | "installation";
  deliveryDate: string;
  customerNumber: string;
  contractDate: string;
  notes: string;
  invoiceGross: string;
  customerVatRate: string;
  paymentOnOrderPercent: string;
  paymentBeforeDeliveryPercent: string;
  restPaymentPercent: string;
  dealerSignatureNote: string;
  customerSignatureNote: string;
  items: ContractItem[];
};

const STORAGE_KEY = "dkh.purchase-contract.draft.v1";

type PurchaseContractFormProps = {
  initialDraft?: Partial<Omit<ContractDraft, "items">> & {
    items?: Array<Partial<Omit<ContractItem, "id">>>;
  };
  customerNumberReadOnly?: boolean;
  customerVatReadOnly?: boolean;
  storageKey?: string;
};

function newItem(initialItem?: Partial<Omit<ContractItem, "id">>): ContractItem {
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

function createInitialDraft(initialDraft?: PurchaseContractFormProps["initialDraft"]): ContractDraft {
  return {
    customerName: "",
    customerPhone: "",
    customerAddress: "",
    deliveryAddress: "",
    deliveryPhone: "",
    deliveryMode: "installation",
    deliveryDate: "",
    customerNumber: "",
    contractDate: todayValue(),
    notes: "",
    invoiceGross: "",
    customerVatRate: "19",
    paymentOnOrderPercent: "30",
    paymentBeforeDeliveryPercent: "60",
    restPaymentPercent: "10",
    dealerSignatureNote: "",
    customerSignatureNote: "",
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

function clampPercent(value: number) {
  return Math.min(100, Math.max(0, value));
}

function roundPercent(value: number) {
  return Math.round((value + Number.EPSILON) * 100) / 100;
}

function formatPercentValue(value: number) {
  return String(roundPercent(value)).replace(".", ",");
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

function isoWeekStart(year: number, week: number) {
  const fourthOfJanuary = new Date(Date.UTC(year, 0, 4));
  const day = fourthOfJanuary.getUTCDay() || 7;
  const firstMonday = new Date(fourthOfJanuary);
  firstMonday.setUTCDate(fourthOfJanuary.getUTCDate() - day + 1);
  firstMonday.setUTCDate(firstMonday.getUTCDate() + (week - 1) * 7);
  return firstMonday.toISOString().slice(0, 10);
}

function weekValueFromDate(value: string) {
  if (!value) return "";

  const date = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) return "";

  const day = date.getUTCDay() || 7;
  date.setUTCDate(date.getUTCDate() + 4 - day);
  const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
  const week = Math.ceil(((date.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);

  return `${date.getUTCFullYear()}-W${String(week).padStart(2, "0")}`;
}

function dateValueFromWeek(value: string) {
  const match = /^(\d{4})-W(\d{2})$/.exec(value);
  if (!match) return "";

  return isoWeekStart(Number(match[1]), Number(match[2]));
}

function nonEmptyLines(...values: string[]) {
  return values
    .flatMap((value) => value.split(/\r?\n/))
    .map((value) => value.trim())
    .filter(Boolean);
}

export function PurchaseContractForm({
  customerNumberReadOnly = true,
  customerVatReadOnly = true,
  initialDraft,
  storageKey = STORAGE_KEY,
}: PurchaseContractFormProps) {
  const [draft, setDraft] = useState<ContractDraft>(() => createInitialDraft(initialDraft));
  const [draftStatus, setDraftStatus] = useState("Noch nicht gespeichert");
  const [useCustomerAddressForDelivery, setUseCustomerAddressForDelivery] = useState(false);
  const [useCustomerPhoneForDelivery, setUseCustomerPhoneForDelivery] = useState(false);

  useEffect(() => {
    const saved = window.localStorage.getItem(storageKey);
    if (!saved) return;

    try {
      const parsed = JSON.parse(saved) as ContractDraft;
      const mergedDraft = {
        ...createInitialDraft(initialDraft),
        ...parsed,
        customerNumber: initialDraft?.customerNumber ?? parsed.customerNumber ?? "",
        customerVatRate: initialDraft?.customerVatRate ?? parsed.customerVatRate ?? "19",
        items: parsed.items?.length ? parsed.items : [newItem()],
      };
      setDraft(mergedDraft);
      setUseCustomerAddressForDelivery(
        Boolean(mergedDraft.deliveryAddress && mergedDraft.deliveryAddress === mergedDraft.customerAddress),
      );
      setUseCustomerPhoneForDelivery(
        Boolean(mergedDraft.deliveryPhone && mergedDraft.deliveryPhone === mergedDraft.customerPhone),
      );
      setDraftStatus("Gespeicherter Entwurf geladen");
    } catch {
      setDraftStatus("Gespeicherter Entwurf konnte nicht geladen werden");
    }
  }, [initialDraft, storageKey]);

  const itemTotal = useMemo(
    () => draft.items.reduce((sum, item) => sum + parseMoney(item.totalPrice), 0),
    [draft.items],
  );
  const invoiceGross = parseMoney(draft.invoiceGross) || itemTotal;
  const customerVatRate = parsePercent(draft.customerVatRate);
  const includedVat =
    customerVatRate > 0
      ? roundMoney(invoiceGross - invoiceGross / (1 + customerVatRate / 100))
      : 0;
  const paymentOnOrderPercent = clampPercent(parsePercent(draft.paymentOnOrderPercent));
  const paymentBeforeDeliveryPercent = clampPercent(parsePercent(draft.paymentBeforeDeliveryPercent));
  const restPaymentPercent = clampPercent(
    roundPercent(100 - paymentOnOrderPercent - paymentBeforeDeliveryPercent),
  );
  const paymentOnOrder = roundMoney(invoiceGross * (paymentOnOrderPercent / 100));
  const paymentBeforeDelivery = roundMoney(invoiceGross * (paymentBeforeDeliveryPercent / 100));
  const restPayment = roundMoney(invoiceGross * (restPaymentPercent / 100));
  const paymentTotal = paymentOnOrder + paymentBeforeDelivery + restPayment;
  const openAmount = invoiceGross - paymentTotal;
  const deliveryWeek = weekValueFromDate(draft.deliveryDate);

  function updateDraft<K extends keyof ContractDraft>(
    key: K,
    value: ContractDraft[K],
  ) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  function updateItem(id: string, patch: Partial<ContractItem>) {
    setDraft((current) => ({
      ...current,
      items: current.items.map((item) =>
        item.id === id ? { ...item, ...patch } : item,
      ),
    }));
  }

  function updateEditablePaymentPercent(
    key: "paymentOnOrderPercent" | "paymentBeforeDeliveryPercent",
    value: string,
  ) {
    const nextValue = clampPercent(parsePercent(value));

    setDraft((current) => {
      const currentOnOrder = clampPercent(parsePercent(current.paymentOnOrderPercent));
      const currentBeforeDelivery = clampPercent(
        parsePercent(current.paymentBeforeDeliveryPercent),
      );
      const nextOnOrder =
        key === "paymentOnOrderPercent"
          ? Math.min(nextValue, roundPercent(100 - currentBeforeDelivery))
          : currentOnOrder;
      const nextBeforeDelivery =
        key === "paymentBeforeDeliveryPercent"
          ? Math.min(nextValue, roundPercent(100 - nextOnOrder))
          : currentBeforeDelivery;
      const restValue = roundPercent(100 - nextOnOrder - nextBeforeDelivery);

      return {
        ...current,
        paymentOnOrderPercent: formatPercentValue(nextOnOrder),
        paymentBeforeDeliveryPercent: formatPercentValue(nextBeforeDelivery),
        restPaymentPercent: formatPercentValue(restValue),
      };
    });
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
    const normalizedDraft = {
      ...draft,
      restPaymentPercent: formatPercentValue(restPaymentPercent),
    };
    window.localStorage.setItem(storageKey, JSON.stringify(normalizedDraft));
    setDraftStatus(`Entwurf gespeichert: ${new Date().toLocaleTimeString("de-DE")}`);
  }

  function resetDraft() {
    window.localStorage.removeItem(storageKey);
    setDraft(createInitialDraft(initialDraft));
    setUseCustomerAddressForDelivery(false);
    setUseCustomerPhoneForDelivery(false);
    setDraftStatus("Entwurf zurückgesetzt");
  }

  function updateCustomerAddress(value: string) {
    setDraft((current) => ({
      ...current,
      customerAddress: value,
      deliveryAddress: useCustomerAddressForDelivery ? value : current.deliveryAddress,
    }));
  }

  function updateCustomerPhone(value: string) {
    setDraft((current) => ({
      ...current,
      customerPhone: value,
      deliveryPhone: useCustomerPhoneForDelivery ? value : current.deliveryPhone,
    }));
  }

  function toggleUseCustomerAddressForDelivery(checked: boolean) {
    setUseCustomerAddressForDelivery(checked);
    if (checked) updateDraft("deliveryAddress", draft.customerAddress);
  }

  function toggleUseCustomerPhoneForDelivery(checked: boolean) {
    setUseCustomerPhoneForDelivery(checked);
    if (checked) updateDraft("deliveryPhone", draft.customerPhone);
  }

  return (
    <>
      <form
        className="purchase-contract-screen grid gap-4"
        onSubmit={(event) => event.preventDefault()}
      >
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_280px]">
        <div className="grid gap-4">
          <Panel>
            <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="section-title">Kunde und Lieferung</h2>
                <p className="mt-1 text-sm text-[var(--muted)]">
                  Entspricht den Adressfeldern links oben im Papierformular.
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
                  placeholder="Name, Firma und Rechnungsanschrift"
                />
              </Label>
              <Label label="Kundenanschrift">
                <Textarea
                  name="customer_address"
                  value={draft.customerAddress}
                  onChange={(event) => updateCustomerAddress(event.target.value)}
                  placeholder="Straße, PLZ, Ort"
                />
              </Label>
              <Label label="Telefon Kunde">
                <Field
                  name="customer_phone"
                  value={draft.customerPhone}
                  onChange={(event) => updateCustomerPhone(event.target.value)}
                />
              </Label>
              <Label label="CARAT-Vorgangsnummer">
                <Field
                  name="customer_number"
                  value={draft.customerNumber}
                  onChange={(event) =>
                    updateDraft("customerNumber", event.target.value)
                  }
                  readOnly={customerNumberReadOnly}
                />
              </Label>
              <Label label="Lieferanschrift" className="md:col-span-2">
                <span className="inline-flex items-center gap-2 text-xs font-semibold text-[var(--muted)]">
                  <input
                    type="checkbox"
                    checked={useCustomerAddressForDelivery}
                    onChange={(event) =>
                      toggleUseCustomerAddressForDelivery(event.target.checked)
                    }
                  />
                  Kundenanschrift übernehmen
                </span>
                <Textarea
                  name="delivery_address"
                  value={draft.deliveryAddress}
                  onChange={(event) =>
                    updateDraft("deliveryAddress", event.target.value)
                  }
                  readOnly={useCustomerAddressForDelivery}
                  placeholder="Leer lassen, wenn identisch mit Rechnungsanschrift"
                />
              </Label>
              <Label label="Telefon Lieferanschrift">
                <span className="inline-flex items-center gap-2 text-xs font-semibold text-[var(--muted)]">
                  <input
                    type="checkbox"
                    checked={useCustomerPhoneForDelivery}
                    onChange={(event) =>
                      toggleUseCustomerPhoneForDelivery(event.target.checked)
                    }
                  />
                  Kundentelefon übernehmen
                </span>
                <Field
                  name="delivery_phone"
                  value={draft.deliveryPhone}
                  onChange={(event) => updateDraft("deliveryPhone", event.target.value)}
                  readOnly={useCustomerPhoneForDelivery}
                />
              </Label>
              <Label label="Liefer-KW">
                <Field
                  name="delivery_week"
                  type="week"
                  value={deliveryWeek}
                  onChange={(event) =>
                    updateDraft("deliveryDate", dateValueFromWeek(event.target.value))
                  }
                />
              </Label>
              <Label label="Liefertermin">
                <Field
                  name="delivery_date"
                  type="date"
                  value={draft.deliveryDate}
                  onChange={(event) => updateDraft("deliveryDate", event.target.value)}
                />
              </Label>
              <Label label="Kaufvertrags-Datum">
                <Field
                  name="contract_date"
                  type="date"
                  value={draft.contractDate}
                  onChange={(event) => updateDraft("contractDate", event.target.value)}
                />
              </Label>
              <Label label="Lieferart">
                <Select
                  name="delivery_mode"
                  value={draft.deliveryMode}
                  onChange={(event) =>
                    updateDraft(
                      "deliveryMode",
                      event.target.value as ContractDraft["deliveryMode"],
                    )
                  }
                >
                  <option value="installation">Montage</option>
                  <option value="pickup">Selbstabholung</option>
                </Select>
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
                  className="purchase-contract-position-row grid gap-3 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-3"
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
                      className="purchase-contract-quantity-field"
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
                      className="purchase-contract-description-field min-h-10"
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
                      placeholder="15.555,55 €"
                    />
                  </Label>
                  <button
                    type="button"
                    className="btn btn-secondary purchase-contract-position-delete aspect-square p-0"
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
              <Label label="Rechnungsendbetrag inkl. gesetzl. MwSt.">
                <Field
                  name="invoice_gross"
                  inputMode="decimal"
                  value={formatMoney(invoiceGross)}
                  readOnly
                />
              </Label>
              <Label label="MwSt. laut Kundenstammdaten">
                <Field
                  name="customer_vat_rate"
                  inputMode="decimal"
                  value={draft.customerVatRate}
                  onChange={(event) =>
                    updateDraft("customerVatRate", event.target.value)
                  }
                  onBlur={() =>
                    updateDraft(
                      "customerVatRate",
                      formatPercentInput(draft.customerVatRate),
                    )
                  }
                  readOnly={customerVatReadOnly}
                />
              </Label>
              <div className="grid gap-2 rounded-lg border border-[var(--border)] bg-[var(--surface-soft)] p-3 text-sm">
                <div className="flex justify-between gap-3">
                  <span>Rechnungsbetrag</span>
                  <strong>{formatMoney(invoiceGross)}</strong>
                </div>
                <div className="flex justify-between gap-3">
                  <span>Enthaltene MwSt. {formatPercentInput(draft.customerVatRate)} %</span>
                  <strong>{formatMoney(includedVat)}</strong>
                </div>
              </div>
            </div>
          </Panel>

          <Panel>
            <h2 className="section-title">Zahlung</h2>
            <div className="mt-4 grid gap-3">
              <Label label="Anzahlung bei Auftrag">
                <div className="grid grid-cols-[72px_16px_minmax(0,1fr)] items-center gap-2">
                  <Field
                    name="payment_on_order_percent"
                    inputMode="decimal"
                    value={draft.paymentOnOrderPercent}
                    onChange={(event) =>
                      updateEditablePaymentPercent("paymentOnOrderPercent", event.target.value)
                    }
                    aria-label="Anzahlung bei Auftrag Prozent"
                  />
                  <span className="text-sm font-bold text-[var(--muted)]">%</span>
                  <Field
                    name="payment_on_order"
                    value={formatMoney(paymentOnOrder)}
                    readOnly
                  />
                </div>
              </Label>
              <Label label="Zahlung vor Lieferung">
                <div className="grid grid-cols-[72px_16px_minmax(0,1fr)] items-center gap-2">
                  <Field
                    name="payment_before_delivery_percent"
                    inputMode="decimal"
                    value={draft.paymentBeforeDeliveryPercent}
                    onChange={(event) =>
                      updateEditablePaymentPercent("paymentBeforeDeliveryPercent", event.target.value)
                    }
                    aria-label="Zahlung vor Lieferung Prozent"
                  />
                  <span className="text-sm font-bold text-[var(--muted)]">%</span>
                  <Field
                    name="payment_before_delivery"
                    value={formatMoney(paymentBeforeDelivery)}
                    readOnly
                  />
                </div>
              </Label>
              <Label label="Restzahlung">
                <div className="grid grid-cols-[72px_16px_minmax(0,1fr)] items-center gap-2">
                  <Field
                    name="rest_payment_percent"
                    inputMode="decimal"
                    value={formatPercentValue(restPaymentPercent)}
                    readOnly
                    aria-label="Restzahlung Prozent"
                  />
                  <span className="text-sm font-bold text-[var(--muted)]">%</span>
                  <Field
                    name="rest_payment"
                    value={formatMoney(restPayment)}
                    readOnly
                  />
                </div>
              </Label>
              <div className="grid gap-2 rounded-lg border border-[var(--border)] bg-[var(--surface-soft)] p-3 text-sm">
                <div className="flex justify-between gap-3">
                  <span>Zahlungen</span>
                  <strong>{formatMoney(paymentTotal)}</strong>
                </div>
                <div className="flex justify-between gap-3">
                  <span>Offener Betrag</span>
                  <strong className={openAmount < 0 ? "text-[var(--danger)]" : ""}>
                    {formatMoney(openAmount)}
                  </strong>
                </div>
              </div>
            </div>
          </Panel>

          <Panel>
            <h2 className="section-title">Abschluss</h2>
            <div className="mt-4 grid gap-3">
              <Label label="Unterschrift Händler">
                <Field
                  name="dealer_signature_note"
                  value={draft.dealerSignatureNote}
                  onChange={(event) =>
                    updateDraft("dealerSignatureNote", event.target.value)
                  }
                  placeholder="Name oder Kürzel"
                />
              </Label>
              <Label label="Unterschrift Kunde">
                <Field
                  name="customer_signature_note"
                  value={draft.customerSignatureNote}
                  onChange={(event) =>
                    updateDraft("customerSignatureNote", event.target.value)
                  }
                  placeholder="Name oder Hinweis"
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

      <PurchaseContractPrintOverlay
        draft={draft}
        includedVat={includedVat}
        invoiceGross={invoiceGross}
        paymentBeforeDelivery={paymentBeforeDelivery}
        paymentOnOrder={paymentOnOrder}
        restPayment={restPayment}
      />
    </>
  );
}

function PurchaseContractPrintOverlay({
  draft,
  includedVat,
  invoiceGross,
  paymentBeforeDelivery,
  paymentOnOrder,
  restPayment,
}: {
  draft: ContractDraft;
  includedVat: number;
  invoiceGross: number;
  paymentBeforeDelivery: number;
  paymentOnOrder: number;
  restPayment: number;
}) {
  const customerLines = nonEmptyLines(draft.customerName, draft.customerAddress);
  const deliveryLines = nonEmptyLines(draft.deliveryAddress || draft.customerAddress);
  const firstPrintItems = draft.items.slice(0, 12);

  return (
    <div className="purchase-contract-print" aria-hidden="true">
      <section className="contract-print-page">
        <div className="print-address-block print-customer-address">
          {customerLines.map((line, index) => (
            <div key={`${line}-${index}`}>{line}</div>
          ))}
        </div>
        <div className="print-phone print-customer-phone">{draft.customerPhone}</div>

        <div className="print-address-block print-delivery-address">
          {deliveryLines.map((line, index) => (
            <div key={`${line}-${index}`}>{line}</div>
          ))}
        </div>
        <div className="print-phone print-delivery-phone">
          {draft.deliveryPhone || draft.customerPhone}
        </div>

        <div className="print-check print-pickup">
          {draft.deliveryMode === "pickup" ? "X" : ""}
        </div>
        <div className="print-check print-installation">
          {draft.deliveryMode === "installation" ? "X" : ""}
        </div>
        <div className="print-field print-delivery-date">
          {formatDateForPrint(draft.deliveryDate)}
        </div>
        <div className="print-field print-customer-number">{draft.customerNumber}</div>
        <div className="print-field print-contract-date">
          {formatDateForPrint(draft.contractDate)}
        </div>

        <div className="print-items">
          {firstPrintItems.map((item, index) => (
            <div className={`print-item-row print-item-row-${index + 1}`} key={item.id}>
              <div className="print-item-supplier">{item.supplier}</div>
              <div className="print-item-quantity">{item.quantity}</div>
              <div className="print-item-description">{item.description}</div>
              <div className="print-item-price">
                {item.totalPrice ? formatMoneyInput(item.totalPrice) : ""}
              </div>
            </div>
          ))}
        </div>

        <div className="print-signature-note print-dealer-signature">
          {draft.dealerSignatureNote}
        </div>
        <div className="print-signature-note print-customer-signature">
          {draft.customerSignatureNote}
        </div>

        <div className="print-money print-invoice-gross">{formatMoney(invoiceGross)}</div>
        <div className="print-money print-included-vat">{formatMoney(includedVat)}</div>
        <div className="print-money print-payment-order">{formatMoney(paymentOnOrder)}</div>
        <div className="print-money print-payment-delivery">
          {formatMoney(paymentBeforeDelivery)}
        </div>
        <div className="print-money print-payment-rest">{formatMoney(restPayment)}</div>
      </section>
    </div>
  );
}
