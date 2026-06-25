import axios from "axios";

// Persistent session: token survives reloads. (localStorage vs sessionStorage
// trade-off documented in the README — persistence chosen for UX.)
const TOKEN_KEY = "mv_access_token";

export const getToken = (): string | null => localStorage.getItem(TOKEN_KEY);
export const setToken = (token: string): void => localStorage.setItem(TOKEN_KEY, token);
export const clearToken = (): void => localStorage.removeItem(TOKEN_KEY);

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:5000",
});

// Attach the bearer token to every request when present.
api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// If a request fails with 401 while we HELD a token, the session expired/was
// revoked: clear it and bounce to login. (We check getToken() so a 401 from a
// login attempt — where no token exists — is left for the form to handle.)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && getToken()) {
      clearToken();
      if (window.location.pathname !== "/login") {
        window.location.assign("/login");
      }
    }
    return Promise.reject(error);
  }
);

export default api;
