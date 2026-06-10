import { KeyRound, LockKeyhole, UserPlus } from "lucide-react";
import { FormEvent, useState } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";

import { LoadingState, SuccessState } from "../components/StateBlock";
import { GoogleLoginButton } from "../components/GoogleLoginButton";
import { api, getApiErrorMessage } from "../lib/api";
import { useAuth } from "../lib/auth";

type AuthMode = "login" | "register" | "recover";

export function AuthPage({ initialMode }: { initialMode: AuthMode }) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { isAuthenticated, isBootstrapping, login, loginWithGoogle, register } = useAuth();
  const [mode, setMode] = useState<AuthMode>(initialMode);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const requestedReturnTo = searchParams.get("next") ?? "";
  const returnTo =
    requestedReturnTo.startsWith("/") && !requestedReturnTo.startsWith("//")
      ? requestedReturnTo
      : "/dashboard";

  if (isBootstrapping) {
    return (
      <main className="center-layout">
        <LoadingState title="Loading session" />
      </main>
    );
  }

  if (isAuthenticated) {
    return <Navigate replace to={returnTo} />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSuccess("");
    setIsSubmitting(true);
    try {
      if (mode === "recover") {
        const response = await api.recoverPassword(email);
        setSuccess(response.detail);
      } else if (mode === "login") {
        await login(email, password);
        navigate(returnTo);
      } else {
        await register({
          email,
          password,
          name,
          organization_name: organizationName,
        });
        navigate(returnTo);
      }
    } catch (caughtError) {
      setError(getApiErrorMessage(caughtError, "Authentication request failed."));
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleModeChange(nextMode: AuthMode) {
    setError("");
    setSuccess("");
    setMode(nextMode);
    navigate(
      nextMode === "login"
        ? "/login"
        : nextMode === "register"
          ? "/register"
          : "/recover-password",
    );
  }

  async function handleGoogleCredential(credential: string) {
    setError("");
    setSuccess("");
    setIsSubmitting(true);
    try {
      await loginWithGoogle(credential);
      navigate(returnTo);
    } catch (caughtError) {
      setError(getApiErrorMessage(caughtError, "Google login failed."));
    } finally {
      setIsSubmitting(false);
    }
  }

  const Icon = mode === "login" ? LockKeyhole : mode === "register" ? UserPlus : KeyRound;

  return (
    <main className="auth-layout">
      <section className="auth-panel">
        <Link className="auth-home-link" to="/">
          Home
        </Link>
        <div className="brand-row">
          <div className="brand-mark">SC</div>
          <div>
            <strong>SaaS Core</strong>
            <span>Template</span>
          </div>
        </div>

        <div className="auth-heading">
          <span className="title-icon">
            <Icon aria-hidden="true" size={20} />
          </span>
          <div>
            <p className="eyebrow">
              {mode === "login" ? "Sign in" : mode === "register" ? "Create account" : "Recover"}
            </p>
            <h1>
              {mode === "login"
                ? "Workspace Login"
                : mode === "register"
                  ? "New Workspace"
                  : "Recover Password"}
            </h1>
          </div>
        </div>

        <div className="segmented-control" role="tablist">
          <button
            aria-selected={mode === "login"}
            className={mode === "login" ? "active" : ""}
            onClick={() => handleModeChange("login")}
            role="tab"
            type="button"
          >
            Login
          </button>
          <button
            aria-selected={mode === "register"}
            className={mode === "register" ? "active" : ""}
            onClick={() => handleModeChange("register")}
            role="tab"
            type="button"
          >
            Register
          </button>
          <button
            aria-selected={mode === "recover"}
            className={mode === "recover" ? "active" : ""}
            onClick={() => handleModeChange("recover")}
            role="tab"
            type="button"
          >
            Recover
          </button>
        </div>

        <form className="form-grid" onSubmit={handleSubmit}>
          {mode === "register" ? (
            <>
              <label>
                Name
                <input
                  autoComplete="name"
                  onChange={(event) => setName(event.target.value)}
                  type="text"
                  value={name}
                />
              </label>
              <label>
                Organization
                <input
                  autoComplete="organization"
                  onChange={(event) => setOrganizationName(event.target.value)}
                  type="text"
                  value={organizationName}
                />
              </label>
            </>
          ) : null}

          <label>
            Email
            <input
              autoComplete="email"
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
            />
          </label>
          {mode !== "recover" ? (
            <label>
              Password
              <input
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                minLength={8}
                onChange={(event) => setPassword(event.target.value)}
                required
                type="password"
                value={password}
              />
            </label>
          ) : null}

          {mode === "register" ? (
            <label className="checkbox-control">
              <input
                checked={acceptedTerms}
                onChange={(event) => setAcceptedTerms(event.target.checked)}
                required
                type="checkbox"
              />
              <span>
                I accept the <Link to="/terms">terms and privacy rules</Link>.
              </span>
            </label>
          ) : null}

          {error ? <div className="inline-error">{error}</div> : null}
          {success ? <SuccessState title={success} /> : null}

          <button className="primary-button" disabled={isSubmitting} type="submit">
            {isSubmitting
              ? "Submitting"
              : mode === "login"
                ? "Login"
                : mode === "register"
                  ? "Register"
                  : "Send recovery email"}
          </button>
        </form>

        {mode !== "recover" ? (
          <div className="social-login-section">
            <span>or</span>
            <GoogleLoginButton
              disabled={isSubmitting}
              onCredential={handleGoogleCredential}
            />
          </div>
        ) : null}

        <div className="auth-footer">
          {mode === "login" ? (
            <Link to="/recover-password">Forgot password?</Link>
          ) : (
            <Link to="/login">Already registered?</Link>
          )}
        </div>
      </section>
    </main>
  );
}
