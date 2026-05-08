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
});
