import Foundation
import SwiftUI

struct DKHWorkspaceScope: Equatable {
    let tenantId: String
    let areaId: String
    let webAppPath: String
    let primaryHostnames: [String]
}

struct DKHWorkspace: Equatable {
    let scope: DKHWorkspaceScope
    let hero: DKHHero
    let dayStrip: [String]
    let statusSignals: [DKHStatusSignal]
    let quickActions: [DKHQuickAction]
    let sections: [DKHSection]
    let privacyRules: [String]
    let excludedCapabilities: [String]
}

struct DKHHero: Equatable {
    let title: String
    let functionText: String
}

struct DKHStatusSignal: Identifiable, Equatable {
    let id: String
    let title: String
    let status: String
    let detail: String
    let action: String
    let tone: DKHTone
    let systemImage: String
}

struct DKHQuickAction: Identifiable, Equatable {
    let id: String
    let title: String
    let detail: String
    let action: String
    let systemImage: String
}

struct DKHSection: Identifiable, Hashable {
    let id: String
    let title: String
    let subtitle: String
    let systemImage: String
    let items: [String]
    let focus: [String]
}

enum DKHTone: Equatable {
    case success
    case warning
    case danger
    case info

    var background: Color {
        switch self {
        case .success:
            Color(red: 0.88, green: 0.94, blue: 0.84)
        case .warning:
            Color(red: 0.98, green: 0.92, blue: 0.74)
        case .danger:
            Color(red: 0.98, green: 0.87, blue: 0.84)
        case .info:
            Color(red: 0.86, green: 0.91, blue: 0.95)
        }
    }

    var foreground: Color {
        switch self {
        case .success:
            Color(red: 0.16, green: 0.35, blue: 0.10)
        case .warning:
            Color(red: 0.44, green: 0.32, blue: 0.06)
        case .danger:
            Color(red: 0.50, green: 0.16, blue: 0.12)
        case .info:
            Color(red: 0.14, green: 0.29, blue: 0.42)
        }
    }
}
