import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef } from "react";

import { api } from "../lib/api";

type GoogleCredentialResponse = {
  credential?: string;
};

type GoogleIdentityApi = {
  initialize: (options: {
    client_id: string;
    nonce: string;
    callback: (response: GoogleCredentialResponse) => void;
  }) => void;
  renderButton: (
    element: HTMLElement,
    options: { theme: string; size: string; shape: string; width: number },
  ) => void;
};

declare global {
  interface Window {
    google?: {
      accounts: {
        id: GoogleIdentityApi;
      };
    };
  }
}

export function GoogleLoginButton({
  disabled,
  onCredential,
}: {
  disabled: boolean;
  onCredential: (credential: string) => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const statusQuery = useQuery({
    queryKey: ["google-login-status"],
    queryFn: api.googleLoginStatus,
    staleTime: 300_000,
  });
  const clientId = statusQuery.data?.client_id ?? "";
  const isEnabled = Boolean(statusQuery.data?.enabled && clientId);

  useEffect(() => {
    if (!isEnabled || disabled || !containerRef.current) {
      return;
    }

    function renderButton() {
      if (!window.google || !containerRef.current) {
        return;
      }
      window.google.accounts.id.initialize({
        client_id: clientId,
        nonce: statusQuery.data?.nonce ?? "",
        callback(response) {
          if (response.credential) {
            onCredential(response.credential);
          }
        },
      });
      containerRef.current.replaceChildren();
      window.google.accounts.id.renderButton(containerRef.current, {
        theme: "outline",
        size: "large",
        shape: "rectangular",
        width: 320,
      });
    }

    const existingScript = document.querySelector<HTMLScriptElement>(
      'script[data-google-identity="true"]',
    );
    if (existingScript) {
      if (window.google) {
        renderButton();
      } else {
        existingScript.addEventListener("load", renderButton, { once: true });
      }
      return () => existingScript.removeEventListener("load", renderButton);
    }

    const script = document.createElement("script");
    script.async = true;
    script.defer = true;
    script.dataset.googleIdentity = "true";
    script.src = "https://accounts.google.com/gsi/client";
    script.addEventListener("load", renderButton, { once: true });
    document.head.appendChild(script);
    return () => script.removeEventListener("load", renderButton);
  }, [clientId, disabled, isEnabled, onCredential, statusQuery.data?.nonce]);

  if (statusQuery.isLoading) {
    return <div className="google-login-placeholder">Checking Google login</div>;
  }
  if (!isEnabled) {
    return (
      <button className="secondary-button google-login-placeholder" disabled type="button">
        Google login not configured
      </button>
    );
  }
  return <div aria-label="Google login" className="google-login-container" ref={containerRef} />;
}
