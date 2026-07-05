import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import Layout from "../components/Layout";
import GradeBadge from "../components/GradeBadge";
import { patientsApi, screeningsApi } from "../api/endpoints";

export default function PatientDetail() {
  const { id } = useParams();
  const [patient, setPatient] = useState(null);
  const [screenings, setScreenings] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([patientsApi.get(id), screeningsApi.list(id)])
      .then(([pRes, sRes]) => {
        setPatient(pRes.data);
        setScreenings(sRes.data);
      })
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <Layout>
        <p className="text-sm text-slate-400">Loading…</p>
      </Layout>
    );
  }

  if (!patient) {
    return (
      <Layout>
        <p className="text-sm text-slate-400">Patient not found.</p>
      </Layout>
    );
  }

  return (
    <Layout>
      <Link to="/patients" className="text-sm text-slate-500 hover:text-slate-700">
        ← Back to patients
      </Link>

      <div className="mt-3 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">{patient.name}</h1>
          <p className="mt-1 text-sm text-slate-500">
            {patient.age} years · {patient.gender}
            {patient.diabetes_duration_years != null && ` · ${patient.diabetes_duration_years}y with diabetes`}
          </p>
        </div>
        <Link to={`/screening/new?patient=${patient.id}`} className="btn-primary">
          + New Screening
        </Link>
      </div>

      <h2 className="mb-3 mt-8 text-sm font-medium text-slate-700">Screening History ({screenings.length})</h2>

      {screenings.length === 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-400">
          No screenings recorded yet.
        </div>
      ) : (
        <div className="space-y-3">
          {screenings.map((s) => (
            <div key={s.id} className="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-4">
              <div>
                <GradeBadge grade={s.grade} />
                <p className="mt-1.5 text-xs text-slate-400">
                  {new Date(s.created_at).toLocaleString()} · confidence {Math.round(s.confidence * 100)}%
                </p>
                {s.notes && <p className="mt-1 text-sm text-slate-600">{s.notes}</p>}
              </div>
              {s.referral_recommended && (
                <span className="rounded-full bg-red-50 px-3 py-1 text-xs font-medium text-red-700">
                  Referral recommended
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </Layout>
  );
}
