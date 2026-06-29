type UnauthorizedHandler = () => Promise<string | null> | string | null;
type TokenProvider = () => Promise<string | null> | string | null;

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

let tokenProvider: TokenProvider | null = null;
let unauthorizedHandler: UnauthorizedHandler | null = null;

export const configureApiClient = (provider: TokenProvider, onUnauthorized: UnauthorizedHandler) => {
  tokenProvider = provider;
  unauthorizedHandler = onUnauthorized;
};

export const apiFetch = async (path: string, options: RequestInit = {}) => {
  const token = tokenProvider ? await tokenProvider() : null;
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const requestInit = {
    ...options,
    cache: options.cache || "no-store",
    headers,
  } satisfies RequestInit;
  const response = await fetch(`${API_BASE_URL}${path}`, requestInit);

  if (response.status === 401) {
    const refreshedToken = unauthorizedHandler ? await unauthorizedHandler() : null;
    if (refreshedToken && refreshedToken !== token) {
      const retryHeaders = new Headers(headers);
      retryHeaders.set("Authorization", `Bearer ${refreshedToken}`);
      return fetch(`${API_BASE_URL}${path}`, {
        ...options,
        headers: retryHeaders,
      });
    }
  }

  return response;
};

export const authFetch = async (path: string, options: RequestInit = {}) => {
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }
  return fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });
};
