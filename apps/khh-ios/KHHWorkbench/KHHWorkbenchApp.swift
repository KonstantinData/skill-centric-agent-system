import SwiftUI

@main
struct KHHWorkbenchApp: App {
    var body: some Scene {
        WindowGroup {
            DashboardView(workbench: .current)
        }
    }
}
