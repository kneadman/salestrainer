import { request } from "./apiClient";

describe("request", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("uses a product-safe network error message", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("network down"));

    await expect(request("/api/health")).rejects.toMatchObject({
      message: "Сервис временно недоступен. Попробуйте обновить страницу или обратиться к администратору.",
    });
  });

  it("maps backend validation errors to a readable message", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            code: "validation_error",
            message: "Request validation failed.",
            details: [{ loc: ["body", "manager_message"], msg: "Field required", type: "missing" }],
          },
        }),
        { status: 422, headers: { "content-type": "application/json" } },
      ),
    );

    await expect(request("/api/sessions/session-1/messages")).rejects.toMatchObject({
      message: "Проверьте заполнение полей и попробуйте снова.",
      code: "validation_error",
      status: 422,
    });
  });

  it("does not expose CSRF wording from backend details", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            code: "forbidden",
            message: "Missing or invalid CSRF token.",
          },
        }),
        { status: 403, headers: { "content-type": "application/json" } },
      ),
    );

    await expect(request("/api/sessions")).rejects.toMatchObject({
      message: "Не удалось подтвердить действие. Обновите страницу и попробуйте снова.",
    });
  });
});
