import api from "./client";

export const authApi = {
  register: (payload) => api.post("/auth/register", payload),
  login: (email, password) => {
    const form = new URLSearchParams();
    form.append("username", email);
    form.append("password", password);
    return api.post("/auth/login", form, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
  },
  me: () => api.get("/auth/me"),
};

export const patientsApi = {
  list: () => api.get("/patients"),
  get: (id) => api.get(`/patients/${id}`),
  create: (payload) => api.post("/patients", payload),
  remove: (id) => api.delete(`/patients/${id}`),
};

export const screeningsApi = {
  list: (patientId) => api.get("/screenings", { params: patientId ? { patient_id: patientId } : {} }),
  get: (id) => api.get(`/screenings/${id}`),
  create: (patientId, file, notes) => {
    const form = new FormData();
    form.append("patient_id", patientId);
    form.append("image", file);
    if (notes) form.append("notes", notes);
    return api.post("/screenings", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
};

export const dashboardApi = {
  stats: () => api.get("/dashboard/stats"),
};
