import { ScrollView, StyleSheet, Text, View } from "react-native";
import { createKhhWorkbenchClient } from "@scas/tenant-workbench-client";
import {
  createDashboardSurfaceContract,
  createDashboardViewModel,
  createNativeWorkbenchAdapterPlan,
} from "@scas/tenant-workbench-ui";
import {
  khhNativeAuthHandoff,
  khhNativeRuntime,
  khhOfflineSummaryStore,
  khhPermissionGate,
  khhPushOptIn,
} from "../src/native-runtime";

const client = createKhhWorkbenchClient(undefined, khhOfflineSummaryStore);
const dashboard = createDashboardViewModel(client.getDashboardSnapshot());
const surface = createDashboardSurfaceContract(client.getDashboardSnapshot());
const nativePlan = createNativeWorkbenchAdapterPlan(surface);

export default function TodayScreen() {
  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.kicker}>KHH iOS</Text>
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
      <View style={styles.contractCard}>
        <Text style={styles.contract}>
          Runtime scope: {khhNativeRuntime.scope.tenantId}
        </Text>
        <Text style={styles.contract}>
          Offline: {khhNativeRuntime.offlineCache.mode}; writes queued:{" "}
          {String(khhNativeRuntime.offlineCache.allowQueuedWrites)}
        </Text>
        <Text style={styles.contract}>
          Push opt-in: {String(khhNativeRuntime.push.optInRequired)}; adapter:{" "}
          {khhPushOptIn.getOptInState.name ? "default-denied" : "default-denied"}
        </Text>
        <Text style={styles.contract}>
          Permissions: {khhNativeRuntime.permissions.length}; default: denied
        </Text>
        <Text style={styles.contract}>
          Native adapter: {nativePlan.platform}; safe area:{" "}
          {String(nativePlan.safeAreaRequired)}
        </Text>
        <Text style={styles.contract}>
          Auth handoff: {khhNativeAuthHandoff.completeAuthHandoff.name}
        </Text>
        <Text style={styles.contract}>
          Permission gate: {khhPermissionGate.getPermissionState.name}
        </Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: 16,
    padding: 24,
    backgroundColor: "#fafaf7",
  },
  kicker: {
    color: "#36533b",
    fontSize: 12,
    fontWeight: "900",
    letterSpacing: 0,
    textTransform: "uppercase",
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
    borderRadius: 8,
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
  contractCard: {
    gap: 6,
    borderColor: "#d8d0bf",
    borderRadius: 8,
    borderWidth: 1,
    backgroundColor: "#f2efe5",
    padding: 16,
  },
  contract: {
    color: "#475569",
    fontSize: 12,
    fontWeight: "700",
  },
});
