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

struct DKHOverviewState: Decodable {
    let currentUser: DKHOverviewUser?
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

struct DKHCustomerCase: Decodable, Identifiable {
    let id: Int
    let caseNumber: String?
    let customerDisplayName: String
    let customerNumber: String?
    let statusPhase: Int?
}

struct DKHTask: Decodable, Identifiable {
    let id: Int
    let title: String
    let statusName: String?
    let priority: String?
    let dueAt: String?
    let caseInfo: DKHCustomerCase?

    enum CodingKeys: String, CodingKey {
        case id
        case title
        case statusName
        case priority
        case dueAt
        case caseInfo = "case"
    }
}

struct DKHEmail: Decodable, Identifiable {
    let id: Int
    let subject: String
    let snippet: String?
    let receivedAt: String?
    let isUnassigned: Bool?
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

struct DKHCustomersState: Decodable {
    let customers: [DKHCustomer]?
    let leads: [DKHLead]?
}

struct DKHCustomer: Decodable, Identifiable {
    let id: Int
    let customerNumber: String?
    let displayName: String
    let primaryEmail: String?
    let primaryPhone: String?
    let primaryMobile: String?
    let updatedAt: String?
}

struct DKHLead: Decodable, Identifiable {
    let id: Int
    let leadNumber: String?
    let displayName: String
    let status: String?
    let source: String?
    let updatedAt: String?
}

struct DKHLiveWorkspace {
    let overview: DKHOverviewState
    let customers: DKHCustomersState
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
        return try await DKHLiveWorkspace(overview: overview, customers: customers)
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

    var body: some View {
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

                if isLoading {
                    Section {
                        ProgressView("DKH Serverdaten werden geladen")
                    }
                }

                if let errorMessage {
                    Section {
                        Text(errorMessage)
                            .foregroundStyle(.red)
                        Button("Erneut laden") {
                            Task { await loadLiveWorkspace() }
                        }
                    }
                }

                if let liveWorkspace {
                    DKHOverviewSection(overview: liveWorkspace.overview)
                    DKHCustomersSection(customersState: liveWorkspace.customers)
                }
            }
            .navigationTitle("DKH CRM")
            .refreshable {
                await loadLiveWorkspace()
            }
            .task {
                await loadLiveWorkspace()
            }
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
}

struct DKHOverviewSection: View {
    let overview: DKHOverviewState

    var body: some View {
        Section("Uebersicht") {
            NavigationLink {
                DKHListDetailView(
                    title: "Aufgaben",
                    rows: (overview.tasks ?? []).map {
                        DKHListRow(
                            title: $0.title,
                            subtitle: [$0.statusName, $0.dueAt].compactMap { $0 }.joined(separator: " · "),
                            detail: $0.caseInfo?.customerDisplayName
                        )
                    }
                )
            } label: {
                DKHMetricRow(title: "Aufgaben", value: overview.tasks?.count ?? 0, systemImage: "checklist")
            }

            NavigationLink {
                DKHListDetailView(
                    title: "Termine",
                    rows: (overview.appointments ?? []).map {
                        DKHListRow(
                            title: $0.title,
                            subtitle: [$0.startsAt, $0.location].compactMap { $0 }.joined(separator: " · "),
                            detail: $0.caseInfo?.customerDisplayName
                        )
                    }
                )
            } label: {
                DKHMetricRow(title: "Termine", value: overview.appointments?.count ?? 0, systemImage: "calendar")
            }

            NavigationLink {
                DKHListDetailView(
                    title: "E-Mails",
                    rows: (overview.emails ?? []).map {
                        DKHListRow(title: $0.subject, subtitle: $0.receivedAt ?? "", detail: $0.snippet)
                    }
                )
            } label: {
                DKHMetricRow(title: "E-Mails", value: overview.emails?.count ?? 0, systemImage: "envelope")
            }

            NavigationLink {
                DKHListDetailView(
                    title: "Vorgaenge",
                    rows: (overview.customerCases ?? []).map {
                        DKHListRow(
                            title: $0.customerDisplayName,
                            subtitle: [$0.caseNumber, $0.customerNumber].compactMap { $0 }.joined(separator: " · "),
                            detail: $0.statusPhase.map { "Phase \($0)" }
                        )
                    }
                )
            } label: {
                DKHMetricRow(title: "Vorgaenge", value: overview.customerCases?.count ?? 0, systemImage: "folder")
            }
        }
    }
}

struct DKHCustomersSection: View {
    let customersState: DKHCustomersState

    var body: some View {
        Section("Kunden") {
            NavigationLink {
                DKHListDetailView(
                    title: "Kunden",
                    rows: (customersState.customers ?? []).map {
                        DKHListRow(
                            title: $0.displayName,
                            subtitle: [$0.customerNumber, $0.primaryEmail].compactMap { $0 }.joined(separator: " · "),
                            detail: $0.primaryPhone ?? $0.primaryMobile
                        )
                    }
                )
            } label: {
                DKHMetricRow(title: "Kunden", value: customersState.customers?.count ?? 0, systemImage: "person.2")
            }

            NavigationLink {
                DKHListDetailView(
                    title: "Leads",
                    rows: (customersState.leads ?? []).map {
                        DKHListRow(
                            title: $0.displayName,
                            subtitle: [$0.leadNumber, $0.status, $0.source].compactMap { $0 }.joined(separator: " · "),
                            detail: $0.updatedAt
                        )
                    }
                )
            } label: {
                DKHMetricRow(title: "Leads", value: customersState.leads?.count ?? 0, systemImage: "person.crop.circle.badge.plus")
            }
        }
    }
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

struct DKHListRow: Identifiable {
    let id = UUID()
    let title: String
    let subtitle: String
    let detail: String?
}

struct DKHListDetailView: View {
    let title: String
    let rows: [DKHListRow]

    var body: some View {
        List {
            if rows.isEmpty {
                Text("Keine Eintraege im aktuellen DKH Serverzustand.")
                    .foregroundStyle(.secondary)
            } else {
                ForEach(rows) { row in
                    VStack(alignment: .leading, spacing: 4) {
                        Text(row.title)
                            .font(.headline)
                        if !row.subtitle.isEmpty {
                            Text(row.subtitle)
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                        if let detail = row.detail, !detail.isEmpty {
                            Text(detail)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                                .lineLimit(3)
                        }
                    }
                    .padding(.vertical, 4)
                }
            }
        }
        .navigationTitle(title)
    }
}
