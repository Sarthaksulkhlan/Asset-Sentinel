export interface Asset {
  hostname: string;
  status: 'Online' | 'Idle' | 'Overload' | 'Offline';
  employee: string;
  ipAddress: string;
  os: string;
  ram: string;
  biosSerial: string;
  lastLogin: string;
  currentWebsite: string;
  alertStatus: 'nominal' | 'warning' | 'critical';
  location: string;
  lastReflash: string;
  cpuModel: string;
  complianceStatus: boolean;
  history: string[];
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
