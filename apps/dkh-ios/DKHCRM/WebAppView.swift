import SafariServices
import SwiftUI

enum DKHWebApp {
    static let productionURL = URL(string: "https://es-daskuechenhaus.de")!
}

struct WebAppView: UIViewControllerRepresentable {
    let startURL: URL

    func makeUIViewController(context: Context) -> SFSafariViewController {
        let configuration = SFSafariViewController.Configuration()
        configuration.entersReaderIfAvailable = false
        configuration.barCollapsingEnabled = false

        let controller = SFSafariViewController(url: startURL, configuration: configuration)
        controller.dismissButtonStyle = .close
        return controller
    }

    func updateUIViewController(_ controller: SFSafariViewController, context: Context) {}
}
