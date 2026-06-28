import SwiftUI

@main
struct DKHCRMApp: App {
    var body: some Scene {
        WindowGroup {
            WebAppView(startURL: DKHWebApp.productionURL)
        }
    }
}
