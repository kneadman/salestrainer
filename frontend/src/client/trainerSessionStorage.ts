const LEGACY_STORAGE_KEY = "salestrainer.currentSessionId";
const STORAGE_KEY_PREFIX = "salestrainer.currentSessionId.";

export function getTrainerSessionStorageKey(userId: string): string {
  /** Scope restored runtime sessions to the authenticated user in this browser. */
  return `${STORAGE_KEY_PREFIX}${userId}`;
}

export function getStoredTrainerSessionId(userId: string): string | null {
  /** Read only the user-scoped trainer session id to avoid cross-account restore. */
  return localStorage.getItem(getTrainerSessionStorageKey(userId));
}

export function storeTrainerSessionId(userId: string, sessionId: string): void {
  /** Persist the current runtime session id for this authenticated user. */
  localStorage.setItem(getTrainerSessionStorageKey(userId), sessionId);
  clearLegacyTrainerSessionId();
}

export function clearStoredTrainerSessionId(userId: string): void {
  /** Remove the user-scoped trainer session id after invalid restore or failed creation. */
  localStorage.removeItem(getTrainerSessionStorageKey(userId));
}

export function clearLegacyTrainerSessionId(): void {
  /** Drop the pre-namespaced key so older state cannot leak across account switches. */
  localStorage.removeItem(LEGACY_STORAGE_KEY);
}

export function clearTrainerSessionRestoreState(userId?: string): void {
  /** Clear restore state that could otherwise survive logout in the same browser. */
  if (userId) {
    clearStoredTrainerSessionId(userId);
  }
  clearLegacyTrainerSessionId();
}
