import { render } from "@testing-library/react";
import { useRouter } from "next/navigation";
import DashboardPage from "@/app/dashboard/page";
import { getApiKey } from "@/lib/auth";

jest.mock("next/navigation", () => ({
  useRouter: jest.fn(),
}));

jest.mock("@/lib/auth", () => ({
  getApiKey: jest.fn(),
}));

describe("DashboardPage", () => {
  const mockPush = jest.fn();

  beforeEach(() => {
    (useRouter as jest.Mock).mockReturnValue({
      push: mockPush,
    });
    mockPush.mockClear();
    (getApiKey as jest.Mock).mockClear();
  });

  it("redirects to login if no API key", () => {
    (getApiKey as jest.Mock).mockReturnValue(null);
    render(<DashboardPage />);
    expect(mockPush).toHaveBeenCalledWith("/login");
  });

  it("does not redirect if API key exists", () => {
    (getApiKey as jest.Mock).mockReturnValue("test-key");
    render(<DashboardPage />);
    expect(mockPush).not.toHaveBeenCalled();
  });
});
