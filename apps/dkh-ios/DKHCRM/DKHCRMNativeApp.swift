import AuthenticationServices
import Foundation
import Security
import SwiftUI

enum DKHMobileAPI {
    static let baseURL = URL(string: "https://app.es-daskuechenhaus.de/api/mobile")!
}

struct DKHCRMUser: Codable, Equatable {
    let id: Int
    let displayName: String
    let email: String
    let roles: [String]
}

struct DKHCRMSection: Identifiable, Equatable {
    let id: String
    let title: String
    let systemImage: String
    let summary: String
}

let dkhCRMSections: [DKHCRMSection] = [
    DKHCRMSection(id: "uebersicht", title: "Uebersicht", systemImage: "chart.bar.doc.horizontal", summary: "Tageslage, Termine, Aufgaben und offene E-Mails"),
    DKHCRMSection(id: "kunden", title: "Kunden", systemImage: "person.2", summary: "Kundenakte, Leads, Vorgaenge und Dokumente"),
    DKHCRMSection(id: "termine", title: "Termine", systemImage: "calendar", summary: "Kalender, Besuchstermine und Wiedervorlagen"),
    DKHCRMSection(id: "aufgaben", title: "Aufgaben", systemImage: "checklist", summary: "Team-Aufgaben, Faelligkeiten und Zuweisungen"),
    DKHCRMSection(id: "emails", title: "E-Mails", systemImage: "envelope", summary: "Posteingang, Fallzuordnung und Antwortvorschlaege"),
    DKHCRMSection(id: "vorgaenge", title: "Vorgaenge", systemImage: "folder", summary: "Aktive Kundenfaelle und Bearbeitungsstatus"),
    DKHCRMSection(id: "kaufvertrag", title: "Kaufvertrag", systemImage: "doc.text", summary: "Vertragsdaten und Kaufvertragsstrecke"),
    DKHCRMSection(id: "rechnung", title: "Rechnung", systemImage: "doc.plaintext", summary: "Rechnungsdaten und Zahlungsstatus"),
    DKHCRMSection(id: "admin", title: "Admin", systemImage: "gearshape", summary: "Benutzer, Rollen und Systemeinstellungen"),
]

struct DKHSessionResponse: Codable {
    let sessionToken: String?
    let status: String
    let user: DKHCRMUser?
}

enum DKHSessionError: LocalizedError {
    case missingIdentityToken
    case serverMessage(String)
    case unauthorized(String)

    var errorDescription: String? {
        switch self {
        case .missingIdentityToken:
            return "Apple hat keinen Identity Token geliefert."
        case .serverMessage(let message):
            return message
        case .unauthorized(let status):
            return "Der Apple-Account ist noch nicht fuer DKH CRM freigeschaltet (\(status))."
        }
    }
}

@MainActor
final class DKHSessionStore: ObservableObject {
    @Published private(set) var user: DKHCRMUser?
    @Published private(set) var status: String = "signed_out"
    @Published var errorMessage: String?
    @Published var isSigningIn = false

    private let keychain = DKHKeychainStore()

    func handleAuthorization(_ result: Result<ASAuthorization, Error>) {
        switch result {
        case .success(let authorization):
            guard
                let credential = authorization.credential as? ASAuthorizationAppleIDCredential,
                let tokenData = credential.identityToken,
                let identityToken = String(data: tokenData, encoding: .utf8)
            else {
                errorMessage = DKHSessionError.missingIdentityToken.localizedDescription
                return
            }
            Task {
                await exchange(identityToken: identityToken)
            }
        case .failure(let error):
            errorMessage = error.localizedDescription
        }
    }

    func signOut() {
        keychain.deleteSessionToken()
        user = nil
        status = "signed_out"
        errorMessage = nil
    }

    private func exchange(identityToken: String) async {
        isSigningIn = true
        errorMessage = nil
        defer { isSigningIn = false }

        do {
            let response = try await DKHMobileSessionClient().createSession(identityToken: identityToken)
            status = response.status
            guard response.status == "active", let sessionToken = response.sessionToken, let user = response.user else {
                throw DKHSessionError.unauthorized(response.status)
            }
            keychain.saveSessionToken(sessionToken)
            self.user = user
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

struct DKHMobileSessionClient {
    func createSession(identityToken: String) async throws -> DKHSessionResponse {
        var request = URLRequest(url: DKHMobileAPI.baseURL.appending(path: "session"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "content-type")
        request.httpBody = try JSONEncoder().encode(["identity_token": identityToken])

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw DKHSessionError.serverMessage("Ungueltige Serverantwort.")
        }
        let decoded = try JSONDecoder().decode(DKHSessionResponse.self, from: data)
        if http.statusCode == 200 {
            return decoded
        }
        throw DKHSessionError.unauthorized(decoded.status)
    }
}

struct DKHKeychainStore {
    private let service = "de.daskuechenhaus.crm.mobile-session"
    private let account = "dkh-crm-session"

    func saveSessionToken(_ token: String) {
        deleteSessionToken()
        guard let data = token.data(using: .utf8) else { return }
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly,
            kSecValueData as String: data,
        ]
        SecItemAdd(query as CFDictionary, nil)
    }

    func deleteSessionToken() {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
        SecItemDelete(query as CFDictionary)
    }
}

struct DKHCRMRootView: View {
    @StateObject private var session = DKHSessionStore()

    var body: some View {
        Group {
            if let user = session.user {
                DKHCRMDashboardView(user: user, signOut: session.signOut)
            } else {
                DKHAppleLoginView(session: session)
            }
        }
    }
}

struct DKHAppleLoginView: View {
    @ObservedObject var session: DKHSessionStore

    var body: some View {
        VStack(alignment: .leading, spacing: 24) {
            Spacer()

            VStack(alignment: .leading, spacing: 10) {
                Text("DKH CRM")
                    .font(.largeTitle.weight(.bold))
                Text("Native App fuer Das Kuechenhaus")
                    .font(.headline)
                    .foregroundStyle(.secondary)
            }

            VStack(alignment: .leading, spacing: 12) {
                Label("Kein Webseitenstart", systemImage: "iphone")
                Label("Keine Cloudflare-Verifikation", systemImage: "checkmark.shield")
                Label("Freischaltung ueber Apple-Account", systemImage: "person.crop.circle.badge.checkmark")
            }
            .font(.body.weight(.medium))

            SignInWithAppleButton(.signIn) { request in
                request.requestedScopes = [.email, .fullName]
            } onCompletion: { result in
                session.handleAuthorization(result)
            }
            .signInWithAppleButtonStyle(.black)
            .frame(height: 52)
            .clipShape(RoundedRectangle(cornerRadius: 8))
            .disabled(session.isSigningIn)

            if session.isSigningIn {
                ProgressView("Zugang wird geprueft")
            }

            if let errorMessage = session.errorMessage {
                Text(errorMessage)
                    .font(.callout)
                    .foregroundStyle(.red)
            }

            Spacer()
        }
        .padding(24)
    }
}

struct DKHCRMDashboardView: View {
    let user: DKHCRMUser
    let signOut: () -> Void

    var body: some View {
        NavigationStack {
            List {
                Section {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(user.displayName)
                            .font(.headline)
                        Text(user.email)
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                    .padding(.vertical, 4)
                }

                Section("CRM") {
                    ForEach(dkhCRMSections) { section in
                        NavigationLink {
                            DKHCRMSectionView(section: section)
                        } label: {
                            Label {
                                VStack(alignment: .leading, spacing: 3) {
                                    Text(section.title)
                                    Text(section.summary)
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                            } icon: {
                                Image(systemName: section.systemImage)
                            }
                        }
                    }
                }
            }
            .navigationTitle("DKH CRM")
            .toolbar {
                Button("Abmelden", action: signOut)
            }
        }
    }
}

struct DKHCRMSectionView: View {
    let section: DKHCRMSection

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Image(systemName: section.systemImage)
                .font(.largeTitle)
            Text(section.title)
                .font(.title.bold())
            Text(section.summary)
                .foregroundStyle(.secondary)
            Text("Diese native Ansicht wird ueber die DKH App-API mit produktiven CRM-Daten versorgt. Sie startet keine Webseite und nutzt keinen Cloudflare-Access-Flow.")
                .font(.callout)
                .foregroundStyle(.secondary)
            Spacer()
        }
        .padding(24)
        .navigationTitle(section.title)
    }
}
