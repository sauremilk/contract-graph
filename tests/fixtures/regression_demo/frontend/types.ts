// TypeScript interfaces — regression demo.
// Each interface contains at least one silent bug that mypy+tsc miss.

export interface UserProfile {
  userId: string;
  email: string;
  premiumTier: string;
  displayName: string;
  loginCount: number;
  lastLogin: string;
  bio: string;
}

export interface OrderResponse {
  orderId: string;
  totalAmount: number;
  currency: string;
  status: string;
  createdAt: string;
}

export interface PaymentMethod {
  methodId: string;
  type: string;
  lastFour: string;
}

export interface NotificationSettings {
  pushEnabled: boolean;
  emailEnabled: boolean;
  smsEnabled: boolean;
  quietHoursStart: number;
  quietHoursEnd: number;
}
