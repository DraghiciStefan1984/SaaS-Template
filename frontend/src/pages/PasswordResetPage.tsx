import { KeyRound } from "lucide-react";
import { FormEvent, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { SuccessState } from "../components/StateBlock";
import { api, getApiErrorMessage } from "../lib/api";

export function PasswordResetPage() {
  const [searchParams] = useSearchParams();
  const uid = searchParams.get("uid") ?? "";
  const token = searchParams.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSuccess("");

    if (!uid || !token) {
      setError("This password reset link is incomplete.");
      return;
    }
    if (password !== confirmation) {
      setError("Passwords do not match.");
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await api.resetPassword({ uid, token, new_password: password });
      setSuccess(response.detail);
      setPassword("");
      setConfirmation("");
    } catch (caughtError) {
      setError(getApiErrorMessage(caughtError, "Password reset failed."));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="auth-layout">
      <section className="auth-panel">
        <Link className="auth-home-link" to="/">
          Home
        </Link>
        <div className="auth-heading">
          <span className="title-icon">
            <KeyRound aria-hidden="true" size={20} />
          </span>
          <div>
            <p className="eyebrow">Recover</p>
            <h1>Reset Password</h1>
          </div>
        </div>

        {success ? (
          <>
            <SuccessState title={success} />
            <Link className="primary-button" to="/login">
              Continue to login
            </Link>
          </>
        ) : (
          <form className="form-grid" onSubmit={handleSubmit}>
            <label>
              New password
              <input
                autoComplete="new-password"
                minLength={8}
                onChange={(event) => setPassword(event.target.value)}
                required
                type="password"
                value={password}
              />
            </label>
            <label>
              Confirm password
              <input
                autoComplete="new-password"
                minLength={8}
                onChange={(event) => setConfirmation(event.target.value)}
                required
                type="password"
                value={confirmation}
              />
            </label>
            {error ? <div className="inline-error">{error}</div> : null}
            <button className="primary-button" disabled={isSubmitting} type="submit">
              {isSubmitting ? "Resetting" : "Reset password"}
            </button>
          </form>
        )}
      </section>
    </main>
  );
}
