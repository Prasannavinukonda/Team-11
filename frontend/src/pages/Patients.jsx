import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Layout from "../components/Layout";
import GradeBadge from "../components/GradeBadge";
import { patientsApi } from "../api/endpoints";

export default function Patients() {
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);

  const load = () => {
    setLoading(true);
    patientsApi
      .list()
      .then((res) => setPatients(res.data))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  return (
    <Layout>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Patients</h1>
          <p className="mt-1 text-sm text-slate-500">{patients.length} registered</p>
        </div>
        <button onClick={() => setShowModal(true)} className="btn-primary">
          + Add Patient
        </button>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        {loading ? (
          <p className="p-6 text-sm text-slate-400">Loading…</p>
        ) : patients.length === 0 ? (
          <p className="p-6 text-sm text-slate-400">No patients yet. Add your first patient to get started.</p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-100 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-5 py-3 font-medium">Name</th>
                <th className="px-5 py-3 font-medium">Age / Gender</th>
                <th className="px-5 py-3 font-medium">Screenings</th>
                <th className="px-5 py-3 font-medium">Latest Result</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody>
              {patients.map((p) => (
                <tr key={p.id} className="border-b border-slate-50 last:border-0 hover:bg-slate-50/60">
                  <td className="px-5 py-3.5 font-medium text-slate-800">{p.name}</td>
                  <td className="px-5 py-3.5 text-slate-500">
                    {p.age} · {p.gender}
                  </td>
                  <td className="px-5 py-3.5 text-slate-500">{p.screening_count}</td>
                  <td className="px-5 py-3.5">
                    <GradeBadge grade={p.latest_grade} size="sm" />
                  </td>
                  <td className="px-5 py-3.5 text-right">
                    <Link to={`/patients/${p.id}`} className="text-sm font-medium text-[#028090] hover:underline">
                      View
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showModal && (
        <AddPatientModal
          onClose={() => setShowModal(false)}
          onCreated={() => {
            setShowModal(false);
            load();
          }}
        />
      )}
    </Layout>
  );
}

function AddPatientModal({ onClose, onCreated }) {
  const [form, setForm] = useState({ name: "", age: "", gender: "male", contact: "", diabetes_duration_years: "" });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const update = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await patientsApi.create({
        ...form,
        age: Number(form.age),
        diabetes_duration_years: form.diabetes_duration_years ? Number(form.diabetes_duration_years) : null,
        contact: form.contact || null,
      });
      onCreated();
    } catch (err) {
      setError(err.response?.data?.detail || "Could not add patient.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
        <h2 className="text-lg font-semibold text-slate-900">Add Patient</h2>
        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-700">Full name</label>
            <input required value={form.name} onChange={update("name")} className="input" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-700">Age</label>
              <input required type="number" min={0} max={120} value={form.age} onChange={update("age")} className="input" />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-700">Gender</label>
              <select value={form.gender} onChange={update("gender")} className="input">
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other</option>
              </select>
            </div>
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-700">Contact (optional)</label>
            <input value={form.contact} onChange={update("contact")} className="input" />
          </div>
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-700">Years with diabetes (optional)</label>
            <input type="number" min={0} max={100} value={form.diabetes_duration_years} onChange={update("diabetes_duration_years")} className="input" />
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="rounded-lg px-4 py-2 text-sm font-medium text-slate-500 hover:bg-slate-100">
              Cancel
            </button>
            <button type="submit" disabled={submitting} className="btn-primary">
              {submitting ? "Adding…" : "Add Patient"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
