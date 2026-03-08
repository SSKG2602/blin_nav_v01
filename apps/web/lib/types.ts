export type NavigationState = {
  status: string;
  step: string;
  url?: string;
  updatedAt?: string;
};

export type CartState = {
  itemCount: number;
  subtotal?: string;
  currency?: string;
  updatedAt?: string;
};

export type VoiceServerMessage = {
  type?: string;
  sessionId?: string;
  agentResponse?: string;
  transcript?: string;
  navigationState?: Partial<NavigationState>;
  cart?: Partial<CartState>;
};
