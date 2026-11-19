export const environment = {
  production: false,
  apiUrl: (window as any)?.__OPSPILOT_CONFIG__?.apiUrl || (
    typeof window !== 'undefined' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1'
      ? '/api/v1'
      : 'http://localhost:8000/api/v1'
  )
};
