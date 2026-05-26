/** Global typings for third-party scripts loaded at runtime. */

declare global {
  interface Window {
    ym?:
      | ((
          counterId: number,
          eventName: string,
          ...args: unknown[]
        ) => void)
      | undefined;
  }
}

export {};
