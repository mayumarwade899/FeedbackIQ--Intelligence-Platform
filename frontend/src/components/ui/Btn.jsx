import Spinner from "./Spinner";
import { COLORS } from "../../utils/constants";

const VARIANTS = {
  primary: { background: COLORS.accent, color: "#0a0c10", border: "none" },
  secondary: { background: "transparent", color: COLORS.textDim, border: `1px solid ${COLORS.border}` },
  danger: { background: "transparent", color: COLORS.danger, border: `1px solid ${COLORS.danger}44` },
  success: { background: "transparent", color: COLORS.success, border: `1px solid ${COLORS.success}44` },
};

export default function Btn({ children, onClick, variant = "primary", small, loading: isLoading, disabled }) {
  const v = VARIANTS[variant] || VARIANTS.primary;

  return (
    <button
      onClick={onClick}
      disabled={disabled || isLoading}
      className={`inline-flex items-center gap-1.5 rounded-md font-semibold transition-opacity duration-150 ${
        small ? "px-3 py-[5px] text-xs" : "px-4 py-2 text-[13px]"
      } ${disabled || isLoading ? "cursor-not-allowed opacity-50" : "cursor-pointer opacity-100"}`}
      style={v}
    >
      {isLoading && <Spinner size={12} />}
      {children}
    </button>
  );
}
