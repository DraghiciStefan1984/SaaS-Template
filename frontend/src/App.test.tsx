import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "./App";

describe("App", () => {
  it("renders the unauthenticated login screen", () => {
    localStorage.clear();
    render(<App />);

    expect(screen.getByRole("heading", { name: "Workspace Login" })).toBeInTheDocument();
  });
});
