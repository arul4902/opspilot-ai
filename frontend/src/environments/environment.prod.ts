export const environment = {
  production: true,
  apiUrl: (window as any)?.__OPSPILOT_CONFIG__?.apiUrl || '/api/v1'
};

