import { PageHero } from "@/components/chrome/page-hero";
import { InvoiceForm } from "@/components/invoice/invoice-form";

export default function InvoicePage() {
  return (
    <div className="content-stack">
      <PageHero
        eyebrow={null}
        title="Rechnung"
        subtitle="Eingabemaske für Rechnungsdaten, Positionen, Endbetrag, Anzahlungen und Restbetrag."
      />
      <InvoiceForm customerNumberReadOnly={false} customerVatReadOnly={false} />
    </div>
  );
}
