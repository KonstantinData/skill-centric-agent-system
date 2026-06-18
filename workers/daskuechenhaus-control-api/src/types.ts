export interface Env {
  DB: D1Database;
  TENANT_ID: string;
  API_SECRET: string;
}

export interface AppVariables {
  tenant_id: string;
}

export type AppEnv = {
  Bindings: Env;
  Variables: AppVariables;
};

export type JsonObject = Record<string, unknown>;
