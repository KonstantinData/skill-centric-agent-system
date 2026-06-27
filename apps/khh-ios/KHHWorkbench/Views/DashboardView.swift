import SwiftUI

struct DashboardView: View {
    let workbench: KHHWorkbench

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    header
                    DayStrip(items: workbench.dayStrip)

                    LazyVGrid(
                        columns: [GridItem(.adaptive(minimum: 156), spacing: 12)],
                        alignment: .leading,
                        spacing: 12
                    ) {
                        ForEach(workbench.dailySignals) { signal in
                            SignalCard(signal: signal)
                        }
                    }

                    VStack(alignment: .leading, spacing: 10) {
                        Text("Schnellzugriff")
                            .font(.title3.weight(.black))
                            .foregroundStyle(KHHColors.foreground)

                        ForEach(workbench.quickActions) { action in
                            QuickActionRow(action: action)
                        }
                    }

                    VStack(alignment: .leading, spacing: 10) {
                        Text("Arbeitsbereiche")
                            .font(.title3.weight(.black))
                            .foregroundStyle(KHHColors.foreground)

                        ForEach(workbench.sections) { section in
                            NavigationLink(value: section) {
                                SectionRow(section: section)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
                .padding(20)
            }
            .background(KHHColors.background)
            .navigationDestination(for: KHHSection.self) { section in
                SectionDetailView(section: section)
            }
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 12) {
                Text("KHH")
                    .font(.headline.weight(.black))
                    .foregroundStyle(.white)
                    .frame(width: 46, height: 46)
                    .background(KHHColors.accentStrong, in: RoundedRectangle(cornerRadius: 8))

                VStack(alignment: .leading, spacing: 3) {
                    Text(workbench.hero.title)
                        .font(.largeTitle.weight(.black))
                        .foregroundStyle(KHHColors.foreground)
                        .lineLimit(2)
                        .minimumScaleFactor(0.78)

                    Text("Heute, Dienste, Fristen und Aufgaben")
                        .font(.subheadline.weight(.bold))
                        .foregroundStyle(KHHColors.muted)
                }
            }

            Text(workbench.hero.functionText)
                .font(.body.weight(.semibold))
                .foregroundStyle(KHHColors.muted)
                .fixedSize(horizontal: false, vertical: true)
        }
    }
}

struct SectionDetailView: View {
    let section: KHHSection

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                HStack(alignment: .top, spacing: 14) {
                    IconBadge(systemImage: section.systemImage)

                    VStack(alignment: .leading, spacing: 6) {
                        Text(section.title)
                            .font(.largeTitle.weight(.black))
                            .foregroundStyle(KHHColors.foreground)

                        Text(section.subtitle)
                            .font(.body.weight(.semibold))
                            .foregroundStyle(KHHColors.muted)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }

                VStack(alignment: .leading, spacing: 10) {
                    ForEach(section.items, id: \.self) { item in
                        HStack(alignment: .top, spacing: 10) {
                            Image(systemName: "checkmark.circle.fill")
                                .foregroundStyle(KHHColors.accent)
                                .padding(.top, 2)

                            Text(item)
                                .font(.subheadline.weight(.semibold))
                                .foregroundStyle(KHHColors.foreground)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                        .padding(14)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(KHHColors.surface, in: RoundedRectangle(cornerRadius: 8))
                        .overlay(
                            RoundedRectangle(cornerRadius: 8)
                                .stroke(KHHColors.border, lineWidth: 1)
                        )
                    }
                }

                VStack(alignment: .leading, spacing: 10) {
                    Text("Arbeitsansicht")
                        .font(.title3.weight(.black))
                        .foregroundStyle(KHHColors.foreground)

                    VStack(alignment: .leading, spacing: 8) {
                        ForEach(section.focus, id: \.self) { focus in
                            Text(focus)
                                .font(.caption.weight(.black))
                                .foregroundStyle(KHHColors.accentStrong)
                                .padding(.horizontal, 10)
                                .padding(.vertical, 7)
                                .background(KHHColors.surfaceStrong, in: Capsule())
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(16)
                    .background(KHHColors.surface, in: RoundedRectangle(cornerRadius: 8))
                    .overlay(
                        RoundedRectangle(cornerRadius: 8)
                            .stroke(KHHColors.border, lineWidth: 1)
                    )
                }
            }
            .padding(20)
        }
        .background(KHHColors.background)
        .navigationTitle(section.title)
        .navigationBarTitleDisplayMode(.inline)
    }
}
