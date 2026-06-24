import { PageHero } from "@/components/chrome/page-hero";
import { PurchaseContractForm } from "@/components/purchase-contract/purchase-contract-form";

export default function PurchaseContractPage() {
  return (
    <div className="content-stack">
      <PageHero
        eyebrow={null}
        title="Kaufvertrag"
        subtitle="Eingabemaske für Kundendaten, Lieferdaten, Positionen, Rechnungsbetrag und Zahlungen."
      />
      <PurchaseContractForm />
    </div>
  );
}
