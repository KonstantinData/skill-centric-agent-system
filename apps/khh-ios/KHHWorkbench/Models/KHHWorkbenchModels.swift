import Foundation
import SwiftUI

struct KHHWorkbenchScope: Equatable {
    let tenantId: String
    let areaId: String
    let primaryHostname: String
}

struct KHHWorkbench: Equatable {
    let scope: KHHWorkbenchScope
    let hero: KHHHero
    let dayStrip: [String]
    let dailySignals: [KHHDailySignal]
    let quickActions: [KHHQuickAction]
    let sections: [KHHSection]
    let privacyRules: [String]
}

struct KHHHero: Equatable {
    let title: String
    let functionText: String
}

struct KHHDailySignal: Identifiable, Equatable {
    let id: String
    let title: String
    let status: String
    let detail: String
    let action: String
    let tone: KHHTone
    let systemImage: String
}

struct KHHQuickAction: Identifiable, Equatable {
    let id: String
    let title: String
    let detail: String
    let action: String
    let systemImage: String
}

struct KHHSection: Identifiable, Hashable {
    let id: String
    let title: String
    let subtitle: String
    let systemImage: String
    let items: [String]
    let focus: [String]
}

enum KHHTone: Equatable {
    case success
    case warning
    case danger
    case info

    var background: Color {
        switch self {
        case .success:
            Color(red: 0.86, green: 0.92, blue: 0.85)
        case .warning:
            Color(red: 0.97, green: 0.91, blue: 0.72)
        case .danger:
            Color(red: 0.97, green: 0.87, blue: 0.87)
        case .info:
            Color(red: 0.86, green: 0.91, blue: 0.95)
        }
    }

    var foreground: Color {
        switch self {
        case .success:
            Color(red: 0.19, green: 0.33, blue: 0.21)
        case .warning:
            Color(red: 0.46, green: 0.34, blue: 0.08)
        case .danger:
            Color(red: 0.52, green: 0.18, blue: 0.18)
        case .info:
            Color(red: 0.16, green: 0.30, blue: 0.42)
        }
    }
}
