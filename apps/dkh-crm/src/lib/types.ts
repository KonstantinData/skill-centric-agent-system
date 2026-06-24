export type Role = {
  code: string;
  name: string;
};

export type Workday = {
  weekday: number;
  is_working_day: boolean;
  morning_start_time: string | null;
  morning_end_time: string | null;
  afternoon_start_time: string | null;
  afternoon_end_time: string | null;
};

export type User = {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  phone: string | null;
  job_title: string | null;
  department: string | null;
  is_active: boolean;
  timezone: string;
  security: {
    mfa_required: boolean;
    password_login_enabled: boolean;
    external_identity_provider: string;
  };
  roles: string[];
  workdays: Workday[];
};

export type CompanySettings = Record<string, string | undefined>;

export type AdminState = {
  users: User[];
  roles: Role[];
  company_settings: CompanySettings;
  integrations: Array<{
    id: number;
    code: string;
    name: string;
    is_enabled: boolean;
    connections: Array<{
      id: number;
      display_name: string;
      status: string;
      secret_reference: string | null;
    }>;
  }>;
};

export type OverviewState = {
  current_user: {
    primary_user_id: number | null;
    display_name: string;
    email: string;
    is_admin: boolean;
    user_ids: number[];
    delegated_user_ids: number[];
    scope_user_ids: number[];
  };
  users: Array<{
    id: number;
    first_name: string;
    last_name: string;
    email: string;
    roles: string[];
  }>;
  task_statuses: Array<{
    code: string;
    name: string;
    is_terminal: boolean;
  }>;
  customer_cases: Array<{
    id: number;
    case_number: string | null;
    customer_display_name: string;
    customer_number: string | null;
    customer_email: string | null;
    status_phase: number | null;
  }>;
  tasks: Array<{
    id: number;
    title: string;
    description: string | null;
    status: string;
    status_name: string;
    priority: string;
    due_at: string | null;
    reminder_at: string | null;
    reminder_email_enabled: boolean;
    reminder_overview_enabled: boolean;
    case: {
      id: number;
      case_number: string | null;
      customer_display_name: string;
      status_phase: number | null;
    } | null;
    assigned_users: Array<{ id: number; name: string }>;
    attachment_count: number;
  }>;
  emails: Array<{
    id: number;
    subject: string;
    snippet: string | null;
    direction: string;
    received_at: string | null;
    is_unassigned: boolean;
    assigned_user_id: number | null;
    participants: Array<{
      type: string;
      display_name: string | null;
      email_address: string;
    }>;
    cases: Array<{
      id: number;
      case_number: string | null;
      customer_display_name: string;
    }>;
    suggestions: Array<{
      id: number;
      confidence: number;
      reason: string | null;
      case: {
        id: number;
        case_number: string | null;
        customer_display_name: string;
      } | null;
    }>;
  }>;
  appointments: Array<{
    id: number;
    title: string;
    appointment_type?: string | null;
    starts_at: string;
    ends_at?: string | null;
    location: string | null;
    case: { id: number; customer_display_name: string } | null;
    user_id?: number | null;
    assigned_user_id?: number | null;
    responsible_user_id?: number | null;
    organizer_email?: string | null;
    source?: string | null;
    visibility?: string | null;
    is_external_blocker?: boolean;
    is_readonly?: boolean;
    sync_status?: string | null;
    conflict_status?: string | null;
    conflict_details?: Array<{
      type?: string;
      severity?: string;
      message?: string;
    }>;
    assigned_users?: Array<{
      id: number;
      name: string;
      email?: string | null;
      role?: string | null;
      is_responsible?: boolean;
    }>;
  }>;
  news_items: Array<{
    id: number;
    title: string;
    body: string | null;
    category: string;
    starts_on: string | null;
    ends_on: string | null;
  }>;
  goal_events: Array<{
    id: number;
    goal: string;
    note: string | null;
    achieved_at: string;
    achieved_by: string | null;
  }>;
  delegations: Array<{
    id: number;
    represented_user: string;
    starts_at: string;
    ends_at: string;
    scope: string;
  }>;
  communication_events?: Array<{
    id: number;
    event_type: string;
    title: string;
    body: string | null;
    occurred_at: string;
    customer_case: {
      id: number;
      case_number: string | null;
      customer_display_name: string;
    } | null;
    actor: string | null;
  }>;
};

export type CustomerAddress = {
  street: string | null;
  house_number: string | null;
  address_extra: string | null;
  postal_code: string | null;
  city: string | null;
  country: string | null;
};

export type SectionPayload = Record<
  string,
  string | number | boolean | null | undefined
>;

export type CustomerRecord = {
  id: number;
  customer_number: string | null;
  customer_type: string;
  display_name: string;
  salutation: string | null;
  title: string | null;
  first_name: string | null;
  last_name: string | null;
  company_name: string | null;
  legal_form: string | null;
  vat_id: string | null;
  tax_number: string | null;
  registry_court: string | null;
  registry_number: string | null;
  object_customer_label: string | null;
  primary_email: string | null;
  primary_phone: string | null;
  primary_mobile: string | null;
  preferred_contact_channel: string;
  country: string | null;
  tax_treatment: string | null;
  tax_treatment_note: string | null;
  has_custom_vat?: boolean | null;
  custom_vat_rate?: string | number | null;
  custom_vat_rate_label?: string | null;
  notes: string | null;
  owner_user_id: number | null;
  address: CustomerAddress | null;
  file_sections?: Record<string, SectionPayload>;
  case_count: number;
  updated_at: string | null;
};

export type LeadRecord = {
  id: number;
  lead_number: string | null;
  status: string;
  source: string;
  source_channel: string;
  salutation: string | null;
  title: string | null;
  first_name: string | null;
  last_name: string | null;
  company_name: string | null;
  display_name: string;
  primary_email: string | null;
  primary_phone: string | null;
  primary_mobile: string | null;
  preferred_contact_channel: string;
  country: string | null;
  postal_code: string | null;
  city: string | null;
  project_summary: string | null;
  initial_message: string | null;
  notes: string | null;
  owner_user_id: number | null;
  converted_customer_id: number | null;
  converted_at: string | null;
  updated_at: string | null;
  notes_history: Array<{
    id: number;
    note_type: string;
    body: string;
    source: string;
    created_by: string | null;
    created_at: string;
  }>;
};

export type CustomerCaseDocumentRecord = {
  id: number;
  customer_case_id: number;
  register_code: string;
  document_category: string;
  document_type: string;
  document_status: string;
  title: string;
  note: string | null;
  version_label: string;
  is_current_version: boolean;
  replaces_document_id: number | null;
  has_file: boolean;
  storage_backend: string | null;
  content_sha256: string | null;
  original_filename: string | null;
  content_type: string | null;
  file_size_bytes: number | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
};

export type CaratImportPositionRecord = {
  id: number;
  source_line: number | null;
  position_number: string | null;
  supplier_code: string | null;
  supplier_name: string | null;
  article_code: string | null;
  title: string;
  description: string | null;
  quantity: number | string | null;
  dimensions: Record<string, number | string | null | undefined>;
  selection_status: string;
  selected_at: string | null;
};

export type CaratImportRecord = {
  id: number;
  customer_case_id: number;
  document_id: number;
  parser_version: string;
  source_filename: string | null;
  carat_version: string | null;
  project_number: string | null;
  project_name: string | null;
  customer_name: string | null;
  currency: string | null;
  supplier_count: number;
  position_count: number;
  status: string;
  summary: Record<string, unknown>;
  created_at: string;
  positions: CaratImportPositionRecord[];
};

export type SupplierOrderPositionRecord = {
  id: number;
  position_number: string | null;
  article_code: string | null;
  title: string;
  description: string | null;
  quantity: number | string | null;
  unit: string;
  ordered_net_price: number | string | null;
  ordered_delivery_week: string | null;
  ordered_delivery_date: string | null;
};

export type SupplierOrderRecord = {
  id: number;
  customer_case_id: number;
  supplier_id: number;
  supplier_name: string;
  source_carat_import_id: number | null;
  order_number: string | null;
  title: string;
  status: string;
  ordered_position_count: number;
  created_at: string;
  positions: SupplierOrderPositionRecord[];
};

export type SupplierConfirmationPositionRecord = {
  id: number;
  matched_order_position_id: number | null;
  position_number: string | null;
  article_code: string | null;
  title: string;
  description: string | null;
  quantity: number | string | null;
  unit: string;
  confirmed_net_price: number | string | null;
  confirmed_delivery_week: string | null;
  confirmed_delivery_date: string | null;
  match_status: string;
  severity: "green" | "yellow" | "red";
};

export type SupplierConfirmationExceptionRecord = {
  id: number;
  confirmation_position_id: number | null;
  order_position_id: number | null;
  difference_type: string;
  severity: "yellow" | "red";
  status: string;
  ordered_value: string | null;
  confirmed_value: string | null;
  difference_value: number | string | null;
  message: string;
  resolution_action: string | null;
  resolution_note: string | null;
  resolved_at: string | null;
};

export type SupplierCommunicationRecord = {
  id: number;
  exception_id: number | null;
  communication_type: string;
  status: string;
  recipient_email: string | null;
  subject: string;
  body: string;
  created_at: string;
};

export type SupplierFollowUpRecord = {
  id: number;
  communication_id: number | null;
  title: string;
  status: string;
  due_at: string | null;
};

export type SupplierOrderConfirmationRecord = {
  id: number;
  inbox_item_id: number;
  customer_case_id: number;
  supplier_order_id: number;
  supplier_id: number;
  supplier_name: string;
  document_id: number | null;
  confirmation_number: string | null;
  status: string;
  ordered_position_count: number;
  confirmation_position_count: number;
  matched_position_count: number;
  unmatched_order_position_count: number;
  unmatched_confirmation_position_count: number;
  match_rate: number | string;
  approved_at: string | null;
  created_at: string;
  positions: SupplierConfirmationPositionRecord[];
  exceptions: SupplierConfirmationExceptionRecord[];
  communications: SupplierCommunicationRecord[];
  follow_ups: SupplierFollowUpRecord[];
};

export type CustomerCaseRecord = {
  id: number;
  customer_id: number | null;
  case_number: string | null;
  carat_order_number: string | null;
  case_title: string | null;
  case_status: string;
  customer_display_name: string;
  customer_number: string | null;
  customer_email: string | null;
  status_phase: number | null;
  status_phase_name: string | null;
  notes: Array<{
    id: number;
    customer_case_id: number;
    note_type: string;
    body: string;
    created_by: string | null;
    created_at: string;
  }>;
  sections?: Record<string, SectionPayload>;
  documents?: CustomerCaseDocumentRecord[];
  carat_imports?: CaratImportRecord[];
  supplier_orders?: SupplierOrderRecord[];
  supplier_order_confirmations?: SupplierOrderConfirmationRecord[];
  updated_at: string | null;
};

export type CustomersState = {
  current_user: OverviewState["current_user"];
  users: OverviewState["users"];
  customers: CustomerRecord[];
  leads: LeadRecord[];
  customer_cases: CustomerCaseRecord[];
  status_phases: Array<{
    phase: number;
    name: string;
    is_terminal: boolean;
  }>;
};

export const EMPTY_OVERVIEW_STATE: OverviewState = {
  current_user: {
    primary_user_id: null,
    display_name: "",
    email: "",
    is_admin: false,
    user_ids: [],
    delegated_user_ids: [],
    scope_user_ids: [],
  },
  users: [],
  task_statuses: [
    { code: "new", name: "Neu", is_terminal: false },
    { code: "planned", name: "Geplant", is_terminal: false },
    { code: "in_progress", name: "In Arbeit", is_terminal: false },
    { code: "waiting", name: "Wartet auf Rueckmeldung", is_terminal: false },
    { code: "done", name: "Erledigt", is_terminal: true },
    { code: "cancelled", name: "Abgebrochen", is_terminal: true },
  ],
  customer_cases: [],
  tasks: [],
  emails: [],
  appointments: [],
  news_items: [],
  goal_events: [],
  delegations: [],
  communication_events: [],
};

export const EMPTY_ADMIN_STATE: AdminState = {
  users: [],
  roles: [
    { code: "admin", name: "Admin" },
    { code: "employee", name: "Mitarbeiter" },
    { code: "sales", name: "Verkauf" },
  ],
  company_settings: {},
  integrations: [],
};

export const EMPTY_CUSTOMERS_STATE: CustomersState = {
  current_user: EMPTY_OVERVIEW_STATE.current_user,
  users: [],
  customers: [],
  leads: [],
  customer_cases: [],
  status_phases: [],
};
