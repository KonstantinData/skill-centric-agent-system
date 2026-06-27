import { ScrollView, StyleSheet, Text, View } from "react-native";
import { createKhhWorkbenchClient } from "@scas/tenant-workbench-client";
import {
  defaultNativePermissionPolicies,
  khhNativePushPolicy,
  readOnlySummaryOfflinePolicy,
} from "@scas/tenant-workbench-client/native-contracts";
import { createDashboardViewModel } from "@scas/tenant-workbench-ui";

const client = createKhhWorkbenchClient();
const dashboard = createDashboardViewModel(client.getDashboardSnapshot());

export default function App() {
  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>{dashboard.hero.title}</Text>
      <Text style={styles.subtitle}>{dashboard.hero.functionText}</Text>
      <View style={styles.section}>
        {dashboard.dailySignals.map((signal) => (
          <View key={signal.signalId} style={styles.card}>
            <Text style={styles.cardTitle}>{signal.title}</Text>
            <Text style={styles.status}>{signal.status}</Text>
            <Text style={styles.body}>{signal.detail}</Text>
            <Text style={styles.action}>{signal.action}</Text>
          </View>
        ))}
      </View>
      <Text style={styles.contract}>
        Offline: {readOnlySummaryOfflinePolicy.mode}; Push opt-in:{" "}
        {String(khhNativePushPolicy.optInRequired)}; Permissions:{" "}
        {defaultNativePermissionPolicies.length}
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: 16,
    padding: 24,
    backgroundColor: "#fafaf7",
  },
  title: {
    color: "#1e293b",
    fontSize: 28,
    fontWeight: "900",
  },
  subtitle: {
    color: "#475569",
    fontSize: 16,
    fontWeight: "700",
    lineHeight: 23,
  },
  section: {
    gap: 12,
  },
  card: {
    gap: 8,
    borderColor: "#d8d0bf",
    borderRadius: 12,
    borderWidth: 1,
    backgroundColor: "#fffefb",
    padding: 16,
  },
  cardTitle: {
    color: "#1e293b",
    fontSize: 18,
    fontWeight: "900",
  },
  status: {
    color: "#36533b",
    fontSize: 13,
    fontWeight: "900",
    textTransform: "uppercase",
  },
  body: {
    color: "#475569",
    fontSize: 15,
    fontWeight: "700",
  },
  action: {
    color: "#36533b",
    fontSize: 15,
    fontWeight: "900",
  },
  contract: {
    color: "#475569",
    fontSize: 12,
    fontWeight: "700",
  },
});
