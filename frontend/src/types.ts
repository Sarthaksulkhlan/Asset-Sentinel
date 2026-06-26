export interface Asset {
  hostname: string;
  status: 'Online' | 'Idle' | 'Overload' | 'Offline';
  employee: string;
  department?: string;
  deviceId?: string;
  assetId?: string;
  ipAddress: string;
  os: string;
  ram: string;
  ramUsage?: string;
  diskUsage?: string;
  networkUsage?: string;
  uptime?: string;
  biosSerial: string;
  biosVersion?: string;
  motherboardSerial?: string;
  uuid?: string;
  macAddress?: string;
  lastLogin?: string;
  lastLogout?: string;
  loginDuration?: string;
  loginsToday?: number;
  currentUser?: string;
  currentWebsite: string;
  activeApplication?: string;
  activeWindow?: string;
  lastActiveTime?: string;
  lastExecutedProcess?: string;
  threatScore?: number;
  alerts?: string[];
  hardwareChanges?: string[];
  unauthorizedSoftware?: string[];
  usbActivity?: string[];
  failedLoginAttempts?: number;
  alertStatus: 'nominal' | 'warning' | 'critical';
  location: string;
  lastReflash: string;
  cpuModel: string;
  cpuUsage?: string;
  lastSeen?: string;
  lastSeenHuman?: string;
  memoryUsedGb?: number;
  memoryAvailableGb?: number;
  loginsThisWeek?: number;
  lastSuccessfulLogin?: string;
  lastFailedLogin?: string;
  applicationHistory?: Array<{
    application?: string;
    application_name?: string;
    window_title?: string;
    process_path?: string;
    timestamp?: string;
  }>;
  complianceStatus: boolean;
  history: string[];
  timeline?: Array<{
    type: 'Login' | 'Logout' | 'Hardware Change' | 'RAM Change' | 'Motherboard Change' | 'Alert' | 'Application Started' | 'Application Closed' | 'Device Online' | 'Device Offline' | 'USB Connected' | 'System Restart';
    timestamp: string;
    detail: string;
    description?: string;
    severity?: string;
  }>;
}

export interface AssetDetailPayload {
  asset: Asset;
  sessions: Array<Record<string, any>>;
  alerts: Array<Record<string, any>>;
  application_timeline: Array<{
    application?: string;
    application_name?: string;
    window_title?: string;
    process_path?: string;
    timestamp?: string;
  }>;
  hardware_changes: Array<Record<string, any>>;
  timeline: Array<{
    type?: Asset["timeline"] extends Array<infer T> ? T extends { type: infer U } ? U : string : string;
    event_type?: string;
    timestamp?: string;
    detail?: string;
    description?: string;
    severity?: string;
  }>;
  charts: {
    cpu_usage_history: Array<{ timestamp?: string; value?: number | string }>;
    ram_usage_history: Array<{ timestamp?: string; value?: number | string }>;
    login_frequency: Array<{ label: string; value: number }>;
    application_usage: Array<{ label: string; value: number }>;
    alert_trend: Array<{ label: string; value: number }>;
  };
}

export interface SecurityFeedItem {
  timestamp: string;
  node: string;
  message: string;
  type: 'info' | 'warning' | 'critical';
}

export interface KPIStats {
  totalAssets: number;
  onlineDevices: number;
  offlineDevices: number;
  activeUsers: number;
  criticalAlerts: number;
  securityIncidents: number;
}
