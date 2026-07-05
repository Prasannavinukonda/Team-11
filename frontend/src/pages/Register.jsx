import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { AuthShell, Field } from "./Login";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
    role: "health_worker",
    facility_name: "",
  });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const update = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await register(form);
      navigate("/");
    } catch (err) {
      setError(err.response?.data?.detail || "Could not create your account.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthShell>
      <h1 className="text-2xl font-semibold text-slate-900">Create your account</h1>
      <p className="mt-1 text-sm text-slate-500">Start screening patients in minutes.</p>

      <form onSubmit={handleSubmit} className="mt-8 space-y-4">
        <Field label="Full name">
          <input required value={form.full_name} onChange={update("full_name")} className="input" placeholder="Asha Sharma" />
        </Field>
        <Field label="Email">
          <input type="email" required value={form.email} onChange={update("email")} className="input" placeholder="you@clinic.in" />
        </Field>
        <Field label="Password">
          <input type="password" required minLength={8} value={form.password} onChange={update("password")} className="input" placeholder="At least 8 characters" />
        </Field>
        <Field label="Role">
          <select value={form.role} onChange={update("role")} className="input">
            <option value="health_worker">Health Worker</option>
            <option value="doctor">Doctor</option>
            <option value="admin">Admin</option>
          </select>
        </Field>
        <Field label="Facility (optional)">
          <input value={form.facility_name} onChange={update("facility_name")} className="input" placeholder="Primary Health Centre, ..." />
        </Field>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button type="submit" disabled={submitting} className="btn-primary w-full">
          {submitting ? "Creating account…" : "Create account"}
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-slate-500">
        Already have an account?{" "}
        <Link to="/login" className="font-medium text-[#028090] hover:underline">
          Sign in
        </Link>
      </p>
    </AuthShell>
  );
}
