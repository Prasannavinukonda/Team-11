const GRADE_STYLES = {
  0: { bg: "bg-emerald-50", text: "text-emerald-700", dot: "bg-emerald-500", label: "No DR" },
  1: { bg: "bg-lime-50", text: "text-lime-700", dot: "bg-lime-500", label: "Mild" },
  2: { bg: "bg-amber-50", text: "text-amber-700", dot: "bg-amber-500", label: "Moderate" },
  3: { bg: "bg-orange-50", text: "text-orange-700", dot: "bg-orange-500", label: "Severe" },
  4: { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500", label: "Proliferative" },
};

export default function GradeBadge({ grade, size = "md" }) {
  if (grade === null || grade === undefined) {
    return <span className="text-sm text-slate-400">No screenings yet</span>;
  }
  const style = GRADE_STYLES[grade] ?? GRADE_STYLES[0];
  const padding = size === "sm" ? "px-2 py-0.5 text-xs" : "px-3 py-1 text-sm";

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full font-medium ${style.bg} ${style.text} ${padding}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
      Grade {grade} · {style.label}
    </span>
  );
}
