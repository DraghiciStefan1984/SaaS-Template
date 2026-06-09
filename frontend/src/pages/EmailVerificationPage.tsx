import { MailCheck } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { ErrorState, LoadingState, SuccessState } from "../components/StateBlock";
import { api, getApiErrorMessage } from "../lib/api";
import { useAuth } from "../lib/auth";

export function EmailVerificationPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const { isAuthenticated } = useAuth();
  const verificationRequest = useRef<ReturnType<typeof api.verifyEmail> | null>(null);
  const [state, setState] = useState<"loading" | "success" | "error">("loading");
  const [detail, setDetail] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function verify() {
      if (!token) {
        setState("error");
        setDetail("This email verification link is incomplete.");
        return;
      }
      try {
        verificationRequest.current ??= api.verifyEmail(token);
        const response = await verificationRequest.current;
        if (!cancelled) {
          setState("success");
          setDetail(response.detail);
        }
      } catch (error) {
        if (!cancelled) {
          setState("error");
          setDetail(getApiErrorMessage(error, "Email verification failed."));
        }
      }
    }

    void verify();
    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <main className="auth-layout">
      <section className="auth-panel">
        <div className="auth-heading">
          <span className="title-icon">
            <MailCheck aria-hidden="true" size={20} />
          </span>
          <div>
            <p className="eyebrow">Account</p>
            <h1>Verify Email</h1>
          </div>
        </div>
        {state === "loading" ? <LoadingState title="Verifying email address" /> : null}
        {state === "success" ? <SuccessState detail={detail} title="Email verified" /> : null}
        {state === "error" ? <ErrorState detail={detail} title="Verification failed" /> : null}
        <Link className="primary-button" to={isAuthenticated ? "/dashboard/account" : "/login"}>
          Continue
        </Link>
      </section>
    </main>
  );
}
