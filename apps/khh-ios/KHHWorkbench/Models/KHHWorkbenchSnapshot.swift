import Foundation

extension KHHWorkbench {
    static let current = KHHWorkbench(
        scope: KHHWorkbenchScope(
            tenantId: "tenant_kinderhaus",
            areaId: "kinderhaus-heuschrecken",
            primaryHostname: "kinderhaus-heuschrecken.cloud"
        ),
        hero: KHHHero(
            title: "Leitungs-Cockpit",
            functionText: "Tageslage, Fristen, Personalrisiken, Dienste und Entwicklung schnell einordnen."
        ),
        dayStrip: [
            "Personal: pruefen",
            "Fristen: 2 kritisch",
            "Kochdienst: bestaetigt",
            "Vorgaenge: 1 offen"
        ],
        dailySignals: [
            KHHDailySignal(
                id: "staffing-afternoon-reserve",
                title: "Personal",
                status: "pruefen",
                detail: "Nachmittag ohne Reserve geplant.",
                action: "Vertretung pruefen",
                tone: .warning,
                systemImage: "person.2"
            ),
            KHHDailySignal(
                id: "deadline-weekly-evidence",
                title: "Fristen",
                status: "kritisch",
                detail: "2 Nachweise laufen diese Woche ab.",
                action: "Nachweise oeffnen",
                tone: .danger,
                systemImage: "calendar.badge.clock"
            ),
            KHHDailySignal(
                id: "service-kitchen-duty",
                title: "Kochdienst",
                status: "ok",
                detail: "Dienst bestaetigt, Hinweis vorhanden.",
                action: "Originalunterlage pruefen",
                tone: .success,
                systemImage: "heart"
            ),
            KHHDailySignal(
                id: "case-leadership-follow-up",
                title: "Vorgaenge",
                status: "offen",
                detail: "1 Wiedervorlage braucht Leitungssicht.",
                action: "Vorgang ansehen",
                tone: .info,
                systemImage: "shield.checkered"
            )
        ],
        quickActions: [
            KHHQuickAction(
                id: "capture-case",
                title: "Vorgang erfassen",
                detail: "Minimalen Bezug, Risiko, Frist und Freigabestatus aufnehmen.",
                action: "Erfassen",
                systemImage: "checklist"
            ),
            KHHQuickAction(
                id: "review-evidence",
                title: "Nachweis pruefen",
                detail: "Gueltigkeit, Verantwortlichkeit und naechste Aktion klaeren.",
                action: "Pruefen",
                systemImage: "doc.text.magnifyingglass"
            ),
            KHHQuickAction(
                id: "replace-duty",
                title: "Dienst ersetzen",
                detail: "Kochdienst oder Arbeitseinsatz mit Belehrungsstatus absichern.",
                action: "Oeffnen",
                systemImage: "arrow.triangle.2.circlepath"
            )
        ],
        sections: [
            KHHSection(
                id: "deadlines",
                title: "Fristen",
                subtitle: "Nachweise, Belehrungen und Wiedervorlagen nach Risiko steuern.",
                systemImage: "calendar.badge.clock",
                items: [
                    "Erweitertes Fuehrungszeugnis, Erste Hilfe, IfSG und Lebensmittelbelehrung",
                    "Status: gueltig, laeuft bald ab, fehlt, unklar oder nicht erforderlich",
                    "Bezug nur als Vorname, Kuerzel, Rolle oder interne Referenz"
                ],
                focus: ["Nachweis", "Bereich", "Status", "Faellig", "Naechste Aktion"]
            ),
            KHHSection(
                id: "staffing",
                title: "Personal-Ampel",
                subtitle: "Tages- und Wochenrisiken fuer Mindestbesetzung sichtbar machen.",
                systemImage: "person.2",
                items: [
                    "Vormittag, Nachmittag, morgen und Risikotage getrennt bewerten",
                    "PiA, FSJ und Praktikum nicht wie voll anrechenbare Fachkraefte behandeln",
                    "Abwesenheiten ohne medizinische Details anzeigen"
                ],
                focus: ["Zeitfenster", "Ampel", "Reserve", "Risiko", "Vertretung"]
            ),
            KHHSection(
                id: "services",
                title: "Dienste",
                subtitle: "Kochdienste, Arbeitseinsaetze und Elternpflichten absichern.",
                systemImage: "heart",
                items: [
                    "Dienststatus fuer heute und morgen schnell erfassen",
                    "Belehrungsstatus und Ersatzbedarf sichtbar machen",
                    "Ernaehrungshinweise nur als knapper Status, nie als Detailakte"
                ],
                focus: ["Dienst", "Status", "Hinweis", "Ersatz", "Aktion"]
            ),
            KHHSection(
                id: "cases",
                title: "Vorgaenge",
                subtitle: "Sensible Vorgaenge getrennt von normalem Aufgaben-Kanban fuehren.",
                systemImage: "shield.checkered",
                items: [
                    "Vorfall, Unfall, Kinderschutz und Beschwerde sauber trennen",
                    "App darf strukturieren, aber keine finale Bewertung treffen",
                    "Meldungen an Jugendamt, KVJS oder Gesundheitsamt nur nach Freigabe"
                ],
                focus: ["Typ", "Risiko", "Freigabe", "Wiedervorlage", "Schutzbereich"]
            ),
            KHHSection(
                id: "occupancy",
                title: "Belegung",
                subtitle: "U3, Kindergarten und Hort mit Uebergaengen planen.",
                systemImage: "house",
                items: [
                    "Kita-Portal-Status nur als Prozessstatus fuehren",
                    "Uebergang U3, Kindergarten, Schule und Hort in Monatslogik planen",
                    "Geschwister- oder Prioritaetsmerkmale ohne Familienakte erfassen"
                ],
                focus: ["Bereich", "Monat", "Plaetze", "Uebergang", "Risiko"]
            ),
            KHHSection(
                id: "development",
                title: "Entwicklung",
                subtitle: "Paedagogik, Team, Raeume und Elterninitiative systematisch verbessern.",
                systemImage: "sparkles",
                items: [
                    "Jahresziele und Quartalsmassnahmen sichtbar halten",
                    "Qualitaetsreviews als Lernsystem, nicht als Kontrollinstrument nutzen",
                    "Ideen aus Team und Elternschaft in kleine Experimente fuehren"
                ],
                focus: ["Ziel", "Massnahme", "Review", "Verantwortung", "Wirkung"]
            ),
            KHHSection(
                id: "documents",
                title: "Dokumente",
                subtitle: "Vorlagen, Konzepte und Nachweise mit Status und Version fuehren.",
                systemImage: "doc.text",
                items: [
                    "Betriebserlaubnis, Konzeption, Schutzkonzept und Hygieneplan referenzieren",
                    "Dokumente mit Version, Gueltigkeit und Verantwortlichkeit versehen",
                    "Originalunterlagen bleiben ausserhalb der Standarduebersichten"
                ],
                focus: ["Dokument", "Version", "Status", "Gueltig bis", "Verantwortung"]
            ),
            KHHSection(
                id: "tasks",
                title: "Aufgaben",
                subtitle: "Kanban nur als Arbeitsschicht ueber Fristen, Nachweisen und Vorgaengen.",
                systemImage: "list.bullet.clipboard",
                items: [
                    "Status: Neu, Geplant, In Arbeit, Wartet, Zur Pruefung, Erledigt",
                    "Jede Aufgabe braucht Bereich, Frist, Risiko und Verantwortung",
                    "Freigabe- und Nachweispflichten direkt sichtbar machen"
                ],
                focus: ["Aufgabe", "Bereich", "Frist", "Risiko", "Status"]
            )
        ],
        privacyRules: [
            "Keine vollstaendigen Kinder-, Eltern- oder Personalstammdaten",
            "Personenbezug nur mit Vorname, Kuerzel oder interner Referenz",
            "Keine Adressen, privaten Kontaktdaten, Geburtsdaten oder Vertragsdaten",
            "Gesundheits- und Sorgerechtshinweise nur als minimaler Status"
        ]
    )
}
