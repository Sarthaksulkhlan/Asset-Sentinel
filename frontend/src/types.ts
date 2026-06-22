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
  complianceStatus: boolean;
  history: string[];
  timeline?: Array<{
    type: 'Login' | 'Logout' | 'Hardware Change' | 'Alert' | 'Application Started' | 'USB Connected' | 'System Restart';
    timestamp: string;
    detail: string;
  }>;
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
