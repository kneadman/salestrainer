import { Suspense, lazy, useCallback, useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ApiError, getMe, logout as logoutRequest } from "./api";
import { AdminApp } from "./admin/AdminApp";
import { ClientApp } from "./client/ClientApp";
import { clearLegacyTrainerSessionId, clearTrainerSessionRestoreState } from "./client/trainerSessionStorage";
import { LoginPage } from "./components/LoginPage";
import { DemoPage } from "./demo/DemoPage";
import PrivacyPage from "./landing/pages/PrivacyPage";
import CookiesPage from "./landing/pages/CookiesPage";
import { useYandexMetrika } from "./hooks/useYandexMetrika";
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

export default function App() {
  /** Render public, login, client cabinet, and internal admin routes. */
  const location = useLocation();
  const routerNavigate = useNavigate();
  const path = `${location.pathname}${location.search}`;
  const routePathname = location.pathname;
  const [bootstrapPathname] = useState(routePathname);
  const [authBootstrapping, setAuthBootstrapping] = useState(true);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [logoutBusy, setLogoutBusy] = useState(false);

  useYandexMetrika(routePathname);

  const navigate = useCallback(
    (nextPath: string, replace = false) => {
      /** Delegate browser history updates to react-router while preserving the local callback contract. */
      routerNavigate(nextPath, { replace });
    },
    [routerNavigate],
  );

  useEffect(() => {
    /** Bootstrap auth once so protected routes can decide redirect/access states. */
    if (bootstrapPathname === "/demo") {
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
  }, [bootstrapPathname]);

  useEffect(() => {
    /** Enforce protected route redirects while route matching stays in feature modules. */
    if (authBootstrapping) {
      return;
    }
    if (routePathname === "/") {
      return;
    }
    if (routePathname === "/demo") {
      return;
    }
    if ((routePathname.startsWith("/admin") || routePathname.startsWith("/app")) && !user) {
      sessionStorage.setItem(POST_LOGIN_REDIRECT_KEY, path);
      navigate("/login", true);
      return;
    }
    if (routePathname === "/login" && user) {
      const storedRedirect = sessionStorage.getItem(POST_LOGIN_REDIRECT_KEY);
      sessionStorage.removeItem(POST_LOGIN_REDIRECT_KEY);
      navigate(storedRedirect?.startsWith("/admin") || storedRedirect?.startsWith("/app") ? storedRedirect : "/app", true);
      return;
    }
    if (routePathname.startsWith("/admin") || routePathname.startsWith("/app")) {
      return;
    }
    if (routePathname !== "/login") {
      navigate(user ? "/app" : "/login", true);
    }
  }, [authBootstrapping, navigate, path, routePathname, user]);

  const handleAuthenticated = (authenticatedUser: AuthUser) => {
    /** Store the authenticated user and honor protected-route redirects after login. */
    clearLegacyTrainerSessionId();
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
      clearTrainerSessionRestoreState(user?.id);
      setUser(null);
      setLogoutBusy(false);
      navigate("/login", true);
    }
  };

  if (routePathname === "/demo") {
    return <DemoPage onNavigate={navigate} />;
  }

  if (routePathname === "/privacy") {
    return <PrivacyPage />;
  }

  if (routePathname === "/cookies") {
    return <CookiesPage />;
  }

  if (authBootstrapping) {
    return <div className="app-shell">Загрузка...</div>;
  }

  if (routePathname === "/") {
    return (
      <Suspense fallback={<div className="app-shell">Загрузка...</div>}>
        <LandingPage authenticated={Boolean(user)} />
      </Suspense>
    );
  }

  if (routePathname === "/login" || !user) {
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

  if (routePathname.startsWith("/admin")) {
    return <AdminApp user={user} path={path} onNavigate={navigate} onLogout={handleLogout} />;
  }

  return <ClientApp user={user} path={path} onNavigate={navigate} onLogout={handleLogout} onUserUpdated={setUser} />;
}
