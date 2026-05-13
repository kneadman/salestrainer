import { Suspense, lazy, useEffect, useState } from "react";
import { ApiError, getMe, logout as logoutRequest } from "./api";
import { AdminApp } from "./admin/AdminApp";
import { ClientApp } from "./client/ClientApp";
import { LoginPage } from "./components/LoginPage";
import { DemoPage } from "./demo/DemoPage";
import type { AuthUser } from "./types";

const POST_LOGIN_REDIRECT_KEY = "salestrainer.postLoginRedirect";
const LandingPage = lazy(() => import("./components/LandingPage").then((module) => ({ default: module.LandingPage })));

function getErrorMessage(error: unknown): string {
  /** Normalize app-level API errors for display. */
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Неожиданная ошибка.";
}

function getCurrentPath(): string {
  /** Read the current browser path for the lightweight path-based router. */
  return window.location.pathname;
}

export default function App() {
  /** Render public, login, client cabinet, and internal admin routes. */
  const [path, setPath] = useState(getCurrentPath);
  const [authBootstrapping, setAuthBootstrapping] = useState(true);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [logoutBusy, setLogoutBusy] = useState(false);

  const navigate = (nextPath: string, replace = false) => {
    /** Push or replace one browser history entry and update local route state. */
    if (window.location.pathname === nextPath) {
      setPath(nextPath);
      return;
    }
    if (replace) {
      window.history.replaceState({}, "", nextPath);
    } else {
      window.history.pushState({}, "", nextPath);
    }
    setPath(nextPath);
  };

  useEffect(() => {
    /** Keep route state synchronized with browser back/forward navigation. */
    const handlePopState = () => setPath(getCurrentPath());
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  useEffect(() => {
    /** Bootstrap auth once so protected routes can decide redirect/access states. */
    if (getCurrentPath() === "/demo") {
      setAuthBootstrapping(false);
      return;
    }

    const bootstrapAuth = async () => {
      try {
        const response = await getMe();
        setUser(response.user);
        setAuthError(null);
      } catch (meError) {
        if (meError instanceof ApiError && meError.status === 401) {
          setUser(null);
          setAuthError(null);
        } else {
          setUser(null);
          setAuthError(getErrorMessage(meError));
        }
      } finally {
        setAuthBootstrapping(false);
      }
    };

    void bootstrapAuth();
  }, []);

  useEffect(() => {
    /** Enforce protected route redirects without adding a routing dependency. */
    if (authBootstrapping) {
      return;
    }
    if (path === "/") {
      return;
    }
    if (path === "/demo") {
      return;
    }
    if ((path.startsWith("/admin") || path.startsWith("/app")) && !user) {
      sessionStorage.setItem(POST_LOGIN_REDIRECT_KEY, path);
      navigate("/login", true);
      return;
    }
    if (path === "/login" && user) {
      const storedRedirect = sessionStorage.getItem(POST_LOGIN_REDIRECT_KEY);
      sessionStorage.removeItem(POST_LOGIN_REDIRECT_KEY);
      navigate(storedRedirect?.startsWith("/admin") || storedRedirect?.startsWith("/app") ? storedRedirect : "/app", true);
      return;
    }
    if (path.startsWith("/admin") || path.startsWith("/app")) {
      return;
    }
    if (path !== "/login") {
      navigate(user ? "/app" : "/login", true);
    }
  }, [authBootstrapping, path, user]);

  const handleAuthenticated = (authenticatedUser: AuthUser) => {
    /** Store the authenticated user and honor protected-route redirects after login. */
    setUser(authenticatedUser);
    setAuthError(null);
    const storedRedirect = sessionStorage.getItem(POST_LOGIN_REDIRECT_KEY);
    sessionStorage.removeItem(POST_LOGIN_REDIRECT_KEY);
    navigate(storedRedirect?.startsWith("/admin") || storedRedirect?.startsWith("/app") ? storedRedirect : "/app", true);
  };

  const handleLogout = async () => {
    /** Logout locally even if server revocation fails, avoiding stale protected UI. */
    if (logoutBusy) {
      return;
    }
    setLogoutBusy(true);
    try {
      await logoutRequest();
    } catch {
      // A failed logout request should not keep stale authenticated UI around.
    } finally {
      setUser(null);
      setLogoutBusy(false);
      navigate("/login", true);
    }
  };

  if (path === "/demo") {
    return <DemoPage onNavigate={navigate} />;
  }

  if (authBootstrapping) {
    return <div className="app-shell">Загрузка...</div>;
  }

  if (path === "/") {
    return (
      <Suspense fallback={<div className="app-shell">Загрузка...</div>}>
        <LandingPage authenticated={Boolean(user)} />
      </Suspense>
    );
  }

  if (path === "/login" || !user) {
    return (
      <>
        {authError ? (
          <div className="auth-error-strip">
            <div className="error-banner">{authError}</div>
          </div>
        ) : null}
        <LoginPage onAuthenticated={handleAuthenticated} />
      </>
    );
  }

  if (path.startsWith("/admin")) {
    return <AdminApp user={user} path={path} onNavigate={navigate} onLogout={handleLogout} />;
  }

  return <ClientApp user={user} path={path} onNavigate={navigate} onLogout={handleLogout} onUserUpdated={setUser} />;
}
