export class APIError extends Error {
  constructor(status, code, message, details = []) {
    super(message);
    this.name = "APIError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

// 토큰은 메모리에만 보관한다. 새로고침하면 로그인 상태를 다시 확인한다.
export function createApiClient(baseUrl = "/api/v1", fetcher = globalThis.fetch) {
  let accessToken = null;
  return {
    setAccessToken(token) { accessToken = token; },
    clearAccessToken() { accessToken = null; },
    async request(path, { method = "GET", body, headers = {} } = {}) {
      const requestHeaders = new Headers(headers);
      if (accessToken) requestHeaders.set("Authorization", `Bearer ${accessToken}`);
      if (body !== undefined) requestHeaders.set("Content-Type", "application/json");
      let response;
      try {
        response = await fetcher(`${baseUrl}${path}`, {
          method, headers: requestHeaders,
          ...(body === undefined ? {} : { body: JSON.stringify(body) }),
        });
      } catch {
        throw new APIError(0, "NETWORK_ERROR", "서버에 연결할 수 없습니다.");
      }
      const payload = response.status === 204 ? null : await response.json().catch(() => null);
      if (!response.ok) {
        if (response.status === 401) accessToken = null;
        throw new APIError(
          response.status,
          payload?.error?.code ?? "HTTP_ERROR",
          payload?.error?.message ?? "요청을 처리할 수 없습니다.",
          payload?.error?.details ?? [],
        );
      }
      return payload;
    },
  };
}

export async function loadSample(name) {
  if (!/^[a-z0-9-]+$/.test(name)) throw new Error("허용되지 않은 샘플 이름입니다.");
  const response = await fetch(`/static/samples/${name}.json`);
  if (!response.ok) throw new Error("샘플 데이터를 불러오지 못했습니다.");
  return response.json();
}

export const api = createApiClient();
