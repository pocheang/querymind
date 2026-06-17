import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

export function NotFoundPage({ pathname }: { pathname: string }) {
  const { t } = useTranslation();

  return (
    <div className="not-found">
      <h1>404</h1>
      <p>{t("pages.notFound.message", { pathname })}</p>
      <div className="top-actions">
        <Link className="secondary link-btn" to="/app">
          {t("pages.notFound.backToApp")}
        </Link>
        <Link className="secondary link-btn" to="/app/login">
          {t("pages.notFound.login")}
        </Link>
      </div>
    </div>
  );
}
