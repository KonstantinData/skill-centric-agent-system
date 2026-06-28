import AuthenticationServices
import Foundation
import Security
import SwiftUI
import UIKit

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

struct DKHStoredSession: Codable {
    let sessionToken: String
    let user: DKHCRMUser
    let storedAt: Date
}

enum DKHSessionError: LocalizedError {
    case deviceGrantCanceled
    case missingIdentityToken
    case mobileAPINotReachable
    case serverMessage(String)
    case unauthorized(String)

    var errorDescription: String? {
        switch self {
        case .deviceGrantCanceled:
            return "Die iPhone-Freigabe wurde abgebrochen."
        case .missingIdentityToken:
            return "Apple hat keinen Identity Token geliefert."
        case .mobileAPINotReachable:
            return "Die DKH Mobile-API ist noch nicht erreichbar. Bitte pruefe die Produktionsfreigabe fuer app.es-daskuechenhaus.de."
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
    @Published private(set) var status: String = "device_not_granted"
    @Published var errorMessage: String?
    @Published var isGrantingDevice = false

    private let keychain = DKHKeychainStore()

    init() {
        if let storedSession = keychain.loadStoredSession() {
            user = storedSession.user
            status = "trusted_device"
        }
    }

    func handleDeviceAuthorization(_ result: Result<ASAuthorization, Error>) {
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
                await grantDevice(identityToken: identityToken)
            }
        case .failure(let error):
            if let authorizationError = error as? ASAuthorizationError, authorizationError.code == .canceled {
                errorMessage = DKHSessionError.deviceGrantCanceled.localizedDescription
            } else {
                errorMessage = error.localizedDescription
            }
        }
    }

    func resetDeviceGrant() {
        keychain.deleteStoredSession()
        user = nil
        status = "device_not_granted"
        errorMessage = nil
    }

    private func grantDevice(identityToken: String) async {
        isGrantingDevice = true
        errorMessage = nil
        defer { isGrantingDevice = false }

        do {
            let response = try await DKHMobileSessionClient().createSession(identityToken: identityToken)
            status = response.status
            guard response.status == "active", let sessionToken = response.sessionToken, let user = response.user else {
                throw DKHSessionError.unauthorized(response.status)
            }
            keychain.saveStoredSession(DKHStoredSession(sessionToken: sessionToken, user: user, storedAt: Date()))
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

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await URLSession.shared.data(for: request)
        } catch let error as URLError where error.code == .cannotFindHost {
            throw DKHSessionError.mobileAPINotReachable
        }
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
    private let service = "de.daskuechenhaus.crm.device-grant"
    private let account = "dkh-crm-trusted-device"

    func saveStoredSession(_ session: DKHStoredSession) {
        deleteStoredSession()
        guard let data = try? JSONEncoder().encode(session) else { return }
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly,
            kSecValueData as String: data,
        ]
        SecItemAdd(query as CFDictionary, nil)
    }

    func loadStoredSession() -> DKHStoredSession? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne,
        ]
        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)
        guard status == errSecSuccess, let data = item as? Data else {
            return nil
        }
        return try? JSONDecoder().decode(DKHStoredSession.self, from: data)
    }

    func deleteStoredSession() {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
        SecItemDelete(query as CFDictionary)
    }
}

final class DKHDeviceAuthorizationController: NSObject, ObservableObject, ASAuthorizationControllerDelegate, ASAuthorizationControllerPresentationContextProviding {
    private var completion: ((Result<ASAuthorization, Error>) -> Void)?

    func start(completion: @escaping (Result<ASAuthorization, Error>) -> Void) {
        self.completion = completion

        let request = ASAuthorizationAppleIDProvider().createRequest()
        request.requestedScopes = [.email, .fullName]

        let controller = ASAuthorizationController(authorizationRequests: [request])
        controller.delegate = self
        controller.presentationContextProvider = self
        controller.performRequests()
    }

    func authorizationController(controller: ASAuthorizationController, didCompleteWithAuthorization authorization: ASAuthorization) {
        completion?(.success(authorization))
    }

    func authorizationController(controller: ASAuthorizationController, didCompleteWithError error: Error) {
        completion?(.failure(error))
    }

    func presentationAnchor(for controller: ASAuthorizationController) -> ASPresentationAnchor {
        let scenes = UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }
        return scenes.flatMap(\.windows).first { $0.isKeyWindow } ?? ASPresentationAnchor()
    }
}

struct DKHCRMRootView: View {
    @StateObject private var session = DKHSessionStore()

    var body: some View {
        Group {
            if let user = session.user {
                DKHCRMDashboardView(user: user)
            } else {
                DKHDeviceGrantView(session: session)
            }
        }
    }
}

struct DKHDeviceGrantView: View {
    @ObservedObject var session: DKHSessionStore
    @StateObject private var deviceAuthorization = DKHDeviceAuthorizationController()
    @State private var didRequestDeviceGrant = false

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
                Label("Dieses iPhone wird einmalig freigegeben", systemImage: "iphone")
                Label("Danach reicht das entsperrte iPhone", systemImage: "lock.open")
                Label("Berechtigungen kommen vom DKH Server", systemImage: "checkmark.shield")
            }
            .font(.body.weight(.medium))

            if session.isGrantingDevice {
                ProgressView("iPhone-Freigabe wird geprueft")
            } else if session.errorMessage == nil {
                ProgressView("iPhone-Freigabe wird gestartet")
            }

            if let errorMessage = session.errorMessage {
                VStack(alignment: .leading, spacing: 12) {
                    Text(errorMessage)
                        .font(.callout)
                        .foregroundStyle(.red)

                    Button("iPhone-Freigabe erneut starten") {
                        requestDeviceGrant()
                    }
                    .buttonStyle(.borderedProminent)
                }
            }

            Spacer()
        }
        .padding(24)
        .onAppear {
            guard !didRequestDeviceGrant else { return }
            requestDeviceGrant()
        }
    }

    private func requestDeviceGrant() {
        didRequestDeviceGrant = true
        deviceAuthorization.start { result in
            session.handleDeviceAuthorization(result)
        }
    }
}

struct DKHCRMDashboardView: View {
    let user: DKHCRMUser

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
