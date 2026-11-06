import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("../app/static/js/api-client.js", import.meta.url), "utf8");
const { createApiClient, APIError } = await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);

test("JSON request and in-memory bearer token use the common contract", async () => {
  let captured;
  const api = createApiClient("/api/v1", async (url, options) => {
    captured = { url, options };
    return new Response(JSON.stringify({ id: 1001 }), { status: 201 });
  });
  api.setAccessToken("temporary-test-token");
  assert.deepEqual(await api.request("/reservations", { method: "POST", body: { seat_ids: [101] } }), { id: 1001 });
  assert.equal(captured.url, "/api/v1/reservations");
  assert.equal(captured.options.headers.get("Authorization"), "Bearer temporary-test-token");
  assert.equal(captured.options.headers.get("Content-Type"), "application/json");
  assert.deepEqual(JSON.parse(captured.options.body), { seat_ids: [101] });
});

test("an expired session clears the token before the next request", async () => {
  const seen = [];
  const api = createApiClient("/api/v1", async (_url, options) => {
    seen.push(options.headers.get("Authorization"));
    return new Response(JSON.stringify({ error: { code: "TOKEN_EXPIRED", message: "로그인 만료", details: [] } }), { status: 401 });
  });
  api.setAccessToken("old-token");
  await assert.rejects(api.request("/users/me"), (error) => error instanceof APIError && error.code === "TOKEN_EXPIRED");
  await assert.rejects(api.request("/users/me"));
  assert.deepEqual(seen, ["Bearer old-token", null]);
});

test("business conflicts preserve the error code and details", async () => {
  const details = [{ field: "seat_ids", message: "좌석 확인" }];
  const api = createApiClient("/api/v1", async () => new Response(JSON.stringify({ error: { code: "SEAT_CONFLICT", message: "좌석 충돌", details } }), { status: 409 }));
  await assert.rejects(api.request("/reservations"), (error) => {
    assert.equal(error.status, 409);
    assert.equal(error.code, "SEAT_CONFLICT");
    assert.deepEqual(error.details, details);
    return true;
  });
});

test("network errors do not expose the original exception", async () => {
  const api = createApiClient("/api/v1", async () => { throw new Error("internal secret"); });
  await assert.rejects(api.request("/runs"), (error) => error.code === "NETWORK_ERROR" && !error.message.includes("secret"));
});

test("non-JSON server errors still use the common error type", async () => {
  const api = createApiClient("/api/v1", async () => new Response("<html>error</html>", { status: 503 }));
  await assert.rejects(api.request("/runs"), (error) => error instanceof APIError && error.status === 503 && error.code === "HTTP_ERROR");
});
