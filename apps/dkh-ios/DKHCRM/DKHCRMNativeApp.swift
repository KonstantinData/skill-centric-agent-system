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

struct DKHMobileResourceResponse<State: Decodable>: Decodable {
    let status: String
    let resource: String
    let state: State
}

struct DKHMobileActionResponse: Decodable {
    let status: String
    let action: String
    let result: [String: DKHJSONValue]?
}

enum DKHJSONValue: Decodable {
    case string(String)
    case int(Int)
    case double(Double)
    case bool(Bool)
    case null

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if container.decodeNil() {
            self = .null
        } else if let value = try? container.decode(Bool.self) {
            self = .bool(value)
        } else if let value = try? container.decode(Int.self) {
            self = .int(value)
        } else if let value = try? container.decode(Double.self) {
            self = .double(value)
        } else {
            self = .string((try? container.decode(String.self)) ?? "")
        }
    }

    var displayText: String {
        switch self {
        case .string(let value):
            return value
        case .int(let value):
            return "\(value)"
        case .double(let value):
            return value.formatted()
        case .bool(let value):
            return value ? "Ja" : "Nein"
        case .null:
            return ""
        }
    }
}

struct DKHOverviewState: Decodable {
    let currentUser: DKHOverviewUser?
    let users: [DKHUserOption]?
    let taskStatuses: [DKHTaskStatus]?
    let customerCases: [DKHCustomerCase]?
    let tasks: [DKHTask]?
    let emails: [DKHEmail]?
    let appointments: [DKHAppointment]?
}

struct DKHOverviewUser: Decodable {
    let displayName: String?
    let email: String?
    let isAdmin: Bool?
}

struct DKHUserOption: Decodable, Identifiable {
    let id: Int
    let firstName: String?
    let lastName: String?
    let email: String?
    let roles: [String]?

    var displayName: String {
        [firstName, lastName].compactMap { $0 }.joined(separator: " ").trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

struct DKHTaskStatus: Decodable, Identifiable {
    let code: String
    let name: String
    let isTerminal: Bool?

    var id: String { code }
}

struct DKHCustomerCase: Decodable, Identifiable {
    let id: Int
    let customerId: Int?
    let caseNumber: String?
    let caratOrderNumber: String?
    let caseTitle: String?
    let caseStatus: String?
    let customerDisplayName: String
    let customerNumber: String?
    let customerEmail: String?
    let statusPhase: Int?
    let statusPhaseName: String?
    let responsibleUserId: Int?
    let notes: [DKHCaseNote]?
    let sections: [String: [String: DKHJSONValue]]?
    let documents: [DKHCaseDocument]?
    let updatedAt: String?
}

struct DKHTask: Decodable, Identifiable {
    let id: Int
    let title: String
    let description: String?
    let status: String?
    let statusName: String?
    let priority: String?
    let dueAt: String?
    let reminderAt: String?
    let assignedUsers: [DKHAssignedUser]?
    let caseInfo: DKHCustomerCase?

    enum CodingKeys: String, CodingKey {
        case id
        case title
        case description
        case status
        case statusName
        case priority
        case dueAt
        case reminderAt
        case assignedUsers
        case caseInfo = "case"
    }
}

struct DKHEmail: Decodable, Identifiable {
    let id: Int
    let subject: String
    let snippet: String?
    let direction: String?
    let receivedAt: String?
    let isUnassigned: Bool?
    let participants: [DKHEmailParticipant]?
    let cases: [DKHEmailCase]?
    let suggestions: [DKHEmailSuggestion]?
}

struct DKHAppointment: Decodable, Identifiable {
    let id: Int
    let title: String
    let startsAt: String
    let location: String?
    let caseInfo: DKHAppointmentCase?

    enum CodingKeys: String, CodingKey {
        case id
        case title
        case startsAt
        case location
        case caseInfo = "case"
    }
}

struct DKHAppointmentCase: Decodable {
    let id: Int
    let customerDisplayName: String
}

struct DKHAssignedUser: Decodable, Identifiable {
    let id: Int
    let name: String
}

struct DKHEmailParticipant: Decodable {
    let type: String?
    let displayName: String?
    let emailAddress: String
}

struct DKHEmailCase: Decodable, Identifiable {
    let id: Int
    let caseNumber: String?
    let customerDisplayName: String
}

struct DKHEmailSuggestion: Decodable, Identifiable {
    let id: Int
    let confidence: Double?
    let reason: String?
    let caseInfo: DKHEmailCase?

    enum CodingKeys: String, CodingKey {
        case id
        case confidence
        case reason
        case caseInfo = "case"
    }
}

struct DKHCustomersState: Decodable {
    let currentUser: DKHOverviewUser?
    let users: [DKHUserOption]?
    let customers: [DKHCustomer]?
    let leads: [DKHLead]?
    let customerCases: [DKHCustomerCase]?
    let statusPhases: [DKHStatusPhase]?
}

struct DKHCustomer: Decodable, Identifiable {
    let id: Int
    let customerNumber: String?
    let customerType: String?
    let displayName: String
    let salutation: String?
    let firstName: String?
    let lastName: String?
    let companyName: String?
    let primaryEmail: String?
    let primaryPhone: String?
    let primaryMobile: String?
    let notes: String?
    let caseCount: Int?
    let updatedAt: String?
    let address: DKHCustomerAddress?
}

struct DKHLead: Decodable, Identifiable {
    let id: Int
    let leadNumber: String?
    let displayName: String
    let status: String?
    let source: String?
    let primaryEmail: String?
    let primaryPhone: String?
    let primaryMobile: String?
    let projectSummary: String?
    let updatedAt: String?
}

struct DKHCustomerAddress: Decodable {
    let street: String?
    let houseNumber: String?
    let addressExtra: String?
    let postalCode: String?
    let city: String?
    let country: String?
}

struct DKHStatusPhase: Decodable, Identifiable {
    let phase: Int
    let name: String
    let isTerminal: Bool?

    var id: Int { phase }
}

struct DKHCaseNote: Decodable, Identifiable {
    let id: Int
    let noteType: String?
    let body: String
    let createdBy: String?
    let createdAt: String?
}

struct DKHCaseDocument: Decodable, Identifiable {
    let id: Int
    let title: String
    let documentType: String?
    let documentStatus: String?
    let note: String?
    let hasFile: Bool?
    let originalFilename: String?
    let createdAt: String?
}

struct DKHCaseRegister: Identifiable {
    let key: String
    let label: String
    let phaseRange: ClosedRange<Int>?
    let description: String

    var id: String { key }
}

let DKHCaseRegisters: [DKHCaseRegister] = [
    DKHCaseRegister(key: "anfrage", label: "Anfrage", phaseRange: 1...1, description: "Projektgrundlagen und erster Anlass."),
    DKHCaseRegister(key: "beratung", label: "Beratung", phaseRange: 2...2, description: "Ansprechpartner und Abstimmung."),
    DKHCaseRegister(key: "planung", label: "Planung", phaseRange: 3...3, description: "Objekte, Raeume und Planungsnotizen."),
    DKHCaseRegister(key: "angebot_auftrag", label: "Angebot / Auftrag", phaseRange: 4...5, description: "Angebote, Auftragsunterlagen und Dokumente."),
    DKHCaseRegister(key: "abwicklung", label: "Abwicklung", phaseRange: 6...8, description: "Aufgaben, Termine und kritische Schritte."),
    DKHCaseRegister(key: "rechnung_abschluss", label: "Rechnung / Abschluss", phaseRange: 9...11, description: "Rechnung, Abschluss und Vorgangshistorie."),
    DKHCaseRegister(key: "kommunikation", label: "Kommunikation", phaseRange: 1...11, description: "Telefonnotizen, E-Mail-Entwuerfe und Historie."),
    DKHCaseRegister(key: "dokumente", label: "Dokumente", phaseRange: nil, description: "Dokumente aus der Vorgangsakte.")
]

struct DKHAdminState: Decodable {
    let users: [DKHAdminUser]?
    let roles: [DKHRole]?
    let companySettings: [String: String]?
    let integrations: [DKHIntegration]?
}

struct DKHAdminUser: Decodable, Identifiable {
    let id: Int
    let firstName: String?
    let lastName: String?
    let email: String
    let phone: String?
    let jobTitle: String?
    let department: String?
    let isActive: Bool?
    let roles: [String]?

    var displayName: String {
        [firstName, lastName].compactMap { $0 }.joined(separator: " ").trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

struct DKHRole: Decodable, Identifiable {
    let code: String
    let name: String

    var id: String { code }
}

struct DKHIntegration: Decodable, Identifiable {
    let id: Int
    let code: String
    let name: String
    let isEnabled: Bool?
    let connections: [DKHIntegrationConnection]?
}

struct DKHIntegrationConnection: Decodable, Identifiable {
    let id: Int
    let displayName: String
    let status: String
    let secretReference: String?
}

struct DKHLiveWorkspace {
    let overview: DKHOverviewState
    let customers: DKHCustomersState
    let admin: DKHAdminState?
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
    @Published private(set) var storedSession: DKHStoredSession?
    @Published private(set) var status: String = "device_not_granted"
    @Published var errorMessage: String?
    @Published var isGrantingDevice = false

    private let keychain = DKHKeychainStore()

    init() {
        if let storedSession = keychain.loadStoredSession() {
            self.storedSession = storedSession
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
        storedSession = nil
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
            let storedSession = DKHStoredSession(sessionToken: sessionToken, user: user, storedAt: Date())
            keychain.saveStoredSession(storedSession)
            self.storedSession = storedSession
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

struct DKHMobileDataClient {
    let sessionToken: String

    func fetchLiveWorkspace() async throws -> DKHLiveWorkspace {
        async let overview: DKHOverviewState = fetchResource("overview", as: DKHOverviewState.self)
        async let customers: DKHCustomersState = fetchResource("customers", as: DKHCustomersState.self)
        async let admin: DKHAdminState? = fetchOptionalResource("admin", as: DKHAdminState.self)
        return try await DKHLiveWorkspace(overview: overview, customers: customers, admin: admin)
    }

    func postAction(_ actionPath: String, fields: [String: String]) async throws {
        let url = URL(string: "\(DKHMobileAPI.baseURL.absoluteString)/actions/\(actionPath)")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "accept")
        request.setValue("application/x-www-form-urlencoded; charset=utf-8", forHTTPHeaderField: "content-type")
        request.setValue("Bearer \(sessionToken)", forHTTPHeaderField: "authorization")
        request.httpBody = formBody(fields)

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw DKHSessionError.serverMessage("Ungueltige Serverantwort.")
        }
        guard http.statusCode == 200 else {
            throw DKHSessionError.serverMessage("DKH Aktion konnte nicht ausgefuehrt werden (\(http.statusCode)).")
        }
        let decoded = try JSONDecoder().decode(DKHMobileActionResponse.self, from: data)
        guard decoded.status == "active" else {
            throw DKHSessionError.serverMessage("DKH Aktion ist nicht freigegeben (\(decoded.status)).")
        }
    }

    private func fetchResource<State: Decodable>(_ resource: String, as type: State.Type) async throws -> State {
        var request = URLRequest(url: DKHMobileAPI.baseURL.appending(path: resource))
        request.httpMethod = "GET"
        request.setValue("application/json", forHTTPHeaderField: "accept")
        request.setValue("Bearer \(sessionToken)", forHTTPHeaderField: "authorization")

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw DKHSessionError.serverMessage("Ungueltige Serverantwort.")
        }
        guard http.statusCode == 200 else {
            throw DKHSessionError.serverMessage("DKH Serverdaten konnten nicht geladen werden (\(http.statusCode)).")
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let decoded = try decoder.decode(DKHMobileResourceResponse<State>.self, from: data)
        guard decoded.status == "active" else {
            throw DKHSessionError.serverMessage("DKH Serverdaten sind nicht freigegeben (\(decoded.status)).")
        }
        return decoded.state
    }

    private func fetchOptionalResource<State: Decodable>(_ resource: String, as type: State.Type) async -> State? {
        try? await fetchResource(resource, as: type)
    }

    private func formBody(_ fields: [String: String]) -> Data {
        let encoded = fields
            .map { key, value in
                "\(percentEncode(key))=\(percentEncode(value))"
            }
            .joined(separator: "&")
        return Data(encoded.utf8)
    }

    private func percentEncode(_ value: String) -> String {
        var allowed = CharacterSet.urlQueryAllowed
        allowed.remove(charactersIn: "&+=?")
        return value.addingPercentEncoding(withAllowedCharacters: allowed) ?? value
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
            if let storedSession = session.storedSession {
                DKHCRMDashboardView(storedSession: storedSession)
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
    let storedSession: DKHStoredSession
    @State private var liveWorkspace: DKHLiveWorkspace?
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var actionMessage: String?

    var body: some View {
        Group {
            if let liveWorkspace {
                TabView {
                    DKHHomePage(
                        workspace: liveWorkspace,
                        user: storedSession.user,
                        isLoading: isLoading,
                        errorMessage: errorMessage,
                        actionMessage: actionMessage,
                        reload: { Task { await loadLiveWorkspace() } }
                    )
                    .tabItem { Label("Uebersicht", systemImage: "rectangle.grid.2x2") }

                    DKHCustomersPage(
                        customersState: liveWorkspace.customers,
                        runAction: runAction
                    )
                    .tabItem { Label("Kunden", systemImage: "person.2") }

                    DKHTasksPage(
                        overview: liveWorkspace.overview,
                        customersState: liveWorkspace.customers,
                        runAction: runAction
                    )
                    .tabItem { Label("Aufgaben", systemImage: "checklist") }

                    DKHEmailsPage(
                        overview: liveWorkspace.overview,
                        runAction: runAction
                    )
                    .tabItem { Label("E-Mails", systemImage: "envelope") }

                    DKHAppointmentsPage(overview: liveWorkspace.overview)
                        .tabItem { Label("Termine", systemImage: "calendar") }

                    DKHTemplatesPage()
                        .tabItem { Label("Vorlagen", systemImage: "doc.text") }

                    DKHAdminPage(admin: liveWorkspace.admin)
                        .tabItem { Label("Admin", systemImage: "gearshape") }
                }
            } else {
                NavigationStack {
                    List {
                        Section {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(storedSession.user.displayName)
                                    .font(.headline)
                                Text(storedSession.user.email)
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)
                            }
                            .padding(.vertical, 4)
                        }
                        Section {
                            if isLoading {
                                ProgressView("DKH Serverdaten werden geladen")
                            }
                            if let errorMessage {
                                Text(errorMessage)
                                    .foregroundStyle(.red)
                                Button("Erneut laden") {
                                    Task { await loadLiveWorkspace() }
                                }
                            }
                        }
                    }
                    .navigationTitle("DKH CRM")
                }
            }
        }
        .task {
            await loadLiveWorkspace()
        }
    }

    @MainActor
    private func loadLiveWorkspace() async {
        guard !isLoading else { return }
        isLoading = true
        errorMessage = nil
        do {
            liveWorkspace = try await DKHMobileDataClient(sessionToken: storedSession.sessionToken).fetchLiveWorkspace()
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    @MainActor
    private func runAction(_ path: String, _ fields: [String: String]) async {
        isLoading = true
        errorMessage = nil
        actionMessage = nil
        do {
            try await DKHMobileDataClient(sessionToken: storedSession.sessionToken).postAction(path, fields: fields)
            actionMessage = "Aenderung gespeichert."
            liveWorkspace = try await DKHMobileDataClient(sessionToken: storedSession.sessionToken).fetchLiveWorkspace()
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }
}

struct DKHHomePage: View {
    let workspace: DKHLiveWorkspace
    let user: DKHCRMUser
    let isLoading: Bool
    let errorMessage: String?
    let actionMessage: String?
    let reload: () -> Void

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
                    if let actionMessage {
                        Label(actionMessage, systemImage: "checkmark.circle")
                            .foregroundStyle(.green)
                    }
                    if let errorMessage {
                        Label(errorMessage, systemImage: "exclamationmark.triangle")
                            .foregroundStyle(.red)
                    }
                }

                Section("CRM Arbeitsbereich") {
                    DKHMetricRow(title: "Heutige Termine", value: workspace.overview.appointments?.count ?? 0, systemImage: "calendar")
                    DKHMetricRow(title: "Offene Aufgaben", value: workspace.overview.tasks?.count ?? 0, systemImage: "checklist")
                    DKHMetricRow(title: "E-Mails", value: workspace.overview.emails?.count ?? 0, systemImage: "envelope")
                    DKHMetricRow(title: "Aktive Vorgaenge", value: workspace.overview.customerCases?.count ?? 0, systemImage: "folder")
                    DKHMetricRow(title: "Kunden", value: workspace.customers.customers?.count ?? 0, systemImage: "person.2")
                }

                Section("Naechste Termine") {
                    let appointments = workspace.overview.appointments ?? []
                    if appointments.isEmpty {
                        Text("Keine Termine im aktuellen Sichtbereich.")
                            .foregroundStyle(.secondary)
                    } else {
                        ForEach(appointments.prefix(5)) { appointment in
                            DKHAppointmentRow(appointment: appointment)
                        }
                    }
                }

                Section("Akute Arbeit") {
                    let tasks = workspace.overview.tasks ?? []
                    if tasks.isEmpty {
                        Text("Keine offenen Aufgaben.")
                            .foregroundStyle(.secondary)
                    } else {
                        ForEach(tasks.prefix(5)) { task in
                            DKHTaskRow(task: task)
                        }
                    }
                }
            }
            .navigationTitle("DKH CRM")
            .toolbar {
                Button {
                    reload()
                } label: {
                    Image(systemName: "arrow.clockwise")
                }
                .disabled(isLoading)
            }
            .refreshable {
                reload()
            }
        }
    }
}

struct DKHAppointmentsPage: View {
    let overview: DKHOverviewState

    var appointments: [DKHAppointment] {
        overview.appointments ?? []
    }

    var body: some View {
        NavigationStack {
            List {
                Section("Heute") {
                    let today = appointments.filter { $0.startsAt.hasPrefix(Date().formatted(.iso8601.year().month().day())) }
                    if today.isEmpty {
                        Text("Heute sind keine Termine sichtbar.")
                            .foregroundStyle(.secondary)
                    } else {
                        ForEach(today) { appointment in
                            DKHAppointmentRow(appointment: appointment)
                        }
                    }
                }
                Section("Alle sichtbaren Termine") {
                    if appointments.isEmpty {
                        Text("Die DKH API liefert aktuell keine Termine.")
                            .foregroundStyle(.secondary)
                    } else {
                        ForEach(appointments) { appointment in
                            DKHAppointmentRow(appointment: appointment)
                        }
                    }
                }
            }
            .navigationTitle("Termine")
        }
    }
}

struct DKHTasksPage: View {
    let overview: DKHOverviewState
    let customersState: DKHCustomersState
    let runAction: (String, [String: String]) async -> Void
    @State private var showingNewTask = false

    var body: some View {
        NavigationStack {
            List {
                Section("Offene Aufgaben") {
                    let tasks = overview.tasks ?? []
                    if tasks.isEmpty {
                        Text("Keine Aufgaben sichtbar.")
                            .foregroundStyle(.secondary)
                    } else {
                        ForEach(tasks) { task in
                            NavigationLink {
                                DKHTaskDetailPage(task: task, runAction: runAction)
                            } label: {
                                DKHTaskRow(task: task)
                            }
                        }
                    }
                }
            }
            .navigationTitle("Aufgaben")
            .toolbar {
                Button {
                    showingNewTask = true
                } label: {
                    Image(systemName: "plus")
                }
            }
            .sheet(isPresented: $showingNewTask) {
                DKHNewTaskSheet(
                    overview: overview,
                    customersState: customersState,
                    runAction: runAction
                )
            }
        }
    }
}

struct DKHNewTaskSheet: View {
    let overview: DKHOverviewState
    let customersState: DKHCustomersState
    let runAction: (String, [String: String]) async -> Void
    @Environment(\.dismiss) private var dismiss
    @State private var title = ""
    @State private var description = ""
    @State private var statusCode = "new"
    @State private var priority = "normal"
    @State private var assignedUserId = ""
    @State private var customerCaseId = ""
    @State private var isSaving = false

    var body: some View {
        NavigationStack {
            Form {
                Section("Neue Aufgabe") {
                    TextField("Titel", text: $title)
                    TextField("Beschreibung", text: $description, axis: .vertical)
                    Picker("Status", selection: $statusCode) {
                        ForEach(overview.taskStatuses ?? []) { status in
                            Text(status.name).tag(status.code)
                        }
                    }
                    Picker("Prioritaet", selection: $priority) {
                        Text("Normal").tag("normal")
                        Text("Hoch").tag("high")
                        Text("Dringend").tag("urgent")
                        Text("Niedrig").tag("low")
                    }
                    Picker("Zustaendig", selection: $assignedUserId) {
                        Text("Ich").tag("")
                        ForEach(overview.users ?? []) { user in
                            Text(user.displayName.isEmpty ? (user.email ?? "Benutzer") : user.displayName)
                                .tag(String(user.id))
                        }
                    }
                    Picker("Vorgang", selection: $customerCaseId) {
                        Text("Ohne Vorgang").tag("")
                        ForEach(customersState.customerCases ?? []) { item in
                            Text([item.caseNumber, item.customerDisplayName].compactMap { $0 }.joined(separator: " · "))
                                .tag(String(item.id))
                        }
                    }
                }
            }
            .navigationTitle("Aufgabe")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Abbrechen") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Speichern") {
                        Task {
                            isSaving = true
                            var fields = [
                                "title": title,
                                "description": description,
                                "status_code": statusCode,
                                "priority": priority,
                                "reminder_overview_enabled": "true",
                            ]
                            if !assignedUserId.isEmpty { fields["assigned_user_id"] = assignedUserId }
                            if !customerCaseId.isEmpty { fields["customer_case_id"] = customerCaseId }
                            await runAction("overview/tasks", fields)
                            isSaving = false
                            dismiss()
                        }
                    }
                    .disabled(title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || isSaving)
                }
            }
        }
    }
}

struct DKHTaskDetailPage: View {
    let task: DKHTask
    let runAction: (String, [String: String]) async -> Void

    var body: some View {
        List {
            Section("Aufgabe") {
                Text(task.title)
                    .font(.headline)
                if let description = task.description, !description.isEmpty {
                    Text(description)
                }
                DKHInfoRow("Status", task.statusName)
                DKHInfoRow("Prioritaet", task.priority)
                DKHInfoRow("Faellig", task.dueAt)
                DKHInfoRow("Vorgang", task.caseInfo?.customerDisplayName)
            }
            Section("Aktionen") {
                Button("Archivieren") {
                    Task { await runAction("overview/tasks/\(task.id)/archive", [:]) }
                }
                Button("Loeschen", role: .destructive) {
                    Task { await runAction("overview/tasks/\(task.id)/delete", [:]) }
                }
            }
        }
        .navigationTitle("Aufgabe")
    }
}

struct DKHEmailsPage: View {
    let overview: DKHOverviewState
    let runAction: (String, [String: String]) async -> Void
    @State private var senderFilter = "Alle"

    var filteredEmails: [DKHEmail] {
        let emails = overview.emails ?? []
        guard senderFilter != "Alle" else { return emails }
        return emails.filter { email in
            (email.participants ?? []).contains { $0.emailAddress == senderFilter }
        }
    }

    var senders: [String] {
        let values = (overview.emails ?? [])
            .flatMap { $0.participants ?? [] }
            .map(\.emailAddress)
        return ["Alle"] + Array(Set(values)).sorted()
    }

    var body: some View {
        NavigationStack {
            List {
                Section("Absender filtern") {
                    Picker("Absender", selection: $senderFilter) {
                        ForEach(senders, id: \.self) { sender in
                            Text(sender).tag(sender)
                        }
                    }
                }
                Section("Nachrichten") {
                    if filteredEmails.isEmpty {
                        Text("Keine E-Mails im aktuellen Sichtbereich.")
                            .foregroundStyle(.secondary)
                    } else {
                        ForEach(filteredEmails) { email in
                            NavigationLink {
                                DKHEmailDetailPage(email: email, cases: overview.customerCases ?? [], runAction: runAction)
                            } label: {
                                DKHEmailRow(email: email)
                            }
                        }
                    }
                }
            }
            .navigationTitle("E-Mails")
        }
    }
}

struct DKHEmailDetailPage: View {
    let email: DKHEmail
    let cases: [DKHCustomerCase]
    let runAction: (String, [String: String]) async -> Void
    @State private var selectedCaseId = ""

    var body: some View {
        List {
            Section("Nachricht") {
                Text(email.subject)
                    .font(.headline)
                DKHInfoRow("Empfangen", email.receivedAt)
                if let snippet = email.snippet, !snippet.isEmpty {
                    Text(snippet)
                }
                ForEach(email.participants ?? [], id: \.emailAddress) { participant in
                    DKHInfoRow(participant.type ?? "Kontakt", participant.emailAddress)
                }
            }
            Section("Vorgangszuordnung") {
                if let linkedCases = email.cases, !linkedCases.isEmpty {
                    ForEach(linkedCases) { item in
                        Label([item.caseNumber, item.customerDisplayName].compactMap { $0 }.joined(separator: " · "), systemImage: "link")
                    }
                }
                Picker("Vorgang", selection: $selectedCaseId) {
                    Text("Vorgang waehlen").tag("")
                    ForEach(cases) { item in
                        Text([item.caseNumber, item.customerDisplayName].compactMap { $0 }.joined(separator: " · "))
                            .tag(String(item.id))
                    }
                }
                Button("Zuordnen") {
                    Task {
                        await runAction("overview/emails/assign", [
                            "email_message_id": String(email.id),
                            "customer_case_id": selectedCaseId,
                        ])
                    }
                }
                .disabled(selectedCaseId.isEmpty)
            }
            if let suggestions = email.suggestions, !suggestions.isEmpty {
                Section("Vorschlaege") {
                    ForEach(suggestions) { suggestion in
                        VStack(alignment: .leading, spacing: 6) {
                            Text(suggestion.caseInfo?.customerDisplayName ?? "Vorschlag")
                                .font(.headline)
                            if let reason = suggestion.reason {
                                Text(reason)
                                    .foregroundStyle(.secondary)
                            }
                            Button("Vorschlag uebernehmen") {
                                Task { await runAction("overview/emails/suggestions/\(suggestion.id)/accept", [:]) }
                            }
                        }
                    }
                }
            }
            Section("Aktionen") {
                Button("Loeschen", role: .destructive) {
                    Task { await runAction("overview/emails/\(email.id)/delete", [:]) }
                }
            }
        }
        .navigationTitle("E-Mail")
    }
}

struct DKHCustomersPage: View {
    let customersState: DKHCustomersState
    let runAction: (String, [String: String]) async -> Void
    @State private var query = ""
    @State private var isShowingLeadForm = false
    @State private var isShowingCustomerForm = false

    var customers: [DKHCustomer] {
        let all = customersState.customers ?? []
        let normalizedQuery = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !normalizedQuery.isEmpty else { return all }
        return all.filter { customerMatches($0, normalizedQuery) }
    }

    var shouldOfferCreateChoice: Bool {
        query.trimmingCharacters(in: .whitespacesAndNewlines).count >= 3 && customers.isEmpty
    }

    var body: some View {
        NavigationStack {
            List {
                Section("Neukundenanlage") {
                    TextField("Name, E-Mail, Kunden-/Vorgangsnummer, CARAT oder Telefon", text: $query)
                        .textInputAutocapitalization(.words)

                    if query.trimmingCharacters(in: .whitespacesAndNewlines).count < 3 {
                        Text("Geben Sie mindestens drei Zeichen ein.")
                            .foregroundStyle(.secondary)
                    } else if shouldOfferCreateChoice {
                        VStack(alignment: .leading, spacing: 10) {
                            Text("Kein Treffer gefunden")
                                .font(.headline)
                            Text("Legen Sie zuerst fest, ob eine schlanke Leadakte oder direkt eine Kundenakte entstehen soll.")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                            HStack {
                                Button("Leadanlage") {
                                    isShowingLeadForm = true
                                }
                                .buttonStyle(.borderedProminent)

                                Button("Kundenanlage") {
                                    isShowingCustomerForm = true
                                }
                                .buttonStyle(.bordered)
                            }
                        }
                        .padding(.vertical, 4)
                    }
                }
                Section("Kunden direkt Suche") {
                    if customers.isEmpty {
                        Text("Keine Kunden gefunden.")
                            .foregroundStyle(.secondary)
                    } else {
                        ForEach(customers) { customer in
                            NavigationLink {
                                DKHCustomerDetailPage(
                                    customer: customer,
                                    cases: cases(for: customer),
                                    customersState: customersState,
                                    runAction: runAction
                                )
                            } label: {
                                DKHCustomerRow(customer: customer)
                            }
                        }
                    }
                }
                Section("Leads") {
                    ForEach(customersState.leads ?? []) { lead in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(lead.displayName)
                                .font(.headline)
                            Text([lead.leadNumber, lead.status, lead.source].compactMap { $0 }.joined(separator: " · "))
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                            if let summary = lead.projectSummary, !summary.isEmpty {
                                Text(summary)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                }
            }
            .navigationTitle("Kunden")
            .sheet(isPresented: $isShowingLeadForm) {
                DKHNewLeadSheet(
                    initialSearchText: query,
                    customersState: customersState,
                    runAction: runAction
                )
            }
            .sheet(isPresented: $isShowingCustomerForm) {
                DKHNewCustomerSheet(
                    initialSearchText: query,
                    customersState: customersState,
                    runAction: runAction
                )
            }
        }
    }

    private func cases(for customer: DKHCustomer) -> [DKHCustomerCase] {
        (customersState.customerCases ?? []).filter { $0.customerId == customer.id }
    }

    private func customerMatches(_ customer: DKHCustomer, _ searchText: String) -> Bool {
        let directHit = [
            customer.displayName,
            customer.customerNumber,
            customer.primaryEmail,
            customer.primaryPhone,
            customer.primaryMobile
        ].compactMap { $0?.localizedCaseInsensitiveContains(searchText) }.contains(true)
        if directHit { return true }
        return cases(for: customer).contains { item in
            [
                item.caseNumber,
                item.caratOrderNumber,
                item.caseTitle,
                item.statusPhaseName
            ].compactMap { $0?.localizedCaseInsensitiveContains(searchText) }.contains(true)
        }
    }
}

struct DKHNewLeadSheet: View {
    let initialSearchText: String
    let customersState: DKHCustomersState
    let runAction: (String, [String: String]) async -> Void
    @Environment(\.dismiss) private var dismiss
    @State private var firstName = ""
    @State private var lastName = ""
    @State private var companyName = ""
    @State private var email = ""
    @State private var phone = ""
    @State private var projectSummary = ""
    @State private var initialMessage = ""
    @State private var source = "website"
    @State private var preferredContactChannel = "phone"
    @State private var ownerUserId = ""

    var body: some View {
        NavigationStack {
            Form {
                Section("Lead anlegen") {
                    TextField("Vorname", text: $firstName)
                    TextField("Nachname", text: $lastName)
                    TextField("Firma / Objektbezug", text: $companyName)
                    TextField("E-Mail", text: $email)
                        .keyboardType(.emailAddress)
                        .textInputAutocapitalization(.never)
                    TextField("Telefon", text: $phone)
                        .keyboardType(.phonePad)
                    Picker("Source", selection: $source) {
                        Text("Website").tag("website")
                        Text("E-Mail").tag("email")
                        Text("Telefon").tag("phone")
                        Text("Ausstellung").tag("showroom")
                        Text("Empfehlung").tag("referral")
                        Text("Sonstiges").tag("other")
                    }
                    Picker("Bevorzugter Kontaktweg", selection: $preferredContactChannel) {
                        Text("Telefon").tag("phone")
                        Text("E-Mail").tag("email")
                        Text("Mobil").tag("mobile")
                        Text("WhatsApp").tag("whatsapp")
                        Text("Noch unklar").tag("none")
                    }
                }
                Section("Anfrage") {
                    TextField("Kurzbeschreibung", text: $projectSummary, axis: .vertical)
                    TextField("Erste Nachricht / Gespraechsnotiz", text: $initialMessage, axis: .vertical)
                        .lineLimit(3...6)
                }
                Section("Zustaendig") {
                    Picker("Benutzer", selection: $ownerUserId) {
                        Text("DKH Server waehlt Standard").tag("")
                        ForEach(customersState.users ?? []) { user in
                            Text(user.displayName.isEmpty ? user.email ?? "Benutzer" : user.displayName)
                                .tag(String(user.id))
                        }
                    }
                }
            }
            .navigationTitle("Lead")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Schliessen") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Speichern") {
                        Task {
                            var fields: [String: String] = [
                                "source": source,
                                "source_channel": source,
                                "preferred_contact_channel": preferredContactChannel,
                                "first_name": firstName,
                                "last_name": lastName,
                                "company_name": companyName,
                                "primary_email": email,
                                "primary_phone": phone,
                                "project_summary": projectSummary,
                                "initial_message": initialMessage.isEmpty ? initialSearchText : initialMessage
                            ]
                            if !ownerUserId.isEmpty { fields["owner_user_id"] = ownerUserId }
                            await runAction("customers/leads", fields)
                            dismiss()
                        }
                    }
                    .disabled(initialMessage.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && initialSearchText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
            }
            .onAppear {
                seedNameFields()
                if initialMessage.isEmpty {
                    initialMessage = initialSearchText
                }
            }
        }
    }

    private func seedNameFields() {
        guard firstName.isEmpty, lastName.isEmpty, companyName.isEmpty else { return }
        let parts = initialSearchText.split(separator: " ").map(String.init)
        if parts.count >= 2 {
            firstName = parts.dropLast().joined(separator: " ")
            lastName = parts.last ?? ""
        } else if let first = parts.first {
            lastName = first
        }
    }
}

struct DKHNewCustomerSheet: View {
    let initialSearchText: String
    let customersState: DKHCustomersState
    let runAction: (String, [String: String]) async -> Void
    @Environment(\.dismiss) private var dismiss
    @State private var customerType = "private"
    @State private var salutation = ""
    @State private var firstName = ""
    @State private var lastName = ""
    @State private var companyName = ""
    @State private var email = ""
    @State private var phone = ""
    @State private var street = ""
    @State private var houseNumber = ""
    @State private var postalCode = ""
    @State private var city = ""
    @State private var notes = ""
    @State private var createCase = true
    @State private var caseTitle = ""
    @State private var caratOrderNumber = ""
    @State private var statusPhaseId = "1"
    @State private var ownerUserId = ""

    var body: some View {
        NavigationStack {
            Form {
                Section("Kunde anlegen") {
                    Picker("Kundentyp", selection: $customerType) {
                        Text("Privatkunde").tag("private")
                        Text("Objektkunde").tag("company")
                    }
                    Picker("Anrede", selection: $salutation) {
                        Text("Keine Angabe").tag("")
                        Text("Herr").tag("Herr")
                        Text("Frau").tag("Frau")
                        Text("Divers").tag("Divers")
                        Text("Familie").tag("Familie")
                    }
                    if customerType == "company" {
                        TextField("Firma", text: $companyName)
                    } else {
                        TextField("Vorname", text: $firstName)
                        TextField("Nachname", text: $lastName)
                    }
                    TextField("E-Mail", text: $email)
                        .keyboardType(.emailAddress)
                        .textInputAutocapitalization(.never)
                    TextField("Telefon", text: $phone)
                        .keyboardType(.phonePad)
                }
                Section("Adresse") {
                    TextField("Strasse", text: $street)
                    TextField("Hausnummer", text: $houseNumber)
                    TextField("PLZ", text: $postalCode)
                    TextField("Ort", text: $city)
                }
                Section("Vorgang") {
                    Toggle("Direkt einen Vorgang anlegen", isOn: $createCase)
                    if createCase {
                        TextField("Vorgangstitel", text: $caseTitle)
                        TextField("CARAT Vorgangsnummer", text: $caratOrderNumber)
                            .textInputAutocapitalization(.characters)
                        Picker("Statusphase", selection: $statusPhaseId) {
                            ForEach(customersState.statusPhases ?? []) { phase in
                                Text("\(phase.phase). \(phase.name)").tag(String(phase.phase))
                            }
                        }
                    }
                }
                Section("Zustaendig / Notizen") {
                    Picker("Benutzer", selection: $ownerUserId) {
                        Text("DKH Server waehlt Standard").tag("")
                        ForEach(customersState.users ?? []) { user in
                            Text(user.displayName.isEmpty ? user.email ?? "Benutzer" : user.displayName)
                                .tag(String(user.id))
                        }
                    }
                    TextField("Notizen", text: $notes, axis: .vertical)
                        .lineLimit(2...5)
                }
            }
            .navigationTitle("Kunde")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Schliessen") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Speichern") {
                        Task {
                            var fields: [String: String] = [
                                "customer_type": customerType,
                                "salutation": salutation,
                                "first_name": firstName,
                                "last_name": lastName,
                                "company_name": companyName,
                                "primary_email": email,
                                "primary_phone": phone,
                                "street": street,
                                "house_number": houseNumber,
                                "postal_code": postalCode,
                                "city": city,
                                "country": "DE",
                                "tax_treatment": "standard_de",
                                "notes": notes,
                                "create_case": createCase ? "true" : "false",
                                "case_title": caseTitle,
                                "carat_order_number": caratOrderNumber,
                                "status_phase_id": statusPhaseId
                            ]
                            if !ownerUserId.isEmpty {
                                fields["owner_user_id"] = ownerUserId
                                fields["responsible_user_id"] = ownerUserId
                            }
                            await runAction("customers/customers", fields)
                            dismiss()
                        }
                    }
                    .disabled(customerType == "company" ? companyName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty : lastName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
            }
            .onAppear {
                seedNameFields()
                if caseTitle.isEmpty {
                    caseTitle = "Kuechenplanung"
                }
            }
        }
    }

    private func seedNameFields() {
        guard firstName.isEmpty, lastName.isEmpty, companyName.isEmpty else { return }
        let parts = initialSearchText.split(separator: " ").map(String.init)
        if parts.count >= 2 {
            firstName = parts.dropLast().joined(separator: " ")
            lastName = parts.last ?? ""
        } else if let first = parts.first {
            lastName = first
        }
    }
}

struct DKHCustomerDetailPage: View {
    let customer: DKHCustomer
    let cases: [DKHCustomerCase]
    let customersState: DKHCustomersState
    let runAction: (String, [String: String]) async -> Void
    @State private var isShowingCaseForm = false

    var body: some View {
        List {
            Section("Stammdaten-Snapshot") {
                Text(customer.displayName)
                    .font(.headline)
                DKHInfoRow("Kundennummer", customer.customerNumber)
                DKHInfoRow("E-Mail", customer.primaryEmail)
                DKHInfoRow("Telefon", customer.primaryPhone ?? customer.primaryMobile)
                DKHInfoRow("Adresse", addressText(customer.address))
                if let notes = customer.notes, !notes.isEmpty {
                    Text(notes)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            Section("Kontakt") {
                if let phone = customer.primaryPhone ?? customer.primaryMobile, let url = URL(string: "tel:\(phone)") {
                    Link("Telefon", destination: url)
                }
                if let email = customer.primaryEmail, let url = URL(string: "mailto:\(email)") {
                    Link("E-Mail", destination: url)
                }
            }
            Section("Vorgangsregal") {
                if cases.isEmpty {
                    Text("Keine Vorgaenge zu diesem Kunden.")
                        .foregroundStyle(.secondary)
                } else {
                    ForEach(cases) { item in
                        NavigationLink {
                            DKHCaseDetailPage(
                                caseRecord: item,
                                customersState: customersState,
                                runAction: runAction
                            )
                        } label: {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(item.caseTitle ?? item.customerDisplayName)
                                    .font(.headline)
                                Text([item.caseNumber, item.statusPhaseName].compactMap { $0 }.joined(separator: " · "))
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                }
            }
            Section {
                Button("Vorgang anlegen") {
                    isShowingCaseForm = true
                }
            }
        }
        .navigationTitle(customer.displayName)
        .sheet(isPresented: $isShowingCaseForm) {
            DKHNewCaseSheet(
                customer: customer,
                customersState: customersState,
                runAction: runAction
            )
        }
    }
}

struct DKHNewCaseSheet: View {
    let customer: DKHCustomer
    let customersState: DKHCustomersState
    let runAction: (String, [String: String]) async -> Void
    @Environment(\.dismiss) private var dismiss
    @State private var caseTitle = "Kuechenplanung"
    @State private var caratOrderNumber = ""
    @State private var statusPhaseId = "1"
    @State private var responsibleUserId = ""

    var body: some View {
        NavigationStack {
            Form {
                Section(customer.displayName) {
                    TextField("Vorgangstitel", text: $caseTitle)
                    TextField("CARAT Vorgangsnummer", text: $caratOrderNumber)
                        .textInputAutocapitalization(.characters)
                    Picker("Statusphase", selection: $statusPhaseId) {
                        ForEach(customersState.statusPhases ?? []) { phase in
                            Text("\(phase.phase). \(phase.name)").tag(String(phase.phase))
                        }
                    }
                    Picker("Vorgang verantwortlich", selection: $responsibleUserId) {
                        Text("DKH Server waehlt Standard").tag("")
                        ForEach(customersState.users ?? []) { user in
                            Text(user.displayName.isEmpty ? user.email ?? "Benutzer" : user.displayName)
                                .tag(String(user.id))
                        }
                    }
                }
            }
            .navigationTitle("Vorgang")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Schliessen") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Speichern") {
                        Task {
                            var fields: [String: String] = [
                                "customer_id": String(customer.id),
                                "case_title": caseTitle,
                                "carat_order_number": caratOrderNumber,
                                "case_status": "active",
                                "status_phase_id": statusPhaseId
                            ]
                            if !responsibleUserId.isEmpty { fields["responsible_user_id"] = responsibleUserId }
                            await runAction("customers/cases", fields)
                            dismiss()
                        }
                    }
                    .disabled(caseTitle.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
            }
        }
    }
}

struct DKHCaseDetailPage: View {
    let caseRecord: DKHCustomerCase
    let customersState: DKHCustomersState
    let runAction: (String, [String: String]) async -> Void
    @State private var selectedRegister: String
    @State private var caseTitle: String
    @State private var caratOrderNumber: String
    @State private var statusPhaseId: String
    @State private var responsibleUserId: String
    @State private var registerNote = ""
    @State private var communicationNote = ""

    init(
        caseRecord: DKHCustomerCase,
        customersState: DKHCustomersState,
        runAction: @escaping (String, [String: String]) async -> Void
    ) {
        self.caseRecord = caseRecord
        self.customersState = customersState
        self.runAction = runAction
        _selectedRegister = State(initialValue: DKHDefaultRegister(for: caseRecord.statusPhase))
        _caseTitle = State(initialValue: caseRecord.caseTitle ?? "")
        _caratOrderNumber = State(initialValue: caseRecord.caratOrderNumber ?? "")
        _statusPhaseId = State(initialValue: String(caseRecord.statusPhase ?? 1))
        _responsibleUserId = State(initialValue: caseRecord.responsibleUserId.map(String.init) ?? "")
    }

    var activeRegister: DKHCaseRegister {
        DKHCaseRegisters.first { $0.key == selectedRegister } ?? DKHCaseRegisters[0]
    }

    var body: some View {
        List {
            Section("Geoeffnete Vorgangsmappe") {
                Text(caseRecord.caseTitle ?? caseRecord.customerDisplayName)
                    .font(.headline)
                DKHInfoRow("Vorgang", caseRecord.caseNumber)
                DKHInfoRow("CARAT", caseRecord.caratOrderNumber)
                DKHInfoRow("Status", caseRecord.statusPhaseName)
            }
            Section("Vorgang bearbeiten") {
                TextField("Vorgangstitel", text: $caseTitle)
                TextField("CARAT Vorgangsnummer", text: $caratOrderNumber)
                    .textInputAutocapitalization(.characters)
                Picker("Ablaufphase", selection: $statusPhaseId) {
                    ForEach(customersState.statusPhases ?? []) { phase in
                        Text("\(phase.phase). \(phase.name)").tag(String(phase.phase))
                    }
                }
                Picker("Vorgang verantwortlich", selection: $responsibleUserId) {
                    Text("DKH Server waehlt Standard").tag("")
                    ForEach(customersState.users ?? []) { user in
                        Text(user.displayName.isEmpty ? user.email ?? "Benutzer" : user.displayName)
                            .tag(String(user.id))
                    }
                }
                Button("Vorgang speichern") {
                    Task {
                        var fields: [String: String] = [
                            "case_title": caseTitle,
                            "carat_order_number": caratOrderNumber,
                            "case_status": caseRecord.caseStatus ?? "active",
                            "status_phase_id": statusPhaseId
                        ]
                        if !responsibleUserId.isEmpty { fields["responsible_user_id"] = responsibleUserId }
                        await runAction("customers/cases/\(caseRecord.id)", fields)
                    }
                }
            }
            Section("Register") {
                Picker("Register", selection: $selectedRegister) {
                    ForEach(DKHCaseRegisters) { item in
                        Text(item.label).tag(item.key)
                    }
                }
                Text(activeRegister.description)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                if let phaseRange = activeRegister.phaseRange {
                    Text(registerStateText(phaseRange))
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            DKHCaseRegisterSection(
                register: activeRegister,
                caseRecord: caseRecord,
                registerNote: $registerNote,
                communicationNote: $communicationNote,
                runAction: runAction
            )
            Section("Notizen") {
                if let notes = caseRecord.notes, !notes.isEmpty {
                    ForEach(notes) { note in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(note.body)
                            Text([note.createdBy, note.createdAt].compactMap { $0 }.joined(separator: " · "))
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                } else {
                    Text("Keine Notizen.")
                        .foregroundStyle(.secondary)
                }
            }
            Section("Dokumente") {
                if let documents = caseRecord.documents, !documents.isEmpty {
                    ForEach(documents) { document in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(document.title)
                                .font(.headline)
                            Text([document.documentType, document.documentStatus, document.originalFilename].compactMap { $0 }.joined(separator: " · "))
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                    }
                } else {
                    Text("Keine Dokumente im aktuellen Register.")
                        .foregroundStyle(.secondary)
                }
            }
        }
        .navigationTitle("Vorgang")
    }

    private func registerStateText(_ phaseRange: ClosedRange<Int>) -> String {
        let currentPhase = caseRecord.statusPhase ?? 1
        if phaseRange.upperBound < currentPhase { return "Vergangenheit" }
        if phaseRange.lowerBound > currentPhase { return "Zukunft" }
        return "Aktueller Bereich"
    }
}

struct DKHCaseRegisterSection: View {
    let register: DKHCaseRegister
    let caseRecord: DKHCustomerCase
    @Binding var registerNote: String
    @Binding var communicationNote: String
    let runAction: (String, [String: String]) async -> Void

    var body: some View {
        Section(register.label) {
            if register.key == "kommunikation" {
                TextField("Telefonnotiz, E-Mail-Entwurf oder Vorgangshinweis", text: $communicationNote, axis: .vertical)
                    .lineLimit(3...8)
                Button("Notiz speichern") {
                    Task {
                        await runAction("customers/cases/\(caseRecord.id)/notes", [
                            "note_type": "general",
                            "body": communicationNote
                        ])
                        communicationNote = ""
                    }
                }
                .disabled(communicationNote.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            } else if register.key == "dokumente" {
                Text("Dokumente werden unten in der Dokumentenliste angezeigt.")
                    .foregroundStyle(.secondary)
            } else {
                if let values = caseRecord.sections?[sectionCode(for: register.key)], !values.isEmpty {
                    ForEach(values.sorted(by: { $0.key < $1.key }), id: \.key) { key, value in
                        DKHInfoRow(prettySectionKey(key), value.displayText)
                    }
                } else {
                    Text("Noch keine Registerdaten gespeichert.")
                        .foregroundStyle(.secondary)
                }
                TextField("Register-Notiz / Arbeitsstand", text: $registerNote, axis: .vertical)
                    .lineLimit(3...8)
                Button("Register speichern") {
                    Task {
                        await runAction("customers/cases/\(caseRecord.id)/sections/\(sectionCode(for: register.key))", [
                            "mobile_note": registerNote,
                            "mobile_register": register.label
                        ])
                        registerNote = ""
                    }
                }
                .disabled(registerNote.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            }
        }
    }

    private func sectionCode(for registerKey: String) -> String {
        switch registerKey {
        case "anfrage", "planung":
            return "project_objects"
        case "beratung":
            return "project_contacts"
        case "abwicklung":
            return "process_control"
        case "angebot_auftrag", "rechnung_abschluss":
            return "documents"
        default:
            return registerKey
        }
    }

    private func prettySectionKey(_ key: String) -> String {
        key.replacingOccurrences(of: "_", with: " ").capitalized
    }
}

func DKHDefaultRegister(for phase: Int?) -> String {
    let currentPhase = phase ?? 1
    return DKHCaseRegisters.first { item in
        guard let range = item.phaseRange, item.key != "kommunikation" else { return false }
        return range.contains(currentPhase)
    }?.key ?? "anfrage"
}

struct DKHTemplatesPage: View {
    @State private var selectedTemplate: String?
    @State private var customerName = ""
    @State private var customerNumber = ""
    @State private var documentDate = ""
    @State private var grossAmount = ""
    @State private var positionText = ""
    @State private var paymentOne = "30"
    @State private var paymentTwo = "60"
    @State private var paymentRest = "10"

    var body: some View {
        NavigationStack {
            Form {
                Section("Blanko-Vorlagen") {
                    Button("Blanko Kaufvertrag") {
                        selectedTemplate = "Kaufvertrag"
                    }
                    Button("Blanko Rechnung") {
                        selectedTemplate = "Rechnung"
                    }
                }
                if let selectedTemplate {
                    Section(selectedTemplate) {
                        TextField("Kundennummer", text: $customerNumber)
                        TextField("Kundenname", text: $customerName)
                        TextField("Datum", text: $documentDate)
                        TextField("Positionen", text: $positionText, axis: .vertical)
                        TextField("Bruttobetrag", text: $grossAmount)
                            .keyboardType(.decimalPad)
                        if selectedTemplate == "Kaufvertrag" {
                            TextField("Anzahlung bei Auftrag in %", text: $paymentOne)
                                .keyboardType(.decimalPad)
                            TextField("Zahlung vor Lieferung in %", text: $paymentTwo)
                                .keyboardType(.decimalPad)
                            TextField("Restzahlung in %", text: $paymentRest)
                                .keyboardType(.decimalPad)
                        }
                    }
                    Section("Berechnung") {
                        DKHInfoRow("Brutto", formatCurrency(grossAmount))
                        if selectedTemplate == "Kaufvertrag" {
                            DKHInfoRow("Bei Auftrag", percentAmount(grossAmount, paymentOne))
                            DKHInfoRow("Vor Lieferung", percentAmount(grossAmount, paymentTwo))
                            DKHInfoRow("Rest", percentAmount(grossAmount, paymentRest))
                        }
                    }
                }
            }
            .navigationTitle("Vorlagen")
        }
    }
}

func decimalValue(_ text: String) -> Double {
    let normalized = text.replacingOccurrences(of: ".", with: "").replacingOccurrences(of: ",", with: ".")
    let filtered = normalized.filter { character in
        character.isNumber || character == "." || character == "-"
    }
    return Double(filtered) ?? 0
}

func formatCurrency(_ text: String) -> String {
    let value = decimalValue(text)
    guard value > 0 else { return "0,00 EUR" }
    return value.formatted(.currency(code: "EUR").locale(Locale(identifier: "de_DE")))
}

func percentAmount(_ amount: String, _ percent: String) -> String {
    let value = decimalValue(amount) * decimalValue(percent) / 100
    guard value > 0 else { return "0,00 EUR" }
    return value.formatted(.currency(code: "EUR").locale(Locale(identifier: "de_DE")))
}

struct DKHAdminPage: View {
    let admin: DKHAdminState?

    var body: some View {
        NavigationStack {
            List {
                if let admin {
                    Section("Benutzer") {
                        ForEach(admin.users ?? []) { user in
                            VStack(alignment: .leading, spacing: 4) {
                                Text(user.displayName.isEmpty ? user.email : user.displayName)
                                    .font(.headline)
                                Text([user.email, user.jobTitle, user.department].compactMap { $0 }.joined(separator: " · "))
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                    Section("Firmenstammdaten") {
                        ForEach((admin.companySettings ?? [:]).keys.sorted(), id: \.self) { key in
                            DKHInfoRow(key, admin.companySettings?[key])
                        }
                    }
                    Section("Integrationen") {
                        ForEach(admin.integrations ?? []) { integration in
                            DKHInfoRow(integration.name, integration.isEnabled == true ? "Aktiv" : "Inaktiv")
                        }
                    }
                } else {
                    Section {
                        Text("Adminbereich ist fuer diesen Nutzer nicht freigegeben.")
                            .foregroundStyle(.secondary)
                    }
                }
            }
            .navigationTitle("Admin")
        }
    }
}

struct DKHAppointmentRow: View {
    let appointment: DKHAppointment

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(appointment.title)
                .font(.headline)
            Text([appointment.startsAt, appointment.location].compactMap { $0 }.joined(separator: " · "))
                .font(.subheadline)
                .foregroundStyle(.secondary)
            if let caseInfo = appointment.caseInfo {
                Text(caseInfo.customerDisplayName)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }
}

struct DKHTaskRow: View {
    let task: DKHTask

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(task.title)
                .font(.headline)
            Text([task.statusName, task.priority, task.dueAt].compactMap { $0 }.joined(separator: " · "))
                .font(.subheadline)
                .foregroundStyle(.secondary)
            if let caseName = task.caseInfo?.customerDisplayName {
                Text(caseName)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }
}

struct DKHEmailRow: View {
    let email: DKHEmail

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(email.subject)
                .font(.headline)
            Text(email.receivedAt ?? "")
                .font(.subheadline)
                .foregroundStyle(.secondary)
            if let snippet = email.snippet {
                Text(snippet)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
            }
        }
    }
}

struct DKHCustomerRow: View {
    let customer: DKHCustomer

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(customer.displayName)
                .font(.headline)
            Text([customer.customerNumber, customer.primaryEmail].compactMap { $0 }.joined(separator: " · "))
                .font(.subheadline)
                .foregroundStyle(.secondary)
            Text(customer.primaryPhone ?? customer.primaryMobile ?? "")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }
}

struct DKHInfoRow: View {
    let label: String
    let value: String?

    init(_ label: String, _ value: String?) {
        self.label = label
        self.value = value
    }

    var body: some View {
        HStack(alignment: .top) {
            Text(label)
                .foregroundStyle(.secondary)
            Spacer()
            Text((value?.isEmpty == false ? value : "Nicht hinterlegt") ?? "Nicht hinterlegt")
                .multilineTextAlignment(.trailing)
        }
    }
}

func addressText(_ address: DKHCustomerAddress?) -> String? {
    guard let address else { return nil }
    return [
        [address.street, address.houseNumber].compactMap { $0 }.joined(separator: " "),
        address.addressExtra ?? "",
        [address.postalCode, address.city].compactMap { $0 }.joined(separator: " "),
        address.country ?? "",
    ]
    .filter { !$0.isEmpty }
    .joined(separator: ", ")
}

struct DKHMetricRow: View {
    let title: String
    let value: Int
    let systemImage: String

    var body: some View {
        Label {
            HStack {
                Text(title)
                Spacer()
                Text("\(value)")
                    .foregroundStyle(.secondary)
            }
        } icon: {
            Image(systemName: systemImage)
        }
    }
}
