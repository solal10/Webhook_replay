import { render, screen, fireEvent } from "@testing-library/react";
import { useRouter } from "next/navigation";
import LoginPage from "@/app/login/page";

jest.mock("next/navigation", () => ({
  useRouter: jest.fn(),
}));

describe("LoginPage", () => {
  const mockPush = jest.fn();

  beforeEach(() => {
    (useRouter as jest.Mock).mockReturnValue({
      push: mockPush,
    });
  });

  it("saves API key and redirects to dashboard", () => {
    render(<LoginPage />);

    const input = screen.getByLabelText("API Key");
    const button = screen.getByText("Save & Continue");

    fireEvent.change(input, { target: { value: "test-api-key" } });
    fireEvent.click(button);

    expect(localStorage.getItem("api_key")).toBe("test-api-key");
    expect(mockPush).toHaveBeenCalledWith("/dashboard");
  });
});
