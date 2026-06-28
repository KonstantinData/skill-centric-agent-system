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
    let customerDisplayName: String
    let customerNumber: String?
    let customerEmail: String?
    let statusPhase: Int?
    let statusPhaseName: String?
    let notes: [DKHCaseNote]?
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

                    DKHAppointmentsPage(overview: liveWorkspace.overview)
                        .tabItem { Label("Termine", systemImage: "calendar") }

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

                    DKHCustomersPage(customersState: liveWorkspace.customers)
                        .tabItem { Label("Kunden", systemImage: "person.2") }

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
    @State private var query = ""

    var customers: [DKHCustomer] {
        let all = customersState.customers ?? []
        guard !query.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return all }
        return all.filter {
            [$0.displayName, $0.customerNumber, $0.primaryEmail, $0.primaryPhone, $0.primaryMobile]
                .compactMap { $0?.localizedCaseInsensitiveContains(query) }
                .contains(true)
        }
    }

    var body: some View {
        NavigationStack {
            List {
                Section("Kunden direkt Suche") {
                    if customers.isEmpty {
                        Text("Keine Kunden gefunden.")
                            .foregroundStyle(.secondary)
                    } else {
                        ForEach(customers) { customer in
                            NavigationLink {
                                DKHCustomerDetailPage(customer: customer, cases: cases(for: customer))
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
            .searchable(text: $query, prompt: "Kunde, E-Mail, Telefon")
        }
    }

    private func cases(for customer: DKHCustomer) -> [DKHCustomerCase] {
        (customersState.customerCases ?? []).filter { $0.customerId == customer.id }
    }
}

struct DKHCustomerDetailPage: View {
    let customer: DKHCustomer
    let cases: [DKHCustomerCase]

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
                            DKHCaseDetailPage(caseRecord: item)
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
        }
        .navigationTitle(customer.displayName)
    }
}

struct DKHCaseDetailPage: View {
    let caseRecord: DKHCustomerCase

    var body: some View {
        List {
            Section("Geoeffnete Vorgangsmappe") {
                Text(caseRecord.caseTitle ?? caseRecord.customerDisplayName)
                    .font(.headline)
                DKHInfoRow("Vorgang", caseRecord.caseNumber)
                DKHInfoRow("CARAT", caseRecord.caratOrderNumber)
                DKHInfoRow("Status", caseRecord.statusPhaseName)
            }
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
