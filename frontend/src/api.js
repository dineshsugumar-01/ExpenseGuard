const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:8000";

export const getAuthToken = () => {
  return localStorage.getItem("expenseguard_token") || "";
};

export const setAuthToken = (token) => {
  if (token) {
    localStorage.setItem("expenseguard_token", token);
  } else {
    localStorage.removeItem("expenseguard_token");
  }
};

export const apiFetch = async (endpoint, options = {}) => {
  const token = getAuthToken();
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  const url = endpoint.startsWith("http") ? endpoint : `${API_BASE}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    // Unauthorized
    // In dev, let user browse or redirect to login
  }

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `API Error ${response.status}`);
  }

  const contentType = response.headers.get("content-type");
  if (contentType && contentType.includes("application/json")) {
    return await response.json();
  }
  return await response.text();
};

export const api = {
  // Overview
  getOverview: (from, to) => {
    const query = new URLSearchParams();
    if (from) query.append("from", from);
    if (to) query.append("to", to);
    return apiFetch(`/api/overview?${query.toString()}`);
  },

  // Transactions
  getTransactions: (params = {}) => {
    const query = new URLSearchParams();
    Object.keys(params).forEach((key) => {
      if (params[key] !== undefined && params[key] !== null) {
        query.append(key, params[key]);
      }
    });
    return apiFetch(`/api/transactions?${query.toString()}`);
  },

  getTransactionDetail: (groupId) => {
    return apiFetch(`/api/transactions/${groupId}`);
  },

  // Flags / Review
  getFlags: (status = "open", page = 1) => {
    return apiFetch(`/api/flags?status=${status}&page=${page}`);
  },

  submitReview: (flagId, decision, note = "") => {
    return apiFetch(`/api/flags/${flagId}/review`, {
      method: "POST",
      body: JSON.stringify({ decision, note }),
    });
  },

  // Analytics
  getSpendOverTime: (interval = "day") => {
    return apiFetch(`/api/analytics/spend-over-time?interval=${interval}`);
  },

  getSpendByCategory: () => {
    return apiFetch("/api/analytics/spend-by-category");
  },

  getRiskDistribution: () => {
    return apiFetch("/api/analytics/risk-distribution");
  },

  getTopRisk: () => {
    return apiFetch("/api/analytics/top-risk");
  },

  // Rules
  getRules: () => {
    return apiFetch("/api/rules");
  },

  updateRule: (ruleId, data) => {
    return apiFetch(`/api/rules/${ruleId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  // Models
  getModels: () => {
    return apiFetch("/api/models");
  },

  triggerRetrain: () => {
    return apiFetch("/api/models/retrain", {
      method: "POST",
    });
  },

  // Alerts
  getAlerts: () => {
    return apiFetch("/api/alerts");
  },

  // Claims
  submitClaim: (formData) => {
    const token = getAuthToken();
    return fetch(`${API_BASE}/api/claims`, {
      method: "POST",
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: formData,
    }).then((res) => res.json());
  },

  // Auth
  login: async (username, password) => {
    const formData = new URLSearchParams();
    formData.append("username", username);
    formData.append("password", password);
    const response = await fetch(`${API_BASE}/api/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: formData,
    });
    if (!response.ok) throw new Error("Invalid credentials");
    const data = await response.json();
    setAuthToken(data.access_token);
    return data;
  },

  getMe: () => {
    return apiFetch("/api/auth/me");
  },
};
