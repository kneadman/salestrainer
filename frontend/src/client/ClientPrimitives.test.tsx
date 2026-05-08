import { render, screen } from "@testing-library/react";
import { statusLabel } from "../labels";
import { SimpleBars } from "./components/ClientPrimitives";

describe("SimpleBars", () => {
  it("formats technical keys with the supplied label formatter", () => {
    render(<SimpleBars values={{ active: 2, finished: 5 }} labelFormatter={statusLabel} />);

    expect(screen.getByText("Активна")).toBeInTheDocument();
    expect(screen.getByText("Завершена")).toBeInTheDocument();
    expect(screen.queryByText("active")).not.toBeInTheDocument();
    expect(screen.queryByText("finished")).not.toBeInTheDocument();
  });
});
