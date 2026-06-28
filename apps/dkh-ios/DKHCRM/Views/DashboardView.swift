import SwiftUI

struct DashboardView: View {
    let workspace: DKHWorkspace

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    header
                    DayStrip(items: workspace.dayStrip)

                    LazyVGrid(
                        columns: [GridItem(.adaptive(minimum: 156), spacing: 12)],
                        alignment: .leading,
                        spacing: 12
                    ) {
                        ForEach(workspace.statusSignals) { signal in
                            SignalCard(signal: signal)
                        }
                    }

                    VStack(alignment: .leading, spacing: 10) {
                        Text("Schnellzugriff")
                            .font(.title3.weight(.black))
                            .foregroundStyle(DKHColors.foreground)

                        ForEach(workspace.quickActions) { action in
                            QuickActionRow(action: action)
                        }
                    }

                    VStack(alignment: .leading, spacing: 10) {
                        Text("Arbeitsbereiche")
                            .font(.title3.weight(.black))
                            .foregroundStyle(DKHColors.foreground)

                        ForEach(workspace.sections) { section in
                            NavigationLink(value: section) {
                                SectionRow(section: section)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
                .padding(20)
            }
            .background(DKHColors.background)
            .navigationDestination(for: DKHSection.self) { section in
                SectionDetailView(section: section)
            }
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 12) {
                Text("DKH")
                    .font(.headline.weight(.black))
                    .foregroundStyle(.white)
                    .frame(width: 50, height: 46)
                    .background(DKHColors.accentStrong, in: RoundedRectangle(cornerRadius: 8))

                VStack(alignment: .leading, spacing: 3) {
                    Text(workspace.hero.title)
                        .font(.largeTitle.weight(.black))
                        .foregroundStyle(DKHColors.foreground)
                        .lineLimit(2)
                        .minimumScaleFactor(0.78)

                    Text("Mobile DKH CRM Uebersicht")
                        .font(.subheadline.weight(.bold))
                        .foregroundStyle(DKHColors.muted)
                }
            }

            Text(workspace.hero.functionText)
                .font(.body.weight(.semibold))
                .foregroundStyle(DKHColors.muted)
                .fixedSize(horizontal: false, vertical: true)
        }
    }
}

struct SectionDetailView: View {
    let section: DKHSection

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                HStack(alignment: .top, spacing: 14) {
                    IconBadge(systemImage: section.systemImage)

                    VStack(alignment: .leading, spacing: 6) {
                        Text(section.title)
                            .font(.largeTitle.weight(.black))
                            .foregroundStyle(DKHColors.foreground)

                        Text(section.subtitle)
                            .font(.body.weight(.semibold))
                            .foregroundStyle(DKHColors.muted)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }

                VStack(alignment: .leading, spacing: 10) {
                    ForEach(section.items, id: \.self) { item in
                        HStack(alignment: .top, spacing: 10) {
                            Image(systemName: "checkmark.circle.fill")
                                .foregroundStyle(DKHColors.accent)
                                .padding(.top, 2)

                            Text(item)
                                .font(.subheadline.weight(.semibold))
                                .foregroundStyle(DKHColors.foreground)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                        .padding(14)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(DKHColors.surface, in: RoundedRectangle(cornerRadius: 8))
                        .overlay(
                            RoundedRectangle(cornerRadius: 8)
                                .stroke(DKHColors.border, lineWidth: 1)
                        )
                    }
                }

                VStack(alignment: .leading, spacing: 10) {
                    Text("Arbeitsansicht")
                        .font(.title3.weight(.black))
                        .foregroundStyle(DKHColors.foreground)

                    VStack(alignment: .leading, spacing: 8) {
                        ForEach(section.focus, id: \.self) { focus in
                            Text(focus)
                                .font(.caption.weight(.black))
                                .foregroundStyle(DKHColors.accentStrong)
                                .padding(.horizontal, 10)
                                .padding(.vertical, 7)
                                .background(DKHColors.surfaceStrong, in: Capsule())
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(16)
                    .background(DKHColors.surface, in: RoundedRectangle(cornerRadius: 8))
                    .overlay(
                        RoundedRectangle(cornerRadius: 8)
                            .stroke(DKHColors.border, lineWidth: 1)
                    )
                }
            }
            .padding(20)
        }
        .background(DKHColors.background)
        .navigationTitle(section.title)
        .navigationBarTitleDisplayMode(.inline)
    }
}
