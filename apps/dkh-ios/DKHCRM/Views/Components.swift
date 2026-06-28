import SwiftUI

enum DKHColors {
    static let background = Color(red: 0.97, green: 0.98, blue: 0.96)
    static let surface = Color.white
    static let surfaceStrong = Color(red: 0.90, green: 0.96, blue: 0.84)
    static let foreground = Color(red: 0.07, green: 0.07, blue: 0.07)
    static let muted = Color(red: 0.24, green: 0.24, blue: 0.24)
    static let accent = Color(red: 0.46, green: 0.72, blue: 0.15)
    static let accentStrong = Color(red: 0.24, green: 0.47, blue: 0.08)
    static let border = Color(red: 0.77, green: 0.86, blue: 0.70)
}

struct SignalCard: View {
    let signal: DKHStatusSignal

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
                .foregroundStyle(DKHColors.foreground)

            Text(signal.detail)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(DKHColors.muted)
                .fixedSize(horizontal: false, vertical: true)

            Text(signal.action)
                .font(.subheadline.weight(.black))
                .foregroundStyle(DKHColors.accentStrong)
        }
        .padding(16)
        .background(DKHColors.surface, in: RoundedRectangle(cornerRadius: 8))
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(DKHColors.border, lineWidth: 1)
        )
    }
}

struct QuickActionRow: View {
    let action: DKHQuickAction

    var body: some View {
        HStack(alignment: .top, spacing: 14) {
            IconBadge(systemImage: action.systemImage)

            VStack(alignment: .leading, spacing: 6) {
                Text(action.title)
                    .font(.headline.weight(.black))
                    .foregroundStyle(DKHColors.foreground)

                Text(action.detail)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(DKHColors.muted)
                    .fixedSize(horizontal: false, vertical: true)
            }

            Spacer(minLength: 8)

            Text(action.action)
                .font(.caption.weight(.black))
                .foregroundStyle(DKHColors.accentStrong)
                .padding(.horizontal, 10)
                .padding(.vertical, 7)
                .background(DKHColors.surfaceStrong, in: Capsule())
        }
        .padding(16)
        .background(DKHColors.surface, in: RoundedRectangle(cornerRadius: 8))
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(DKHColors.border, lineWidth: 1)
        )
    }
}

struct SectionRow: View {
    let section: DKHSection

    var body: some View {
        HStack(spacing: 14) {
            IconBadge(systemImage: section.systemImage)

            VStack(alignment: .leading, spacing: 5) {
                Text(section.title)
                    .font(.headline.weight(.black))
                    .foregroundStyle(DKHColors.foreground)

                Text(section.subtitle)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(DKHColors.muted)
                    .lineLimit(2)
            }

            Spacer()

            Image(systemName: "chevron.right")
                .font(.caption.weight(.bold))
                .foregroundStyle(DKHColors.muted)
        }
        .padding(16)
        .background(DKHColors.surface, in: RoundedRectangle(cornerRadius: 8))
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(DKHColors.border, lineWidth: 1)
        )
    }
}

struct IconBadge: View {
    let systemImage: String

    var body: some View {
        Image(systemName: systemImage)
            .font(.system(size: 17, weight: .bold))
            .foregroundStyle(DKHColors.accentStrong)
            .frame(width: 36, height: 36)
            .background(DKHColors.surfaceStrong, in: RoundedRectangle(cornerRadius: 8))
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
                    .foregroundStyle(DKHColors.accentStrong)

                ForEach(items, id: \.self) { item in
                    Text(item)
                        .font(.caption.weight(.bold))
                        .foregroundStyle(DKHColors.foreground)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 7)
                        .background(DKHColors.surface, in: Capsule())
                        .overlay(Capsule().stroke(DKHColors.border, lineWidth: 1))
                }
            }
            .padding(.vertical, 2)
        }
    }
}
