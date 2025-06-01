export const getApiKey = () => typeof window !== "undefined"
  ? localStorage.getItem("api_key") ?? ""
  : "";
