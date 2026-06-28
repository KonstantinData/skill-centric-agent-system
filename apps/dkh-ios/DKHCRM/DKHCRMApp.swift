import SwiftUI

@main
struct DKHCRMApp: App {
    var body: some Scene {
        WindowGroup {
            DashboardView(workspace: DKHWorkspace.current)
        }
    }
}
