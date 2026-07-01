import SwiftUI

enum KHHColors {
    static let background = Color(red: 0.98, green: 0.98, blue: 0.97)
    static let surface = Color(red: 1.00, green: 1.00, blue: 0.98)
    static let surfaceStrong = Color(red: 0.95, green: 0.94, blue: 0.90)
    static let foreground = Color(red: 0.12, green: 0.16, blue: 0.23)
    static let muted = Color(red: 0.28, green: 0.33, blue: 0.41)
    static let accent = Color(red: 0.44, green: 0.56, blue: 0.45)
    static let accentStrong = Color(red: 0.21, green: 0.33, blue: 0.23)
    static let border = Color(red: 0.85, green: 0.82, blue: 0.75)
}

struct SignalCard: View {
    let signal: KHHDailySignal

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .top) {
                IconBadge(systemImage: signal.systemImage)
                Spacer()
                Text(signal.status)
                    .font(.caption.weight(.black))
                    .foregroundStyle(signal.tone.foreground)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(signal.tone.background, in: Capsule())
            }

            Text(signal.title)
                .font(.headline.weight(.black))
                .foregroundStyle(KHHColors.foreground)

            Text(signal.detail)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(KHHColors.muted)
                .fixedSize(horizontal: false, vertical: true)

            Text(signal.action)
                .font(.subheadline.weight(.black))
                .foregroundStyle(KHHColors.accentStrong)
        }
        .padding(16)
        .background(KHHColors.surface, in: RoundedRectangle(cornerRadius: 8))
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(KHHColors.border, lineWidth: 1)
        )
    }
}

struct QuickActionRow: View {
    let action: KHHQuickAction

    var body: some View {
        HStack(alignment: .top, spacing: 14) {
            IconBadge(systemImage: action.systemImage)

            VStack(alignment: .leading, spacing: 6) {
                Text(action.title)
                    .font(.headline.weight(.black))
                    .foregroundStyle(KHHColors.foreground)

                Text(action.detail)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(KHHColors.muted)
                    .fixedSize(horizontal: false, vertical: true)
            }

            Spacer(minLength: 8)

            Text(action.action)
                .font(.caption.weight(.black))
                .foregroundStyle(KHHColors.accentStrong)
                .padding(.horizontal, 10)
                .padding(.vertical, 7)
                .background(KHHColors.surfaceStrong, in: Capsule())
        }
        .padding(16)
        .background(KHHColors.surface, in: RoundedRectangle(cornerRadius: 8))
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(KHHColors.border, lineWidth: 1)
        )
    }
}

struct SectionRow: View {
    let section: KHHSection

    var body: some View {
        HStack(spacing: 14) {
            IconBadge(systemImage: section.systemImage)

            VStack(alignment: .leading, spacing: 5) {
                Text(section.title)
                    .font(.headline.weight(.black))
                    .foregroundStyle(KHHColors.foreground)

                Text(section.subtitle)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(KHHColors.muted)
                    .lineLimit(2)
            }

            Spacer()

            Image(systemName: "chevron.right")
                .font(.caption.weight(.bold))
                .foregroundStyle(KHHColors.muted)
        }
        .padding(16)
        .background(KHHColors.surface, in: RoundedRectangle(cornerRadius: 8))
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(KHHColors.border, lineWidth: 1)
        )
    }
}

struct IconBadge: View {
    let systemImage: String

    var body: some View {
        Image(systemName: systemImage)
            .font(.system(size: 17, weight: .bold))
            .foregroundStyle(KHHColors.accentStrong)
            .frame(width: 36, height: 36)
            .background(KHHColors.surfaceStrong, in: RoundedRectangle(cornerRadius: 8))
            .accessibilityHidden(true)
    }
}

struct DayStrip: View {
    let items: [String]

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                Text("Heute")
                    .font(.caption.weight(.black))
                    .foregroundStyle(KHHColors.accentStrong)

                ForEach(items, id: \.self) { item in
                    Text(item)
                        .font(.caption.weight(.bold))
                        .foregroundStyle(KHHColors.foreground)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 7)
                        .background(KHHColors.surface, in: Capsule())
                        .overlay(Capsule().stroke(KHHColors.border, lineWidth: 1))
                }
            }
            .padding(.vertical, 2)
        }
    }
}
