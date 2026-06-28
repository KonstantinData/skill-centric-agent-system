import Foundation

extension DKHWorkspace {
    static let current = DKHWorkspace(
        scope: DKHWorkspaceScope(
            tenantId: "daskuechenhaus",
            areaId: "daskuechenhaus",
            webAppPath: "apps/dkh-crm/",
            primaryHostnames: ["es-daskuechenhaus.de", "www.es-daskuechenhaus.de"]
        ),
        hero: DKHHero(
            title: "CRM Arbeitsbereich",
            functionText: "Termine, Aufgaben, E-Mails, Kundenakten und Vorgaenge als mobile DKH-Uebersicht."
        ),
        dayStrip: [
            "Termine: heute pruefen",
            "Aufgaben: offene Arbeit",
            "E-Mails: Zuordnung klaeren",
            "Vorgaenge: aktive Sicht"
        ],
        statusSignals: [
            DKHStatusSignal(
                id: "appointments-today",
                title: "Heutige Termine",
                status: "sichtbar",
                detail: "Kalenderdaten bleiben aus der bestehenden CRM-API abgeleitet.",
                action: "Termine oeffnen",
                tone: .info,
                systemImage: "calendar"
            ),
            DKHStatusSignal(
                id: "open-tasks",
                title: "Offene Aufgaben",
                status: "offen",
                detail: "Aufgaben werden mit Status, Prioritaet, Faelligkeit und Vorgangsbezug gefuehrt.",
                action: "Aufgaben ansehen",
                tone: .warning,
                systemImage: "checklist"
            ),
            DKHStatusSignal(
                id: "unassigned-mail",
                title: "Unzugeordnete E-Mails",
                status: "klaeren",
                detail: "E-Mail-Eingang zeigt Zuordnungsvorschlaege und sichtbaren Vorgangsbezug.",
                action: "Postfach pruefen",
                tone: .danger,
                systemImage: "envelope.badge"
            ),
            DKHStatusSignal(
                id: "active-cases",
                title: "Aktive Vorgaenge",
                status: "laufend",
                detail: "Kundenakten und Vorgangsregister bleiben im Hetzner Tenant-Kontext.",
                action: "Vorgaenge ansehen",
                tone: .success,
                systemImage: "folder"
            )
        ],
        quickActions: [
            DKHQuickAction(
                id: "open-customer-search",
                title: "Kunden direkt Suche",
                detail: "Mobiler Einstieg in Suche und Kundenakten ohne lokale Stammdatenkopie.",
                action: "Suchen",
                systemImage: "person.text.rectangle"
            ),
            DKHQuickAction(
                id: "review-acute-work",
                title: "Akute Arbeit",
                detail: "Faellige Aufgaben, Terminrisiken und ungeklaerte E-Mails priorisieren.",
                action: "Pruefen",
                systemImage: "exclamationmark.triangle"
            ),
            DKHQuickAction(
                id: "open-templates",
                title: "Vorlagen",
                detail: "Blanko Kaufvertrag und Blanko Rechnung bleiben getrennte Dokumentflaechen.",
                action: "Oeffnen",
                systemImage: "doc.text"
            )
        ],
        sections: [
            DKHSection(
                id: "overview",
                title: "Uebersicht",
                subtitle: "CRM-Tageslage fuer Termine, Aufgaben, E-Mails, Vorgaenge und Konflikte.",
                systemImage: "rectangle.grid.2x2",
                items: [
                    "Statuskarten fuer heutige Termine, offene Aufgaben, unzugeordnete E-Mails und aktive Vorgaenge",
                    "Naechste Termine und akute Arbeit bleiben lesende Uebersichten",
                    "Konfliktstatus kommt aus dem Kalender-Sync und wird nicht lokal entschieden"
                ],
                focus: ["Heute", "Aufgaben", "E-Mails", "Vorgaenge", "Konflikte"]
            ),
            DKHSection(
                id: "appointments",
                title: "Termine",
                subtitle: "Kalenderdaten mit Konfliktstatus und Vorgangsbezug anzeigen.",
                systemImage: "calendar.badge.clock",
                items: [
                    "Heute und alle sichtbaren Termine getrennt darstellen",
                    "Ort, Zeitfenster, Verantwortlichkeit und Vorgangsbezug nur aus CRM/API-Kontext",
                    "Readonly- und Sync-Status sichtbar halten"
                ],
                focus: ["Start", "Ende", "Ort", "Vorgang", "Konflikt"]
            ),
            DKHSection(
                id: "tasks",
                title: "Aufgaben",
                subtitle: "Aufgaben mit Status, Prioritaet, Faelligkeit und Verantwortlichkeit fuehren.",
                systemImage: "checklist",
                items: [
                    "Neue Aufgabe bleibt Web/API-Schreibfunktion, nicht Snapshot-Daten",
                    "Offene Aufgaben zeigen Status, Prioritaet und optionalen Vorgangsbezug",
                    "Erinnerungen und Anlagen werden nur als Status, nicht als Rohdaten gespiegelt"
                ],
                focus: ["Titel", "Status", "Prioritaet", "Faellig", "Zustaendig"]
            ),
            DKHSection(
                id: "emails",
                title: "E-Mails",
                subtitle: "E-Mail-Eingang mit Vorgangszuordnung und Vorschlaegen pruefen.",
                systemImage: "envelope",
                items: [
                    "Nachrichtenliste bleibt Zuordnungs- und Lebenszyklusansicht",
                    "Absenderfilter und Vorgangsauswahl stammen aus dem DKH CRM",
                    "Keine Mailinhalte, privaten Adressen oder Rohkopfzeilen in Seed-Daten"
                ],
                focus: ["Betreff", "Zuordnung", "Vorschlag", "Richtung", "Status"]
            ),
            DKHSection(
                id: "customers",
                title: "Kunden",
                subtitle: "Suche, Neuanlage und direkter Einstieg in Kundenakten.",
                systemImage: "person.crop.rectangle.stack",
                items: [
                    "Neukundenanlage nutzt den Such-zuerst Dublettenfluss",
                    "Leads und Kunden bleiben getrennt, bis ein Lead umgewandelt wird",
                    "Kundennummern und Vorgangsnummern werden von der Hetzner Admin API erzeugt"
                ],
                focus: ["Suche", "Lead", "Kunde", "Dublettenwarnung", "Kundenakte"]
            ),
            DKHSection(
                id: "cases",
                title: "Vorgaenge",
                subtitle: "Kundenakte, Vorgangsregister und Kuechenstudio-Prozessphasen.",
                systemImage: "folder.badge.gearshape",
                items: [
                    "Statusphasen laufen von Anfrage bis Abgeschlossen",
                    "Projektobjekte, Kontakte, Prozesssteuerung, Dokumentregister und Notizen bleiben case-gebunden",
                    "CARAT Vorgangsnummer bleibt manuell und getrennt von generierten CRM-Nummern"
                ],
                focus: ["Phase", "Register", "Dokumente", "CARAT", "Naechster Schritt"]
            ),
            DKHSection(
                id: "forms",
                title: "Kaufvertrag und Rechnung",
                subtitle: "Formularflaechen bleiben getrennt und koennen kundenvorgangsbezogen starten.",
                systemImage: "doc.richtext",
                items: [
                    "Kaufvertrag und Rechnung verwenden getrennte Komponenten, Routen und Draft-Schluessel",
                    "Kundenverknuepfte Formulare starten aus dem passenden Vorgangsregister",
                    "Blanko-Vorlagen bleiben ohne Kunden- oder Vorgangsverknuepfung"
                ],
                focus: ["Kaufvertrag", "Rechnung", "Positionen", "Betraege", "Druck"]
            ),
            DKHSection(
                id: "admin",
                title: "Admin",
                subtitle: "Mitarbeiter, Firmenstammdaten, Integrationen und Systemgrenzen.",
                systemImage: "gearshape.2",
                items: [
                    "Adminrechte bleiben tenant-lokal und werden nicht aus E-Mail-Domain-Wissen abgeleitet",
                    "Secrets und Integrationsreferenzen gehoeren in Runtime-Quellen, nicht in die App",
                    "Owner- und Admin-Bootstrap bleiben ueber die dokumentierten Governance-Gates abgesichert"
                ],
                focus: ["Benutzer", "Rollen", "Firmendaten", "Integrationen", "System"]
            )
        ],
        privacyRules: [
            "Keine echten Kundennamen, E-Mail-Adressen, Telefonnummern oder Postadressen im Snapshot",
            "Keine Dokumentinhalte, Roh-Mails, API-Antworten, Tokens oder Runtime-Traces",
            "Personenbezug nur generisch, rollenbasiert, count-basiert oder intern referenziert",
            "Read-only bis Auth, sichere Speicherung, Redaction und Audit-Gates implementiert sind"
        ],
        excludedCapabilities: [
            "No write intents",
            "No customer master-data cache",
            "No object-storage document access",
            "No Cloudflare Access token storage",
            "No Hetzner Admin API secrets"
        ]
    )
}
