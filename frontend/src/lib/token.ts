// Access-токен только в памяти: в localStorage его не кладём, чтобы XSS не мог его украсть.
let accessToken: string | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
}