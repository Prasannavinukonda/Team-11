import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import Layout from "../components/Layout";
import GradeBadge from "../components/GradeBadge";
import { patientsApi, screeningsApi } from "../api/endpoints";

export default function NewScreening() {
  const [searchParams] = useSearchParams();
  const preselectedPatient = searchParams.get("patient");

  const [patients, setPatients] = useState([]);
  const [patientId, setPatientId] = useState(preselectedPatient || "");
  const [notes, setNotes] = useState("");
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    patientsApi.list().then((res) => setPatients(res.data));
  }, []);

  const handleFile = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setFile(f);
    setResult(null);
    setError("");
    setPreview(URL.createObjectURL(f));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!patientId || !file) return;
    setError("");
    setSubmitting(true);
    setResult(null);
    try {
      const res = await screeningsApi.create(patientId, file, notes);
      setResult(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Could not process this image.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Layout>
      <h1 className="text-2xl font-semibold text-slate-900">New Screening</h1>
      <p className="mt-1 text-sm text-slate-500">
        Upload a retinal fundus photograph to get an instant DR severity grade.
      </p>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <form onSubmit={handleSubmit} className="space-y-4 rounded-xl border border-slate-200 bg-white p-6">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-700">Patient</label>
            <select required value={patientId} onChange={(e) => setPatientId(e.target.value)} className="input">
              <option value="" disabled>
                Select a patient…
              </option>
              {patients.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.age}, {p.gender})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-700">Fundus photograph</label>
            <div className="flex items-center justify-center rounded-lg border-2 border-dashed border-slate-200 p-6">
              {preview ? (
                <img src={preview} alt="Fundus preview" className="h-40 w-40 rounded-lg object-cover" />
              ) : (
                <p className="text-sm text-slate-400">JPEG or PNG, up to 10MB</p>
              )}
            </div>
            <input required type="file" accept="image/jpeg,image/png" onChange={handleFile} className="mt-3 w-full text-sm text-slate-500 file:mr-3 file:rounded-lg file:border-0 file:bg-[#028090] file:px-3 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-[#026e77]" />
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-700">Notes (optional)</label>
            <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} className="input" placeholder="Any clinical observations…" />
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <button type="submit" disabled={submitting || !patientId || !file} className="btn-primary w-full">
            {submitting ? "Analyzing…" : "Run Analysis"}
          </button>
        </form>

        <div className="rounded-xl border border-slate-200 bg-white p-6">
          <p className="text-sm font-medium text-slate-700">Result</p>
          {!result && !submitting && (
            <p className="mt-4 text-sm text-slate-400">Upload an image and run analysis to see the severity grade here.</p>
          )}
          {submitting && <p className="mt-4 text-sm text-slate-400">Running EfficientNet-B4 inference…</p>}
          {result && (
            <div className="mt-4 space-y-4">
              <GradeBadge grade={result.grade} />
              <p className="text-sm text-slate-500">Confidence: {Math.round(result.confidence * 100)}%</p>

              {result.referral_recommended && (
                <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
                  ⚠ Referral to an ophthalmologist is recommended.
                </div>
              )}

              {result.model_mode === "demo" ? (
                <div className="rounded-lg bg-amber-50 p-3 text-xs text-amber-700">
                  This prediction used the demo model (pretrained backbone, untrained head) —
                  it is not clinically validated. Swap in fine-tuned weights per the README to
                  get real predictions.
                </div>
              ) : (
                <div className="rounded-lg bg-blue-50 p-3 text-xs text-blue-700">
                  Trained model
                  {result.model_val_f1 != null && ` — val F1 ${result.model_val_f1.toFixed(2)}, epoch ${result.model_epoch}`}
                  . This is an early checkpoint; treat results as provisional and always confirm
                  with a specialist.
                </div>
              )}

              <div>
                <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-400">Class probabilities</p>
                <div className="space-y-1.5">
                  {["No DR", "Mild", "Moderate", "Severe", "Proliferative"].map((label, i) => (
                    <div key={label} className="flex items-center gap-2">
                      <span className="w-24 text-xs text-slate-500">{label}</span>
                      <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
                        <div
                          className="h-full rounded-full bg-[#028090]"
                          style={{ width: `${Math.round(result.class_probabilities[i] * 100)}%` }}
                        />
                      </div>
                      <span className="w-10 text-right text-xs text-slate-500">
                        {Math.round(result.class_probabilities[i] * 100)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
