/// <reference path="../testing-library-react.d.ts" />
import React from "react";
import { render, screen } from "@testing-library/react";
import Home from "./page";

describe("Home", () => {
  it("renders meeting intelligence title and links to ingest and contacts", () => {
    render(<Home />);
    expect(screen.getByRole("heading", { name: /truthOS — Meeting intelligence/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Meeting ingestion/i })).toHaveAttribute("href", "/ingest");
    expect(screen.getByRole("link", { name: /Contact intelligence/i })).toHaveAttribute("href", "/contacts");
  });
});
