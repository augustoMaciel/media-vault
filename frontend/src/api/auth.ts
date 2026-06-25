import api, { setToken } from "./client";
import type { AuthResponse, User } from "../types";

// Raw backend shapes (snake_case) — mapped to camelCase domain types below.
interface RawUser {
  id: number;
  email: string;
  created_at: string;
}
interface RawAuth {
  access_token: string;
  user: RawUser;
}

const mapUser = (u: RawUser): User => ({
  id: u.id,
  email: u.email,
  createdAt: u.created_at,
});

const mapAuth = (a: RawAuth): AuthResponse => ({
  accessToken: a.access_token,
  user: mapUser(a.user),
});

export async function register(email: string, password: string): Promise<AuthResponse> {
  const { data } = await api.post<RawAuth>("/auth/register", { email, password });
  const auth = mapAuth(data);
  setToken(auth.accessToken); // backend auto-logs-in on register
  return auth;
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  const { data } = await api.post<RawAuth>("/auth/login", { email, password });
  const auth = mapAuth(data);
  setToken(auth.accessToken);
  return auth;
}

export async function me(): Promise<User> {
  const { data } = await api.get<RawUser>("/auth/me");
  return mapUser(data);
}
