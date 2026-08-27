import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { activityRangeLabel, activityRanges } from "../lib/dashboard";
import { NotFoundPage } from "./NotFoundPage";

describe("Release UI", () => {
  it("exposes the complete dashboard activity range model", () => {
    expect(activityRanges).toEqual([1, 6, 24, 72, 168]);
    expect(activityRangeLabel(1)).toBe("last hour");
    expect(activityRangeLabel(72)).toBe("last 72 hours");
    expect(activityRangeLabel(168)).toBe("last 7 days");
  });

  it("renders an intentional 404 with a safe recovery path", () => {
    const markup = renderToStaticMarkup(
      <MemoryRouter>
        <NotFoundPage />
      </MemoryRouter>,
    );

    expect(markup).toContain("404");
    expect(markup).toContain("No monitoring data was changed");
    expect(markup).toContain('href="/"');
  });
});
