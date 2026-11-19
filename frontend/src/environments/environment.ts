export const environment = {
  production: false,
  apiUrl: (window as any)?.__OPSPILOT_CONFIG__?.apiUrl || 'http://localhost:8000/api/v1'
};

