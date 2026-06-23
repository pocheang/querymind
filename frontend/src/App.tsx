import { lazy, Suspense, useEffect, useMemo, useState, type ReactNode } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { authApi } from "@/lib/api";
import { applyTheme, getSavedTheme, nextTheme, saveTheme, type ThemeMode } from "@/lib/theme";
import type { AuthUser } from "@/types/api";

const LoginPage = lazy(() => import("@/pages/LoginPage").then(({ LoginPage }) => ({ default: LoginPage })));
const ChatPage = lazy(() => import("@/pages/ChatPage").then(({ ChatPage }) => ({ default: ChatPage })));
const AdminPage = lazy(() => import("@/pages/AdminPage").then(({ AdminPage }) => ({ default: AdminPage })));
const AnalyticsPage = lazy(() => import("@/pages/AnalyticsPage").then(({ AnalyticsPage }) => ({ default: AnalyticsPage })));
const ArchitecturePage = lazy(() => import("@/pages/ArchitecturePage").then(({ ArchitecturePage }) => ({ default: ArchitecturePage })));
const ChangePasswordPage = lazy(() => import("@/pages/ChangePasswordPage").then(({ ChangePasswordPage }) => ({ default: ChangePasswordPage })));
const ProfilePage = lazy(() => import("@/pages/ProfilePage").then(({ ProfilePage }) => ({ default: ProfilePage })));
const ForgotPasswordPage = lazy(() => import("@/pages/ForgotPasswordPage").then(({ ForgotPasswordPage }) => ({ default: ForgotPasswordPage })));
const NotFoundPage = lazy(() => import("@/pages/NotFoundPage").then(({ NotFoundPage }) => ({ default: NotFoundPage })));
const LandingPage = lazy(() => import("@/pages/LandingPage").then(({ LandingPage }) => ({ default: LandingPage })));

function RouteFallback() {
  return <div className="app-loading" aria-live="polite" />;
}

function Protected({
  user,
  authReady,
  children,
}: {
  user: AuthUser | null;
  authReady: boolean;
  children: ReactNode;
}) {
  if (!authReady) return null;
  if (!user) return <Navigate to="/app/login" replace />;
  return <>{children}</>;
}

export function App() {
  const { t, i18n } = useTranslation();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [theme, setTheme] = useState<ThemeMode>(getSavedTheme());
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    applyTheme(theme);
    saveTheme(theme);
  }, [theme]);

  useEffect(() => {
    authApi
      .me()
      .then(setUser)
      .catch(() => {
        authApi.setToken("");
        setUser(null);
      })
      .finally(() => setAuthReady(true));
  }, []);

  const themeLabel = useMemo(() => {
    return theme === "dark" ? t('theme.dark') : t('theme.light');
  }, [theme, t, i18n.language]);

  const logout = async () => {
    await authApi.logout();
    authApi.setToken("");
    setUser(null);
    navigate("/app/login");
  };

  const loginSuccess = (nextUser: AuthUser) => {
    setUser(nextUser);
  };

  return (
    <Suspense fallback={<RouteFallback />}>
      <Routes>
        <Route
          path="/app/login"
          element={
            user ? (
              <Navigate to="/app" replace />
            ) : (
              <LoginPage
                onLogin={loginSuccess}
                themeLabel={themeLabel}
                onThemeToggle={() => setTheme((prev) => nextTheme(prev))}
              />
            )
          }
        />
        <Route
          path="/app/forgot-password"
          element={
            user ? (
              <Navigate to="/app" replace />
            ) : (
              <ForgotPasswordPage
                themeLabel={themeLabel}
                onThemeToggle={() => setTheme((prev) => nextTheme(prev))}
              />
            )
          }
        />
        <Route
          path="/app"
          element={
            <Protected user={user} authReady={authReady}>
              <ChatPage
                user={user}
                onLogout={logout}
                themeLabel={themeLabel}
                onThemeToggle={() => setTheme((prev) => nextTheme(prev))}
              />
            </Protected>
          }
        />
        <Route
          path="/app/admin"
          element={
            <Protected user={user} authReady={authReady}>
              <AdminPage
                user={user}
                onLogout={logout}
                themeLabel={themeLabel}
                onThemeToggle={() => setTheme((prev) => nextTheme(prev))}
              />
            </Protected>
          }
        />
        <Route
          path="/app/analytics"
          element={
            <Protected user={user} authReady={authReady}>
              <AnalyticsPage
                user={user}
                onLogout={logout}
                themeLabel={themeLabel}
                onThemeToggle={() => setTheme((prev) => nextTheme(prev))}
              />
            </Protected>
          }
        />
        <Route
          path="/app/change-password"
          element={
            <Protected user={user} authReady={authReady}>
              <ChangePasswordPage themeLabel={themeLabel} onThemeToggle={() => setTheme((prev) => nextTheme(prev))} />
            </Protected>
          }
        />
        <Route
          path="/app/profile"
          element={
            <Protected user={user} authReady={authReady}>
              <ProfilePage user={user} />
            </Protected>
          }
        />
        <Route
          path="/app/architecture"
          element={
            <ArchitecturePage
              isLoggedIn={!!user}
              themeLabel={themeLabel}
              onThemeToggle={() => setTheme((prev) => nextTheme(prev))}
            />
          }
        />
        <Route
          path="/"
          element={
            <LandingPage
              isLoggedIn={!!user}
              themeLabel={themeLabel}
              onThemeToggle={() => setTheme((prev) => nextTheme(prev))}
            />
          }
        />
        <Route path="*" element={<NotFoundPage pathname={location.pathname} />} />
      </Routes>
    </Suspense>
  );
}
