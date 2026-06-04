import { LockKeyhole, UserPlus } from "lucide-react";
import { FormEvent, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";

import { getApiErrorMessage } from "../lib/api";
import { useAuth } from "../lib/auth";
import { LoadingState } from "../components/StateBlock";

type AuthMode = "login" | "register";

export function AuthPage() {
  const navigate = useNavigate();
  const { isAuthenticated, isBootstrapping, login, register } = useAuth();
  const [mode, setMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (isBootstrapping) {
    return (
      <main className="center-layout">
        <LoadingState title="Loading session" />
      </main>
    );
  }

  if (isAuthenticated) {
    return <Navigate replace to="/" />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register({
          email,
          password,
          name,
          organization_name: organizationName,
        });
      }
      navigate("/");
    } catch (caughtError) {
      setError(getApiErrorMessage(caughtError, "Authentication request failed."));
    } finally {
      setIsSubmitting(false);
    }
  }

  const Icon = mode === "login" ? LockKeyhole : UserPlus;

  return (
    <main className="auth-layout">
      <section className="auth-panel">
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
            <p className="eyebrow">{mode === "login" ? "Sign in" : "Create account"}</p>
            <h1>{mode === "login" ? "Workspace Login" : "New Workspace"}</h1>
          </div>
        </div>

        <div className="segmented-control" role="tablist">
          <button
            aria-selected={mode === "login"}
            className={mode === "login" ? "active" : ""}
            onClick={() => setMode("login")}
            role="tab"
            type="button"
          >
            Login
          </button>
          <button
            aria-selected={mode === "register"}
            className={mode === "register" ? "active" : ""}
            onClick={() => setMode("register")}
            role="tab"
            type="button"
          >
            Register
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

          {error ? <div className="inline-error">{error}</div> : null}

          <button className="primary-button" disabled={isSubmitting} type="submit">
            {isSubmitting ? "Submitting" : mode === "login" ? "Login" : "Register"}
          </button>
        </form>
      </section>
    </main>
  );
}
